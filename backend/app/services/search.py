import time
from typing import Any

from langchain_core.documents import Document
from sqlalchemy.orm import Session

from app.retrieval.bm25 import BM25Index
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.reranker import rerank_documents
from app.security.acl import allowed_document_ids
from app.vectorstore.client import get_chroma_client, get_vectorstore
from app.observability.metrics import RETRIEVAL_LATENCY, RETRIEVAL_REQUESTS


def _tenant_documents(tenant_id: str, allowed_ids: list[str] | None) -> list[Document]:
    collection = get_chroma_client().get_collection("documents")
    where: dict[str, Any] = {"tenant_id": tenant_id}
    if allowed_ids is not None:
        if not allowed_ids:
            return []
        where = {"$and": [{"tenant_id": tenant_id}, {"doc_id": {"$in": allowed_ids}}]}
    payload = collection.get(where=where, include=["documents", "metadatas"])
    documents = payload.get("documents") or []
    metadatas = payload.get("metadatas") or []
    return [Document(page_content=text or "", metadata=metadata or {}) for text, metadata in zip(documents, metadatas)]


def _dense_search(query: str, top_k: int, tenant_id: str, allowed_ids: list[str] | None) -> list[tuple[Document, float]]:
    vectorstore = get_vectorstore()
    if allowed_ids is not None and not allowed_ids:
        return []
    filter_: dict[str, Any] = {"tenant_id": tenant_id}
    if allowed_ids is not None:
        filter_ = {"$and": [{"tenant_id": tenant_id}, {"doc_id": {"$in": allowed_ids}}]}
    return vectorstore.similarity_search_with_score(query, k=top_k, filter=filter_)


def search_documents(query: str, top_k: int = 5, tenant_id: str = "default-tenant", mode: str = "hybrid", rerank: bool = False, db: Session | None = None, user_id: str = "dev-user", role: str = "admin") -> list[dict[str, Any]]:
    if top_k < 1:
        raise ValueError("top_k must be positive")
    if mode not in {"dense", "sparse", "hybrid"}:
        raise ValueError("mode must be one of: dense, sparse, hybrid")
    started = time.perf_counter()
    try:
        allowed_ids = allowed_document_ids(db, tenant_id=tenant_id, user_id=user_id, role=role) if db else None
        candidate_k = max(top_k * 4, 10)
        dense = _dense_search(query, candidate_k, tenant_id, allowed_ids) if mode in {"dense", "hybrid"} else []
        sparse = []
        if mode in {"sparse", "hybrid"}:
            sparse = [(hit.document, hit.score) for hit in BM25Index(_tenant_documents(tenant_id, allowed_ids)).search(query, candidate_k)]
        if mode == "dense": ranked = dense
        elif mode == "sparse": ranked = sparse
        else: ranked = reciprocal_rank_fusion([dense, sparse])
        if rerank and ranked:
            ranked = rerank_documents(query, [doc for doc, _ in ranked], top_k=top_k)
        return [{"rank": rank, "content": doc.page_content, "metadata": doc.metadata, "score": float(score), "retrieval_mode": mode, "reranked": rerank} for rank, (doc, score) in enumerate(ranked[:top_k], start=1)]
    finally:
        RETRIEVAL_REQUESTS.labels(mode).inc()
        RETRIEVAL_LATENCY.labels(mode).observe(time.perf_counter() - started)
