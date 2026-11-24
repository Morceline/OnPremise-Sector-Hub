"""
services/file_search.py
--------------------------
Busca de ARQUIVOS, com resposta determinística (sem o modelo):
- dado exato (CPF, e-mail, número) na pergunta;
- período ("em outubro", "em 10/2026", "dia 15/05/2026") pela data de alteração;
- palavras (nome, pasta ou conteúdo do documento), como "onde está a Mariana?".

Observação: a data de alteração é a última modificação do arquivo; a data
de criação não é confiável em pastas sincronizadas.
"""

import re
from datetime import datetime
from typing import Optional

from app.services.catalog import Catalog
from app.services.query_normalizer import normalize as normalize_text
from app.services.terms import extract_terms

_SEARCH_HINTS = ("onde", "qual arquivo", "quais arquivos", "procur", "achar", "encontr", "tem arquivo",
                 "documento", "pasta", "arquivo", "foi criado", "foi feito", "foram")
_STOP = {"onde", "esta", "qual", "quais", "arquivo", "arquivos", "documento", "documentos", "pasta", "tem",
         "sobre", "para", "com", "que", "uma", "um", "dos", "das", "do", "da", "de", "no", "na", "em", "o", "a",
         "e", "foi", "foram", "feito", "feitos", "criado", "criados", "procura", "procurar", "achar", "encontrar",
         "meu", "minha", "esse", "essa", "dia", "mes", "ano", "alterado", "alterados", "alterada", "alteradas", "modificado", "modificados", "gerado", "gerados", "dia"}
_MONTHS = {"janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5, "junho": 6, "julho": 7,
           "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12}
_DATE_HINTS = ("criad", "alterad", "feit", "gerad", "modificad", "foram", "foi ", "em ", "dia ")
_DATE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(20\d{2})\b")
_MONTH_YEAR = re.compile(r"\b(\d{1,2})/(20\d{2})\b")
_YEAR = re.compile(r"\b(20\d{2})\b")
_MAX_RESULTS = 10


def _when(item) -> str:
    return datetime.fromtimestamp(item.mtime).strftime("%d/%m/%Y %H:%M") if item.mtime else "data desconhecida"


def _format(items, titulo: str) -> str:
    linhas = [titulo]
    for item in items[:_MAX_RESULTS]:
        linhas.append(f"- {item.name}: pasta {item.folder}, alterado em {_when(item)}")
    if len(items) > _MAX_RESULTS:
        linhas.append(f"... e mais {len(items) - _MAX_RESULTS}.")
    return "\n".join(linhas)


def _period(normalizada: str) -> Optional[dict]:
    """Período citado: dia, mês/ano ou mês (com ou sem ano)."""
    if not any(h in normalizada for h in _DATE_HINTS):
        return None
    match = _DATE.search(normalizada)
    if match:
        return {"day": int(match.group(1)), "month": int(match.group(2)), "year": int(match.group(3))}
    match = _MONTH_YEAR.search(normalizada)
    if match:
        return {"day": None, "month": int(match.group(1)), "year": int(match.group(2))}
    for nome, numero in _MONTHS.items():
        if re.search(rf"\b(em|de|do|no|dia) {nome}\b", normalizada):
            ano = _YEAR.search(normalizada)
            return {"day": None, "month": numero, "year": int(ano.group(1)) if ano else None}
    return None


def _in_period(item, period: dict) -> bool:
    if not item.mtime:
        return False
    data = datetime.fromtimestamp(item.mtime)
    if period.get("year") and data.year != period["year"]:
        return False
    if data.month != period["month"]:
        return False
    return period.get("day") is None or data.day == period["day"]


def answer_search(question: str, catalog: Catalog) -> Optional[str]:
    """Resposta de busca de arquivo, ou None se a pergunta não for de busca."""
    termos = extract_terms(question)
    if termos:
        encontrados = []
        for termo in termos:
            for source in catalog.sources_with_term(termo):
                item = catalog.get(source)
                if item and item not in encontrados:
                    encontrados.append(item)
        if encontrados:
            return _format(encontrados, "Encontrei esse dado nos arquivos:")
        return "Não encontrei esse dado em nenhum arquivo sincronizado. Se o arquivo é novo, use 'Sincronizar agora' e tente de novo."

    normalizada = normalize_text(question)
    if not any(hint in normalizada for hint in _SEARCH_HINTS):
        return None

    periodo = _period(normalizada)
    texto_sem_data = _DATE.sub(" ", _MONTH_YEAR.sub(" ", normalizada))
    palavras = [w for w in re.findall(r"[a-z0-9]{3,}", texto_sem_data)
                if w not in _STOP and w not in _MONTHS and not w.isdigit()]
    if periodo is None and not palavras:
        return None

    candidatos = catalog.file_items()
    if periodo is not None:
        candidatos = [i for i in candidatos if _in_period(i, periodo)]
    if palavras:
        filtrados = []
        for item in candidatos:
            nome = set(re.findall(r"[a-z0-9]{3,}", normalize_text(f"{item.name} {item.folder}")))
            conteudo = nome | catalog.words_for(item.source)
            if all(p in conteudo for p in palavras):
                filtrados.append(item)
        candidatos = filtrados

    if candidatos:
        return _format(candidatos, f"Encontrei {len(candidatos)} arquivo(s):")
    if periodo is not None and not palavras:
        return "Não encontrei arquivos alterados nesse período nas pastas sincronizadas."
    return f"Não encontrei arquivos com: {' '.join(palavras) or 'esses termos'}. Confira o nome ou tente outras palavras."
