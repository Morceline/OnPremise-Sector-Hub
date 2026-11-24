"""
services/catalog.py
---------------------
Catálogo das fontes de conhecimento (arquivos, páginas web, regras tácitas)
e estado da sincronização. Guardado em SQLite — que já vem no Python, não
exige serviço novo e consome pouquíssima RAM (importante em PC básico).

Um único catálogo atende três necessidades:
1. Sincronização incremental: saber o que já foi indexado (tamanho, data,
   hash do conteúdo) para só reprocessar o que mudou.
2. Limpeza: saber o que foi indexado de cada fonte para apagar os trechos
   antigos quando o arquivo muda, some ou é bloqueado.
3. Consulta ("onde está o arquivo X?", "quando foi alterado?") — a busca por
   nome entra no próximo lote, em cima desta mesma tabela.

Uma conexão por operação: o volume de escrita é baixo e isso evita
problemas de uso do mesmo objeto entre threads.
"""

import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Set


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class CatalogItem:
    source: str                       # caminho do arquivo, URL ou rótulo (tácito)
    kind: str                         # 'file' | 'web' | 'tacit'
    name: str
    folder: str = ""
    ext: str = ""
    size: int = 0
    mtime: float = 0.0
    content_hash: str = ""
    chunk_count: int = 0
    indexed_at: Optional[str] = None
    last_checked_at: Optional[str] = None
    status: str = "ok"                # 'ok' | 'erro' | 'sem_texto'
    error: str = ""

    def with_changes(self, **changes) -> "CatalogItem":
        return replace(self, **changes)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    source          TEXT PRIMARY KEY,
    kind            TEXT NOT NULL,
    name            TEXT NOT NULL,
    folder          TEXT NOT NULL DEFAULT '',
    ext             TEXT NOT NULL DEFAULT '',
    size            INTEGER NOT NULL DEFAULT 0,
    mtime           REAL NOT NULL DEFAULT 0,
    content_hash    TEXT NOT NULL DEFAULT '',
    chunk_count     INTEGER NOT NULL DEFAULT 0,
    indexed_at      TEXT,
    last_checked_at TEXT,
    status          TEXT NOT NULL DEFAULT 'ok',
    error           TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_items_kind ON items(kind);
CREATE TABLE IF NOT EXISTS doc_words (
    source TEXT NOT NULL,
    word   TEXT NOT NULL,
    PRIMARY KEY (source, word)
);
CREATE TABLE IF NOT EXISTS terms (
    source TEXT NOT NULL,
    term   TEXT NOT NULL,
    PRIMARY KEY (source, term)
);
CREATE INDEX IF NOT EXISTS idx_terms_term ON terms(term);
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

_COLUMNS = (
    "source", "kind", "name", "folder", "ext", "size", "mtime",
    "content_hash", "chunk_count", "indexed_at", "last_checked_at", "status", "error",
)


class Catalog:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn:
            conn.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    # ------------------------------------------------------------ itens

    def get(self, source: str) -> Optional[CatalogItem]:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT * FROM items WHERE source = ?", (source,)).fetchone()
        return CatalogItem(**{c: row[c] for c in _COLUMNS}) if row else None

    def upsert(self, item: CatalogItem) -> None:
        values = [getattr(item, c) for c in _COLUMNS]
        placeholders = ", ".join("?" for _ in _COLUMNS)
        updates = ", ".join(f"{c} = excluded.{c}" for c in _COLUMNS if c != "source")
        with closing(self._connect()) as conn, conn:
            conn.execute(
                f"INSERT INTO items ({', '.join(_COLUMNS)}) VALUES ({placeholders}) "
                f"ON CONFLICT(source) DO UPDATE SET {updates}",
                values,
            )

    def touch(self, source: str, checked_at: Optional[str] = None) -> None:
        """Só registra que a fonte foi conferida agora (nada mudou)."""
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "UPDATE items SET last_checked_at = ? WHERE source = ?",
                (checked_at or utcnow_iso(), source),
            )

    def replace_doc_words(self, source: str, words) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute("DELETE FROM doc_words WHERE source = ?", (source,))
            conn.executemany("INSERT INTO doc_words (source, word) VALUES (?, ?)", [(source, w) for w in words])

    def words_for(self, source: str) -> set:
        with closing(self._connect()) as conn:
            rows = conn.execute("SELECT word FROM doc_words WHERE source = ?", (source,)).fetchall()
        return {row["word"] for row in rows}

    def replace_terms(self, source: str, terms) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute("DELETE FROM terms WHERE source = ?", (source,))
            conn.execute("DELETE FROM doc_words WHERE source = ?", (source,))
            conn.executemany("INSERT INTO terms (source, term) VALUES (?, ?)", [(source, t) for t in terms])

    def sources_with_term(self, term: str):
        with closing(self._connect()) as conn:
            rows = conn.execute("SELECT source FROM terms WHERE term = ?", (term,)).fetchall()
        return [row["source"] for row in rows]

    def all_items(self):
        with closing(self._connect()) as conn:
            rows = conn.execute("SELECT * FROM items").fetchall()
        return [CatalogItem(**{c: row[c] for c in _COLUMNS}) for row in rows]

    def file_items(self):
        with closing(self._connect()) as conn:
            rows = conn.execute("SELECT * FROM items WHERE kind = 'file' AND status = 'ok'").fetchall()
        return [CatalogItem(**{c: row[c] for c in _COLUMNS}) for row in rows]

    def delete(self, source: str) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute("DELETE FROM terms WHERE source = ?", (source,))
        with closing(self._connect()) as conn, conn:
            conn.execute("DELETE FROM items WHERE source = ?", (source,))

    def sources(self, kind: Optional[str] = None) -> Set[str]:
        query, params = "SELECT source FROM items", ()
        if kind:
            query, params = query + " WHERE kind = ?", (kind,)
        with closing(self._connect()) as conn:
            return {row["source"] for row in conn.execute(query, params)}

    # ------------------------------------------------------------- meta

    def set_meta(self, key: str, value: str) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "INSERT INTO meta (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def delete_meta(self, key: str) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute("DELETE FROM meta WHERE key = ?", (key,))

    def get_meta(self, key: str) -> Optional[str]:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None

    def get_meta_json(self, key: str) -> Optional[dict]:
        raw = self.get_meta(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    # ----------------------------------------------------------- resumo

    def stats(self) -> Dict[str, int]:
        """Contagens para o painel (sem expor caminhos)."""
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT kind, status, COUNT(*) AS n, COALESCE(SUM(chunk_count), 0) AS chunks "
                "FROM items GROUP BY kind, status"
            ).fetchall()
        result = {"files": 0, "web": 0, "tacit": 0, "chunks": 0, "errors": 0, "without_text": 0}
        label = {"file": "files", "web": "web", "tacit": "tacit"}
        for row in rows:
            result[label.get(row["kind"], "files")] += row["n"]
            result["chunks"] += row["chunks"]
            if row["status"] == "erro":
                result["errors"] += row["n"]
            elif row["status"] == "sem_texto":
                result["without_text"] += row["n"]
        return result
