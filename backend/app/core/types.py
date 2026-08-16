from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Evidence:
    document_id: str
    filename: str
    chunk_id: str
    content: str
    score: float
    page: int | None = None


@dataclass(frozen=True)
class AgentResult:
    answer: str
    evidence: list[Evidence]
    verified: bool
    confidence: float
    metadata: dict[str, Any]
