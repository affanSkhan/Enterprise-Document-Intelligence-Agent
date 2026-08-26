import json
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import AuditLog


def record_audit(db: Session, *, tenant_id: str, actor_id: str | None, action: str, resource_type: str | None = None, resource_id: str | None = None, details: dict[str, Any] | None = None) -> AuditLog:
    event = AuditLog(
        tenant_id=tenant_id,
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=json.dumps(details or {}, ensure_ascii=False),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_audit(db: Session, *, tenant_id: str, limit: int = 100) -> list[AuditLog]:
    return db.query(AuditLog).filter(AuditLog.tenant_id == tenant_id).order_by(AuditLog.created_at.desc()).limit(limit).all()
