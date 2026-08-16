import time
from starlette.middleware.base import BaseHTTPMiddleware
from .metrics import REQUEST_LATENCY, REQUESTS


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        started = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            path = request.url.path
            elapsed = time.perf_counter() - started
            REQUESTS.labels(request.method, path, str(status)).inc()
            REQUEST_LATENCY.labels(request.method, path).observe(elapsed)
