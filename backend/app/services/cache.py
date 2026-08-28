import json
from typing import Any

from redis import Redis

from app.core.config import settings


def _client() -> Redis:
    return Redis.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=1, socket_timeout=1)


def get_json(key: str) -> Any | None:
    try:
        value = _client().get(key)
        return json.loads(value) if value else None
    except Exception:
        return None


def set_json(key: str, value: Any, ttl_seconds: int = 60) -> bool:
    try:
        _client().setex(key, ttl_seconds, json.dumps(value, ensure_ascii=False))
        return True
    except Exception:
        return False


def delete(key: str) -> bool:
    try:
        _client().delete(key)
        return True
    except Exception:
        return False
