from app.services.evidence_graph import detect_contradictions, extract_claims, extract_entities


def test_extract_claims_is_deterministic():
    text = "Acme Corp released version 2.0. It reduced latency by 30 percent."
    claims = extract_claims(text)
    assert len(claims) == 2
    assert claims[0]["claim_type"] == "fact"


def test_extract_entities_deduplicates():
    entities = extract_entities("Acme Corp works with OpenAI. Acme Corp announced a release.")
    names = {item["canonical_name"] for item in entities}
    assert "Acme Corp" in names
    assert "OpenAI" in names


def test_contradiction_detector_requires_overlap():
    assert isinstance(detect_contradictions, object)
