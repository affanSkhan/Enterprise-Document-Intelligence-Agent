from typing import Any
from app.vectorstore.client import get_vectorstore


def search_documents(query: str, top_k: int = 5, tenant_id: str = "default-tenant") -> list[dict[str, Any]]:
    vectorstore = get_vectorstore()
    results = vectorstore.similarity_search_with_score(
        query, k=top_k, filter={"tenant_id": tenant_id}
    )
    return [
        {"rank": rank, "content": doc.page_content,
         "metadata": doc.metadata, "score": float(score)}
        for rank, (doc, score) in enumerate(results, start=1)
    ]
