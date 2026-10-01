"""
api/chat.py
------------
Endpoint principal do chat do colaborador: recebe a pergunta, busca contexto
no Qdrant (RAG) e gera a resposta final com o LLM local.

Mudanças:
- RAGEngine e o httpx.AsyncClient não são mais instanciados a cada request
  (Depends injeta os singletons criados no lifespan da aplicação).
- Prompt agora inclui a persona/tom de voz e as regras táticas do setor,
  lidas da configuração ativa persistida.
- Erros de comunicação com o Ollama retornam 503 (serviço indisponível),
  não 500 — 500 sugere bug da aplicação, 503 deixa claro que é um serviço
  externo (o Ollama) que está fora do ar, o que ajuda o usuário a
  diagnosticar sozinho sem chamar o suporte.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from httpx import AsyncClient
from qdrant_client.http.exceptions import UnexpectedResponse

from app.core.config import Settings, get_settings
from app.core.dependencies import get_http_client, get_rag_engine
from app.models.config import ChatMessage
from app.services.llm_client import LLMGenerationError, generate_completion
from app.services.persistence import load_active_config
from app.services.rag_engine import RAGEngine

logger = logging.getLogger(__name__)
router = APIRouter()


def _build_prompt(question: str, context: str, settings: Settings) -> str:
    active_config = load_active_config(settings.active_config_path)

    persona = active_config.niche_persona if active_config else "assistente corporativo neutro"
    tacit_rules = active_config.tacit_knowledge if active_config and active_config.tacit_knowledge else ""

    tacit_block = f"\nRegras e diretrizes internas do setor:\n{tacit_rules}\n" if tacit_rules else ""

    return f"""Você é um assistente corporativo do setor, agindo com a seguinte persona: {persona}.
Use APENAS o contexto abaixo para responder à pergunta. Se a resposta não estiver no
contexto, diga claramente que não tem essa informação — nunca invente.
{tacit_block}
Contexto recuperado da base de conhecimento:
{context}

Pergunta do colaborador: {question}
Resposta:"""


@router.post("/query")
async def process_chat(
    payload: ChatMessage,
    rag_engine: RAGEngine = Depends(get_rag_engine),
    http_client: AsyncClient = Depends(get_http_client),
    settings: Settings = Depends(get_settings),
):
    try:
        resultados = await rag_engine.search(query_text=payload.message, limit=3)
    except UnexpectedResponse as exc:
        logger.exception("Qdrant retornou erro inesperado durante a busca.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de conhecimento indisponível no momento. Tente novamente em instantes.",
        ) from exc

    contexto_recuperado = "\n".join(hit.payload.get("text", "") for hit in resultados)
    fontes = sorted({hit.payload.get("source", "Desconhecida") for hit in resultados})

    if not contexto_recuperado.strip():
        contexto_recuperado = "Nenhum documento encontrado na base de dados para responder a isto."

    prompt_final = _build_prompt(payload.message, contexto_recuperado, settings)

    try:
        texto_gerado = await generate_completion(prompt_final, http_client, settings)
    except LLMGenerationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return {"response": texto_gerado, "sources": fontes}
