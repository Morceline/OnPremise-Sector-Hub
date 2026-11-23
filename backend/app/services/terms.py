"""
services/terms.py
-------------------
Termos EXATOS extraídos dos documentos durante a indexação: CPF válido,
e-mail e sequências numéricas longas (número de processo, pedido, RG).

Por que existe: busca por significado não acha uma sequência exata. Guardar
esses termos à parte permite responder "em qual arquivo está este CPF?" com
precisão, sem depender do modelo.
"""

import re
from typing import Set



def only_digits(value: str) -> str:
    return re.sub(r"\D", "", value)


def is_valid_cpf(value: str) -> bool:
    """Confere os dois dígitos verificadores do CPF."""
    digits = only_digits(value)
    if len(digits) != 11 or digits == digits[0] * 11:
        return False
    for size in (9, 10):
        total = sum(int(d) * w for d, w in zip(digits[:size], range(size + 1, 1, -1)))
        if (total * 10) % 11 % 10 != int(digits[size]):
            return False
    return True

_CPF = re.compile(r"(?<!\d)(\d{3}\.?\d{3}\.?\d{3}-?\d{2})(?!\d)")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_NUMBER = re.compile(r"(?<!\d)(\d{5,})(?!\d)")


def extract_terms(text: str) -> Set[str]:
    terms: Set[str] = set()
    for match in _CPF.finditer(text or ""):
        digits = only_digits(match.group(1))
        if is_valid_cpf(digits):
            terms.add(digits)
    for match in _EMAIL.finditer(text or ""):
        terms.add(match.group(0).lower())
    for match in _NUMBER.finditer(text or ""):
        terms.add(match.group(1))
    return terms
