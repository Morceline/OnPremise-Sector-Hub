"""
models/config.py
------------------
Esquemas Pydantic para a configuração do setor (RF04) e para a mensagem
de chat do colaborador.

Mudanças:
- `sector_type` (enum) foi adicionado para o bot "saber com quem está
  lidando" (jurídico, saúde, RH, militar, alimentício, etc.) — pedido
  explícito do usuário para adaptar tom e regras por setor.
- `allowed_web_urls` / `blocked_web_urls` continuam como HttpUrl, mas agora
  documentamos que só `allowed_web_urls` é de fato consultado (blocklist de
  URL é reservada para casos em que um domínio pai é liberado, mas um
  caminho específico deve ser excluído).
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class SectorType(str, Enum):
    """
    Setores conhecidos. Usado para ajustar o tom de voz e as regras padrão
    que o LLM recebe no prompt (ex: jurídico é mais formal, alimentício
    pode ser mais direto/casual).
    """

    JURIDICO = "juridico"
    SAUDE = "saude"
    RECURSOS_HUMANOS = "recursos_humanos"
    MILITAR = "militar"
    ALIMENTICIO = "alimenticio"
    FINANCEIRO = "financeiro"
    OPERACIONAL = "operacional"
    OUTRO = "outro"


class SectorConfig(BaseModel):
    sector_name: str = Field(..., min_length=1, description="Nome do setor/departamento")
    sector_type: SectorType = Field(default=SectorType.OUTRO)
    palette_color: str = Field(default="blue", description="Tema visual: blue | green | dark | light")
    niche_persona: str = Field(..., description="Persona/tom de voz da IA para este setor")

    allowed_local_paths: List[str] = Field(default_factory=list)
    blocked_local_paths: List[str] = Field(default_factory=list)

    allowed_web_urls: List[HttpUrl] = Field(default_factory=list)
    blocked_web_urls: List[HttpUrl] = Field(default_factory=list)

    # Conhecimento tácito: regras, jargões e "como a rotina funciona" que
    # normalmente só passam de boca a boca e não estão em nenhum documento.
    tacit_knowledge: Optional[str] = Field(default=None, max_length=8000)

    # Se True, o feedback (estrelas + comentário) é enviado por e-mail ao
    # término da conversa. O usuário final pode desativar (RNF de privacidade).
    feedback_email_enabled: bool = True
    feedback_email_to: Optional[str] = None


class ChatMessage(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    # Identifica se a pergunta veio do fluxo de "dúvidas de TI" (universal,
    # não depende da base RAG do setor) ou do chat normal do setor.
    session_id: Optional[str] = Field(
        default=None, description="ID de sessão opcional, usado só para agrupar feedback no fim da conversa."
    )
