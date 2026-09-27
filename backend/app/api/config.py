from fastapi import APIRouter, BackgroundTasks, HTTPException
from app.models.config import SectorConfig
from app.services.document import SafeDocumentReader
from app.services.rag_engine import RAGEngine

router = APIRouter()
rag_engine = RAGEngine()

# Armazenamento simples em memória da configuração ativa
ACTIVE_CONFIG: SectorConfig = None

@router.post("/save")
async def save_configuration(config: SectorConfig, background_tasks: BackgroundTasks):
    global ACTIVE_CONFIG
    ACTIVE_CONFIG = config
    
    # Inicia o processamento de leitura e indexação em segundo plano
    background_tasks.add_task(process_indexing, config)
    
    return {
        "status": "success",
        "message": "Configurações salvas. A indexação das fontes de dados foi iniciada em segundo plano."
    }

def process_indexing(config: SectorConfig):
    reader = SafeDocumentReader(
        allowed_paths=config.allowed_local_paths,
        blocked_paths=config.blocked_local_paths
    )
    docs = reader.load_and_extract()
    
    # Adiciona o conhecimento tácito se houver
    if config.tacit_knowledge:
        docs.append({
            "source": "Regras Tácitas do Gestor",
            "content": config.tacit_knowledge
        })
        
    import asyncio
    asyncio.run(rag_engine.index_documents(docs))