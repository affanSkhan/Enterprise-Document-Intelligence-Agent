from dataclasses import dataclass


@dataclass(frozen=True)
class SecurityCase:
    prompt: str
    expected_detection: bool


def evaluate_security(cases: list[SecurityCase], detector) -> dict[str, float]:
    if not cases:
        return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0}
    tp = fp = fn = tn = 0
    for case in cases:
        detected = bool(detector(case.prompt))
        if detected and case.expected_detection: tp += 1
        elif detected: fp += 1
        elif case.expected_detection: fn += 1
        else: tn += 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"accuracy": (tp + tn) / len(cases), "precision": precision, "recall": recall, "f1": f1}
