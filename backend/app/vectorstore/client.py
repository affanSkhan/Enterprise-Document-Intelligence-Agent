from __future__ import annotations

import hashlib
import logging
import math
import re
from functools import lru_cache

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.core.config import settings

logger = logging.getLogger(__name__)
_WORD_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


class LocalHashEmbeddings(Embeddings):
    """Deterministic lexical embeddings for the explicitly enabled demo fallback.

    These are not semantic model embeddings. They keep indexing/search available
    for a demo when Gemini credentials are absent.
    """

    dimensions = 384

    def _embed(self, text: str) -> list[float]:
        tokens = _WORD_RE.findall((text or "").lower())
        features = list(tokens)
        features.extend(f"{left}_{right}" for left, right in zip(tokens, tokens[1:]))
        vector = [0.0] * self.dimensions
        for feature in features:
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "little") % self.dimensions
            vector[index] += 1.0 if digest[4] & 1 else -1.0
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector] if norm else vector

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


@lru_cache(maxsize=1)
def get_embeddings() -> Embeddings:
    """Use Gemini embeddings when configured, or the explicit local demo fallback."""
    if settings.GEMINI_API_KEY:
        return GoogleGenerativeAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
        )
    if settings.ENABLE_LOCAL_DEMO_FALLBACK:
        logger.warning(
            "GEMINI_API_KEY is not configured; using LocalHashEmbeddings. "
            "This is a demo retrieval fallback, not semantic model embeddings."
        )
        return LocalHashEmbeddings()
    raise RuntimeError(
        "GEMINI_API_KEY is required for vector operations. Set GEMINI_API_KEY "
        "or explicitly enable ENABLE_LOCAL_DEMO_FALLBACK for a demo."
    )


@lru_cache(maxsize=1)
def get_chroma_client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(
        path=settings.CHROMA_DB_DIR,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def get_vectorstore(collection_name: str | None = None) -> Chroma:
    collection_name = collection_name or settings.VECTOR_COLLECTION_NAME
    return Chroma(
        client=get_chroma_client(),
        collection_name=collection_name,
        embedding_function=get_embeddings(),
    )
