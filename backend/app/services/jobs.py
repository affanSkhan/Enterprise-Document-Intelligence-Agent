import json

from sqlalchemy.orm import Session

from app.db.models import Job
from app.worker.tasks import ingest_document


def enqueue_ingestion(job: Job) -> str:
    result = ingest_document.delay(job.id)
    return result.id


def job_payload(job: Job) -> dict:
    try:
        return json.loads(job.payload)
    except json.JSONDecodeError:
        return {}
