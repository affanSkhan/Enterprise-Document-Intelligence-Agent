import json

from app.db.models import Job
from app.db.session import SessionLocal
from app.worker.celery_app import INGESTION_QUEUE
from app.worker.tasks import ingest_document


def enqueue_ingestion(job: Job) -> str:
    """Publish an ingestion job explicitly to the worker's queue."""
    result = ingest_document.apply_async(
        args=[job.id],
        queue=INGESTION_QUEUE,
        exchange=INGESTION_QUEUE,
        routing_key=INGESTION_QUEUE,
    )
    return result.id


def recover_pending_ingestion_jobs() -> int:
    """Requeue durable ingestion jobs after an API/worker restart.

    Render can restart the combined API + worker service while a document is
    being processed. The database record must remain the source of truth so a
    restart cannot strand a document in queued/running state.
    """
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
