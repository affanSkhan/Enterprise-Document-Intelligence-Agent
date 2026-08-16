from typing import Iterable


def reciprocal_rank_fusion(result_lists: Iterable[list[tuple[object, float]]], k: int = 60):
    scores: dict[str, float] = {}
    objects: dict[str, object] = {}
    for results in result_lists:
        for rank, (obj, _) in enumerate(results, start=1):
            key = getattr(obj, "page_content", repr(obj))[:500]
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
            objects[key] = obj
    return sorted(((objects[key], score) for key, score in scores.items()),
                  key=lambda item: item[1], reverse=True)
