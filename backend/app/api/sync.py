"""
api/sync.py
-------------
Controle da sincronização incremental.

- GET  /api/v1/sync/status  -> público (somente leitura): quando foi a última
  conferência e contagens. NÃO expõe caminhos de arquivo. O widget usa isso
  para mostrar "conferido às HH:MM".
- POST /api/v1/sync/run     -> exige a chave do gestor: botão "Sincronizar
  agora". Roda em segundo plano e responde na hora.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.core.config import Settings, get_settings
from app.core.dependencies import get_sync_service
from app.core.security import require_manager_key
from app.services.persistence import load_active_config
from app.services.sync_service import SyncService, run_in_background

router = APIRouter()


@router.get("/status")
async def sync_status(service: SyncService = Depends(get_sync_service)):
    return service.status()


@router.post("/run", dependencies=[Depends(require_manager_key)])
async def run_sync(
    background_tasks: BackgroundTasks,
    service: SyncService = Depends(get_sync_service),
    settings: Settings = Depends(get_settings),
):
    config = load_active_config(settings.active_config_path)
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nenhuma configuração ativa. Salve a configuração do setor primeiro.",
        )

    if service.running:
        return {"status": "already_running"}

    # force_web=True: pedido manual = quer o conteúdo mais novo, inclusive das páginas web.
    background_tasks.add_task(run_in_background, service, config, True)
    return {"status": "started"}
