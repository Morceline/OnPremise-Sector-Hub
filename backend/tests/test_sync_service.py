"""
tests/test_sync_service.py
-----------------------------
Testa a sincronização incremental contra um Qdrant EM MEMÓRIA de verdade
(qdrant-client em modo local) — não um dublê. Assim os testes provam o
comportamento que importa: trechos antigos somem, novos ficam, nada é
apagado por engano. Só o modelo de embeddings (Ollama) é substituído por
uma função determinística.
"""

import asyncio
import hashlib
import os
from pathlib import Path

import httpx
import pytest
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from app.core.activity import ActivityGate
from app.core.config import Settings
from app.models.config import SectorConfig
from app.services import sync_service as sync_module
from app.services.catalog import Catalog
from app.services.rag_engine import RAGEngine
from app.services.sync_service import TACIT_SOURCE, SyncAlreadyRunning, SyncService

DIM = 4


def _vector(text: str):
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return [b / 255 + 0.01 for b in digest[:DIM]]


class Embed:
    """Controle do 'Ollama' falso: conta chamadas e permite simular queda."""

    def __init__(self):
        self.calls = 0
        self.fail = False


@pytest.fixture
def embed(monkeypatch):
    ctl = Embed()

    async def fake_embedding(self, text):
        ctl.calls += 1
        return [] if ctl.fail else _vector(text)

    monkeypatch.setattr(RAGEngine, "_get_embedding", fake_embedding)
    return ctl


@pytest.fixture
def qdrant(monkeypatch):
    client = QdrantClient(":memory:")
    monkeypatch.setattr("app.services.rag_engine.QdrantClient", lambda **kwargs: client)
    return client


def _settings(**overrides) -> Settings:
    base = dict(embedding_dimension=DIM, sync_startup_delay_seconds=0, web_refresh_minutes=60, max_file_size_mb=1)
    base.update(overrides)
    return Settings(**base)


@pytest.fixture
def make_service(qdrant, embed, tmp_path):
    def _make(**settings_overrides):
        settings = _settings(**settings_overrides)
        engine = RAGEngine(settings=settings, http_client=httpx.AsyncClient())
        catalog = Catalog(str(tmp_path / "catalog.db"))
        gate = ActivityGate(poll_seconds=0.01, max_wait_seconds=0.1)
        return SyncService(engine, catalog, httpx.AsyncClient(), settings, gate)

    return _make


@pytest.fixture
def service(make_service):
    return make_service()


@pytest.fixture
def docs(tmp_path) -> Path:
    pasta = (tmp_path / "docs").resolve()
    pasta.mkdir()
    return pasta


def cfg(allowed=(), blocked=(), urls=(), tacit=None) -> SectorConfig:
    return SectorConfig(
        sector_name="Teste",
        niche_persona="neutra",
        allowed_local_paths=[str(p) for p in allowed],
        blocked_local_paths=[str(p) for p in blocked],
        allowed_web_urls=list(urls),
        tacit_knowledge=tacit,
    )


def texts_of(qdrant, source: str):
    records, _ = qdrant.scroll(
        "sector_knowledge",
        scroll_filter=qm.Filter(must=[qm.FieldCondition(key="source", match=qm.MatchValue(value=source))]),
        limit=1000,
        with_payload=True,
    )
    return sorted(r.payload["text"] for r in records)


# ---------------------------------------------------------------- arquivos


async def test_primeira_sincronizacao_indexa_e_registra_no_catalogo(service, docs, qdrant):
    arquivo = docs / "ferias.txt"
    arquivo.write_text("Pedido de férias com 30 dias de antecedência.", encoding="utf-8")

    report = await service.run(cfg([docs]))

    assert (report.indexed, report.errors, report.aborted) == (1, 0, False)
    item = service.catalog.get(str(arquivo))
    assert item.status == "ok" and item.kind == "file" and item.name == "ferias.txt"
    assert item.chunk_count == len(texts_of(qdrant, str(arquivo))) >= 1


async def test_segunda_sincronizacao_sem_mudanca_nao_gasta_embeddings(service, docs, embed):
    (docs / "a.txt").write_text("conteúdo estável", encoding="utf-8")
    await service.run(cfg([docs]))
    chamadas_antes = embed.calls

    report = await service.run(cfg([docs]))

    assert report.unchanged == 1 and report.indexed == 0
    assert embed.calls == chamadas_antes


