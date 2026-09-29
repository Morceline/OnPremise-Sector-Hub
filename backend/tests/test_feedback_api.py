"""
tests/test_feedback_api.py
------------------------------
Garante que o envio de feedback nunca quebra por falta de configuração de
SMTP, e que o log local é sempre gravado (fonte de verdade caso o e-mail
falhe).
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app_instance(monkeypatch):
    fake_qdrant = MagicMock()
    fake_qdrant.get_collections.return_value = MagicMock(collections=[])
    monkeypatch.setattr("app.services.rag_engine.QdrantClient", lambda **kwargs: fake_qdrant)

    from app.main import app

    return app


def test_submit_feedback_retorna_200(app_instance, monkeypatch, tmp_path):
    log_path = tmp_path / "feedback.jsonl"
    monkeypatch.setenv("FEEDBACK_LOG_PATH", str(log_path))
    monkeypatch.setenv("FEEDBACK_ENABLED", "false")

    from app.core.config import get_settings

    get_settings.cache_clear()

    with TestClient(app_instance) as client:
        resp = client.post(
            "/api/v1/feedback/submit",
            json={"rating": 5, "comment": "Resolveu rapidinho!", "sector_name": "TI"},
        )

    get_settings.cache_clear()

    assert resp.status_code == 200
    assert resp.json()["status"] == "received"


def test_feedback_invalido_fora_do_intervalo_e_rejeitado(app_instance):
    with TestClient(app_instance) as client:
        resp = client.post("/api/v1/feedback/submit", json={"rating": 7})

    assert resp.status_code == 422
