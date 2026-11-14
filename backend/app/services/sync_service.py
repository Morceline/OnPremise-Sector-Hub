"""
services/sync_service.py
--------------------------
Sincronização INCREMENTAL entre as fontes autorizadas (pastas, páginas web,
regras tácitas) e o índice vetorial (Qdrant).

Decisões de projeto (ver docs/SEQUENCIA_LOTE_01.md):

1. Periódica, não em tempo real. Eventos de arquivo são pouco confiáveis
   entre Windows, volumes do Docker e pastas de rede, e fontes online não
   avisam mudanças. Um único mecanismo periódico serve a todas as fontes e
   agrupa as mudanças (menos disputa de CPU com o Ollama).

2. Incremental. Compara data+tamanho (barato) e só abre o arquivo se mudou;
   só reindexa se o TEXTO mudou (hash). Arquivo salvo de novo sem alterar o
   conteúdo não custa embeddings.

3. Sem lixo. Ao reindexar um arquivo, grava os trechos novos e SÓ DEPOIS
   apaga os antigos (nunca fica sem nada se algo falhar no meio). Arquivo
   apagado, movido para uma pasta bloqueada ou removido da configuração tem
   os trechos removidos do índice — bloquear uma pasta realmente "esquece".

4. Proteção contra "pasta fora do ar". Se a pasta raiz está temporariamente
   inacessível (compartilhamento de rede desligado, disco desmontado), o
   que foi indexado dela é PRESERVADO — não confundimos "sumiu" com
   "está indisponível agora".

5. O chat tem prioridade (ActivityGate): a sincronização espera enquanto
   alguém está conversando, para não deixar a resposta lenta.
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List, Optional, Set

import httpx

from app.core.activity import ActivityGate
from app.core.config import Settings
from app.models.config import SectorConfig
from app.services.catalog import Catalog, CatalogItem, utcnow_iso
from app.services.document import SafeDocumentReader
from app.services.rag_engine import IndexOutcome, RAGEngine
from app.services.web_scraper import fetch_url_content, is_url_allowed

logger = logging.getLogger(__name__)

TACIT_SOURCE = "Regras Tácitas do Gestor"


class SyncAlreadyRunning(Exception):
    """Já existe uma sincronização em andamento."""


class EmbeddingUnavailable(Exception):
    """O modelo de embeddings (Ollama) não respondeu — aborta o ciclo."""


@dataclass
class SyncReport:
    started_at: str = ""
    finished_at: str = ""
    indexed: int = 0               # fontes (re)indexadas neste ciclo
    unchanged: int = 0             # fontes sem mudança
    removed: int = 0               # fontes removidas do índice
    without_text: int = 0          # arquivos sem texto legível (ex.: PDF escaneado)
    errors: int = 0                # fontes com erro neste ciclo
    preserved_unavailable: int = 0  # preservadas porque a pasta raiz estava fora do ar
    aborted: bool = False
    message: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def _age_minutes(iso_value: Optional[str]) -> float:
    if not iso_value:
        return float("inf")
    try:
        moment = datetime.fromisoformat(iso_value)
    except ValueError:
        return float("inf")
    return (datetime.now(timezone.utc) - moment).total_seconds() / 60


def _under_any(path: Path, roots: List[Path]) -> bool:
    return any(root == path or root in path.parents for root in roots)


class SyncService:
    def __init__(
        self,
        rag_engine: RAGEngine,
        catalog: Catalog,
        http_client: httpx.AsyncClient,
        settings: Settings,
        gate: ActivityGate,
    ):
        self.rag = rag_engine
        self.catalog = catalog
        self.http_client = http_client
        self.settings = settings
        self.gate = gate
        self._lock = asyncio.Lock()
        self.running = False

    # ------------------------------------------------------------ API

    async def run(self, config: SectorConfig, force_web: bool = False) -> SyncReport:
        """Executa UM ciclo de sincronização para a configuração dada."""
        if self._lock.locked():
            raise SyncAlreadyRunning()

        async with self._lock:
            self.running = True
            report = SyncReport(started_at=utcnow_iso())
            self.catalog.set_meta("last_sync_started", report.started_at)
            try:
                current: Set[str] = set()
                unavailable_roots = await self._sync_files(config, report, current)
                await self._sync_web(config, report, current, force_web)
                await self._sync_tacit(config, report, current)
                # Só poda se o ciclo foi até o fim: com `current` incompleto
                # (ciclo abortado) apagaríamos fontes que nem chegamos a olhar.
                await self._prune_removed(current, unavailable_roots, report)
            except EmbeddingUnavailable as exc:
                report.aborted = True
                report.message = str(exc)
                logger.warning("Sincronização interrompida: %s", exc)
            except Exception as exc:
                self.catalog.set_meta("last_sync_error", f"Erro inesperado: {exc}")
                raise
            finally:
                report.finished_at = utcnow_iso()
                self.running = False

            if report.aborted:
                self.catalog.set_meta("last_sync_error", report.message)
            else:
                self.catalog.set_meta("last_sync_finished", report.finished_at)
                self.catalog.set_meta("last_sync_error", "")
            self.catalog.set_meta("last_sync_summary", json.dumps(report.to_dict()))
            return report

    def status(self) -> dict:
        """Resumo para o painel — sem caminhos de arquivo."""
        return {
            "running": self.running,
            "interval_minutes": self.settings.sync_interval_minutes,
            "last_started": self.catalog.get_meta("last_sync_started"),
            "last_finished": self.catalog.get_meta("last_sync_finished"),
            "last_error": self.catalog.get_meta("last_sync_error") or None,
            "last_summary": self.catalog.get_meta_json("last_sync_summary"),
            "items": self.catalog.stats(),
        }

    async def run_periodic(self, get_config: Callable[[], Optional[SectorConfig]]) -> None:
        """Laço de fundo: roda um ciclo a cada `sync_interval_minutes`."""
        await asyncio.sleep(self.settings.sync_startup_delay_seconds)
        while True:
            try:
                config = get_config()
                if config is not None:
                    report = await self.run(config)
                    logger.info("Sincronização: %s", report.to_dict())
            except SyncAlreadyRunning:
                pass
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Falha no ciclo de sincronização")
            await asyncio.sleep(max(60, self.settings.sync_interval_minutes * 60))

    # --------------------------------------------------------- arquivos

    async def _sync_files(self, config: SectorConfig, report: SyncReport, current: Set[str]) -> List[Path]:
        reader = SafeDocumentReader(
            allowed_paths=config.allowed_local_paths,
            blocked_paths=config.blocked_local_paths,
            max_file_size_mb=self.settings.max_file_size_mb,
        )
        unavailable_roots = [root for root in reader.allowed_paths if not root.exists()]
        paths = await asyncio.to_thread(lambda: list(reader.iter_safe_files()))

        # `current` completo ANTES de processar: se o ciclo for abortado no
        # meio, a poda nem roda — e, rodando, enxerga todas as fontes.
        current.update(str(p) for p in paths)

        for path in paths:
            await self.gate.wait_idle()
            await self._sync_one_file(reader, path, report)
        return unavailable_roots

    async def _sync_one_file(self, reader: SafeDocumentReader, path: Path, report: SyncReport) -> None:
        source = str(path)
        existing = self.catalog.get(source)
        now = utcnow_iso()

        try:
            stat = await asyncio.to_thread(path.stat)
        except OSError as exc:
            self._save_error(existing, CatalogItem(source, "file", path.name, str(path.parent), path.suffix.lower()),
                             f"Não foi possível acessar o arquivo: {exc}")
            report.errors += 1
            return

        base = CatalogItem(
            source=source, kind="file", name=path.name, folder=str(path.parent),
            ext=path.suffix.lower(), size=stat.st_size, mtime=stat.st_mtime,
        )

        # 1) Nada mudou desde a última vez?
        if existing and existing.size == stat.st_size and existing.mtime == stat.st_mtime:
            if existing.status in ("ok", "sem_texto"):
                self.catalog.touch(source, now)
                report.unchanged += 1
                return
            if existing.status == "erro" and _age_minutes(existing.last_checked_at) < self.settings.sync_error_retry_hours * 60:
                report.unchanged += 1  # erro recente: só tenta de novo depois do intervalo
                return

        # 2) Acima do limite de tamanho: não lê, registra o motivo.
        if not reader.is_within_size_limit(path):
            await self.rag.delete_source(source)
            self.catalog.upsert(base.with_changes(
                status="erro", last_checked_at=now,
                error=f"Arquivo acima do limite de {self.settings.max_file_size_mb} MB",
            ))
            report.errors += 1
            return

        # 3) Lê o texto (em thread: PDF grande não pode travar o chat).
        try:
            text = await asyncio.to_thread(reader.extract_text, path, True)
        except Exception as exc:
            logger.warning("Falha ao ler %s: %s", path, exc)
            self._save_error(existing, base, f"Falha ao ler o arquivo: {exc}", checked_at=now)
            report.errors += 1
            return

        if not text.strip():
            await self.rag.delete_source(source)  # o arquivo pode ter ficado vazio
            self.catalog.upsert(base.with_changes(
                status="sem_texto", indexed_at=now, last_checked_at=now,
                error="Sem texto legível (PDF escaneado ou imagem?)",
            ))
            report.without_text += 1
            return

        # 4) Mudou data/tamanho mas o TEXTO é o mesmo? Não gasta embeddings.
        content_hash = _sha256(text)
        if existing and existing.status == "ok" and existing.content_hash == content_hash:
            self.catalog.upsert(existing.with_changes(size=stat.st_size, mtime=stat.st_mtime, last_checked_at=now))
            report.unchanged += 1
            return

        # 5) Indexa a versão nova; só então apaga os trechos antigos.
        outcome = await self.rag.index_document(source, text, throttle=self.gate.wait_idle)
        await self._finish_indexing(existing, base, outcome, content_hash, now, report)

    # -------------------------------------------------------------- web

    async def _sync_web(self, config: SectorConfig, report: SyncReport, current: Set[str], force: bool) -> None:
        urls = [str(u) for u in config.allowed_web_urls]
        current.update(urls)

        for url in urls:
            if not is_url_allowed(url, urls):
                continue
            await self.gate.wait_idle()

            existing = self.catalog.get(url)
            recently_checked = _age_minutes(existing.last_checked_at) < self.settings.web_refresh_minutes if existing else False
            if existing and existing.status == "ok" and recently_checked and not force:
                report.unchanged += 1
                continue

            now = utcnow_iso()
            base = CatalogItem(source=url, kind="web", name=url)
            content = await fetch_url_content(
                url, self.http_client,
                max_chars=self.settings.max_web_fetch_chars,
                timeout=self.settings.embedding_timeout_seconds,
            )
            if not content:
                # Site fora do ar: mantém o que já estava indexado.
                self._save_error(existing, base, "Não foi possível ler a página agora.", checked_at=now)
                report.errors += 1
                continue

            content_hash = _sha256(content)
            if existing and existing.status == "ok" and existing.content_hash == content_hash:
                self.catalog.touch(url, now)
                report.unchanged += 1
                continue

            outcome = await self.rag.index_document(url, content, throttle=self.gate.wait_idle)
            await self._finish_indexing(existing, base, outcome, content_hash, now, report)

    # ------------------------------------------------------------ tácito

    async def _sync_tacit(self, config: SectorConfig, report: SyncReport, current: Set[str]) -> None:
        text = (config.tacit_knowledge or "").strip()
        if not text:
            return  # se existia antes, a poda remove

        current.add(TACIT_SOURCE)
        existing = self.catalog.get(TACIT_SOURCE)
        content_hash = _sha256(text)
        now = utcnow_iso()

        if existing and existing.status == "ok" and existing.content_hash == content_hash:
            self.catalog.touch(TACIT_SOURCE, now)
            report.unchanged += 1
            return

        base = CatalogItem(source=TACIT_SOURCE, kind="tacit", name=TACIT_SOURCE)
        outcome = await self.rag.index_document(TACIT_SOURCE, text, throttle=self.gate.wait_idle)
        await self._finish_indexing(existing, base, outcome, content_hash, now, report)

    # ------------------------------------------------------------- poda

    async def _prune_removed(self, current: Set[str], unavailable_roots: List[Path], report: SyncReport) -> None:
        for source in sorted(self.catalog.sources() - current):
            item = self.catalog.get(source)
            if item and item.kind == "file" and _under_any(Path(source), unavailable_roots):
                # A pasta raiz está fora do ar AGORA: preserva, não apaga.
                report.preserved_unavailable += 1
                continue
            await self.rag.delete_source(source)
            self.catalog.delete(source)
            report.removed += 1

    # ---------------------------------------------------------- helpers

    async def _finish_indexing(
        self,
        existing: Optional[CatalogItem],
        base: CatalogItem,
        outcome: IndexOutcome,
        content_hash: str,
        now: str,
        report: SyncReport,
    ) -> None:
        if outcome.failed_chunks > 0 or not outcome.chunk_ids:
            # Embeddings falharam (Ollama fora do ar?). NÃO apagamos a versão
            # antiga e NÃO gravamos data/tamanho novos — assim o próximo
            # ciclo tenta de novo — e interrompemos o ciclo.
            self._save_error(existing, base.with_changes(size=0, mtime=0.0),
                             "Falha ao gerar embeddings (Ollama indisponível?)", checked_at=now, keep_stat=True)
            report.errors += 1
            raise EmbeddingUnavailable("Não foi possível gerar embeddings. Verifique se o Ollama está em execução.")

        await self.rag.prune_source(base.source, outcome.chunk_ids)
        self.catalog.upsert(base.with_changes(
            content_hash=content_hash, chunk_count=len(outcome.chunk_ids),
            indexed_at=now, last_checked_at=now, status="ok", error="",
        ))
        report.indexed += 1

    def _save_error(
        self,
        existing: Optional[CatalogItem],
        base: CatalogItem,
        message: str,
        checked_at: Optional[str] = None,
        keep_stat: bool = False,
    ) -> None:
        """Registra o erro preservando o que já estava indexado (se havia)."""
        if existing:
            changes = {"status": "erro", "error": message[:300], "last_checked_at": checked_at or utcnow_iso()}
            if not keep_stat:
                changes.update(size=base.size, mtime=base.mtime)
            item = existing.with_changes(**changes)
        else:
            item = base.with_changes(status="erro", error=message[:300], last_checked_at=checked_at or utcnow_iso())
        self.catalog.upsert(item)


async def run_in_background(service: SyncService, config: SectorConfig, force_web: bool = False) -> None:
    """Executa um ciclo sem deixar exceção escapar (usado por rotas/BackgroundTasks)."""
    try:
        await service.run(config, force_web=force_web)
    except SyncAlreadyRunning:
        logger.info("Sincronização já em andamento; pedido ignorado.")
    except Exception:
        logger.exception("Falha na sincronização em segundo plano")
