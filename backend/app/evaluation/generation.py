from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class CitationScore:
    supported: int
    cited: int
    precision: float


def citation_precision(answer: str, source_names: Iterable[str]) -> CitationScore:
    """Measure whether bracketed [source] citations refer to supplied evidence names."""
    sources = {str(name).strip() for name in source_names if str(name).strip()}
    cited = set()
    token = "["
    remaining = answer or ""
    while token in remaining:
        start = remaining.find(token)
        end = remaining.find("]", start + 1)
        if end < 0:
            break
        value = remaining[start + 1:end].strip()
        if value:
            cited.add(value)
        remaining = remaining[end + 1:]
    supported = len(cited & sources)
    return CitationScore(supported=supported, cited=len(cited), precision=(supported / len(cited) if cited else 1.0))


def answer_grounded(answer: str, evidence: list[str]) -> bool:
    """Conservative smoke metric: empty evidence must never be considered grounded."""
    return bool(evidence) and bool((answer or "").strip())
