"""Small, dependency-free BM25 implementation for tenant-scoped sparse retrieval."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Sequence

from langchain_core.documents import Document

TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


@dataclass(frozen=True)
class BM25Hit:
    document: Document
    score: float


class BM25Index:
    """In-memory BM25 index built from the persisted vector-store corpus.

    The index is deliberately rebuilt per tenant so sparse retrieval cannot
    accidentally cross an authorization boundary. A later platform iteration
    can persist this index behind the same interface.
    """

    def __init__(self, documents: Sequence[Document], k1: float = 1.5, b: float = 0.75):
        self.documents = list(documents)
        self.k1 = k1
        self.b = b
        self._tokens = [tokenize(doc.page_content) for doc in self.documents]
        self._lengths = [len(tokens) for tokens in self._tokens]
        self._avgdl = sum(self._lengths) / max(len(self._lengths), 1)
        self._df: Counter[str] = Counter()
        for tokens in self._tokens:
            self._df.update(set(tokens))

    def search(self, query: str, top_k: int = 10) -> list[BM25Hit]:
        query_terms = tokenize(query)
        if not query_terms or not self.documents:
            return []

        n_docs = len(self.documents)
        scores: list[float] = []
        for tokens, length in zip(self._tokens, self._lengths):
            frequencies = Counter(tokens)
            score = 0.0
            for term in query_terms:
                df = self._df.get(term, 0)
                if not df:
                    continue
                idf = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
                tf = frequencies.get(term, 0)
                if not tf:
                    continue
                denominator = tf + self.k1 * (1 - self.b + self.b * length / max(self._avgdl, 1.0))
                score += idf * (tf * (self.k1 + 1)) / denominator
            scores.append(score)

        ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)
        return [BM25Hit(self.documents[i], score) for i, score in ranked[:top_k] if score > 0]
