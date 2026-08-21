import json

from app.db.models import Job
from app.worker.celery_app import INGESTION_QUEUE
from app.worker.tasks import ingest_document


def enqueue_ingestion(job: Job) -> str:
    """Publish an ingestion job explicitly to the worker's queue.

    Do not rely only on Celery's global task routing here. The API process and
    the worker may be running different application instances during local
    development, so the producer should make the destination unambiguous.
    """
    result = ingest_document.apply_async(
        args=[job.id],
        queue=INGESTION_QUEUE,
        exchange=INGESTION_QUEUE,
        routing_key=INGESTION_QUEUE,
    )
    return result.id


def job_payload(job: Job) -> dict:
    try:
        return json.loads(job.payload)
    except json.JSONDecodeError:
        return {}
