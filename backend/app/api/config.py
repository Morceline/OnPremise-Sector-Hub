"""
api/config.py
---------------
Endpoint que o gestor do setor usa para cadastrar/atualizar a configuração
(persona, allowlist/blocklist de arquivos e URLs, conhecimento tácito).

Mudança deste lote: ao salvar, a indexação passa pelo SyncService (a mesma
sincronização incremental que roda periodicamente), em vez de um caminho
próprio. Resultado: salvar a configuração também PODA o que deixou de ser
autorizado (pasta que virou bloqueada, URL removida) — antes, o conteúdo
indexado ficava no índice para sempre.
"""

from fastapi import APIRouter, BackgroundTasks, Depends

from app.core.config import Settings, get_settings
from app.core.dependencies import get_sync_service
from app.core.security import require_manager_key
from app.models.config import SectorConfig
from app.services.persistence import load_active_config, save_active_config
from app.services.sync_service import SyncService, run_in_background

router = APIRouter()


@router.post("/save", dependencies=[Depends(require_manager_key)])
async def save_configuration(
    config: SectorConfig,
    background_tasks: BackgroundTasks,
    sync_service: SyncService = Depends(get_sync_service),
    settings: Settings = Depends(get_settings),
):
    save_active_config(config, settings.active_config_path)

    # force_web=True: configuração nova -> relê também as páginas web.
    background_tasks.add_task(run_in_background, sync_service, config, True)

    return {
        "status": "success",
        "message": "Configuração salva. A sincronização das fontes foi iniciada em segundo plano.",
    }


@router.get("/manager", dependencies=[Depends(require_manager_key)])
async def get_manager_configuration(settings: Settings = Depends(get_settings)):
    """Configuração COMPLETA, só para o gestor (com a chave). É o que faz o
    formulário reabrir com o que já foi salvo, inclusive pastas e links."""
    config = load_active_config(settings.active_config_path)
    if config is None:
        return {"configured": False}
    return {"configured": True, **config.model_dump(mode="json")}


@router.get("/active")
async def get_active_configuration(settings: Settings = Depends(get_settings)):
    """Consulta pública (somente leitura) da config ativa, usada pelo widget
    para saber persona/paleta/setor — não expõe caminhos locais sensíveis."""
    config = load_active_config(settings.active_config_path)
    if config is None:
        return {"configured": False}

    return {
        "configured": True,
        "sector_name": config.sector_name,
        "sector_type": config.sector_type,
        "palette_color": config.palette_color,
    }
