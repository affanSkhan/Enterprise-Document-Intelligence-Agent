"""Run the explicit contradiction benchmark without claiming model accuracy.

The benchmark currently validates the deterministic baseline's intended behavior on
explicit negation pairs. Cases labelled unknown/same are intentionally not counted
as contradictions, which keeps the test conservative.
"""
import json
import re
from pathlib import Path


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\b(not|no|never)\b", "", text)
    return re.sub(r"\s+", " ", text).strip()


def is_explicit_contradiction(a: str, b: str) -> bool:
    a_low, b_low = a.lower(), b.lower()
    neg_a = bool(re.search(r"\b(not|no|never)\b", a_low))
    neg_b = bool(re.search(r"\b(not|no|never)\b", b_low))
    if neg_a == neg_b:
        return False
    return normalize(a) == normalize(b)


def main() -> int:
    path = Path(__file__).with_name("contradiction_benchmark.json")
    cases = json.loads(path.read_text(encoding="utf-8"))["cases"]
    expected = [c["label"] == "contradiction" for c in cases]
    predicted = [is_explicit_contradiction(c["claim_a"], c["claim_b"]) for c in cases]
    tp = sum(p and y for p, y in zip(predicted, expected))
    fp = sum(p and not y for p, y in zip(predicted, expected))
    fn = sum(not p and y for p, y in zip(predicted, expected))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    print(json.dumps({"cases": len(cases), "tp": tp, "fp": fp, "fn": fn, "precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}, indent=2))
    return 0 if fp == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
