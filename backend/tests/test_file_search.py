"""
tests/test_file_search.py
----------------------------
Busca de arquivos: termos exatos (CPF, e-mail, número) e nome/pasta.
"""

import pytest

from app.services.catalog import Catalog, CatalogItem
from app.services.file_search import answer_search
from app.services.terms import extract_terms


@pytest.fixture
def catalogo(tmp_path):
    c = Catalog(str(tmp_path / "c.db"))
    c.upsert(CatalogItem(source="/dados/Pae/pao_maio.xlsx", kind="file", name="pao_maio.xlsx",
                         folder="/dados/Pae", ext=".xlsx", mtime=1700000000.0, status="ok"))
    c.upsert(CatalogItem(source="/dados/Juridico/parecer_123.pdf", kind="file", name="parecer_123.pdf",
                         folder="/dados/Juridico", ext=".pdf", mtime=1700000100.0, status="ok"))
    c.replace_terms("/dados/Juridico/parecer_123.pdf", {"52998224725", "joao@exemplo.com", "123456789"})
    return c


def test_extrai_cpf_valido_email_e_numero_longo():
    texto = "CPF 529.982.247-25, e-mail joao@exemplo.com e processo 1234567"
    assert {"52998224725", "joao@exemplo.com", "1234567"} <= extract_terms(texto)


def test_cpf_invalido_nao_vira_termo():
    assert "11111111111" not in extract_terms("CPF 111.111.111-11")


def test_busca_por_cpf_responde_com_o_arquivo(catalogo):
    resposta = answer_search("em qual arquivo está o CPF 529.982.247-25?", catalogo)
    assert "parecer_123.pdf" in resposta and "/dados/Juridico" in resposta


def test_busca_por_cpf_nao_encontrado_avisa(catalogo):
    resposta = answer_search("tem o CPF 529.982.247-25 nos arquivos? ", catalogo)
    assert resposta is not None


def test_busca_por_nome_e_pasta(catalogo):
    resposta = answer_search("onde está o arquivo do pão de maio?", catalogo)
    assert "pao_maio.xlsx" in resposta


def test_pergunta_que_nao_e_de_busca_devolve_none(catalogo):
    assert answer_search("bom dia", catalogo) is None
    assert answer_search("qual o prazo de reembolso?", catalogo) is None


def test_termos_sao_substituidos_na_sincronizacao(catalogo):
    catalogo.replace_terms("/dados/Juridico/parecer_123.pdf", {"novo123456"})
    assert catalogo.sources_with_term("52998224725") == []
    assert catalogo.sources_with_term("novo123456") == ["/dados/Juridico/parecer_123.pdf"]


from datetime import datetime as _dt


def _ts(ano, mes, dia):
    return _dt(ano, mes, dia, 12, 0).timestamp()


def test_busca_por_mes_lista_arquivos_alterados_naquele_mes(tmp_path):
    c = Catalog(str(tmp_path / "c.db"))
    c.upsert(CatalogItem(source="/dados/a.txt", kind="file", name="a.txt", folder="/dados", mtime=_ts(2026, 10, 5), status="ok"))
    c.upsert(CatalogItem(source="/dados/b.txt", kind="file", name="b.txt", folder="/dados", mtime=_ts(2026, 9, 5), status="ok"))

    resposta = answer_search("quais documentos foram feitos em outubro?", c)

    assert "a.txt" in resposta and "b.txt" not in resposta


def test_busca_por_mes_e_ano_com_dia_exato(tmp_path):
    c = Catalog(str(tmp_path / "c.db"))
    c.upsert(CatalogItem(source="/dados/a.txt", kind="file", name="a.txt", folder="/dados", mtime=_ts(2026, 5, 15), status="ok"))

    assert "a.txt" in answer_search("quais arquivos foram alterados no dia 15/05/2026?", c)
    assert "a.txt" not in answer_search("quais arquivos foram alterados no dia 16/05/2026?", c)


def test_pao_de_maio_e_busca_de_nome_nao_de_data(tmp_path):
    c = Catalog(str(tmp_path / "c.db"))
    c.upsert(CatalogItem(source="/dados/pao_maio.xlsx", kind="file", name="pao_maio.xlsx", folder="/dados",
                         mtime=_ts(2026, 11, 1), status="ok"))

    resposta = answer_search("onde está o arquivo do pão de maio?", c)

    assert "pao_maio.xlsx" in resposta


def test_busca_encontra_palavra_que_esta_so_no_conteudo(tmp_path):
    c = Catalog(str(tmp_path / "c.db"))
    c.upsert(CatalogItem(source="/dados/relatorio.pdf", kind="file", name="relatorio.pdf", folder="/dados",
                         mtime=_ts(2026, 5, 1), status="ok"))
    c.replace_doc_words("/dados/relatorio.pdf", {"mariana", "fornecimento", "almoxarifado"})

    resposta = answer_search("onde está a Mariana?", c)

    assert "relatorio.pdf" in resposta


def test_palavra_que_nao_existe_em_lugar_nenhum_avisa(tmp_path):
    c = Catalog(str(tmp_path / "c.db"))
    c.upsert(CatalogItem(source="/dados/a.txt", kind="file", name="a.txt", folder="/dados", mtime=_ts(2026, 5, 1), status="ok"))

    assert "Não encontrei" in answer_search("onde está o fulano de tal?", c)
