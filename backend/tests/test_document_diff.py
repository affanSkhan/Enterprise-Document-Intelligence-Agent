from app.services.document_diff import semantic_diff


def artifact(*rows):
    return {"pages": [{"page": 1, "blocks": [{"kind": "text", "text": text, "page": 1, "order": i} for i, text in enumerate(rows)]}]}


def test_numeric_change_is_classified():
    result = semantic_diff(artifact("Payment is 100 USD."), artifact("Payment is 150 USD."))
    assert result["summary"]["modified"] == 1
    assert result["changes"][0]["type"] == "numeric_change"


def test_added_risk_term_is_exposed():
    result = semantic_diff(artifact("The agreement renews annually."), artifact("The agreement terminates annually with a penalty."))
    change = result["changes"][0]
    assert "termination" in change["risk_terms_added"] or "penalty" in change["risk_terms_added"]
    assert result["summary"]["risk_changes"] == 1


def test_add_remove_are_reported():
    result = semantic_diff(artifact("A", "B"), artifact("A", "C", "D"))
    assert result["summary"]["added"] >= 1
    assert result["summary"]["removed"] >= 1
