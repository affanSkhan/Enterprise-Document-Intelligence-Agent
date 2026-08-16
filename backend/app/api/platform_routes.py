from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents.cost_policy import choose_cost_aware_model
from app.db.session import get_db
from app.security.dependencies import CurrentUser, get_current_user, get_tenant_id, require_role
from app.services.audit import list_audit

router = APIRouter(prefix="/platform", tags=["platform"])


@router.get("/audit")
async def audit_events(limit: int = 100, tenant_id: str = Depends(get_tenant_id), _: str = Depends(require_role("admin", "manager")), db: Session = Depends(get_db)):
    limit = max(1, min(limit, 500))
    return {"events": list_audit(db, tenant_id=tenant_id, limit=limit)}


@router.get("/identity")
async def identity(current: CurrentUser = Depends(get_current_user)):
    return {"user_id": current.id, "tenant_id": current.tenant_id, "role": current.role}


@router.get("/model-policy")
async def model_policy(query_tokens: int = 200, context_tokens: int = 800, budget_usd: float | None = None, _: CurrentUser = Depends(get_current_user)):
    policy = choose_cost_aware_model(query_tokens, context_tokens, budget_usd=budget_usd)
    return {"model": policy.model, "max_output_tokens": policy.max_output_tokens, "estimated_usd_per_1k_tokens": policy.estimated_usd_per_1k_tokens, "estimate_only": True}
