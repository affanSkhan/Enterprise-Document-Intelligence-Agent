import re
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Document, EvidenceClaim, EvidenceEdge, EvidenceEntity

ENTITY_RE = re.compile(r"\b(?:[A-Z][\w.-]+(?:\s+[A-Z][\w.-]+){0,3})\b")
NEGATION_RE = re.compile(r"\b(not|no|never)\b", re.IGNORECASE)


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).lower()


def extract_claims(text: str) -> list[dict[str, Any]]:
    """Deterministic baseline; intentionally conservative and replaceable."""
    sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
    claims = []
    for sentence in sentences:
        sentence = sentence.strip()
        if 20 <= len(sentence) <= 800:
            claim_type = "numeric" if re.search(r"\b\d+(?:\.\d+)?\b", sentence) else "fact"
            claims.append({"text": sentence, "claim_type": claim_type, "confidence": 0.55})
    return claims[:100]


def extract_entities(text: str) -> list[dict[str, str]]:
    seen = set()
    entities = []
    for match in ENTITY_RE.findall(text):
        value = match.strip(".,:;()[]{}")
        key = _norm(value)
        if len(value) >= 2 and key not in seen:
            seen.add(key)
            entities.append({"canonical_name": value, "entity_type": "named_entity"})
    return entities[:100]


def build_document_graph(db: Session, *, tenant_id: str, document_id: str, text: str) -> dict[str, Any]:
    document = db.query(Document).filter(Document.id == document_id, Document.tenant_id == tenant_id).first()
    if not document:
        raise ValueError("Document not found in tenant")

    claims = []
    for item in extract_claims(text):
        existing = db.query(EvidenceClaim).filter(EvidenceClaim.document_id == document_id, EvidenceClaim.text == item["text"]).first()
        claim = existing or EvidenceClaim(tenant_id=tenant_id, document_id=document_id, source_locator="document", **item)
        if not existing:
            db.add(claim)
            db.flush()
        claims.append(claim)

    entities = []
    for item in extract_entities(text):
        entity = db.query(EvidenceEntity).filter(EvidenceEntity.tenant_id == tenant_id, EvidenceEntity.canonical_name == item["canonical_name"], EvidenceEntity.entity_type == item["entity_type"]).first()
        if not entity:
            entity = EvidenceEntity(tenant_id=tenant_id, **item)
            db.add(entity)
            db.flush()
        entities.append(entity)

    edges = 0
    for claim in claims:
        for entity in entities:
            if _norm(entity.canonical_name) in _norm(claim.text):
                exists = db.query(EvidenceEdge).filter(EvidenceEdge.tenant_id == tenant_id, EvidenceEdge.subject_type == "claim", EvidenceEdge.subject_id == claim.id, EvidenceEdge.predicate == "mentions", EvidenceEdge.object_type == "entity", EvidenceEdge.object_id == entity.id).first()
                if not exists:
                    db.add(EvidenceEdge(tenant_id=tenant_id, subject_type="claim", subject_id=claim.id, predicate="mentions", object_type="entity", object_id=entity.id, confidence=claim.confidence, evidence_claim_id=claim.id))
                    edges += 1
    db.commit()
    return {"document_id": document_id, "claims": len(claims), "entities": len(entities), "edges_created": edges}


def verify_claims(db: Session, *, tenant_id: str, claims: list[str]) -> list[dict[str, Any]]:
    rows = db.query(EvidenceClaim).filter(EvidenceClaim.tenant_id == tenant_id).all()
    result = []
    for requested in claims:
        key = _norm(requested)
        matches = [row for row in rows if key in _norm(row.text) or _norm(row.text) in key]
        result.append({"claim": requested, "supported": bool(matches), "evidence": [{"claim_id": row.id, "document_id": row.document_id, "text": row.text, "confidence": row.confidence, "source_locator": row.source_locator} for row in matches[:5]]})
    return result


def detect_contradictions(db: Session, *, tenant_id: str) -> list[dict[str, Any]]:
    """Conservative explicit-negation detector. Numeric disagreements remain unknown."""
    claims = db.query(EvidenceClaim).filter(EvidenceClaim.tenant_id == tenant_id).all()
    contradictions = []
    negated = [(c, NEGATION_RE.sub("", _norm(c.text))) for c in claims if NEGATION_RE.search(c.text)]
    positive = [(c, _norm(c.text)) for c in claims if not NEGATION_RE.search(c.text)]
    for negative_claim, neg_text in negated:
        for positive_claim, pos_text in positive:
            if negative_claim.id == positive_claim.id:
                continue
            neg_words, pos_words = set(neg_text.split()), set(pos_text.split())
            overlap = len(neg_words & pos_words) / max(1, len(neg_words | pos_words))
            if overlap >= 0.45:
                contradictions.append({"claim_a": negative_claim.id, "claim_b": positive_claim.id, "confidence": round(overlap, 3), "type": "lexical_negation"})
    return contradictions[:100]


def graph_snapshot(db: Session, *, tenant_id: str, entity: str | None = None) -> dict[str, Any]:
    entities = db.query(EvidenceEntity).filter(EvidenceEntity.tenant_id == tenant_id).all()
    if entity:
        key = _norm(entity)
        entities = [e for e in entities if key in _norm(e.canonical_name)]
    edges = db.query(EvidenceEdge).filter(EvidenceEdge.tenant_id == tenant_id).all()
    allowed = {e.id for e in entities}
    if entity:
        edges = [e for e in edges if e.object_id in allowed or e.subject_id in allowed]
    return {"nodes": [{"id": e.id, "type": "entity", "name": e.canonical_name, "entity_type": e.entity_type} for e in entities], "edges": [{"id": e.id, "source": e.subject_id, "target": e.object_id, "predicate": e.predicate, "confidence": e.confidence, "evidence_claim_id": e.evidence_claim_id} for e in edges]}
