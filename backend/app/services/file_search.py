"""
services/file_search.py
--------------------------
Busca de ARQUIVOS: onde está, quais arquivos tratam de um CPF, número ou
e-mail, e quais nomes batem com o que a pessoa pediu. Responde com caminho,
pasta e data de alteração, de forma determinística (sem o modelo).

Ordem: termos exatos (CPF, e-mail, número) > nome e pasta.
"""

import re
from typing import Optional

from app.services.catalog import Catalog
from app.services.query_normalizer import normalize as normalize_text
from app.services.terms import extract_terms

_SEARCH_HINTS = ("onde", "qual arquivo", "quais arquivos", "procur", "achar", "encontr", "tem arquivo",
                 "documento", "pasta", "arquivo", "foi criado", "foi feito")
_STOP = {"onde", "esta", "qual", "quais", "arquivo", "arquivos", "documento", "documentos", "pasta", "tem", "tem",
         "sobre", "para", "com", "que", "uma", "um", "dos", "das", "do", "da", "de", "no", "na", "em", "o", "a", "e",
         "foi", "feito", "criado", "procura", "procurar", "achar", "encontrar", "meu", "minha", "esse", "essa"}
_MAX_RESULTS = 10


def _when(item) -> str:
    from datetime import datetime
    return datetime.fromtimestamp(item.mtime).strftime("%d/%m/%Y %H:%M") if item.mtime else "data desconhecida"


def _format(items, titulo: str) -> str:
    linhas = [titulo]
    for item in items[:_MAX_RESULTS]:
        linhas.append(f"- {item.name}: pasta {item.folder}, alterado em {_when(item)}")
    if len(items) > _MAX_RESULTS:
        linhas.append(f"... e mais {len(items) - _MAX_RESULTS}.")
    return "\n".join(linhas)


def answer_search(question: str, catalog: Catalog) -> Optional[str]:
    """Resposta de busca de arquivo, ou None se a pergunta não for de busca."""
    # 1) dado exato na pergunta (CPF, e-mail, número)
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

    # 2) pergunta de localização: nome ou pasta
    normalizada = normalize_text(question)
    if not any(hint in normalizada for hint in _SEARCH_HINTS):
        return None
    palavras = [w for w in re.findall(r"[a-z0-9]{3,}", normalizada) if w not in _STOP]
    if not palavras:
        return None
    achados = []
    for item in catalog.file_items():
        texto = normalize_text(f"{item.name} {item.folder}")
        if all(p in texto for p in palavras):
            achados.append(item)
    if achados:
        return _format(achados, f"Encontrei {len(achados)} arquivo(s):")
    return f"Não encontrei arquivos com: {' '.join(palavras)}. Confira o nome ou tente outras palavras."
