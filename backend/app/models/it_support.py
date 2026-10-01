"""
models/it_support.py
----------------------
Esquemas do fluxo universal de dúvidas de TI (periférico, rede, sistema
lento, servidor). Esse fluxo é INDEPENDENTE da base RAG do setor —
todo bot, não importa o setor, deve saber responder isso.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

class ITCategory(str, Enum):
    REDE = "rede"
    PERIFERICO = "periferico"
    SISTEMA_LENTO = "sistema_lento"
    SERVIDOR = "servidor"
    DOCUMENTOS_PLANILHAS = "documentos_planilhas"
    OUTRO = "outro"


class ITSupportQuery(BaseModel):
    problem_description: str = Field(..., min_length=1, max_length=2000)
    category: Optional[ITCategory] = Field(
        default=None, description="Se não informado, a IA tenta inferir pela descrição."
    )
    # Quando o usuário aperta "não entendi, explique mais simples".
    simplify: bool = Field(default=False)
    # Texto da resposta anterior, necessário só quando simplify=True,
    # para a IA reescrever de forma mais simples em vez de repetir do zero.
    previous_answer: Optional[str] = Field(default=None, max_length=4000)
