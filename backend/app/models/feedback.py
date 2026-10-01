"""
models/feedback.py
--------------------
Esquema do feedback enviado pelo colaborador ao final da conversa
(avaliação por estrelas + comentário opcional).
"""

from typing import Optional

from pydantic import BaseModel, Field

class FeedbackPayload(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Avaliação de 1 a 5 estrelas")
    comment: Optional[str] = Field(default=None, max_length=2000)
    session_id: Optional[str] = Field(default=None)
    sector_name: Optional[str] = Field(default=None)
