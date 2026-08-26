from collections.abc import Iterable


def _key(obj: object) -> str:
    """Prefer stable document identity over truncated text for fusion."""
    metadata = getattr(obj, "metadata", {}) or {}
    chunk_id = metadata.get("chunk_id")
    if chunk_id:
        return str(chunk_id)
    identity = (metadata.get("doc_id"), metadata.get("version"), metadata.get("chunk_idx"))
    if any(value is not None for value in identity):
        return str(identity)
    return str(getattr(obj, "page_content", repr(obj))[:500])


def reciprocal_rank_fusion(
    result_lists: Iterable[list[tuple[object, float]]], k: int = 60
) -> list[tuple[object, float]]:
    """Fuse independently ranked retrievers without comparing score scales."""
    scores: dict[str, float] = {}
    objects: dict[str, object] = {}
    for results in result_lists:
        for rank, (obj, _) in enumerate(results, start=1):
            key = _key(obj)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
            objects[key] = obj
    return sorted(
        ((objects[key], score) for key, score in scores.items()),
        key=lambda item: item[1],
        reverse=True,
    )
