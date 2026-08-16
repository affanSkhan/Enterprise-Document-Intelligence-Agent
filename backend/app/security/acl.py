from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentPermission

TENANT_WIDE_ROLES = {"admin", "manager"}


def allowed_document_ids(db: Session, *, tenant_id: str, user_id: str, role: str) -> list[str] | None:
    """Return None for tenant-wide access, otherwise explicit read ACL document IDs."""
    if role in TENANT_WIDE_ROLES:
        return None
    rows = db.execute(
        select(DocumentPermission.document_id)
        .join(Document, Document.id == DocumentPermission.document_id)
        .where(
            Document.tenant_id == tenant_id,
            DocumentPermission.user_id == user_id,
            DocumentPermission.permission == "read",
        )
    ).scalars().all()
    return list(rows)


def can_read_document(db: Session, *, document_id: str, tenant_id: str, user_id: str, role: str) -> bool:
    if role in TENANT_WIDE_ROLES:
        return db.query(Document.id).filter(Document.id == document_id, Document.tenant_id == tenant_id).first() is not None
    return db.query(DocumentPermission.id).join(Document).filter(
        Document.id == document_id,
        Document.tenant_id == tenant_id,
        DocumentPermission.user_id == user_id,
        DocumentPermission.permission == "read",
    ).first() is not None
