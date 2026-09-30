"""
Embedding provider abstraction.

Production systems would call a hosted embedding model (OpenAI, Voyage,
Anthropic, or a local sentence-transformers model). This sandbox has no
network access to model-weight hosts, so the DEFAULT provider is a fully
local, dependency-light TF-IDF + Truncated-SVD pipeline fit on the
tool/document corpus at startup. It is deterministic, requires no external
calls, and produces fixed-dimension dense vectors -- the same shape a real
embedding model would produce -- so it is a drop-in replacement.

To use a real model in production, implement `EmbeddingProvider` and set
it via `get_embedding_provider()`; nothing else in the codebase needs to
change (routing, RAG retrieval, and the vector store all depend only on
this interface).
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from functools import lru_cache

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer

from app.core.config import get_settings

_TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")


def _normalize(text: str) -> str:
    """Lowercase + strip punctuation. Keeps Indonesian & English tokens as-is
    (no stemming) since the corpus is small and domain vocabulary is stable."""
    return " ".join(_TOKEN_RE.findall(text.lower()))


class EmbeddingProvider(ABC):
    dimension: int

    @abstractmethod
    def fit(self, corpus: list[str]) -> None: ...

    @abstractmethod
    def embed(self, text: str) -> list[float]: ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


class LocalTfidfSvdEmbeddingProvider(EmbeddingProvider):
    """Default dev/offline provider: TF-IDF vectorizer -> Truncated SVD to a
    fixed dimension -> L2 normalize. Cosine similarity on these vectors
    behaves like a lightweight semantic embedding for this closed domain
    (IT infra / enterprise ops vocabulary)."""

    def __init__(self, dimension: int | None = None):
        settings = get_settings()
        self.dimension = dimension or settings.EMBEDDING_DIMENSION
        self._vectorizer = TfidfVectorizer(
            preprocessor=_normalize,
            ngram_range=(1, 2),
            min_df=1,
            sublinear_tf=True,
        )
        self._svd: TruncatedSVD | None = None
        self._fitted = False

    def fit(self, corpus: list[str]) -> None:
        if not corpus:
            raise ValueError("Cannot fit embedding provider on empty corpus")
        tfidf_matrix = self._vectorizer.fit_transform(corpus)
        n_components = min(self.dimension, max(2, min(tfidf_matrix.shape) - 1))
        self._svd = TruncatedSVD(n_components=n_components, random_state=42)
        self._svd.fit(tfidf_matrix)
        self._actual_dim = n_components
        self._fitted = True

    def embed(self, text: str) -> list[float]:
        if not self._fitted or self._svd is None:
            raise RuntimeError("EmbeddingProvider.fit() must be called before embed()")
        vec = self._svd.transform(self._vectorizer.transform([text]))[0]
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        # Pad to the configured dimension so downstream storage is uniform.
        if len(vec) < self.dimension:
            vec = np.pad(vec, (0, self.dimension - len(vec)))
        return vec.astype(float).tolist()


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    return LocalTfidfSvdEmbeddingProvider()


def cosine_similarity(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a), np.array(b)
    denom = (np.linalg.norm(va) * np.linalg.norm(vb)) or 1e-9
    return float(np.dot(va, vb) / denom)
