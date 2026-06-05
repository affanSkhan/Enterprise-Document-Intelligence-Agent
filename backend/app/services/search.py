from app.vectorstore.client import get_vectorstore
from typing import List, Dict, Any

def search_documents(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    vectorstore = get_vectorstore()
    results = vectorstore.similarity_search_with_score(query, k=top_k)
    
    formatted_results = []
    for doc, score in results:
        formatted_results.append({
            "content": doc.page_content,
            "metadata": doc.metadata,
            "score": score
        })
    return formatted_results
