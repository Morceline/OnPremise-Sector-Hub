"""
tests/test_query_normalizer.py
---------------------------------
Abreviações e erros de digitação: a correção só mexe no que é desconhecido e
nunca estraga palavras que já existem no vocabulário do setor.
"""

import pytest

from app.services.query_normalizer import correct_query, words_of

VOCAB = ["reembolso", "prazo", "ferias", "despesas", "pagamento"]


@pytest.mark.parametrize("entrada, esperado", [
    ("vc pode me ajudar", "voce pode me ajudar"),
    ("pq o prazo é curto", "porque o prazo é curto"),
    ("oq é reembolso", "o que é reembolso"),
    ("qnd sai o pagamento", "quando sai o pagamento"),
])
def test_abreviacoes_sao_expandidas(entrada, esperado):
    assert correct_query(entrada, VOCAB) == esperado


def test_erro_de_digitacao_e_corrigido_pelo_vocabulario():
    assert correct_query("qual o prazo de reembolco", VOCAB) == "qual o prazo de reembolso"
    assert correct_query("preciso de ferias", VOCAB) == "preciso de ferias"


def test_palavra_conhecida_nao_e_alterada_mesmo_parecida():
    assert correct_query("prazo", VOCAB) == "prazo"
    assert correct_query("despesas", VOCAB) == "despesas"


def test_palavras_curtas_nao_sao_corrigidas():
    assert correct_query("tem ferias", VOCAB) == "tem ferias"


def test_sem_vocabulario_so_expande_abreviacoes():
    assert correct_query("vc sabe o reembolco", []) == "voce sabe o reembolco"


def test_palavra_muito_diferente_e_mantida():
    assert correct_query("xptoabc", VOCAB) == "xptoabc"


def test_vocabulario_vem_das_palavras_dos_documentos():
    palavras = words_of("O prazo de Reembolso de despesas é de 5 dias úteis.")
    assert {"prazo", "reembolso", "despesas", "uteis"} <= palavras
    assert "de" not in palavras
