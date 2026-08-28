from __future__ import annotations

import json
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from app.db.models import Job
from app.db.session import SessionLocal
from app.services.ingestion import process_document_job

# Render's free web instance has only 512 MB RAM. Running Uvicorn and a
# separate Celery Python process in the same service exceeded that limit and
# made the public API intermittently return 502. Keep one process and use a
# bounded background executor instead. PostgreSQL remains the durable source
# of truth, and startup recovery re-submits queued/running jobs.
_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ingestion")
_FUTURES: dict[str, object] = {}
_LOCK = threading.Lock()


def _run_job_with_retries(job_id: str) -> None:
    while True:
        try:
            process_document_job(job_id)
            return
        except Exception:
            with SessionLocal() as db:
                job = db.get(Job, job_id)
                if not job or job.status == "dead" or job.attempts >= job.max_attempts:
                    return
                attempt = job.attempts
            time.sleep(min(300, 2 ** max(attempt - 1, 0) * 10))


def enqueue_ingestion(job: Job) -> str:
    """Queue an ingestion job on the API process without spawning a second Python runtime."""
    task_id = str(uuid.uuid4())
    future = _EXECUTOR.submit(_run_job_with_retries, job.id)
    with _LOCK:
        _FUTURES[task_id] = future
    return task_id


def recover_pending_ingestion_jobs() -> int:
    """Requeue durable ingestion jobs after an API restart."""
    recovered = 0
    with SessionLocal() as db:
        jobs = (
            db.query(Job)
            .filter(
                Job.type == "document_ingestion",
                Job.status.in_(["queued", "running"]),
            )
            .order_by(Job.created_at.asc())
            .all()
        )
        for job in jobs:
            job.status = "queued"
            job.error = None
            db.commit()
            enqueue_ingestion(job)
            recovered += 1
    return recovered


def job_payload(job: Job) -> dict:
    try:
        return json.loads(job.payload)
    except json.JSONDecodeError:
        return {}
