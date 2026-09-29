"""
api/config.py
---------------
Endpoint que o gestor do setor usa para cadastrar/atualizar a configuração
(persona, allowlist/blocklist de arquivos e URLs, conhecimento tácito).

Mudanças:
- Protegido por `require_manager_key` (RF04: só efetivo autorizado configura).
- A configuração agora é persistida em disco (services/persistence.py) em
  vez de uma variável global em memória — sobrevive a restart do processo.
- `process_indexing` virou uma função ASYNC nativa (BackgroundTasks do
  Starlette suporta corrotinas diretamente desde a v0.15), eliminando o
  `asyncio.run(...)` dentro de uma função síncrona da versão anterior.
- Passou a também sincronizar as URLs da allowlist (services/web_scraper),
  não só arquivos locais.
"""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends
from httpx import AsyncClient

from app.core.config import Settings, get_settings
from app.core.dependencies import get_http_client, get_rag_engine
from app.core.security import require_manager_key
from app.models.config import SectorConfig
from app.services.document import SafeDocumentReader
from app.services.persistence import save_active_config
from app.services.rag_engine import RAGEngine
from app.services.web_scraper import fetch_url_content, is_url_allowed

logger = logging.getLogger(__name__)
router = APIRouter()


async def process_indexing(
    config: SectorConfig,
    rag_engine: RAGEngine,
    http_client: AsyncClient,
    settings: Settings,
) -> None:
    """Lê arquivos locais autorizados + URLs autorizadas e indexa tudo no Qdrant."""
    reader = SafeDocumentReader(
        allowed_paths=config.allowed_local_paths,
        blocked_paths=config.blocked_local_paths,
        max_file_size_mb=settings.max_file_size_mb,
    )
    docs = reader.load_and_extract()

    allowed_urls_str = [str(u) for u in config.allowed_web_urls]
    for url in allowed_urls_str:
        if not is_url_allowed(url, allowed_urls_str):
            continue  # nunca deve acontecer aqui, mas mantemos fail-safe
        content = await fetch_url_content(
            url, http_client, max_chars=settings.max_web_fetch_chars, timeout=settings.embedding_timeout_seconds
        )
        if content:
            docs.append({"source": url, "content": content})

    if config.tacit_knowledge:
        docs.append({"source": "Regras Tácitas do Gestor", "content": config.tacit_knowledge})

    total_chunks = await rag_engine.index_documents(docs)
    logger.info("Indexação concluída: %s documentos processados, %s chunks gerados.", len(docs), total_chunks)


@router.post("/save", dependencies=[Depends(require_manager_key)])
async def save_configuration(
    config: SectorConfig,
    background_tasks: BackgroundTasks,
    rag_engine: RAGEngine = Depends(get_rag_engine),
    http_client: AsyncClient = Depends(get_http_client),
    settings: Settings = Depends(get_settings),
):
    save_active_config(config, settings.active_config_path)

    background_tasks.add_task(process_indexing, config, rag_engine, http_client, settings)

    return {
        "status": "success",
        "message": "Configuração salva. A indexação das fontes de dados foi iniciada em segundo plano.",
    }


@router.get("/active")
async def get_active_configuration(settings: Settings = Depends(get_settings)):
    """Consulta pública (somente leitura) da config ativa, usada pelo widget
    para saber persona/paleta/setor — não expõe caminhos locais sensíveis."""
    from app.services.persistence import load_active_config

    config = load_active_config(settings.active_config_path)
    if config is None:
        return {"configured": False}

    return {
        "configured": True,
        "sector_name": config.sector_name,
        "sector_type": config.sector_type,
        "palette_color": config.palette_color,
    }
