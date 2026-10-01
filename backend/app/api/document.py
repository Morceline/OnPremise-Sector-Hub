"""
api/document.py
------------------
Permite ao gestor forçar uma resincronização manual dos arquivos locais
autorizados, sem precisar reenviar toda a configuração.

Mudança: a lógica de vetorizar e fazer upsert
chunk a chunk estava duplicada aqui (fora do RAGEngine). Agora delega
inteiramente para `rag_engine.index_documents`, que já gera IDs
determinísticos (idempotente) — uma única implementação, sem duplicação
de lógica entre este arquivo e o RAGEngine.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List

from app.core.config import Settings, get_settings
from app.core.dependencies import get_rag_engine
from app.core.security import require_manager_key
from app.services.document import SafeDocumentReader
from app.services.rag_engine import RAGEngine

router = APIRouter()


class SyncPayload(BaseModel):
    allowed_paths: List[str]
    blocked_paths: List[str] = []


@router.post("/sync", dependencies=[Depends(require_manager_key)])
async def sync_folder_documents(
    payload: SyncPayload,
    rag_engine: RAGEngine = Depends(get_rag_engine),
    settings: Settings = Depends(get_settings),
):
    reader = SafeDocumentReader(
        allowed_paths=payload.allowed_paths,
        blocked_paths=payload.blocked_paths,
        max_file_size_mb=settings.max_file_size_mb,
    )
    extracted_docs = reader.load_and_extract()

    if not extracted_docs:
        return {"message": "Nenhum documento novo ou válido encontrado para ingestão.", "documents_ingested": 0}

    total_chunks = await rag_engine.index_documents(extracted_docs)

    return {
        "message": "Sincronização concluída com sucesso.",
        "documents_found": len(extracted_docs),
        "chunks_indexed": total_chunks,
    }
