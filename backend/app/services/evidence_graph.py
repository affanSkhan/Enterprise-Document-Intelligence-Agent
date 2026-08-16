import json
import re
from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Document, EvidenceClaim, EvidenceEdge, EvidenceEntity

ENTITY_RE = re.compile(r"\b(?:[A-Z][\w.-]+(?:\s+[A-Z][\w.-]+){0,3})\b")


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).lower()


def extract_claims(text: str) -> list[dict[str, Any]]:
    """Deterministic baseline claim extraction; designed to be replaceable by an LLM extractor."""
    sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
    claims = []
    for sentence in sentences:
        sentence = sentence.strip()
        if 20 <= len(sentence) <= 800:
            claims.append({"text": sentence, "claim_type": "fact", "confidence": 0.55})
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
        claim = existing or EvidenceClaim(tenant_id=tenant_id, document_id=document_id, **item)
        if not existing:
            db.add(claim)
            db.flush()
        claims.append(claim)

    entities = []
    for item in extract_entities(text):
        entity = db.query(EvidenceEntity).filter(
            EvidenceEntity.tenant_id == tenant_id,
            EvidenceEntity.canonical_name == item["canonical_name"],
            EvidenceEntity.entity_type == item["entity_type"],
        ).first()
        if not entity:
            entity = EvidenceEntity(tenant_id=tenant_id, **item)
            db.add(entity)
            db.flush()
        entities.append(entity)

    # Baseline graph edges connect claims to entities appearing in the claim.
    edges = 0
    for claim in claims:
        for entity in entities:
            if _norm(entity.canonical_name) in _norm(claim.text):
                exists = db.query(EvidenceEdge).filter(
                    EvidenceEdge.tenant_id == tenant_id,
                    EvidenceEdge.subject_type == "claim",
                    EvidenceEdge.subject_id == claim.id,
                    EvidenceEdge.predicate == "mentions",
                    EvidenceEdge.object_type == "entity",
                    EvidenceEdge.object_id == entity.id,
                ).first()
                if not exists:
                    db.add(EvidenceEdge(tenant_id=tenant_id, subject_type="claim", subject_id=claim.id,
                                        predicate="mentions", object_type="entity", object_id=entity.id,
                                        confidence=claim.confidence, evidence_claim_id=claim.id))
                    edges += 1
    db.commit()
    return {"document_id": document_id, "claims": len(claims), "entities": len(entities), "edges_created": edges}


def verify_claims(db: Session, *, tenant_id: str, claims: list[str]) -> list[dict[str, Any]]:
    rows = db.query(EvidenceClaim).filter(EvidenceClaim.tenant_id == tenant_id).all()
    result = []
    for requested in claims:
        key = _norm(requested)
        matches = [row for row in rows if key in _norm(row.text) or _norm(row.text) in key]
        result.append({
            "claim": requested,
            "supported": bool(matches),
            "evidence": [{"claim_id": row.id, "document_id": row.document_id, "text": row.text, "confidence": row.confidence} for row in matches[:5]],
        })
    return result


def detect_contradictions(db: Session, *, tenant_id: str) -> list[dict[str, Any]]:
    """Conservative baseline: detects explicit negation pairs with high lexical overlap."""
    claims = db.query(EvidenceClaim).filter(EvidenceClaim.tenant_id == tenant_id).all()
    contradictions = []
    negated = [(c, re.sub(r"\bnot\b|\bno\b|\bnever\b", "", _norm(c.text))) for c in claims if re.search(r"\bnot\b|\bno\b|\bnever\b", _norm(c.text))]
    positive = [(c, _norm(c.text)) for c in claims if not re.search(r"\bnot\b|\bno\b|\bnever\b", _norm(c.text))]
    for negative_claim, neg_text in negated:
        for positive_claim, pos_text in positive:
            neg_words, pos_words = set(neg_text.split()), set(pos_text.split())
            overlap = len(neg_words & pos_words) / max(1, len(neg_words | pos_words))
            if overlap >= 0.45 and negative_claim.id != positive_claim.id:
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
    return {
        "nodes": [{"id": e.id, "type": "entity", "name": e.canonical_name, "entity_type": e.entity_type} for e in entities],
        "edges": [{"id": e.id, "source": e.subject_id, "target": e.object_id, "predicate": e.predicate, "confidence": e.confidence, "evidence_claim_id": e.evidence_claim_id} for e in edges],
    }
