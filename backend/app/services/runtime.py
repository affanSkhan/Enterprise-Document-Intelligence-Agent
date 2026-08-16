import hashlib
import json
import time
from typing import Any
from app.core.logging import log


def fingerprint(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str).encode()
    return hashlib.sha256(raw).hexdigest()


def record_usage(model: str, latency_ms: float, input_tokens: int = 0, output_tokens: int = 0, cost_usd: float = 0.0) -> dict:
    event = {"model": model, "latency_ms": round(latency_ms, 2), "input_tokens": input_tokens, "output_tokens": output_tokens, "cost_usd": cost_usd}
    log.info("llm.usage", **event)
    return event


def retry(operation, attempts: int = 3, base_delay: float = 0.5):
    last_error = None
    for attempt in range(attempts):
        try:
            return operation()
        except Exception as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(base_delay * (2 ** attempt))
    raise last_error
