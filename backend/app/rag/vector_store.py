"""
Vector store abstraction.

`VECTOR_STORE_BACKEND=local` (default): in-process numpy cosine similarity.
Good enough for hundreds-to-low-thousands of tools/doc-chunks and requires
zero external infrastructure -- appropriate for this sandbox and for local
development.

`VECTOR_STORE_BACKEND=pgvector` / `qdrant`: production adapters. They are
stubbed here with a clear implementation contract so swapping backends does
not touch any caller (ToolRetrievalEngine, RagRetriever) -- only
`get_vector_store()` changes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from app.core.config import get_settings
from app.rag.embeddings import cosine_similarity


@dataclass
class VectorSearchResult:
    id: str
    score: float
    metadata: dict


class VectorStore(ABC):
    @abstractmethod
    def upsert(self, namespace: str, item_id: str, vector: list[float], metadata: dict) -> None: ...

    @abstractmethod
    def search(
        self, namespace: str, query_vector: list[float], top_k: int, metadata_filter: dict | None = None
    ) -> list[VectorSearchResult]: ...

    @abstractmethod
    def delete(self, namespace: str, item_id: str) -> None: ...


class LocalNumpyVectorStore(VectorStore):
    """Namespaced in-memory store. Namespaces keep 'mcp_tools' and
    'rag_documents' embeddings from ever being searched against each other."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, tuple[list[float], dict]]] = {}

    def upsert(self, namespace: str, item_id: str, vector: list[float], metadata: dict) -> None:
        self._store.setdefault(namespace, {})[item_id] = (vector, metadata)

    def search(
        self, namespace: str, query_vector: list[float], top_k: int, metadata_filter: dict | None = None
    ) -> list[VectorSearchResult]:
        bucket = self._store.get(namespace, {})
        results: list[VectorSearchResult] = []
        for item_id, (vector, metadata) in bucket.items():
            if metadata_filter and not _matches_filter(metadata, metadata_filter):
                continue
            score = cosine_similarity(query_vector, vector)
            results.append(VectorSearchResult(id=item_id, score=score, metadata=metadata))
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def delete(self, namespace: str, item_id: str) -> None:
        self._store.get(namespace, {}).pop(item_id, None)


def _matches_filter(metadata: dict, metadata_filter: dict) -> bool:
    for key, expected in metadata_filter.items():
        actual = metadata.get(key)
        if isinstance(expected, (list, set, tuple)):
            if actual not in expected:
                return False
        elif actual != expected:
            return False
    return True


class PgVectorStore(VectorStore):
    """Production adapter contract for PostgreSQL + pgvector.

    Implementation notes for production:
      - `namespace` maps to a table (mcp_tools.semantic_embedding / a
        `document_chunks.embedding vector(N)` column).
      - `search` becomes: `SELECT id, 1 - (embedding <=> :query) AS score
        FROM <table> WHERE <metadata_filter as SQL> ORDER BY embedding <=> :query
        LIMIT :top_k;` using the cosine-distance operator `<=>` from pgvector.
      - Requires the `vector` extension and an ivfflat/hnsw index on the
        embedding column for production-scale latency.
    """

    def __init__(self, dsn: str):
        self.dsn = dsn

    def upsert(self, namespace: str, item_id: str, vector: list[float], metadata: dict) -> None:
        raise NotImplementedError("Configure a PostgreSQL DSN with the pgvector extension enabled.")

    def search(
        self, namespace: str, query_vector: list[float], top_k: int, metadata_filter: dict | None = None
    ) -> list[VectorSearchResult]:
        raise NotImplementedError("Configure a PostgreSQL DSN with the pgvector extension enabled.")

    def delete(self, namespace: str, item_id: str) -> None:
        raise NotImplementedError("Configure a PostgreSQL DSN with the pgvector extension enabled.")


class QdrantVectorStore(VectorStore):
    """Production adapter contract for Qdrant (high-scale alternative to pgvector)."""

    def __init__(self, url: str):
        self.url = url

    def upsert(self, namespace: str, item_id: str, vector: list[float], metadata: dict) -> None:
        raise NotImplementedError("Set QDRANT_URL and install `qdrant-client` to enable this backend.")

    def search(
        self, namespace: str, query_vector: list[float], top_k: int, metadata_filter: dict | None = None
    ) -> list[VectorSearchResult]:
        raise NotImplementedError("Set QDRANT_URL and install `qdrant-client` to enable this backend.")

    def delete(self, namespace: str, item_id: str) -> None:
        raise NotImplementedError("Set QDRANT_URL and install `qdrant-client` to enable this backend.")


@lru_cache
def get_vector_store() -> VectorStore:
    settings = get_settings()
    if settings.VECTOR_STORE_BACKEND == "pgvector":
        return PgVectorStore(settings.DATABASE_URL)
    if settings.VECTOR_STORE_BACKEND == "qdrant":
        return QdrantVectorStore(settings.QDRANT_URL or "")
    return LocalNumpyVectorStore()
