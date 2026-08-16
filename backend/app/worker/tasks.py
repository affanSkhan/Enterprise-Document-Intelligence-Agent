from celery import Task

from app.db.models import Job
from app.db.session import SessionLocal
from app.worker.celery_app import celery_app


class IngestionTask(Task):
    autoretry_for = ()
    max_retries = 5
    default_retry_delay = 10


@celery_app.task(bind=True, base=IngestionTask, name="app.worker.tasks.ingest_document")
def ingest_document(self, job_id: str):
    from app.services.ingestion import process_document_job

    try:
        process_document_job(job_id)
        return {"job_id": job_id, "status": "succeeded"}
    except Exception as exc:
        with SessionLocal() as db:
            job = db.get(Job, job_id)
            if not job or job.status == "dead":
                return {"job_id": job_id, "status": "dead"}
            attempt = job.attempts
        countdown = min(300, 2 ** max(attempt - 1, 0) * 10)
        raise self.retry(exc=exc, countdown=countdown)
