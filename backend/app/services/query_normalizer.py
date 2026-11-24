"""
services/query_normalizer.py
------------------------------
Entende o que a pessoa quis dizer quando digita rápido: expande abreviações
comuns ("vc", "pq", "oq") e corrige erros de digitação de palavras que NÃO
existem no vocabulário dos documentos do setor ("reembolco" -> "reembolso").

Regras de segurança:
- abreviações são trocadas por um dicionário fixo (determinístico);
- erros só são corrigidos em palavras com 4 letras ou mais e que não existem
  no vocabulário; palavras reconhecidas nunca são alteradas;
- a correção tem limiar alto de semelhança (80%).
"""

import difflib
import re
import unicodedata
from typing import Iterable, List, Set

ABBREVIATIONS = {
    "vc": "voce", "vcs": "voces", "pq": "porque", "oq": "o que", "tbm": "tambem", "tb": "tambem",
    "qdo": "quando", "qnd": "quando", "dps": "depois", "hj": "hoje", "qnt": "quanto",
    "qts": "quantos", "fzr": "fazer", "pra": "para", "pro": "para o", "msg": "mensagem",
}

# Palavras comuns de pergunta e de busca: nunca são "corrigidas" para outra palavra.
PROTECTED = {
    "quais", "qual", "foram", "foi", "sobre", "alterado", "alterados", "alterada", "alteradas", "criado", "criados",
    "feito", "feitos", "documento", "documentos", "arquivo", "arquivos", "pasta", "pastas", "onde", "esta", "estao",
    "tem", "tinha", "faco", "fazer", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro",
    "dezembro", "janeiro", "fevereiro", "marco", "abril", "problema", "mensagem",
}

_WORD = re.compile(r"[A-Za-zÀ-ÿ]+")
_MIN_LEN_TO_CORRECT = 4
_CUTOFF = 0.8


def normalize(text: str) -> str:
    """Minúsculo e sem acento: 'Reembolsó' -> 'reembolso'."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).lower()


def words_of(text: str) -> Set[str]:
    """Palavras relevantes (4+ letras) de um texto, normalizadas. Alimenta o vocabulário."""
    return {w for w in re.findall(r"[a-z]+", normalize(text)) if len(w) >= _MIN_LEN_TO_CORRECT}


def correct_query(text: str, vocabulary: Iterable[str]) -> str:
    """Devolve a pergunta com abreviações expandidas e erros de digitação corrigidos."""
    vocab: List[str] = list(vocabulary or [])
    vocab_set = set(vocab)

    def fix(match: "re.Match[str]") -> str:
        original = match.group(0)
        word = normalize(original)
        if word in ABBREVIATIONS:
            return ABBREVIATIONS[word]
        if len(word) < _MIN_LEN_TO_CORRECT or word in vocab_set or word in PROTECTED or not vocab:
            return original
        close = difflib.get_close_matches(word, vocab, n=1, cutoff=_CUTOFF)
        return close[0] if close else original

    return _WORD.sub(fix, text or "")
