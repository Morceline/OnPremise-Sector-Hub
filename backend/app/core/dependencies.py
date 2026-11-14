"""
core/dependencies.py
----------------------
Funções de dependência do FastAPI que dão acesso aos recursos "singleton"
da aplicação: o cliente HTTP compartilhado (httpx.AsyncClient), o RAGEngine,
o porteiro de atividade (prioridade do chat) e o serviço de sincronização.

Por que isso importa: criar RAGEngine/httpx.AsyncClient a cada request
reabriria conexões a toda chamada. Guardamos as instâncias em `app.state`
(criadas uma única vez no lifespan, ver main.py) e as expomos via
`Depends(...)`.
"""

from fastapi import Request
from httpx import AsyncClient

from app.core.activity import ActivityGate
from app.services.rag_engine import RAGEngine
from app.services.sync_service import SyncService


def get_http_client(request: Request) -> AsyncClient:
    return request.app.state.http_client


def get_rag_engine(request: Request) -> RAGEngine:
    return request.app.state.rag_engine


def get_activity_gate(request: Request) -> ActivityGate:
    return request.app.state.activity_gate


def get_sync_service(request: Request) -> SyncService:
    return request.app.state.sync_service
