import json
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Job

STATES = {"draft", "pending_approval", "approved", "rejected", "completed"}


def create_workflow(db: Session, *, tenant_id: str, actor_id: str, name: str, payload: dict[str, Any]) -> Job:
    job = Job(
        tenant_id=tenant_id,
        type="human_approval_workflow",
        status="pending_approval",
        idempotency_key=f"workflow:{tenant_id}:{name}:{actor_id}",
        checkpoint="pending_approval",
        payload=json.dumps({"name": name, "actor_id": actor_id, "data": payload}, ensure_ascii=False),
        max_attempts=1,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def decide_workflow(db: Session, job: Job, *, approved: bool, actor_id: str) -> Job:
    if job.type != "human_approval_workflow" or job.status != "pending_approval":
        raise ValueError("Workflow is not awaiting approval")
    data = json.loads(job.payload)
    data["decision"] = {"approved": approved, "actor_id": actor_id}
    job.payload = json.dumps(data, ensure_ascii=False)
    job.status = "approved" if approved else "rejected"
    job.checkpoint = job.status
    db.commit()
    db.refresh(job)
    return job
