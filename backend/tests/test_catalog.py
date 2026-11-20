"""
tests/test_catalog.py
------------------------
O catálogo SQLite é a "memória" da sincronização: se ele errar, a
sincronização reindexa tudo sem necessidade ou deixa lixo no índice.
"""

from app.services.catalog import Catalog, CatalogItem


def _item(source="C:/docs/a.txt", **kw) -> CatalogItem:
    return CatalogItem(source=source, kind=kw.pop("kind", "file"), name=kw.pop("name", "a.txt"), **kw)


def test_grava_e_le_um_item(tmp_path):
    catalog = Catalog(str(tmp_path / "c.db"))
    catalog.upsert(_item(size=10, mtime=123.5, content_hash="abc", chunk_count=3, status="ok"))

    got = catalog.get("C:/docs/a.txt")

    assert got is not None
    assert (got.size, got.mtime, got.content_hash, got.chunk_count, got.status) == (10, 123.5, "abc", 3, "ok")


def test_item_inexistente_retorna_none(tmp_path):
    assert Catalog(str(tmp_path / "c.db")).get("nao-existe") is None


def test_upsert_atualiza_em_vez_de_duplicar(tmp_path):
    catalog = Catalog(str(tmp_path / "c.db"))
    catalog.upsert(_item(size=1))
    catalog.upsert(_item(size=2, status="erro", error="falhou"))

    assert catalog.get("C:/docs/a.txt").size == 2
    assert catalog.get("C:/docs/a.txt").status == "erro"
    assert len(catalog.sources()) == 1


def test_touch_so_atualiza_a_data_de_conferencia(tmp_path):
    catalog = Catalog(str(tmp_path / "c.db"))
    catalog.upsert(_item(size=5, last_checked_at="2026-01-01T00:00:00+00:00"))

    catalog.touch("C:/docs/a.txt", "2026-02-02T00:00:00+00:00")

    got = catalog.get("C:/docs/a.txt")
    assert got.last_checked_at == "2026-02-02T00:00:00+00:00"
    assert got.size == 5


def test_delete_remove_o_item(tmp_path):
    catalog = Catalog(str(tmp_path / "c.db"))
    catalog.upsert(_item())
    catalog.delete("C:/docs/a.txt")

    assert catalog.get("C:/docs/a.txt") is None


def test_sources_filtra_por_tipo(tmp_path):
    catalog = Catalog(str(tmp_path / "c.db"))
    catalog.upsert(_item("a.txt"))
    catalog.upsert(_item("https://x.com/p", kind="web", name="x"))

    assert catalog.sources() == {"a.txt", "https://x.com/p"}
    assert catalog.sources(kind="web") == {"https://x.com/p"}


def test_meta_grava_le_e_sobrescreve(tmp_path):
    catalog = Catalog(str(tmp_path / "c.db"))
    assert catalog.get_meta("k") is None

    catalog.set_meta("k", "1")
    catalog.set_meta("k", "2")

    assert catalog.get_meta("k") == "2"


def test_meta_json_invalido_retorna_none(tmp_path):
    catalog = Catalog(str(tmp_path / "c.db"))
    catalog.set_meta("k", "{quebrado")
    catalog.set_meta("ok", '{"a": 1}')

    assert catalog.get_meta_json("k") is None
    assert catalog.get_meta_json("ok") == {"a": 1}


def test_stats_conta_por_tipo_e_situacao(tmp_path):
    catalog = Catalog(str(tmp_path / "c.db"))
    catalog.upsert(_item("a.txt", chunk_count=2))
    catalog.upsert(_item("b.pdf", status="sem_texto"))
    catalog.upsert(_item("c.pdf", status="erro"))
    catalog.upsert(_item("https://x.com/p", kind="web", chunk_count=4))
    catalog.upsert(_item("Regras", kind="tacit", chunk_count=1))

    assert catalog.stats() == {
        "files": 3, "web": 1, "tacit": 1, "chunks": 7, "errors": 1, "without_text": 1,
    }


def test_dados_sobrevivem_a_reabrir_o_banco(tmp_path):
    path = str(tmp_path / "pasta" / "c.db")  # a pasta ainda não existe
    Catalog(path).upsert(_item("relatório_ação.txt", name="relatório_ação.txt"))

    assert Catalog(path).get("relatório_ação.txt") is not None


def test_delete_meta_remove_a_chave(tmp_path):
    catalog = Catalog(str(tmp_path / "c.db"))
    catalog.set_meta("k", "1")
    catalog.delete_meta("k")

    assert catalog.get_meta("k") is None