async def test_so_data_mudou_mas_texto_igual_nao_reindexa(service, docs, embed):
    arquivo = docs / "a.txt"
    arquivo.write_text("mesmo texto", encoding="utf-8")
    await service.run(cfg([docs]))
    chamadas_antes = embed.calls

    novo_instante = arquivo.stat().st_mtime + 500
    os.utime(arquivo, (novo_instante, novo_instante))  # "salvou de novo" sem alterar o texto
    report = await service.run(cfg([docs]))

    assert report.unchanged == 1 and report.indexed == 0
    assert embed.calls == chamadas_antes
    assert service.catalog.get(str(arquivo)).mtime == novo_instante


async def test_arquivo_alterado_troca_os_trechos_antigos_pelos_novos(service, docs, qdrant):
    arquivo = docs / "regra.txt"
    arquivo.write_text("Texto antigo sobre férias.", encoding="utf-8")
    await service.run(cfg([docs]))
    assert texts_of(qdrant, str(arquivo)) == ["Texto antigo sobre férias."]

    arquivo.write_text("Texto novo e mais longo sobre reembolso de despesas.", encoding="utf-8")
    report = await service.run(cfg([docs]))

    assert report.indexed == 1
    assert texts_of(qdrant, str(arquivo)) == ["Texto novo e mais longo sobre reembolso de despesas."]


async def test_arquivo_apagado_some_do_indice_e_do_catalogo(service, docs, qdrant):
    arquivo = docs / "velho.txt"
    arquivo.write_text("vai sumir", encoding="utf-8")
    await service.run(cfg([docs]))

    arquivo.unlink()
    report = await service.run(cfg([docs]))

    assert report.removed == 1
    assert texts_of(qdrant, str(arquivo)) == []
    assert service.catalog.get(str(arquivo)) is None


async def test_pasta_que_virou_bloqueada_e_esquecida(service, docs, qdrant):
    """Segurança: bloquear uma pasta depois de indexada tem que REMOVER o conteúdo."""
    sigilo = docs / "diretoria"
    sigilo.mkdir()
    secreto = sigilo / "salarios.txt"
    secreto.write_text("dados sigilosos", encoding="utf-8")
    (docs / "manual.txt").write_text("manual público", encoding="utf-8")
    await service.run(cfg([docs]))
    assert texts_of(qdrant, str(secreto)) == ["dados sigilosos"]

    report = await service.run(cfg([docs], blocked=[sigilo]))

    assert report.removed == 1
    assert texts_of(qdrant, str(secreto)) == []
    assert service.catalog.get(str(secreto)) is None
    assert service.catalog.get(str(docs / "manual.txt")) is not None


async def test_pasta_removida_da_configuracao_e_esquecida(service, docs, qdrant):
    arquivo = docs / "a.txt"
    arquivo.write_text("conteúdo", encoding="utf-8")
    await service.run(cfg([docs]))

    report = await service.run(cfg([]))  # gestor tirou a pasta da lista

    assert report.removed == 1
    assert texts_of(qdrant, str(arquivo)) == []


async def test_pasta_fora_do_ar_preserva_o_que_ja_foi_indexado(service, docs, qdrant, tmp_path):
    """Compartilhamento de rede desligado NÃO pode apagar o conhecimento indexado."""
    arquivo = docs / "a.txt"
    arquivo.write_text("conteúdo importante", encoding="utf-8")
    await service.run(cfg([docs]))

    docs.rename(tmp_path / "docs_desligada")  # simula pasta indisponível
    report = await service.run(cfg([docs]))

    assert report.removed == 0 and report.preserved_unavailable == 1
    assert texts_of(qdrant, str(arquivo)) == ["conteúdo importante"]
    assert service.catalog.get(str(arquivo)) is not None

    (tmp_path / "docs_desligada").rename(docs)  # voltou
    report = await service.run(cfg([docs]))
    assert report.unchanged == 1


async def test_arquivo_vazio_vira_sem_texto_e_nao_e_relido(service, docs, qdrant):
    vazio = docs / "escaneado.txt"
    vazio.write_text("   \n", encoding="utf-8")

    primeiro = await service.run(cfg([docs]))
    segundo = await service.run(cfg([docs]))

    assert primeiro.without_text == 1
    assert segundo.unchanged == 1
    assert service.catalog.get(str(vazio)).status == "sem_texto"
    assert texts_of(qdrant, str(vazio)) == []


