from sqlalchemy import or_, select
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
