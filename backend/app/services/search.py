from app.vectorstore.client import get_vectorstore
from typing import List, Dict, Any


def search_documents(query: str, top_k: int = 5, tenant_id: str = "default-tenant") -> List[Dict[str, Any]]:
    vectorstore = get_vectorstore()
    results = vectorstore.similarity_search_with_score(query, k=top_k)
    formatted = []
    for rank, (doc, score) in enumerate(results, start=1):
        if doc.metadata.get("tenant_id", tenant_id) != tenant_id:
            continue
        formatted.append({"rank": rank, "content": doc.page_content,
                          "metadata": doc.metadata, "score": float(score)})
    return formatted
