import ssl

from celery import Celery

from app.core.config import settings

INGESTION_QUEUE = "document-ingestion"

redis_ssl = {"ssl_cert_reqs": ssl.CERT_REQUIRED}

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
    broker_use_ssl=redis_ssl if settings.REDIS_URL.startswith("rediss://") else None,
    redis_backend_use_ssl=redis_ssl if settings.REDIS_URL.startswith("rediss://") else None,
    task_default_queue=INGESTION_QUEUE,
    task_default_exchange=INGESTION_QUEUE,
    task_default_routing_key=INGESTION_QUEUE,
    task_routes={
        "app.worker.tasks.ingest_document": {"queue": INGESTION_QUEUE}
    },
)

celery_app.autodiscover_tasks(["app.worker"])
