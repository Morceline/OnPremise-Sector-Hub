"""
tests/test_small_talk.py
---------------------------
Regra que decide o que é conversa e o que é pergunta de trabalho. Erro aqui
faz o bot responder "oi" como se fosse documento, ou ignorar uma pergunta real.
"""

import pytest

from app.services.small_talk import classify, reply_for


@pytest.mark.parametrize("mensagem, esperado", [
    ("oi", "greeting"),
    ("Oi!", "greeting"),
    ("bom dia", "greeting"),
    ("Boa tarde!", "greeting"),
    ("olá, boa noite", "greeting"),
    ("tudo bem?", "how_are_you"),
    ("oi, tudo bem", "how_are_you"),
    ("como você está", "how_are_you"),
    ("obrigado", "thanks"),
    ("valeu!", "thanks"),
    ("tchau", "goodbye"),
    ("até logo", "goodbye"),
])
def test_conversa_curta_e_classificada(mensagem, esperado):
    assert classify(mensagem) == esperado


@pytest.mark.parametrize("mensagem", [
    "qual o prazo de reembolso?",
    "bom dia, qual o prazo de reembolso?",
    "como faço para pedir férias",
    "",
    "   ",
    "oi oi oi oi oi oi oi",
    "obrigado, como faço para pedir férias?",
    "qual o prazo? obrigado",
])
def test_pergunta_de_trabalho_nao_e_tratada_como_conversa(mensagem):
    assert classify(mensagem) is None


def test_resposta_usa_o_nome_do_setor():
    assert "do setor Jurídico" in reply_for("greeting", "Jurídico")
    assert "assistente do setor" not in reply_for("greeting", None)


@pytest.mark.parametrize("mensagem, esperado", [
    ("obrigado, era só isso", "thanks"),
    ("muito obrigado pela ajuda", "thanks"),
    ("valeu, foi útil", "thanks"),
    ("ok, entendi, obrigado", "thanks"),
    ("era só isso mesmo", "closing"),
])
def test_agradecimento_e_encerramento_com_outras_palavras(mensagem, esperado):
    assert classify(mensagem) == esperado


def test_resposta_de_encerramento_nao_repete_informacao():
    assert "prazo" not in reply_for("closing").lower()
