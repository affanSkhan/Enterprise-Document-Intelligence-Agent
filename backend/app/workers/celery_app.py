import ssl

from celery import Celery

from app.core.config import settings


redis_ssl = {"ssl_cert_reqs": ssl.CERT_REQUIRED}

celery_app = Celery(
    "enterprise_runtime",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    broker_use_ssl=redis_ssl if settings.REDIS_URL.startswith("rediss://") else None,
    redis_backend_use_ssl=redis_ssl if settings.REDIS_URL.startswith("rediss://") else None,
)


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def health_task(self):
    return {"status": "ok", "task_id": self.request.id}
