"""Offline retrieval evaluation metrics used by benchmarks and CI."""

from __future__ import annotations

from collections.abc import Iterable, Sequence


def recall_at_k(ranked_ids: Sequence[str], relevant_ids: Iterable[str], k: int) -> float:
    relevant = set(relevant_ids)
    if not relevant:
        return 0.0
    return len(set(ranked_ids[:k]) & relevant) / len(relevant)


def reciprocal_rank(ranked_ids: Sequence[str], relevant_ids: Iterable[str]) -> float:
    relevant = set(relevant_ids)
    for rank, doc_id in enumerate(ranked_ids, start=1):
        if doc_id in relevant:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(ranked_ids: Sequence[str], relevant_ids: Iterable[str], k: int) -> float:
    relevant = set(relevant_ids)
    if not relevant:
        return 0.0

    def dcg(ids: Sequence[str]) -> float:
        return sum(
            (1.0 if doc_id in relevant else 0.0) / __import__("math").log2(rank + 1)
            for rank, doc_id in enumerate(ids[:k], start=1)
        )

    ideal = dcg(list(relevant))
    return dcg(ranked_ids) / ideal if ideal else 0.0
