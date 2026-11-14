"""
api/document.py
------------------
ROTA LEGADA. Antes, /document/sync lia pastas informadas no corpo da
requisição e indexava direto, sem registrar nada — o que deixava trechos
"órfãos" que nenhuma sincronização conhecia. Agora existe UMA fonte da
verdade (a configuração ativa do setor) e UM mecanismo (SyncService).

Mantida só como atalho de compatibilidade: dispara a mesma sincronização de
POST /api/v1/sync/run. O corpo da requisição, se enviado, é ignorado.
"""

from fastapi import APIRouter, BackgroundTasks, Depends

from app.api.sync import run_sync
from app.core.config import Settings, get_settings
from app.core.dependencies import get_sync_service
from app.core.security import require_manager_key
from app.services.sync_service import SyncService

router = APIRouter()


@router.post("/sync", dependencies=[Depends(require_manager_key)], deprecated=True)
async def sync_folder_documents(
    background_tasks: BackgroundTasks,
    service: SyncService = Depends(get_sync_service),
    settings: Settings = Depends(get_settings),
):
    return await run_sync(background_tasks, service, settings)
