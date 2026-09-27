from pydantic import BaseModel, HttpUrl
from typing import List, Optional

class SectorConfig(BaseModel):
    sector_name: str
    palette_color: str = "blue"
    niche_persona: str  # Ex: Jurídico, Saúde, Recursos Humanos
    allowed_local_paths: List[str] = []
    blocked_local_paths: List[str] = []
    allowed_web_urls: List[HttpUrl] = []
    blocked_web_urls: List[HttpUrl] = []
    tacit_knowledge: Optional[str] = None  # Caixa de texto de diretrizes e jargões

class ChatMessage(BaseModel):
    message: str