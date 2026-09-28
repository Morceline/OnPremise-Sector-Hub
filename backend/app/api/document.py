from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from app.services.document import SafeDocumentReader
from app.services.rag_engine import RAGEngine
import uuid

router = APIRouter()

class SyncPayload(BaseModel):
    allowed_paths: List[str]
    blocked_paths: List[str]

@router.post("/sync")
async def sync_folder_documents(payload: SyncPayload):
    try:
        # 1. Instancia o Leitor Seguro criado em services/document.py
        reader = SafeDocumentReader(
            allowed_paths=payload.allowed_paths,
            blocked_paths=payload.blocked_paths
        )
        
        # 2. Extrai os documentos das pastas permitidas (respeitando bloqueios)
        extracted_docs = reader.load_and_extract()
        
        if not extracted_docs:
            return {"message": "Nenhum documento novo ou válido encontrado para ingestão.", "count": 0}

        rag_engine = RAGEngine()
        ingested_count = 0

        # 3. Vetoriza e envia cada documento para o Qdrant
        for doc in extracted_docs:
            vector = await rag_engine._get_embedding(doc["content"])
            if vector:
                rag_engine.client.upsert(
                    collection_name=rag_engine.collection_name,
                    points=[
                        {
                            "id": str(uuid.uuid4()),
                            "vector": vector,
                            "payload": {
                                "text": doc["content"],
                                "source": doc["source"]
                            }
                        }
                    ]
                )
                ingested_count += 1

        return {
            "message": f"Sincronização concluída com sucesso!",
            "documents_ingested": ingested_count
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))