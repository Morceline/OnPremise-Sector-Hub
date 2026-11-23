"""
api/it_support.py
--------------------
Fluxo UNIVERSAL de dúvidas básicas de TI (periférico, rede, sistema lento,
servidor, planilhas/documentos). Diferente do chat do setor, este endpoint
NÃO depende da base RAG cadastrada pelo gestor — todo bot, em qualquer
setor, deve saber sugerir passos básicos de TI, conforme pedido do usuário.

O objetivo é reduzir chamados triviais ao TI: o colaborador testa passos
simples e seguros primeiro, sem precisar de conhecimento técnico ou
ferramentas especiais. Por isso o prompt exige explicitamente:
- linguagem simples, sem jargão técnico;
- passos que não exigem abrir o gabinete, instalar software ou ter
  permissão de administrador;
- reconhecer quando o usuário não pode prosseguir (falta de periférico
  para testar, por exemplo) e nesse caso orientar a abrir um chamado real.

O modo `simplify=True` implementa o balão "não entendi, explique mais
simples" pedido pelo usuário: reescreve a última resposta em linguagem
ainda mais simples, em vez de gerar uma resposta nova do zero.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from httpx import AsyncClient

from app.core.config import Settings, get_settings
from app.core.activity import ActivityGate
from app.core.dependencies import get_activity_gate, get_http_client
from app.models.it_support import ITSupportQuery
from pydantic import BaseModel, Field

from app.services import it_flows
from app.services.it_topics import answer_for, list_titles
from app.services.llm_client import LLMGenerationError, generate_completion

router = APIRouter()

_BASE_SYSTEM_PROMPT = """Você ajuda uma pessoa SEM conhecimento de informática a resolver um problema simples no computador.
Fale como um colega paciente, que não é da área de tecnologia:
- Frases curtas, com no máximo 15 palavras cada. Palavras do dia a dia.
- Nunca use termos técnicos: cache, driver, servidor, rede, IP, registro, sistema operacional, navegador, processo, memória RAM, configurações avançadas. Se precisar citar algo, diga o que a pessoa VÊ na tela.
- No máximo 3 passos, numerados. Cada passo com uma única ação.
- Nunca peça para abrir o computador, instalar programas, apagar arquivos importantes ou mexer em configurações avançadas.
- Se o problema precisar da equipe de TI, diga isso em uma frase e peça para abrir um chamado.
- Escreva com português correto e revise as palavras antes de responder."""

# Limites para a resposta ficar curta e o modelo não inventar tanto.
_GENERATION_OPTIONS = {"temperature": 0.2, "num_predict": 220}


def _build_prompt(payload: ITSupportQuery) -> str:
    if payload.simplify and payload.previous_answer:
        return f"""{_BASE_SYSTEM_PROMPT}
Problema original: {payload.problem_description}
A resposta abaixo ficou difícil de entender. Reescreva em no máximo 3 passos, seguindo todas as regras acima:

Resposta difícil:
{payload.previous_answer}

Nova resposta simples:"""

    category_hint = f"Categoria informada: {payload.category.value}.\n" if payload.category else ""
    return f"""{_BASE_SYSTEM_PROMPT}
{category_hint}Problema relatado pelo colaborador: {payload.problem_description}

Responda com os passos simples que a pessoa pode tentar agora:"""


@router.post("/query")
async def query_it_support(
    payload: ITSupportQuery,
    http_client: AsyncClient = Depends(get_http_client),
    settings: Settings = Depends(get_settings),
    gate: ActivityGate = Depends(get_activity_gate),
):
    # Dúvida que casa com um tema revisado: resposta fixa, sem o modelo.
    if not payload.simplify:
        topic_answer = answer_for(payload.problem_description)
        if topic_answer is not None:
            return {"response": topic_answer}

    prompt = _build_prompt(payload)

    async with gate.chat():  # a sincronização em segundo plano cede a vez
        try:
            texto_gerado = await generate_completion(prompt, http_client, settings, options=_GENERATION_OPTIONS)
        except LLMGenerationError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return {"response": texto_gerado}


@router.get("/topics")
async def get_topics():
    """Temas de TI para os atalhos da tela."""
    return {"topics": list_titles()}


class StartRequest(BaseModel):
    flow_id: str = Field(..., max_length=40)


class StepRequest(BaseModel):
    node_id: str = Field(..., max_length=60)
    option: int = Field(..., ge=0, le=20)


class TriageRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)


@router.get("/menu")
async def get_menu():
    return it_flows.menu()


@router.post("/start")
async def start_flow(payload: StartRequest):
    node = it_flows.start(payload.flow_id)
    if node is None:
        raise HTTPException(status_code=404, detail="Tema não encontrado.")
    return node


@router.post("/step")
async def next_step(payload: StepRequest):
    node = it_flows.step(payload.node_id, payload.option)
    if node is None:
        raise HTTPException(status_code=400, detail="Opção inválida para esta etapa.")
    return node


@router.post("/triage")
async def triage_problem(payload: TriageRequest):
    return it_flows.triage(payload.text)


class AnswerRequest(BaseModel):
    node_id: str = Field(..., max_length=60)
    text: str = Field(..., min_length=1, max_length=500)


@router.post("/answer")
async def answer_free_text(payload: AnswerRequest):
    return it_flows.answer_text(payload.node_id, payload.text)
