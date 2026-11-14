"""
tests/test_rag_engine.py
---------------------------
Testa o RAGEngine sem depender de um Qdrant ou Ollama reais:
- QdrantClient é substituído por um MagicMock (monkeypatch na classe).
- Chamadas HTTP ao Ollama são interceptadas com respx.

Cobre especificamente a correção mais importante desta revisão: os IDs de
ponto agora são determinísticos (uuid5), então reindexar o MESMO conteúdo
não deve criar pontos duplicados.
"""

from unittest.mock import MagicMock

import httpx
import pytest
import respx

from app.core.config import Settings
from app.services.rag_engine import RAGEngine


@pytest.fixture
def fake_qdrant_client(monkeypatch):
    """Substitui QdrantClient por um mock que simula 'nenhuma coleção existente ainda'."""
    fake_client = MagicMock()
    fake_client.get_collections.return_value = MagicMock(collections=[])

    monkeypatch.setattr("app.services.rag_engine.QdrantClient", lambda **kwargs: fake_client)
    return fake_client


@pytest.fixture
def rag_engine(fake_qdrant_client) -> RAGEngine:
    settings = Settings(ollama_host="http://fake-ollama:11434", embedding_dimension=4)
    http_client = httpx.AsyncClient()
    engine = RAGEngine(settings=settings, http_client=http_client)
    return engine


def test_make_point_id_e_deterministico(rag_engine: RAGEngine):
    id_1 = rag_engine._make_point_id("manual.pdf", "conteudo do chunk")
    id_2 = rag_engine._make_point_id("manual.pdf", "conteudo do chunk")
    id_3 = rag_engine._make_point_id("manual.pdf", "outro conteudo")

    assert id_1 == id_2, "Mesmo conteúdo e mesma fonte devem gerar o MESMO id (idempotência)."
    assert id_1 != id_3, "Conteúdos diferentes devem gerar ids diferentes."


@pytest.mark.asyncio
@respx.mock
async def test_get_embedding_sucesso(rag_engine: RAGEngine):
    respx.post("http://fake-ollama:11434/api/embeddings").mock(
        return_value=httpx.Response(200, json={"embedding": [0.1, 0.2, 0.3, 0.4]})
    )

    vector = await rag_engine._get_embedding("texto de teste")

    assert vector == [0.1, 0.2, 0.3, 0.4]


@pytest.mark.asyncio
@respx.mock
async def test_get_embedding_falha_retorna_lista_vazia(rag_engine: RAGEngine):
    respx.post("http://fake-ollama:11434/api/embeddings").mock(
        return_value=httpx.Response(500, json={"error": "modelo indisponivel"})
    )

    vector = await rag_engine._get_embedding("texto de teste")

    assert vector == []


@pytest.mark.asyncio
@respx.mock
async def test_index_documents_reindexar_mesmo_conteudo_nao_duplica(rag_engine: RAGEngine, fake_qdrant_client):
    respx.post("http://fake-ollama:11434/api/embeddings").mock(
        return_value=httpx.Response(200, json={"embedding": [0.1, 0.2, 0.3, 0.4]})
    )

    documentos = [{"source": "boas_vindas.txt", "content": "Bem-vindo ao setor jurídico."}]

    total_primeira_vez = await rag_engine.index_documents(documentos)
    total_segunda_vez = await rag_engine.index_documents(documentos)

    assert total_primeira_vez == total_segunda_vez
    assert fake_qdrant_client.upsert.call_count == 2

    ids_primeira_chamada = {p.id for p in fake_qdrant_client.upsert.call_args_list[0].kwargs["points"]}
    ids_segunda_chamada = {p.id for p in fake_qdrant_client.upsert.call_args_list[1].kwargs["points"]}

    assert ids_primeira_chamada == ids_segunda_chamada, "Reindexar o mesmo conteúdo deve gerar os MESMOS IDs."


@pytest.mark.asyncio
async def test_search_retorna_vazio_quando_embedding_falha(rag_engine: RAGEngine, monkeypatch):
    async def fake_embedding_vazio(_text):
        return []

    monkeypatch.setattr(rag_engine, "_get_embedding", fake_embedding_vazio)

    resultados = await rag_engine.search("pergunta qualquer")

    assert resultados == []


@pytest.mark.asyncio
async def test_search_delega_para_query_points_do_qdrant(rag_engine: RAGEngine, fake_qdrant_client, monkeypatch):
    async def fake_embedding(_text):
        return [0.1, 0.2, 0.3, 0.4]

    monkeypatch.setattr(rag_engine, "_get_embedding", fake_embedding)

    fake_hit = MagicMock()
    fake_hit.payload = {"text": "trecho relevante", "source": "manual.pdf"}
    fake_qdrant_client.query_points.return_value = MagicMock(points=[fake_hit])

    resultados = await rag_engine.search("qual o procedimento?", limit=3)

    assert len(resultados) == 1
    assert resultados[0].payload["source"] == "manual.pdf"
    fake_qdrant_client.query_points.assert_called_once()


@pytest.mark.asyncio
async def test_index_document_desiste_cedo_quando_os_embeddings_falham(rag_engine: RAGEngine, monkeypatch):
    chamadas = {"n": 0}

    async def sempre_falha(_text):
        chamadas["n"] += 1
        return []

    monkeypatch.setattr(rag_engine, "_get_embedding", sempre_falha)

    resultado = await rag_engine.index_document("grande.txt", "palavra " * 1200)  # vários trechos

    assert resultado.total_chunks > 3
    assert chamadas["n"] == 3, "deve parar após 3 falhas seguidas, sem esperar trecho a trecho"
    assert resultado.chunk_ids == [] and resultado.failed_chunks == resultado.total_chunks


@pytest.mark.asyncio
async def test_index_document_devolve_ids_unicos_dos_trechos_gravados(rag_engine: RAGEngine, fake_qdrant_client, monkeypatch):
    async def ok(_text):
        return [0.1, 0.2, 0.3, 0.4]

    monkeypatch.setattr(rag_engine, "_get_embedding", ok)

    resultado = await rag_engine.index_document("a.txt", "Um texto curto.")

    assert len(resultado.chunk_ids) == 1 and resultado.failed_chunks == 0
    fake_qdrant_client.upsert.assert_called_once()
