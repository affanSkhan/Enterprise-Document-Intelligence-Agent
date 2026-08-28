import time
from typing import Any

from langchain_core.documents import Document
from sqlalchemy.orm import Session

from app.core.config import settings
from app.retrieval.bm25 import BM25Index
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.reranker import rerank_documents
from app.security.acl import allowed_document_ids
from app.vectorstore.client import get_chroma_client, get_vectorstore
from app.vectorstore.pgvector_store import dense_search as pg_dense_search, tenant_documents as pg_tenant_documents
from app.observability.metrics import RETRIEVAL_LATENCY, RETRIEVAL_REQUESTS


def _tenant_documents(tenant_id: str, allowed_ids: list[str] | None, db: Session | None = None) -> list[Document]:
    if settings.use_pgvector:
        if db is None:
            return []
        return pg_tenant_documents(db, tenant_id, allowed_ids)
    collection = get_chroma_client().get_collection(settings.VECTOR_COLLECTION_NAME)
    where: dict[str, Any] = {"tenant_id": tenant_id}
    if allowed_ids is not None:
        if not allowed_ids:
            return []
        where = {"$and": [{"tenant_id": tenant_id}, {"doc_id": {"$in": allowed_ids}}]}
    payload = collection.get(where=where, include=["documents", "metadatas"])
    documents = payload.get("documents") or []
    metadatas = payload.get("metadatas") or []
    return [Document(page_content=text or "", metadata=metadata or {}) for text, metadata in zip(documents, metadatas)]


def _dense_search(query: str, top_k: int, tenant_id: str, allowed_ids: list[str] | None, db: Session | None = None) -> list[tuple[Document, float]]:
    if settings.use_pgvector:
        if db is None:
            return []
        return pg_dense_search(db, query, top_k, tenant_id, allowed_ids)
    vectorstore = get_vectorstore()
    if allowed_ids is not None and not allowed_ids:
        return []
    filter_: dict[str, Any] = {"tenant_id": tenant_id}
    if allowed_ids is not None:
        filter_ = {"$and": [{"tenant_id": tenant_id}, {"doc_id": {"$in": allowed_ids}]}}
    return vectorstore.similarity_search_with_score(query, k=top_k, filter=filter_)


def _expand_adjacent_chunks(
    ranked: list[tuple[Document, float]],
    corpus: list[Document],
    max_neighbors: int = 2,
) -> list[tuple[Document, float]]:
    """Add nearby chunks from the same authorized document for broad/list questions.

    Chunk-level reranking can otherwise select two chunks from a section while
    dropping the next chunk that contains the remaining item in a list. We only
    expand within the already ACL-filtered tenant corpus and preserve the
    strongest nearby score as a context score.
    """
    if not ranked or not corpus:
        return ranked

    by_doc: dict[str, dict[int, Document]] = {}
    for document in corpus:
        metadata = document.metadata or {}
        doc_id = str(metadata.get("doc_id") or "")
        idx = metadata.get("chunk_idx")
        if not doc_id or idx is None:
            continue
        try:
            by_doc.setdefault(doc_id, {})[int(idx)] = document
        except (TypeError, ValueError):
            continue

    selected: dict[tuple[str, int], tuple[Document, float]] = {}
    for document, score in ranked:
        metadata = document.metadata or {}
        doc_id = str(metadata.get("doc_id") or "")
        idx = metadata.get("chunk_idx")
        if doc_id and idx is not None:
            try:
                selected[(doc_id, int(idx))] = (document, float(score))
            except (TypeError, ValueError):
                pass

    expanded = list(ranked)
    for document, score in ranked:
        metadata = document.metadata or {}
        doc_id = str(metadata.get("doc_id") or "")
        idx = metadata.get("chunk_idx")
        if not doc_id or idx is None:
            continue
        try:
            center = int(idx)
        except (TypeError, ValueError):
            continue

        for distance in range(1, max_neighbors + 1):
            for neighbor_idx in (center - distance, center + distance):
                neighbor = by_doc.get(doc_id, {}).get(neighbor_idx)
                if neighbor is None:
                    continue
                key = (doc_id, neighbor_idx)
                if key in selected:
                    continue
                neighbor_score = max(float(score) * (0.92 ** distance), 0.0)
                selected[key] = (neighbor, neighbor_score)
                expanded.append((neighbor, neighbor_score))

    return expanded


def search_documents(
    query: str,
    top_k: int = 5,
    tenant_id: str = "default-tenant",
    mode: str = "hybrid",
    rerank: bool = False,
    db: Session | None = None,
    user_id: str = "dev-user",
    role: str = "admin",
    expand_context: bool = False,
) -> list[dict[str, Any]]:
    if top_k < 1:
        raise ValueError("top_k must be positive")
    if mode not in {"dense", "sparse", "hybrid"}:
        raise ValueError("mode must be one of: dense, sparse, hybrid")
    started = time.perf_counter()
    try:
        allowed_ids = allowed_document_ids(db, tenant_id=tenant_id, user_id=user_id, role=role) if db else None

        # Broad questions need higher recall before reranking. The final answer
        # still uses the requested top_k unless contextual expansion is enabled.
        retrieval_k = max(top_k, settings.RETRIEVAL_TOP_K) if expand_context else top_k
        candidate_k = max(retrieval_k * 4, 10)

        dense = _dense_search(query, candidate_k, tenant_id, allowed_ids, db) if mode in {"dense", "hybrid"} else []
        sparse = []
        corpus: list[Document] = []
        if mode in {"sparse", "hybrid"}:
            corpus = _tenant_documents(tenant_id, allowed_ids, db)
            sparse = [(hit.document, hit.score) for hit in BM25Index(corpus).search(query, candidate_k)]

        if mode == "dense":
            ranked = dense
        elif mode == "sparse":
            ranked = sparse
        else:
            ranked = reciprocal_rank_fusion([dense, sparse])

        if rerank and ranked:
            ranked = rerank_documents(query, [doc for doc, _ in ranked], top_k=retrieval_k)

        if expand_context:
            if not corpus:
                corpus = _tenant_documents(tenant_id, allowed_ids, db)
            ranked = _expand_adjacent_chunks(ranked, corpus)

        return [
            {
                "rank": rank,
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score),
                "retrieval_mode": mode,
                "reranked": rerank,
            }
            for rank, (doc, score) in enumerate(ranked[:retrieval_k], start=1)
        ]
    finally:
        RETRIEVAL_REQUESTS.labels(mode).inc()
        RETRIEVAL_LATENCY.labels(mode).observe(time.perf_counter() - started)
