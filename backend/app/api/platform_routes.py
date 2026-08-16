from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents.cost_policy import choose_cost_aware_model
from app.db.models import Job
from app.db.session import get_db
from app.security.dependencies import CurrentUser, get_current_user, get_tenant_id, require_role
from app.services.audit import list_audit, record_audit
from app.services.calculator import safe_calculate
from app.services.workflow import create_workflow, decide_workflow

router = APIRouter(prefix="/platform", tags=["platform"])


class WorkflowRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    data: dict = Field(default_factory=dict)


class CalculationRequest(BaseModel):
    expression: str = Field(min_length=1, max_length=200)


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


@router.post("/calculate")
async def calculate(request: CalculationRequest, tenant_id: str = Depends(get_tenant_id), current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        result = safe_calculate(request.expression)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    record_audit(db, tenant_id=tenant_id, actor_id=current.id, action="tool.calculate", resource_type="calculation", details={"expression": request.expression})
    return {"expression": request.expression, "result": result, "tool": "safe-arithmetic", "verified": True}


@router.post("/workflows", status_code=201)
async def create_approval_workflow(request: WorkflowRequest, tenant_id: str = Depends(get_tenant_id), current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    job = create_workflow(db, tenant_id=tenant_id, actor_id=current.id, name=request.name, payload=request.data)
    record_audit(db, tenant_id=tenant_id, actor_id=current.id, action="workflow.created", resource_type="job", resource_id=job.id, details={"name": request.name})
    return {"workflow_id": job.id, "status": job.status, "checkpoint": job.checkpoint}


@router.post("/workflows/{workflow_id}/decision")
async def decide_approval_workflow(workflow_id: str, approved: bool, tenant_id: str = Depends(get_tenant_id), current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == workflow_id, Job.tenant_id == tenant_id, Job.type == "human_approval_workflow").first()
    if not job:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if current.role not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="Approval requires manager or admin role")
    try:
        job = decide_workflow(db, job, approved=approved, actor_id=current.id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    record_audit(db, tenant_id=tenant_id, actor_id=current.id, action="workflow.decision", resource_type="job", resource_id=job.id, details={"approved": approved})
    return {"workflow_id": job.id, "status": job.status, "checkpoint": job.checkpoint}
