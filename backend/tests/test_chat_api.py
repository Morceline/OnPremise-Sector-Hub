"""
tests/test_chat_api.py
--------------------------
Testes de integração do endpoint POST /api/v1/chat/query, usando o
TestClient do FastAPI. Tanto o RAGEngine quanto o cliente HTTP (Ollama)
são substituídos via `app.dependency_overrides` — nenhum destes testes
depende de um Qdrant ou Ollama reais rodando na máquina.
"""

from typing import Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

class FakeHit:
    def __init__(self, text: str, source: str):
        self.payload = {"text": text, "source": source}


class FakeRAGEngine:
    def __init__(self, hits=None):
        self._hits = hits or []

    async def search(self, query_text: str, limit: int = 3):
        return self._hits

    async def index_documents(self, docs):
        return 0


def _fake_http_client(json_response: dict, status_code: int = 200, raise_exc: Optional[Exception] = None):
    client = MagicMock()
    if raise_exc:
        client.post = AsyncMock(side_effect=raise_exc)
        return client

    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_response
    if status_code >= 400:
        import httpx

        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "erro", request=MagicMock(), response=response
        )
    else:
        response.raise_for_status.return_value = None

    client.post = AsyncMock(return_value=response)
    return client


@pytest.fixture
def app_with_fake_qdrant(monkeypatch):
    """Evita conexão real ao Qdrant durante o lifespan da aplicação."""
    fake_qdrant = MagicMock()
    fake_qdrant.get_collections.return_value = MagicMock(collections=[])
    monkeypatch.setattr("app.services.rag_engine.QdrantClient", lambda **kwargs: fake_qdrant)

    from app.main import app

    return app


def test_chat_query_retorna_resposta_com_fontes(app_with_fake_qdrant, tmp_active_config_path):
    from app.core.dependencies import get_http_client, get_rag_engine

    app = app_with_fake_qdrant
    app.dependency_overrides[get_rag_engine] = lambda: FakeRAGEngine(
        hits=[FakeHit("Procedimento de férias está no manual X.", "manual_rh.pdf")]
    )
    app.dependency_overrides[get_http_client] = lambda: _fake_http_client(
        {"response": "Você deve preencher o formulário de férias com 30 dias de antecedência."}
    )

    with TestClient(app) as client:
        resp = client.post("/api/v1/chat/query", json={"message": "Como funciona o pedido de férias?"})

    app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert "formulário de férias" in body["response"]
    assert body["sources"] == ["manual_rh.pdf"]


def test_chat_query_sem_contexto_ainda_responde(app_with_fake_qdrant, tmp_active_config_path):
    from app.core.dependencies import get_http_client, get_rag_engine

    app = app_with_fake_qdrant
    app.dependency_overrides[get_rag_engine] = lambda: FakeRAGEngine(hits=[])
    app.dependency_overrides[get_http_client] = lambda: _fake_http_client(
        {"response": "Não encontrei essa informação na base de conhecimento."}
    )

    with TestClient(app) as client:
        resp = client.post("/api/v1/chat/query", json={"message": "Pergunta sem resposta na base"})

    app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json()["sources"] == []


def test_chat_query_ollama_indisponivel_retorna_503(app_with_fake_qdrant, tmp_active_config_path):
    import httpx

    from app.core.dependencies import get_http_client, get_rag_engine

    app = app_with_fake_qdrant
    app.dependency_overrides[get_rag_engine] = lambda: FakeRAGEngine(hits=[])
    app.dependency_overrides[get_http_client] = lambda: _fake_http_client(
        {}, raise_exc=httpx.ConnectError("conexão recusada")
    )

    with TestClient(app) as client:
        resp = client.post("/api/v1/chat/query", json={"message": "oi"})

    app.dependency_overrides.clear()

    assert resp.status_code == 503


def test_chat_query_mensagem_vazia_e_rejeitada_pela_validacao(app_with_fake_qdrant):
    with TestClient(app_with_fake_qdrant) as client:
        resp = client.post("/api/v1/chat/query", json={"message": ""})

    assert resp.status_code == 422
