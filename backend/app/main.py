from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import config, chat

app = FastAPI(
    title="Assistente de Setor - Core API",
    version="1.0.0",
    description="Backend RAG On-Premise com isolamento de permissões e processamento local."
)

# Configuração de CORS para permitir comunicação com o Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusão dos Roteadores
app.include_router(config.router, prefix="/api/v1/config", tags=["Configuração do Gestor"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Atendimento Ao Colaborador"])

@app.get("/health", tags=["Infraestrutura"])
async def health_check():
    return {"status": "online", "system": "Assistente de Setor"}