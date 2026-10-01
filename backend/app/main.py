"""
main.py
--------
Ponto de entrada da API. Mudanças:

1. CORS deixou de ser `allow_origins=["*"]` (aberto para qualquer origem)
   e passou a restringir explicitamente às origens do widget Tauri/Vite em
   desenvolvimento e produção. Wildcard era desnecessariamente permissivo
   para uma aplicação que só precisa falar com o próprio widget desktop.

2. Introduzido um `lifespan` que cria, na inicialização da aplicação:
   - um único `httpx.AsyncClient` reutilizado por toda a aplicação
     (evita reabrir conexões TCP a cada request);
   - uma única instância de `RAGEngine` (evita reconectar ao Qdrant e
     reprocessar a checagem de coleção a cada request).
   Ambos ficam disponíveis via `app.state` e são injetados nas rotas por
   `core/dependencies.py`.

3. Endpoint `/health` passou a checar também a disponibilidade do Qdrant
   e do Ollama, não só responder "online" de forma incondicional — isso
   ajuda o widget a mostrar ao usuário exatamente qual serviço está fora
   do ar (útil já que o Ollama roda nativo no Windows, fora do Docker).
"""

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, config, document, feedback, it_support
from app.core.config import get_settings
from app.services.rag_engine import RAGEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    http_client = httpx.AsyncClient()
    app.state.http_client = http_client
    app.state.rag_engine = RAGEngine(settings=settings, http_client=http_client)

    logger.info("Aplicação iniciada. Qdrant=%s:%s Ollama=%s", settings.qdrant_host, settings.qdrant_port, settings.ollama_host)

    yield

    await http_client.aclose()
    logger.info("Aplicação encerrada, conexões liberadas.")


app = FastAPI(
    title="Assistente de Setor - Core API",
    version="1.1.0",
    description="Backend RAG on-premise com isolamento de permissões e processamento 100% local.",
    lifespan=lifespan,
)

# Origens explicitamente permitidas: dev do Vite (widget React) e o
# esquema customizado do Tauri em produção. Ajuste conforme a config
# de porta em .env / tauri.conf.json.
ALLOWED_ORIGINS = [
    "tauri://localhost",
    "http://localhost:1420",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Manager-Key"],
)

app.include_router(document.router, prefix="/api/v1/document", tags=["Base de Conhecimento"])
app.include_router(config.router, prefix="/api/v1/config", tags=["Configuração do Gestor"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Atendimento ao Colaborador"])
app.include_router(feedback.router, prefix="/api/v1/feedback", tags=["Feedback"])
app.include_router(it_support.router, prefix="/api/v1/it-support", tags=["Suporte de TI Universal"])


@app.get("/health", tags=["Infraestrutura"])
async def health_check():
    settings = get_settings()
    http_client: httpx.AsyncClient = app.state.http_client

    qdrant_ok = True
    try:
        app.state.rag_engine.client.get_collections()
    except Exception:
        qdrant_ok = False

    ollama_ok = True
    try:
        response = await http_client.get(f"{settings.ollama_host}/api/tags", timeout=3.0)
        ollama_ok = response.status_code == 200
    except Exception:
        ollama_ok = False

    overall = "online" if (qdrant_ok and ollama_ok) else "degraded"

    return {
        "status": overall,
        "system": "Assistente de Setor",
        "dependencies": {"qdrant": qdrant_ok, "ollama": ollama_ok},
    }
