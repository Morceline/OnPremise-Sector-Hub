"""
tests/test_it_topics.py
--------------------------
Temas fixos de TI: a dúvida certa cai no tema certo, e perigo tem prioridade.
"""

import pytest

from app.services.it_topics import SAFETY_TEXT, answer_for, list_titles


@pytest.mark.parametrize("duvida, tema", [
    ("minha impressora não imprime", "Impressora não imprime"),
    ("o mouse parou", "Teclado, mouse ou monitor não funcionam"),
    ("a tela está preta, sem imagem", "Teclado, mouse ou monitor não funcionam"),
    ("o computador está muito lento", "Sistema ou site travou, ou o computador está lento"),
    ("sem internet hoje", "Sem internet ou Wi-Fi"),
    ("não abro a pasta da equipe", "Não consigo abrir a pasta da equipe"),
    ("a planilha mostra erro na fórmula", "Problema em planilha"),
    ("não sai som", "Sem som"),
    ("como salvar um arquivo", "Dúvida básica de uso do computador"),
])
def test_duvida_cai_no_tema_certo(duvida, tema):
    assert answer_for(duvida).startswith(tema)


def test_resposta_de_tema_traz_perguntas_passos_e_escalonamento():
    texto = answer_for("minha impressora não imprime")
    assert "Antes, responda para você:" in texto
    assert "Tente, nesta ordem:" in texto
    assert "1. " in texto and "2. " in texto and "3. " in texto
    assert "TI" in texto


def test_fumaca_tem_prioridade_sobre_qualquer_tema():
    assert answer_for("a impressora está soltando fumaça") == SAFETY_TEXT
    assert "chame a TI" in SAFETY_TEXT


def test_duvida_fora_dos_temas_devolve_none_para_o_modelo():
    assert answer_for("quero saber sobre férias") is None


def test_lista_de_temas_para_os_atalhos():
    titulos = [t["title"] for t in list_titles()]
    assert "Impressora não imprime" in titulos
    assert "Sem som" in titulos
    assert len(titulos) == 8
