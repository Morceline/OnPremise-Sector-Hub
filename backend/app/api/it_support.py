"""
api/it_support.py
--------------------
Fluxo UNIVERSAL de dúvidas básicas de TI (periférico, rede, sistema lento,
servidor, planilhas/documentos). Diferente do chat do setor, este endpoint
NÃO depende da base RAG cadastrada pelo gestor — todo bot, em qualquer
setor, deve saber sugerir passos básicos de TI.

O objetivo é reduzir chamados triviais ao TI: o colaborador testa passos
simples e seguros primeiro, sem precisar de conhecimento técnico ou
ferramentas especiais. Por isso o prompt exige explicitamente:
- linguagem simples, sem jargão técnico;
- passos que não exigem abrir o gabinete, instalar software ou ter
  permissão de administrador;
- reconhecer quando o usuário não pode prosseguir (falta de periférico
  para testar, por exemplo) e nesse caso orientar a abrir um chamado real.

O modo `simplify=True` implementa o balão "não entendi, explique mais
simples" reescreve a última resposta em linguagem
ainda mais simples, em vez de gerar uma resposta nova do zero.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from httpx import AsyncClient

from app.core.config import Settings, get_settings
from app.core.dependencies import get_http_client
from app.models.it_support import ITSupportQuery
from app.services.llm_client import LLMGenerationError, generate_completion

router = APIRouter()

_BASE_SYSTEM_PROMPT = """Você é um assistente de suporte de TI de primeiro nível, falando com um \
colaborador SEM conhecimento técnico. Regras obrigatórias:
1. Use linguagem simples, cotidiana, sem jargão técnico.
2. Sugira no máximo 3 passos por vez, numerados, que a pessoa consiga fazer sozinha, \
sem abrir o computador, sem instalar nada e sem precisar de permissão de administrador.
3. Se o problema exigir hardware que a pessoa não tem, acesso que ela não possui, ou for \
claramente algo que só a equipe de TI pode resolver, diga isso claramente e recomende \
abrir um chamado — não invente soluções arriscadas.
4. Nunca peça para a pessoa mexer em configurações de rede avançadas, registro do Windows \
ou qualquer coisa que possa piorar o problema.
"""


def _build_prompt(payload: ITSupportQuery) -> str:
    if payload.simplify and payload.previous_answer:
        return f"""{_BASE_SYSTEM_PROMPT}
A resposta abaixo foi considerada difícil de entender pelo colaborador. Reescreva-a de forma \
AINDA MAIS simples, com frases curtas, como se explicasse para alguém que nunca usou o termo técnico antes:

Resposta original:
{payload.previous_answer}

Nova resposta simplificada:"""

    category_hint = f"Categoria informada: {payload.category.value}.\n" if payload.category else ""
    return f"""{_BASE_SYSTEM_PROMPT}
{category_hint}Problema relatado pelo colaborador: {payload.problem_description}

Responda com os passos simples que a pessoa pode tentar agora:"""


@router.post("/query")
async def query_it_support(
    payload: ITSupportQuery,
    http_client: AsyncClient = Depends(get_http_client),
    settings: Settings = Depends(get_settings),
):
    prompt = _build_prompt(payload)

    try:
        texto_gerado = await generate_completion(prompt, http_client, settings)
    except LLMGenerationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return {"response": texto_gerado}
