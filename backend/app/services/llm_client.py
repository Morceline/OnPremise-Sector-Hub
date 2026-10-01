"""
services/llm_client.py
-------------------------
Wrapper único para chamadas de geração de texto ao Ollama.

(o conhecimento de TI é universal, não depende
dos documentos do setor).
"""

import logging

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)


class LLMGenerationError(Exception):
    """Erro ao gerar resposta no Ollama (host fora do ar, modelo ausente etc.)."""


async def generate_completion(
    prompt: str,
    http_client: httpx.AsyncClient,
    settings: Settings,
) -> str:
    try:
        response = await http_client.post(
            f"{settings.ollama_host}/api/generate",
            json={"model": settings.llm_model, "prompt": prompt, "stream": False},
            timeout=settings.request_timeout_seconds,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.exception("Falha ao chamar o Ollama em %s", settings.ollama_host)
        raise LLMGenerationError(
            "Não foi possível falar com o modelo local (Ollama). Verifique se ele está em execução."
        ) from exc

    data = response.json()
    text = data.get("response")
    if not text:
        raise LLMGenerationError("O modelo local não retornou nenhum texto.")
    return text
