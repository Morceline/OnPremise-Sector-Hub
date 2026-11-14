"""
tests/test_sync_api.py
-------------------------
Rotas de controle da sincronização: status público (sem caminhos) e
"sincronizar agora" protegido pela chave do gestor.
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.models.config import SectorConfig
from app.services.persistence import save_active_config


class FakeSyncService:
    def __init__(self, running=False):
        self.running = running
        self.calls = []

    async def run(self, config, force_web=False):
        self.calls.append((config.sector_name, force_web))

    def status(self):
        return {
            "running": self.running,
            "interval_minutes": 15,
            "last_started": "2026-10-10T12:00:00+00:00",
            "last_finished": "2026-10-10T12:00:05+00:00",
            "last_error": None,
            "last_summary": {"indexed": 2},
            "items": {"files": 2, "web": 0, "tacit": 0, "chunks": 5, "errors": 0, "without_text": 0},
        }


@pytest.fixture
def app_and_fake(monkeypatch):
    fake_qdrant = MagicMock()
    fake_qdrant.get_collections.return_value = MagicMock(collections=[])
    monkeypatch.setattr("app.services.rag_engine.QdrantClient", lambda **kwargs: fake_qdrant)

    from app.core.dependencies import get_sync_service
    from app.main import app

    fake = FakeSyncService()
    app.dependency_overrides[get_sync_service] = lambda: fake
    yield app, fake
    app.dependency_overrides.clear()


def _config() -> SectorConfig:
    return SectorConfig(sector_name="Jurídico", niche_persona="formal")


def test_status_e_publico_e_devolve_o_resumo(app_and_fake):
    app, _ = app_and_fake
    with TestClient(app) as client:
        resp = client.get("/api/v1/sync/status")

    assert resp.status_code == 200
    assert resp.json()["last_finished"] == "2026-10-10T12:00:05+00:00"
    assert resp.json()["items"]["files"] == 2


def test_sincronizar_agora_exige_a_chave_do_gestor(app_and_fake):
    app, fake = app_and_fake
    with TestClient(app) as client:
        sem_chave = client.post("/api/v1/sync/run")
        chave_errada = client.post("/api/v1/sync/run", headers={"X-Manager-Key": "errada"})

    assert sem_chave.status_code == 401
    assert chave_errada.status_code == 403
    assert fake.calls == []


def test_sem_configuracao_ativa_retorna_409(app_and_fake, tmp_active_config_path, manager_key):
    app, fake = app_and_fake
    with TestClient(app) as client:
        resp = client.post("/api/v1/sync/run", headers={"X-Manager-Key": manager_key})

    assert resp.status_code == 409
    assert fake.calls == []


def test_com_chave_e_configuracao_dispara_a_sincronizacao_forcando_web(app_and_fake, tmp_active_config_path, manager_key):
    app, fake = app_and_fake
    save_active_config(_config(), tmp_active_config_path)

    with TestClient(app) as client:
        resp = client.post("/api/v1/sync/run", headers={"X-Manager-Key": manager_key})

    assert resp.status_code == 200 and resp.json() == {"status": "started"}
    assert fake.calls == [("Jurídico", True)]


def test_se_ja_esta_rodando_nao_dispara_outra(app_and_fake, tmp_active_config_path, manager_key):
    app, fake = app_and_fake
    fake.running = True
    save_active_config(_config(), tmp_active_config_path)

    with TestClient(app) as client:
        resp = client.post("/api/v1/sync/run", headers={"X-Manager-Key": manager_key})

    assert resp.json() == {"status": "already_running"}
    assert fake.calls == []


def test_rota_legada_document_sync_faz_o_mesmo(app_and_fake, tmp_active_config_path, manager_key):
    app, fake = app_and_fake
    save_active_config(_config(), tmp_active_config_path)

    with TestClient(app) as client:
        sem_chave = client.post("/api/v1/document/sync")
        com_chave = client.post("/api/v1/document/sync", headers={"X-Manager-Key": manager_key})

    assert sem_chave.status_code == 401
    assert com_chave.json() == {"status": "started"}
    assert fake.calls == [("Jurídico", True)]
