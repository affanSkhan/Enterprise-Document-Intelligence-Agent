"""Memory-safe reranking for high-precision retrieval.

The cross-encoder implementation remains available for larger instances, but
production defaults to a deterministic lexical reranker so the API does not
load PyTorch/sentence-transformers on a small Render instance during the first
chat request.
"""

from __future__ import annotations

import math
import re
from functools import lru_cache
from typing import Sequence

from langchain_core.documents import Document

from app.core.config import settings

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall((text or "").lower()))


def _lightweight_rerank(
    query: str,
    documents: Sequence[Document],
    top_k: int,
) -> list[tuple[Document, float]]:
    """Rank candidates without heavyweight ML dependencies.

    The score combines query-term coverage, a small phrase-match bonus, and
    document/query length normalization. It is intentionally deterministic so
    retrieval remains available even on low-memory production instances.
    """
    query_text = (query or "").strip().lower()
    query_tokens = _tokens(query_text)
    if not query_tokens:
        return [(document, 0.0) for document in documents[:top_k]]

    scored: list[tuple[Document, float]] = []
    query_len = max(1, len(query_tokens))
    for document in documents:
        content = document.page_content or ""
        content_tokens = _tokens(content)
        overlap = len(query_tokens & content_tokens)
        coverage = overlap / query_len
        phrase_bonus = 0.25 if query_text and query_text in content.lower() else 0.0
        density = overlap / math.sqrt(max(1, len(content_tokens)))
        score = coverage + phrase_bonus + min(0.15, density)
        scored.append((document, float(score)))

    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:top_k]


@lru_cache(maxsize=2)
def get_reranker(model_name: str | None = None):
    """Load the optional cross-encoder only when explicitly enabled."""
    from sentence_transformers import CrossEncoder

    return CrossEncoder(model_name or settings.RERANKER_MODEL)


def rerank_documents(
    query: str,
    documents: Sequence[Document],
    top_k: int = 5,
    model_name: str | None = None,
) -> list[tuple[Document, float]]:
    """Score query/document pairs and return top results.

    By default this uses the lightweight implementation. On a larger
    deployment, set ENABLE_CROSS_ENCODER_RERANKER=true to use the configured
    sentence-transformers cross-encoder. If that optional model fails to
    initialize, safely fall back to lightweight reranking instead of taking
    down the API process.
    """
    if not documents or top_k < 1:
        return []

    if not settings.ENABLE_CROSS_ENCODER_RERANKER:
        return _lightweight_rerank(query, documents, top_k)

    try:
        pairs = [(query, document.page_content) for document in documents]
        scores = get_reranker(model_name).predict(pairs, show_progress_bar=False)
        ranked = sorted(
            zip(documents, scores),
            key=lambda item: float(item[1]),
            reverse=True,
        )
        return [(document, float(score)) for document, score in ranked[:top_k]]
    except Exception:
        return _lightweight_rerank(query, documents, top_k)
