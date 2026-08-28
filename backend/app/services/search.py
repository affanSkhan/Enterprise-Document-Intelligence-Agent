import re
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


_BROAD_LIST_PATTERNS = (
    re.compile(r"\bwhat\s+(?:projects?|skills?|technolog(?:y|ies)|experience|tools?|certifications?)\b", re.I),
    re.compile(r"\bwhich\s+(?:projects?|skills?|technolog(?:y|ies)|experience|tools?|certifications?)\b", re.I),
    re.compile(r"\b(?:list|name|show|give)\b.*\b(?:projects?|skills?|technolog(?:y|ies)|experience|tools?|certifications?|items?)\b", re.I),
    re.compile(r"\b(?:all|every)\b.*\b(?:projects?|skills?|technolog(?:y|ies)|experiences?|tools?|certifications?|items?)\b", re.I),
    re.compile(r"\bprojects?\b.*\b(?:worked|work|built|developed|done)\b", re.I),
    re.compile(r"\b(?:worked|work|built|developed)\b.*\bprojects?\b", re.I),
)


def _is_broad_list_query(query: str) -> bool:
    """Identify questions where completeness matters more than top-k precision."""
    text = " ".join((query or "").strip().lower().split())
    if not text:
        return False
    return any(pattern.search(text) for pattern in _BROAD_LIST_PATTERNS)


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
        filter_ = {"$and": [{"tenant_id": tenant_id}, {"doc_id": {"$in": allowed_ids}}]}
    return vectorstore.similarity_search_with_score(query, k=top_k, filter=filter_)


def _expand_adjacent_chunks(ranked: list[tuple[Document, float]], corpus: list[Document], max_neighbors: int = 3, max_results: int = 32) -> list[tuple[Document, float]]:
    """Expand strong hits with nearby chunks from the same authorized document."""
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
                continue

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
                selected[key] = (neighbor, max(float(score) * (0.94 ** distance), 0.0))

    expanded = list(selected.values())
    expanded.sort(key=lambda item: item[1], reverse=True)
    return expanded[:max_results]


def _expand_document_context(ranked: list[tuple[Document, float]], corpus: list[Document], max_chunks_per_document: int = 30, max_documents: int = 3, max_results: int = 30) -> list[tuple[Document, float]]:
    """For broad list questions, retain complete relevant document context."""
    if not ranked or not corpus:
        return ranked

    relevant_doc_ids: list[str] = []
    max_score_by_doc: dict[str, float] = {}
    for document, score in ranked:
        doc_id = str((document.metadata or {}).get("doc_id") or "")
        if not doc_id:
            continue
        max_score_by_doc[doc_id] = max(max_score_by_doc.get(doc_id, float("-inf")), float(score))
        if doc_id not in relevant_doc_ids:
            relevant_doc_ids.append(doc_id)
        if len(relevant_doc_ids) >= max_documents:
            break

    if not relevant_doc_ids:
        return ranked

    by_doc: dict[str, list[tuple[int, Document]]] = {}
    for document in corpus:
        metadata = document.metadata or {}
        doc_id = str(metadata.get("doc_id") or "")
        idx = metadata.get("chunk_idx")
        if doc_id not in relevant_doc_ids or idx is None:
            continue
        try:
            by_doc.setdefault(doc_id, []).append((int(idx), document))
        except (TypeError, ValueError):
            continue

    expanded: list[tuple[Document, float]] = []
    for doc_id in relevant_doc_ids:
        direct_score = max(max_score_by_doc.get(doc_id, 0.0), settings.RERANKER_MIN_SCORE)
        chunks = sorted(by_doc.get(doc_id, []), key=lambda item: item[0])
        for _, document in chunks[:max_chunks_per_document]:
            expanded.append((document, direct_score))
        if len(expanded) >= max_results:
            break

    return expanded[:max_results] if expanded else ranked


def search_documents(query: str, top_k: int = 5, tenant_id: str = "default-tenant", mode: str = "hybrid", rerank: bool = False, db: Session | None = None, user_id: str = "dev-user", role: str = "admin", expand_context: bool = False) -> list[dict[str, Any]]:
    if top_k < 1:
        raise ValueError("top_k must be positive")
    if mode not in {"dense", "sparse", "hybrid"}:
        raise ValueError("mode must be one of: dense, sparse, hybrid")
    started = time.perf_counter()
    try:
        allowed_ids = allowed_document_ids(db, tenant_id=tenant_id, user_id=user_id, role=role) if db else None

        if expand_context:
            retrieval_k = max(top_k * 5, settings.RETRIEVAL_TOP_K, 30)
            candidate_k = max(retrieval_k * 4, 120)
        else:
            retrieval_k = top_k
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
            rerank_k = retrieval_k if expand_context else top_k
            ranked = rerank_documents(query, [doc for doc, _ in ranked], top_k=rerank_k)

        if expand_context:
            if not corpus:
                corpus = _tenant_documents(tenant_id, allowed_ids, db)
            ranked = _expand_adjacent_chunks(ranked, corpus, max_neighbors=3, max_results=32)
            ranked = _expand_document_context(ranked, corpus, max_chunks_per_document=30, max_documents=3, max_results=30)

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
