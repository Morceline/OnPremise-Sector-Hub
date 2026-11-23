"""
services/rag_engine.py
------------------------
Motor de RAG: gera embeddings via Ollama, indexa no Qdrant e faz busca
semântica dos top-k chunks relevantes.

Mudanças em relação à versão anterior:
1. IDs determinísticos (uuid5 a partir do hash do conteúdo do chunk + fonte)
   em vez de um contador `point_id = 1` incremental. O contador antigo
   colidia toda vez que o serviço reiniciava (voltava a contar do 1 e
   sobrescrevia pontos de outros documentos) e, ao reindexar o mesmo
   arquivo, criava duplicatas em vez de atualizar. Com uuid5 determinístico,
   reindexar o mesmo conteúdo gera o MESMO id -> o Qdrant faz upsert
   (atualiza) em vez de duplicar. Isso resolve o pedido de reindexação
   idempotente sem precisar de um banco extra para rastrear hashes.
2. Reuso de um único httpx.AsyncClient (injetado) em vez de abrir um
   client novo a cada chamada de embedding — reduz overhead de conexão,
   importante em uma máquina de usuário básica.
3. Timeout de embedding configurável e separado do timeout de geração.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Dict, List, Optional, Sequence

import httpx
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    HasIdCondition,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

# Namespace fixo para gerar UUIDs determinísticos e estáveis entre execuções.
_UUID_NAMESPACE = uuid.UUID("6b7f2c2a-8f2b-4b8a-9b8e-7e2f1a2b3c4d")

# Quantos embeddings seguidos podem falhar antes de desistir do documento.
# Evita ficar minutos esperando timeout trecho a trecho se o Ollama caiu.
_MAX_CONSECUTIVE_EMBEDDING_FAILURES = 3
_UPSERT_BATCH_SIZE = 32


@dataclass
class IndexOutcome:
    """Resultado de indexar UM documento."""

    chunk_ids: List[str] = field(default_factory=list)  # trechos gravados com sucesso
    failed_chunks: int = 0                               # trechos sem embedding
    total_chunks: int = 0                                # trechos gerados pelo splitter
    words: set = field(default_factory=set)              # vocabulário dos trechos (para correção de digitação)
    terms: set = field(default_factory=set)              # termos exatos: CPF, e-mail, números longos


class RAGEngine:
    def __init__(self, settings: Optional[Settings] = None, http_client: Optional[httpx.AsyncClient] = None):
        self.settings = settings or get_settings()
        # Se nenhum client for injetado (ex: uso em script standalone/teste),
        # cria um próprio — mas em produção o main.py injeta um compartilhado.
        self._http_client = http_client
        self._owns_http_client = http_client is None

        self.client = QdrantClient(host=self.settings.qdrant_host, port=self.settings.qdrant_port)
        self.collection_name = "sector_knowledge"

        self._init_collection()

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""],
        )

    def _init_collection(self) -> None:
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.settings.embedding_dimension, distance=Distance.COSINE),
            )
        self._ensure_source_index()

    def _ensure_source_index(self) -> None:
        """Índice no campo 'source': deixa rápidas as buscas/remoções por arquivo."""
        try:
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="source",
                field_schema=PayloadSchemaType.KEYWORD,
            )
        except Exception:
            # Sem índice tudo continua funcionando (só mais lento em bases enormes).
            logger.warning("Não foi possível criar o índice do campo 'source'.", exc_info=True)

    async def _get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is not None:
            return self._http_client
        # Fallback só usado quando ninguém injetou um client (testes/scripts).
        self._http_client = httpx.AsyncClient()
        return self._http_client

    async def aclose(self) -> None:
        """Fecha o client HTTP somente se este RAGEngine o criou (não é compartilhado)."""
        if self._owns_http_client and self._http_client is not None:
            await self._http_client.aclose()

    async def _get_embedding(self, text: str) -> List[float]:
        client = await self._get_http_client()
        try:
            response = await client.post(
                f"{self.settings.ollama_host}/api/embeddings",
                json={"model": self.settings.embedding_model, "prompt": text},
                timeout=self.settings.embedding_timeout_seconds,
            )
            response.raise_for_status()
            return response.json().get("embedding", [])
        except httpx.HTTPError:
            logger.exception("Falha ao gerar embedding via Ollama (%s)", self.settings.ollama_host)
            return []

    @staticmethod
    def _make_point_id(source: str, chunk: str) -> str:
        """ID determinístico: mesmo conteúdo + mesma fonte => mesmo ID.
        Isso torna a reindexação idempotente (upsert, sem duplicar)."""
        return str(uuid.uuid5(_UUID_NAMESPACE, f"{source}::{chunk}"))

    async def index_documents(self, raw_documents: List[Dict[str, str]]) -> int:
        """Indexa uma lista de documentos {source, content}. Retorna quantos chunks foram enviados."""
        points: List[PointStruct] = []

        for doc in raw_documents:
            chunks = self.text_splitter.split_text(doc["content"])
            for chunk in chunks:
                vector = await self._get_embedding(chunk)
                if not vector:
                    continue
                points.append(
                    PointStruct(
                        id=self._make_point_id(doc["source"], chunk),
                        vector=vector,
                        payload={"source": doc["source"], "text": chunk},
                    )
                )

        if points:
            self.client.upsert(collection_name=self.collection_name, points=points)

        return len(points)

    async def index_document(
        self,
        source: str,
        content: str,
        throttle: Optional[Callable[[], Awaitable[None]]] = None,
    ) -> IndexOutcome:
        """
        Indexa UM documento e devolve os IDs dos trechos gravados.

        `throttle` (opcional) é chamado antes de cada embedding — a
        sincronização usa isso para ceder a vez quando alguém está no chat.
        Se os embeddings falharem seguidos (Ollama fora do ar), desiste cedo.
        """
        chunks = self.text_splitter.split_text(content)
        outcome = IndexOutcome(total_chunks=len(chunks))
        batch: List[PointStruct] = []
        consecutive_failures = 0

        for chunk in chunks:
            if throttle is not None:
                await throttle()

            vector = await self._get_embedding(chunk)
            if not vector:
                outcome.failed_chunks += 1
                consecutive_failures += 1
                if consecutive_failures >= _MAX_CONSECUTIVE_EMBEDDING_FAILURES:
                    # conta o restante como não indexado
                    outcome.failed_chunks = outcome.total_chunks - len(set(outcome.chunk_ids))
                    break
                continue

            consecutive_failures = 0
            point_id = self._make_point_id(source, chunk)
            outcome.chunk_ids.append(point_id)
            batch.append(PointStruct(id=point_id, vector=vector, payload={"source": source, "text": chunk}))

            if len(batch) >= _UPSERT_BATCH_SIZE:
                await asyncio.to_thread(self.client.upsert, collection_name=self.collection_name, points=batch)
                batch = []

        if batch:
            await asyncio.to_thread(self.client.upsert, collection_name=self.collection_name, points=batch)

        outcome.chunk_ids = list(dict.fromkeys(outcome.chunk_ids))  # sem repetidos, mesma ordem
        from app.services.query_normalizer import words_of
        for chunk in chunks:
            outcome.words |= words_of(chunk)
        from app.services.terms import extract_terms
        for chunk in chunks:
            outcome.terms |= extract_terms(chunk)
        return outcome

    async def prune_source(self, source: str, keep_ids: Sequence[str]) -> None:
        """
        Apaga os trechos de `source` que NÃO estão em `keep_ids`.

        Usado depois de indexar a versão nova de um arquivo: só então os
        trechos antigos são removidos — se algo falhar no meio, o arquivo
        nunca fica sem nenhum trecho.
        """
        conditions = Filter(
            must=[FieldCondition(key="source", match=MatchValue(value=source))],
            must_not=[HasIdCondition(has_id=list(keep_ids))] if keep_ids else None,
        )
        await asyncio.to_thread(
            self.client.delete,
            collection_name=self.collection_name,
            points_selector=FilterSelector(filter=conditions),
        )

    async def delete_source(self, source: str) -> None:
        """Remove TODOS os trechos de uma fonte (arquivo apagado, bloqueado ou removido)."""
        await self.prune_source(source, [])

    async def count_source(self, source: str) -> int:
        result = await asyncio.to_thread(
            self.client.count,
            collection_name=self.collection_name,
            count_filter=Filter(must=[FieldCondition(key="source", match=MatchValue(value=source))]),
            exact=True,
        )
        return result.count

    def collect_vocabulary(self) -> set:
        """Palavras de TODOS os trechos já indexados (usado quando o vocabulário ainda não existe)."""
        from app.services.query_normalizer import words_of

        words: set = set()
        offset = None
        while True:
            points, offset = self.client.scroll(
                collection_name=self.collection_name,
                limit=256,
                offset=offset,
                with_payload=["text"],
                with_vectors=False,
            )
            for point in points:
                words |= words_of(point.payload.get("text", ""))
            if offset is None:
                return words

    async def search(self, query_text: str, limit: int = 3):
        """Busca os `limit` chunks mais relevantes no Qdrant para a query."""
        query_vector = await self._get_embedding(query_text)
        if not query_vector:
            return []

        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=limit,
        )
        return response.points
