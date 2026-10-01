"""
tests/test_it_support_api.py
--------------------------------
Cobre o fluxo universal de TI, incluindo o botão "não entendi, explique
mais simples" (simplify=True), que reescreve a resposta anterior em vez
de gerar uma resposta nova do zero.
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from tests.test_chat_api import _fake_http_client


@pytest.fixture
def app_with_fake_deps(monkeypatch):
    fake_qdrant = MagicMock()
    fake_qdrant.get_collections.return_value = MagicMock(collections=[])
    monkeypatch.setattr("app.services.rag_engine.QdrantClient", lambda **kwargs: fake_qdrant)

    from app.core.dependencies import get_http_client
    from app.main import app

    app.dependency_overrides[get_http_client] = lambda: _fake_http_client(
        {"response": "1. Verifique se o cabo USB do mouse está bem encaixado."}
    )

    yield app
    app.dependency_overrides.clear()


def test_it_support_query_basico(app_with_fake_deps):
    with TestClient(app_with_fake_deps) as client:
        resp = client.post(
            "/api/v1/it-support/query",
            json={"problem_description": "Meu mouse parou de funcionar", "category": "periferico"},
        )

    assert resp.status_code == 200
    assert "cabo USB" in resp.json()["response"]


def test_it_support_query_modo_simplificar_exige_resposta_anterior_no_prompt(app_with_fake_deps):
    with TestClient(app_with_fake_deps) as client:
        resp = client.post(
            "/api/v1/it-support/query",
            json={
                "problem_description": "não importa aqui",
                "simplify": True,
                "previous_answer": "Verifique a conectividade do dispositivo periférico USB.",
            },
        )

    assert resp.status_code == 200
