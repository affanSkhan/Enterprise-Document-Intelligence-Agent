"""Optional cross-encoder reranking for high-precision retrieval."""

from __future__ import annotations

from functools import lru_cache
from typing import Sequence

from langchain_core.documents import Document

from app.core.config import settings


@lru_cache(maxsize=2)
def get_reranker(model_name: str | None = None):
    from sentence_transformers import CrossEncoder

    return CrossEncoder(model_name or settings.RERANKER_MODEL)


def rerank_documents(
    query: str,
    documents: Sequence[Document],
    top_k: int = 5,
    model_name: str | None = None,
) -> list[tuple[Document, float]]:
    """Score query/document pairs with a cross-encoder and return top results."""
    if not documents or top_k < 1:
        return []
    pairs = [(query, document.page_content) for document in documents]
    scores = get_reranker(model_name).predict(pairs, show_progress_bar=False)
    ranked = sorted(
        zip(documents, scores),
        key=lambda item: float(item[1]),
        reverse=True,
    )
    return [(document, float(score)) for document, score in ranked[:top_k]]
