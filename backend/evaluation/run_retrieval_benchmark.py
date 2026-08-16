"""Run the retrieval benchmark against a supplied JSON dataset.

The benchmark intentionally accepts a retriever callable so it can be wired to
production search without coupling the evaluation layer to an HTTP server.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from app.evaluation.retrieval import ndcg_at_k, recall_at_k, reciprocal_rank


def evaluate(cases: list[dict], retrieve: Callable[[str, int], list[str]], k: int = 5) -> dict[str, float]:
    if not cases:
        return {"recall_at_k": 0.0, "mrr": 0.0, "ndcg_at_k": 0.0}
    recalls, mrrs, ndcgs = [], [], []
    for case in cases:
        ranked = retrieve(case["query"], k)
        relevant = case["relevant_chunk_ids"]
        recalls.append(recall_at_k(ranked, relevant, k))
        mrrs.append(reciprocal_rank(ranked, relevant))
        ndcgs.append(ndcg_at_k(ranked, relevant, k))
    return {
        "recall_at_k": sum(recalls) / len(recalls),
        "mrr": sum(mrrs) / len(mrrs),
        "ndcg_at_k": sum(ndcgs) / len(ndcgs),
    }


def load_cases(path: str | Path) -> list[dict]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return payload["cases"]
