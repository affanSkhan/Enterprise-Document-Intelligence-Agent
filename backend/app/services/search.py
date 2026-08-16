from typing import Any

from langchain_core.documents import Document

from app.retrieval.bm25 import BM25Index
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.reranker import rerank_documents
from app.vectorstore.client import get_chroma_client, get_vectorstore


def _tenant_documents(tenant_id: str) -> list[Document]:
    """Load the tenant's indexed chunks for sparse retrieval."""
    collection = get_chroma_client().get_collection("documents")
    payload = collection.get(where={"tenant_id": tenant_id}, include=["documents", "metadatas"])
    documents = payload.get("documents") or []
    metadatas = payload.get("metadatas") or []
    return [Document(page_content=text or "", metadata=metadata or {}) for text, metadata in zip(documents, metadatas)]


def _dense_search(query: str, top_k: int, tenant_id: str) -> list[tuple[Document, float]]:
    vectorstore = get_vectorstore()
    return vectorstore.similarity_search_with_score(query, k=top_k, filter={"tenant_id": tenant_id})


def search_documents(
    query: str,
    top_k: int = 5,
    tenant_id: str = "default-tenant",
    mode: str = "hybrid",
    rerank: bool = False,
) -> list[dict[str, Any]]:
    """Search with dense/sparse/hybrid retrieval and optional cross-encoder reranking."""
    if top_k < 1:
        raise ValueError("top_k must be positive")
    if mode not in {"dense", "sparse", "hybrid"}:
        raise ValueError("mode must be one of: dense, sparse, hybrid")

    candidate_k = max(top_k * 4, 10)
    dense = _dense_search(query, candidate_k, tenant_id) if mode in {"dense", "hybrid"} else []
    sparse = []
    if mode in {"sparse", "hybrid"}:
        sparse = [(hit.document, hit.score) for hit in BM25Index(_tenant_documents(tenant_id)).search(query, candidate_k)]

    if mode == "dense":
        ranked = dense
    elif mode == "sparse":
        ranked = sparse
    else:
        ranked = reciprocal_rank_fusion([dense, sparse])

    if rerank and ranked:
        reranked = rerank_documents(query, [doc for doc, _ in ranked], top_k=top_k)
        ranked = reranked

    return [
        {
            "rank": rank,
            "content": doc.page_content,
            "metadata": doc.metadata,
            "score": float(score),
            "retrieval_mode": mode,
            "reranked": rerank,
        }
        for rank, (doc, score) in enumerate(ranked[:top_k], start=1)
    ]