async def test_arquivo_corrompido_vira_erro_sem_derrubar_os_outros(service, docs):
    (docs / "quebrado.pdf").write_bytes(b"isto nao e um pdf")
    (docs / "bom.txt").write_text("conteúdo ok", encoding="utf-8")

    report = await service.run(cfg([docs]))

    assert report.errors == 1 and report.indexed == 1 and not report.aborted
    assert service.catalog.get(str(docs / "quebrado.pdf")).status == "erro"
    assert service.catalog.get(str(docs / "bom.txt")).status == "ok"


async def test_arquivo_acima_do_limite_e_registrado_com_o_motivo(make_service, docs):
    service = make_service(max_file_size_mb=0)
    (docs / "grande.txt").write_text("qualquer conteúdo", encoding="utf-8")

    report = await service.run(cfg([docs]))

    item = service.catalog.get(str(docs / "grande.txt"))
    assert report.errors == 1 and item.status == "erro" and "limite" in item.error


async def test_ignora_temporarios_do_office_e_tipos_nao_suportados(service, docs):
    (docs / "~$relatorio.docx").write_bytes(b"lixo")
    (docs / "foto.png").write_bytes(b"png")
    (docs / "ok.txt").write_text("texto", encoding="utf-8")

    await service.run(cfg([docs]))

    assert service.catalog.sources() == {str(docs / "ok.txt")}


# ----------------------------------------------------- falha do Ollama


async def test_ollama_fora_do_ar_aborta_sem_apagar_nada_e_tenta_de_novo(service, docs, qdrant, embed):
    antigo = docs / "a.txt"
    antigo.write_text("versão antiga", encoding="utf-8")
    await service.run(cfg([docs]))

    antigo.write_text("versão nova, bem diferente da antiga", encoding="utf-8")
    novo = docs / "b.txt"
    novo.write_text("arquivo novo", encoding="utf-8")
    embed.fail = True
    report = await service.run(cfg([docs]))

    assert report.aborted and "Ollama" in report.message
    assert texts_of(qdrant, str(antigo)) == ["versão antiga"], "a versão antiga NÃO pode ser apagada"
    # A ordem de varredura não é garantida (no Windows costuma ser alfabética; no
    # Linux não). O ciclo pode ter parado ANTES de chegar a um dos arquivos, e esse
    # arquivo nem entra no catálogo (get devolve None). O que importa: pelo menos um
    # arquivo ficou marcado com erro e o erro aparece no status.
    itens = [service.catalog.get(str(arquivo)) for arquivo in (antigo, novo)]
    estados = {item.status for item in itens if item is not None}
    assert "erro" in estados
    assert service.status()["last_error"]

    embed.fail = False  # Ollama voltou
    report = await service.run(cfg([docs]))

    assert not report.aborted
    assert texts_of(qdrant, str(antigo)) == ["versão nova, bem diferente da antiga"]
    assert texts_of(qdrant, str(novo)) == ["arquivo novo"]
    assert service.status()["last_error"] is None


async def test_ciclo_abortado_nao_poda_fontes_que_nem_foram_olhadas(service, docs, qdrant, embed):
    a = docs / "a.txt"
    b = docs / "b.txt"
    a.write_text("conteúdo a", encoding="utf-8")
    b.write_text("conteúdo b", encoding="utf-8")
    await service.run(cfg([docs]))

    a.write_text("conteúdo a alterado", encoding="utf-8")
    b.write_text("conteúdo b alterado", encoding="utf-8")
    embed.fail = True
    await service.run(cfg([docs]))

    assert texts_of(qdrant, str(a)) == ["conteúdo a"]
    assert texts_of(qdrant, str(b)) == ["conteúdo b"]


# --------------------------------------------------------------- web


@pytest.fixture
def web(monkeypatch):
    class Web:
        calls = 0
        content = "Manual publicado na intranet."

    state = Web()

    async def fake_fetch(url, http_client, max_chars=20000, timeout=15.0):
        state.calls += 1
        return state.content

    monkeypatch.setattr(sync_module, "fetch_url_content", fake_fetch)
    return state


URL = "https://intranet.exemplo.com/manual"


