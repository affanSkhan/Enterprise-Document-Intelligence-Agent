import sys
import time
from contextlib import contextmanager

import structlog


def configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


log = structlog.get_logger()


@contextmanager
def timed(operation: str, **fields):
    started = time.perf_counter()
    try:
        yield
        log.info("operation.completed", operation=operation,
                 duration_ms=round((time.perf_counter() - started) * 1000, 2), **fields)
    except Exception:
        log.exception("operation.failed", operation=operation,
                      duration_ms=round((time.perf_counter() - started) * 1000, 2), **fields)
        raise
