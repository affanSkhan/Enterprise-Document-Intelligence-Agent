from app.evaluation.generation import citation_precision
from app.evaluation.security import SecurityCase, evaluate_security


def test_citation_precision_counts_only_supported_sources():
    score = citation_precision("Answer [report.pdf] and [fake.pdf]", ["report.pdf"])
    assert score.supported == 1
    assert score.cited == 2
    assert score.precision == 0.5


def test_security_evaluation_metrics():
    cases = [SecurityCase("attack", True), SecurityCase("normal", False)]
    result = evaluate_security(cases, lambda prompt: prompt == "attack")
    assert result["accuracy"] == 1.0
    assert result["precision"] == 1.0
    assert result["recall"] == 1.0
    assert result["f1"] == 1.0