async def test_pagina_web_e_indexada_uma_vez_dentro_da_janela_de_atualizacao(service, web, qdrant):
    await service.run(cfg(urls=[URL]))
    assert texts_of(qdrant, URL) == ["Manual publicado na intranet."]
    assert service.catalog.get(URL).kind == "web"

    report = await service.run(cfg(urls=[URL]))  # logo depois: não busca de novo

    assert web.calls == 1 and report.unchanged == 1


async def test_sincronizar_agora_busca_de_novo_mas_nao_reindexa_se_igual(service, web, embed):
    await service.run(cfg(urls=[URL]))
    chamadas_antes = embed.calls

    report = await service.run(cfg(urls=[URL]), force_web=True)

    assert web.calls == 2
    assert report.unchanged == 1 and embed.calls == chamadas_antes


async def test_pagina_que_mudou_troca_o_conteudo(service, web, qdrant):
    await service.run(cfg(urls=[URL]))
    web.content = "Manual atualizado com novas regras de acesso."

    await service.run(cfg(urls=[URL]), force_web=True)

    assert texts_of(qdrant, URL) == ["Manual atualizado com novas regras de acesso."]


async def test_site_fora_do_ar_mantem_o_conteudo_ja_indexado(service, web, qdrant):
    await service.run(cfg(urls=[URL]))
    web.content = None  # fetch_url_content devolve None quando falha

    report = await service.run(cfg(urls=[URL]), force_web=True)

    assert report.errors == 1 and not report.aborted
    assert texts_of(qdrant, URL) == ["Manual publicado na intranet."]
    assert service.catalog.get(URL).status == "erro"


async def test_url_removida_da_configuracao_e_esquecida(service, web, qdrant):
    await service.run(cfg(urls=[URL]))

    report = await service.run(cfg(urls=[]))

    assert report.removed == 1 and texts_of(qdrant, URL) == []


# ------------------------------------------------------ conhecimento tácito


async def test_conhecimento_tacito_indexa_troca_e_remove(service, qdrant):
    await service.run(cfg(tacit="Sempre confirmar o prazo de 5 dias úteis."))
    assert texts_of(qdrant, TACIT_SOURCE) == ["Sempre confirmar o prazo de 5 dias úteis."]
    assert service.catalog.get(TACIT_SOURCE).kind == "tacit"

    await service.run(cfg(tacit="Prazo agora é de 3 dias úteis."))
    assert texts_of(qdrant, TACIT_SOURCE) == ["Prazo agora é de 3 dias úteis."]

    report = await service.run(cfg(tacit=None))
    assert report.removed == 1 and texts_of(qdrant, TACIT_SOURCE) == []


# ----------------------------------------------------- controle / status


async def test_nao_roda_dois_ciclos_ao_mesmo_tempo(service, docs):
    await service._lock.acquire()
    try:
        with pytest.raises(SyncAlreadyRunning):
            await service.run(cfg([docs]))
    finally:
        service._lock.release()


async def test_status_resume_o_ultimo_ciclo_sem_expor_caminhos(service, docs):
    (docs / "a.txt").write_text("conteúdo", encoding="utf-8")
    (docs / "b.txt").write_text("outro conteúdo", encoding="utf-8")
    await service.run(cfg([docs]))

    status = service.status()

    assert status["running"] is False
    assert status["last_finished"] and status["last_error"] is None
    assert status["last_summary"]["indexed"] == 2
    assert status["items"]["files"] == 2
    assert str(docs) not in str(status), "o status não pode vazar caminhos do servidor"


async def test_laco_periodico_roda_um_ciclo_e_pode_ser_cancelado(service, docs):
    (docs / "a.txt").write_text("conteúdo", encoding="utf-8")
    config = cfg([docs])

    tarefa = asyncio.create_task(service.run_periodic(lambda: config))
    for _ in range(100):
        if service.catalog.get_meta("last_sync_finished"):
            break
        await asyncio.sleep(0.05)

    tarefa.cancel()
    with pytest.raises(asyncio.CancelledError):
        await tarefa
    assert service.catalog.get(str(docs / "a.txt")).status == "ok"


async def test_laco_periodico_sem_configuracao_nao_faz_nada(service):
    tarefa = asyncio.create_task(service.run_periodic(lambda: None))
    await asyncio.sleep(0.1)

    tarefa.cancel()
    with pytest.raises(asyncio.CancelledError):
        await tarefa
    assert service.catalog.get_meta("last_sync_started") is None
