"""
core/dependencies.py
----------------------
Funções de dependência do FastAPI que dão acesso aos recursos "singleton"
da aplicação: o cliente HTTP compartilhado (httpx.AsyncClient) e a instância
do RAGEngine.
"""

from fastapi import Request
from httpx import AsyncClient

from app.services.rag_engine import RAGEngine


def get_http_client(request: Request) -> AsyncClient:
    return request.app.state.http_client


def get_rag_engine(request: Request) -> RAGEngine:
    return request.app.state.rag_engine
