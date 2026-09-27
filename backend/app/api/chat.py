from fastapi import APIRouter, HTTPException
from app.models.config import ChatMessage
from app.services.rag_engine import RAGEngine

router = APIRouter()
rag_engine = RAGEngine()

@router.post("/query")
async def process_chat(payload: ChatMessage):
    try:
        # 1. Converter a pergunta do utilizador num vetor (Embedding) via Ollama Nativo
        pergunta_vector = await rag_engine._get_embedding(payload.message)
        
        if not pergunta_vector:
            raise HTTPException(status_code=500, detail="Falha ao comunicar com o Ollama local.")

        # 2. Pesquisar no Qdrant os fragmentos de documentos mais semelhantes à pergunta
        resultados = rag_engine.client.search(
            collection_name=rag_engine.collection_name,
            query_vector=pergunta_vector,
            limit=3 # Recupera os 3 trechos mais relevantes
        )

        # 3. Compilar o contexto recuperado e as fontes originais
        contexto_recuperado = "\n".join([hit.payload.get("text", "") for hit in resultados])
        fontes = list(set([hit.payload.get("source", "Desconhecida") for hit in resultados]))

        # Retorno provisório para validar a pesquisa vetorial antes da geração de texto
        return {
            "response": f"Contexto encontrado na base de dados:\n{contexto_recuperado}",
            "sources": fontes
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))