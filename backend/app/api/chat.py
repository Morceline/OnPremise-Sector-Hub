from fastapi import APIRouter, HTTPException
from app.models.config import ChatMessage
from app.services.rag_engine import RAGEngine
import httpx
import os

router = APIRouter()

@router.post("/query")
async def process_chat(payload: ChatMessage):
    try:
        rag_engine = RAGEngine()
        
        # 1. Busca os documentos usando a função search corrigida do RAGEngine
        resultados = await rag_engine.search(query_text=payload.message, limit=3)

        # O Qdrant moderno retorna os resultados dentro de .points ou direto na lista dependendo do método
        contexto_recuperado = "\n".join([hit.payload.get("text", "") for hit in resultados])
        fontes = list(set([hit.payload.get("source", "Desconhecida") for hit in resultados]))

        # Se não houver contexto, avisamos a IA
        if not contexto_recuperado.strip():
            contexto_recuperado = "Nenhum documento encontrado na base de dados para responder a isto."

        # 2. Montar o Prompt para o Ollama
        prompt_final = f"""Você é um assistente corporativo. Use APENAS o contexto abaixo para responder à pergunta. 
Se a resposta não estiver no contexto, diga que não tem essa informação.

Contexto:
{contexto_recuperado}

Pergunta: {payload.message}
Resposta:"""

        # 3. Enviar para o Ollama gerar a resposta final
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        async with httpx.AsyncClient() as client:
            resposta_ia = await client.post(
                f"{ollama_host}/api/generate",
                json={
                    "model": "qwen2.5:3b",
                    "prompt": prompt_final,
                    "stream": False
                },
                timeout=60.0
            )
            
            resposta_json = resposta_ia.json()
            texto_gerado = resposta_json.get("response", "Erro na geração.")

        return {
            "response": texto_gerado,
            "sources": fontes
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
