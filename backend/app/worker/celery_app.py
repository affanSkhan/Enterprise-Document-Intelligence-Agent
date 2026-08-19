from celery import Celery

from app.core.config import settings

INGESTION_QUEUE = "document-ingestion"

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
    # Make the ingestion queue the default as well as an explicit task route.
    # This protects producers running outside Docker from silently publishing
    # ingestion jobs to Celery's default `celery` queue.
    task_default_queue=INGESTION_QUEUE,
    task_default_exchange=INGESTION_QUEUE,
    task_default_routing_key=INGESTION_QUEUE,
    task_routes={
        "app.worker.tasks.ingest_document": {"queue": INGESTION_QUEUE}
    },
)

celery_app.autodiscover_tasks(["app.worker"])
