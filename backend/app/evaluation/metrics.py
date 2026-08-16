from dataclasses import dataclass
from typing import Sequence

@dataclass
class RetrievalCase:
    question: str
    relevant_document_ids: Sequence[str]


def recall_at_k(results: Sequence[dict], relevant_ids: set[str], k: int) -> float:
    if not relevant_ids:
        return 0.0
    found = {str(r.get("metadata", {}).get("doc_id")) for r in results[:k]}
    return len(found & relevant_ids) / len(relevant_ids)


def mrr(results: Sequence[dict], relevant_ids: set[str]) -> float:
    for rank, result in enumerate(results, start=1):
        if str(result.get("metadata", {}).get("doc_id")) in relevant_ids:
            return 1.0 / rank
    return 0.0
