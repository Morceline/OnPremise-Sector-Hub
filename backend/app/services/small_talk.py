"""
services/small_talk.py
-------------------------
Responde cumprimentos, agradecimentos e despedidas SEM chamar o modelo.

Por que existe: sem isso, "oi" entrava na busca de documentos e o modelo
respondia "não tenho essa informação", o que parece robótico e confuso. Aqui
a regra é simples e previsível: só mensagens curtas, formadas apenas por
palavras de conversa, são tratadas assim. Qualquer pergunta com conteúdo
(ex.: "qual o prazo de reembolso?") continua indo para a busca normalmente.
"""

import re
import unicodedata
from typing import Optional


def _normalize(text: str) -> str:
    """Minúsculo e sem acento: 'Você está?' -> 'voce esta?'"""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).lower()

MAX_TOKENS = 6

_GOODBYE_WORDS = {"tchau"}
_GOODBYE_PAIR = {"ate", "logo"}
_THANKS_WORDS = {"obrigado", "obrigada", "valeu", "vlw", "brigado"}
_HOW_WORDS = {"tudo", "como", "vai", "esta"}
_GREETING_WORDS = {"oi", "ola", "opa", "bom", "boa", "dia", "tarde", "noite"}

# Só estas palavras podem aparecer numa mensagem de conversa.
_ALLOWED = (
    _GOODBYE_WORDS | _GOODBYE_PAIR | _THANKS_WORDS | _HOW_WORDS | _GREETING_WORDS
    | {"bem", "voce", "vc", "de", "nada", "muito", "td", "tb", "e", "sim", "obrigado"}
)


# Perguntas: se a mensagem tiver uma destas palavras ou um "?", não é conversa.
_QUESTION_WORDS = {
    "qual", "quais", "quando", "onde", "quem", "quanto", "quanta", "quantos", "quantas",
    "porque", "pq", "como", "posso", "pode", "devo", "existe", "tem", "ha", "faco",
}
# Frases de encerramento que aparecem junto de outras palavras ("era so isso").
_CLOSING_PHRASES = ("era so isso", "so isso", "nada mais", "foi util", "ajudou", "perfeito", "ok", "entendi", "beleza")


def _is_closing_conversation(text: str, tokens: list) -> Optional[str]:
    """Agradecimento ou encerramento escrito com outras palavras. None se for pergunta."""
    if "?" in (text or "") or set(tokens) & _QUESTION_WORDS or len(tokens) > 14:
        return None
    normalized = " ".join(tokens)
    if set(tokens) & _THANKS_WORDS:
        return "thanks"
    if any(phrase in normalized for phrase in _CLOSING_PHRASES):
        return "closing"
    return None


def classify(text: str) -> Optional[str]:
    """Devolve 'goodbye', 'thanks', 'how_are_you' ou 'greeting'; None se não for conversa."""
    tokens = re.findall(r"[a-z]+", _normalize(text or ""))
    if not tokens:
        return None
    if len(tokens) > MAX_TOKENS or any(token not in _ALLOWED for token in tokens):
        return _is_closing_conversation(text, tokens)

    words = set(tokens)
    if words & _GOODBYE_WORDS or _GOODBYE_PAIR <= words:
        return "goodbye"
    if words & _THANKS_WORDS:
        return "thanks"
    if words & _HOW_WORDS:
        return "how_are_you"
    if words & _GREETING_WORDS:
        return "greeting"
    return None


def reply_for(intent: str, sector_name: Optional[str] = None) -> str:
    setor = f" do setor {sector_name}" if sector_name else ""
    if intent == "goodbye":
        return "Até logo! Quando precisar, estou por aqui."
    if intent == "thanks":
        return "De nada! Se precisar de mais alguma coisa, é só perguntar."
    if intent == "closing":
        return "Que bom que ajudou! Se precisar de mais alguma coisa, é só perguntar."
    if intent == "how_are_you":
        return "Estou bem, obrigado por perguntar! Em que posso ajudar hoje?"
    return f"Olá! Sou o assistente{setor}. Em que posso ajudar? Pode perguntar sobre processos, regras ou documentos do setor."
