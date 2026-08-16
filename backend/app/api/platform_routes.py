from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.security.dependencies import CurrentUser, get_current_user, get_tenant_id, require_role
from app.services.audit import list_audit

router = APIRouter(prefix="/platform", tags=["platform"])


@router.get("/audit")
async def audit_events(
    limit: int = 100,
    tenant_id: str = Depends(get_tenant_id),
    _: str = Depends(require_role("admin", "manager")),
    db: Session = Depends(get_db),
):
    limit = max(1, min(limit, 500))
    return {"events": list_audit(db, tenant_id=tenant_id, limit=limit)}


@router.get("/identity")
async def identity(current: CurrentUser = Depends(get_current_user)):
    return {"user_id": current.id, "tenant_id": current.tenant_id, "role": current.role}
