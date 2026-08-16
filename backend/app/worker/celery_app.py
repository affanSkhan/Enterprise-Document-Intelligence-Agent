from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "enterprise-intelligence",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)
celery_app.conf.update(
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    result_expires=settings.JOB_TTL_SECONDS,
    task_routes={"app.worker.tasks.ingest_document": {"queue": "document-ingestion"}},
)

celery_app.autodiscover_tasks(["app.worker"])
