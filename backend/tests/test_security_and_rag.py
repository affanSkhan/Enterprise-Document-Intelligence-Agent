from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agents.retrieval import _abstention_response, _score_to_confidence
from app.db.models import Base, Document, DocumentPermission, Tenant, User
from app.security.acl import allowed_document_ids, can_read_document
from app.security.auth import create_access_token, decode_access_token, hash_password, verify_password


def make_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)()


def test_password_hash_and_jwt_round_trip():
    password = "TestPassword123!"
    hashed = hash_password(password)
    assert hashed.startswith("$2")
    assert verify_password(password, hashed)
    assert not verify_password("wrong-password", hashed)

    token = create_access_token(user_id="user-1", tenant_id="tenant-1", role="viewer")
    claims = decode_access_token(token)
    assert claims["sub"] == "user-1"
    assert claims["tenant_id"] == "tenant-1"
    assert claims["role"] == "viewer"


def test_viewer_acl_denies_until_explicit_read_permission():
    db = make_session()
    tenant = Tenant(id="tenant-1", name="Test Tenant")
    user = User(id="user-1", tenant_id=tenant.id, email="viewer@test.local", role="viewer", is_active=True)
    document = Document(
        id="doc-1",
        tenant_id=tenant.id,
        filename="policy.pdf",
        file_type="application/pdf",
        file_path="/tmp/policy.pdf",
        checksum="a" * 64,
        status="INDEXED",
    )
    db.add_all([tenant, user, document])
    db.commit()

    assert allowed_document_ids(db, tenant_id=tenant.id, user_id=user.id, role="viewer") == []
    assert not can_read_document(db, document_id=document.id, tenant_id=tenant.id, user_id=user.id, role="viewer")

    db.add(DocumentPermission(document_id=document.id, user_id=user.id, permission="read"))
    db.commit()

    assert allowed_document_ids(db, tenant_id=tenant.id, user_id=user.id, role="viewer") == [document.id]
    assert can_read_document(db, document_id=document.id, tenant_id=tenant.id, user_id=user.id, role="viewer")
    db.close()


def test_admin_has_tenant_wide_document_access_but_not_cross_tenant_access():
    db = make_session()
    tenant_a = Tenant(id="tenant-a", name="Tenant A")
    tenant_b = Tenant(id="tenant-b", name="Tenant B")
    admin = User(id="admin-a", tenant_id=tenant_a.id, email="admin@a.local", role="admin", is_active=True)
    doc_a = Document(id="doc-a", tenant_id=tenant_a.id, filename="a.pdf", file_type="application/pdf", file_path="/tmp/a", checksum="b" * 64, status="INDEXED")
    doc_b = Document(id="doc-b", tenant_id=tenant_b.id, filename="b.pdf", file_type="application/pdf", file_path="/tmp/b", checksum="c" * 64, status="INDEXED")
    db.add_all([tenant_a, tenant_b, admin, doc_a, doc_b])
    db.commit()

    assert allowed_document_ids(db, tenant_id=tenant_a.id, user_id=admin.id, role="admin") is None
    assert can_read_document(db, document_id=doc_a.id, tenant_id=tenant_a.id, user_id=admin.id, role="admin")
    assert not can_read_document(db, document_id=doc_b.id, tenant_id=tenant_a.id, user_id=admin.id, role="admin")
    db.close()


def test_abstention_response_is_explicit_and_safe():
    response = _abstention_response(5)
    assert response["abstained"] is True
    assert response["verified"] is False
    assert response["confidence"] == 0.0
    assert response["model"] is None
    assert response["evidence"] == []
    assert response["retrieval"]["accepted_evidence"] == 0


def test_confidence_is_bounded_heuristic():
    assert 0.0 < _score_to_confidence(-10) < 0.5
    assert _score_to_confidence(0) == 0.5
    assert 0.5 < _score_to_confidence(10) < 1.0
