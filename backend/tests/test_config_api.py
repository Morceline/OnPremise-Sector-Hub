"""
tests/test_config_api.py
----------------------------
Garante que:
1. Ninguém sem a chave do gestor consegue alterar a configuração (401).
2. Uma chave errada é rejeitada (403).
3. A chave correta persiste a configuração em disco e sobrevive a uma
   nova leitura (substitui a antiga variável global em memória).
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from tests.test_sync_api import FakeSyncService

VALID_PAYLOAD = {
    "sector_name": "Recursos Humanos",
    "sector_type": "recursos_humanos",
    "niche_persona": "Assistente de RH, formal e acolhedor",
    "allowed_local_paths": [],
    "blocked_local_paths": [],
    "allowed_web_urls": [],
    "blocked_web_urls": [],
    "tacit_knowledge": "Sempre confirme o prazo de 5 dias úteis para reembolsos.",
}


@pytest.fixture
def app_with_fake_deps(monkeypatch):
    fake_qdrant = MagicMock()
    fake_qdrant.get_collections.return_value = MagicMock(collections=[])
    monkeypatch.setattr("app.services.rag_engine.QdrantClient", lambda **kwargs: fake_qdrant)

    from app.core.dependencies import get_sync_service
    from app.main import app

    fake_sync = FakeSyncService()
    app.dependency_overrides[get_sync_service] = lambda: fake_sync
    app.state_fake_sync = fake_sync  # para os testes conferirem as chamadas

    yield app

    app.dependency_overrides.clear()


def test_salvar_configuracao_sem_chave_retorna_401(app_with_fake_deps, tmp_active_config_path):
    with TestClient(app_with_fake_deps) as client:
        resp = client.post("/api/v1/config/save", json=VALID_PAYLOAD)

    assert resp.status_code == 401


def test_salvar_configuracao_com_chave_invalida_retorna_403(app_with_fake_deps, tmp_active_config_path):
    with TestClient(app_with_fake_deps) as client:
        resp = client.post(
            "/api/v1/config/save", json=VALID_PAYLOAD, headers={"X-Manager-Key": "chave-errada"}
        )

    assert resp.status_code == 403


def test_salvar_configuracao_com_chave_valida_persiste(app_with_fake_deps, tmp_active_config_path, manager_key):
    with TestClient(app_with_fake_deps) as client:
        resp = client.post(
            "/api/v1/config/save", json=VALID_PAYLOAD, headers={"X-Manager-Key": manager_key}
        )
        assert resp.status_code == 200

        resp_ativa = client.get("/api/v1/config/active")

    assert resp_ativa.status_code == 200
    body = resp_ativa.json()
    assert body["configured"] is True
    assert body["sector_name"] == "Recursos Humanos"
    # Caminhos locais NUNCA devem ser expostos por essa rota pública.
    assert "allowed_local_paths" not in body


def test_configuracao_ativa_quando_nada_foi_salvo_ainda(app_with_fake_deps, tmp_active_config_path):
    with TestClient(app_with_fake_deps) as client:
        resp = client.get("/api/v1/config/active")

    assert resp.status_code == 200
    assert resp.json() == {"configured": False}


def test_salvar_configuracao_dispara_sincronizacao_forcando_web(app_with_fake_deps, tmp_active_config_path, manager_key):
    with TestClient(app_with_fake_deps) as client:
        client.post("/api/v1/config/save", json=VALID_PAYLOAD, headers={"X-Manager-Key": manager_key})

    assert app_with_fake_deps.state_fake_sync.calls == [("Recursos Humanos", True)]


def test_chave_invalida_nao_dispara_sincronizacao(app_with_fake_deps, tmp_active_config_path):
    with TestClient(app_with_fake_deps) as client:
        client.post("/api/v1/config/save", json=VALID_PAYLOAD, headers={"X-Manager-Key": "errada"})

    assert app_with_fake_deps.state_fake_sync.calls == []


def test_gestor_recebe_a_configuracao_completa_com_a_chave(app_with_fake_deps, tmp_active_config_path, manager_key):
    with TestClient(app_with_fake_deps) as client:
        client.post("/api/v1/config/save", json=VALID_PAYLOAD, headers={"X-Manager-Key": manager_key})
        resp = client.get("/api/v1/config/manager", headers={"X-Manager-Key": manager_key})

    assert resp.status_code == 200
    body = resp.json()
    assert body["configured"] is True
    assert body["sector_name"] == "Recursos Humanos"
    assert body["tacit_knowledge"].startswith("Sempre confirme")


def test_configuracao_completa_exige_a_chave(app_with_fake_deps, tmp_active_config_path):
    with TestClient(app_with_fake_deps) as client:
        resp = client.get("/api/v1/config/manager")
    assert resp.status_code == 401


def test_configuracao_completa_sem_nada_salvo(app_with_fake_deps, tmp_active_config_path, manager_key):
    with TestClient(app_with_fake_deps) as client:
        resp = client.get("/api/v1/config/manager", headers={"X-Manager-Key": manager_key})
    assert resp.json() == {"configured": False}
