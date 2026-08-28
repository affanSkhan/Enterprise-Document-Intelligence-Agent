import ssl
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from celery import Celery

from app.core.config import settings

INGESTION_QUEUE = "document-ingestion"


def _normalize_redis_url(url: str) -> str:
    """Make Celery's Redis backend explicit about TLS certificate verification."""
    if not url.startswith("rediss://"):
        return url
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.setdefault("ssl_cert_reqs", "CERT_REQUIRED")
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


redis_url = _normalize_redis_url(settings.REDIS_URL)
redis_ssl = {"ssl_cert_reqs": ssl.CERT_REQUIRED}

celery_app = Celery(
    "enterprise-intelligence",
    broker=redis_url,
    backend=redis_url,
)
celery_app.conf.update(
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    result_expires=settings.JOB_TTL_SECONDS,
    broker_use_ssl=redis_ssl if redis_url.startswith("rediss://") else None,
    redis_backend_use_ssl=redis_ssl if redis_url.startswith("rediss://") else None,
    task_default_queue=INGESTION_QUEUE,
    task_default_exchange=INGESTION_QUEUE,
    task_default_routing_key=INGESTION_QUEUE,
    task_routes={
        "app.worker.tasks.ingest_document": {"queue": INGESTION_QUEUE}
    },
)

celery_app.autodiscover_tasks(["app.worker"])
