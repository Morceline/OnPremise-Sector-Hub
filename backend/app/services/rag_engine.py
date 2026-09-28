import os
import httpx
from typing import List, Dict
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct

class RAGEngine:
    def __init__(self):
        self.qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        self.qdrant_port = int(os.getenv("QDRANT_PORT", 6333))
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        
        self.client = QdrantClient(host=self.qdrant_host, port=self.qdrant_port)
        self.collection_name = "sector_knowledge"
        
        # Inicializar coleção no Qdrant se não existir
        self._init_collection()
        
        # Configurar divisor de texto (Chunking)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )

    def _init_collection(self):
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE)
            )

    async def _get_embedding(self, text: str) -> List[float]:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(
                f"{self.ollama_host}/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": text},
                timeout=30.0
            )
            return response.json().get("embedding", [])

    async def index_documents(self, raw_documents: List[Dict[str, str]]):
        points = []
        point_id = 1

        for doc in raw_documents:
            chunks = self.text_splitter.split_text(doc["content"])
            for chunk in chunks:
                vector = await self._get_embedding(chunk)
                if vector:
                    points.append(
                        PointStruct(
                            id=point_id,
                            vector=vector,
                            payload={"source": doc["source"], "text": chunk}
                        )
                    )
                    point_id += 1

        if points:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )

    async def search(self, query_text: str, limit: int = 3):
        """Busca documentos relevantes no banco vetorial Qdrant."""
        query_vector = await self._get_embedding(query_text)
        if not query_vector:
            return []
        
        # O método query_points evita o erro de falta de atributo
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=limit
        )
        return response.points
