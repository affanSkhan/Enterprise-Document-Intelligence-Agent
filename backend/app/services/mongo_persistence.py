"""Persistence repository for schema-variable AI history and execution telemetry."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pymongo.errors import PyMongoError

from app.core.logging import log
from app.db.mongodb import get_mongodb


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _safe(value: Any) -> Any:
    """Keep provider-specific objects out of BSON while preserving useful structure."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value
    if isinstance(value, dict):
        return {str(k): _safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe(v) for v in value]
    return str(value)


class MongoPersistence:
    """Tenant/user-scoped repository. MongoDB is never used as an auth layer."""

    def __init__(self, mongo=None) -> None:
        self.mongo = mongo if mongo is not None else get_mongodb()

    @property
    def enabled(self) -> bool:
        return self.mongo is not None

    def _run(self, operation, default=None):
        if not self.enabled:
            return default
        try:
            return operation()
        except PyMongoError as exc:
            log.warning("mongodb.persistence_failed", error=str(exc))
            return default

    def create_or_get_conversation(
        self,
        tenant_id: str,
        user_id: str,
        conversation_id: str | None = None,
        title: str | None = None,
    ) -> str | None:
        cid = conversation_id or str(uuid4())
        now = utcnow()

        def op():
            conversations = self.mongo.collection("conversations")
            conversations.update_one(
                {"conversation_id": cid, "tenant_id": tenant_id, "user_id": user_id},
                {
                    "$setOnInsert": {
                        "_id": cid,
                        "conversation_id": cid,
                        "tenant_id": tenant_id,
                        "user_id": user_id,
                        "title": title or "New conversation",
                        "message_count": 0,
                        "created_at": now,
                    },
                    "$set": {"updated_at": now},
                },
                upsert=True,
            )
            return cid

        return self._run(op)

    def append_message(
        self,
        tenant_id: str,
        user_id: str,
        conversation_id: str,
        role: str,
        content: str,
        citations: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
        message_id: str | None = None,
    ) -> str | None:
        mid = message_id or str(uuid4())
        now = utcnow()

        def op():
            conversations = self.mongo.collection("conversations")
            messages = self.mongo.collection("conversation_messages")
            scope = {
                "conversation_id": conversation_id,
                "tenant_id": tenant_id,
                "user_id": user_id,
            }
            if conversations.count_documents(scope, limit=1) == 0:
                return None
            result = messages.update_one(
                {"message_id": mid, **scope},
                {
                    "$setOnInsert": {
                        "_id": mid,
                        "message_id": mid,
                        "conversation_id": conversation_id,
                        "tenant_id": tenant_id,
                        "user_id": user_id,
                        "role": role,
                        "content": content,
                        "citations": _safe(citations or []),
                        "metadata": _safe(metadata or {}),
                        "created_at": now,
                    }
                },
                upsert=True,
            )
            conversation_update: dict[str, Any] = {"$set": {"updated_at": now}}
            if result.upserted_id is not None:
                conversation_update["$inc"] = {"message_count": 1}
            conversations.update_one(scope, conversation_update)
            return mid

        return self._run(op)

    def list_conversations(self, tenant_id: str, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        def op():
            cursor = (
                self.mongo.collection("conversations")
                .find(
                    {"tenant_id": tenant_id, "user_id": user_id},
                    {"_id": 0},
                )
                .sort("updated_at", -1)
                .limit(limit)
            )
            return list(cursor)

        return self._run(op, default=[])

    def get_conversation(self, tenant_id: str, user_id: str, conversation_id: str) -> dict[str, Any] | None:
        def op():
            conversation = self.mongo.collection("conversations").find_one(
                {"conversation_id": conversation_id, "tenant_id": tenant_id, "user_id": user_id},
                {"_id": 0},
            )
            if not conversation:
                return None
            conversation["messages"] = list(
                self.mongo.collection("conversation_messages")
                .find(
                    {
                        "conversation_id": conversation_id,
                        "tenant_id": tenant_id,
                        "user_id": user_id,
                    },
                    {"_id": 0},
                )
                .sort("created_at", 1)
            )
            return conversation

        return self._run(op)

    def start_agent_run(
        self,
        tenant_id: str,
        user_id: str,
        agent_type: str,
        task_type: str,
        conversation_id: str | None = None,
        input_data: dict[str, Any] | None = None,
        run_id: str | None = None,
    ) -> str | None:
        rid = run_id or str(uuid4())
        now = utcnow()

        def op():
            self.mongo.collection("agent_runs").update_one(
                {"run_id": rid},
                {
                    "$setOnInsert": {
                        "_id": rid,
                        "run_id": rid,
                        "tenant_id": tenant_id,
                        "user_id": user_id,
                        "conversation_id": conversation_id,
                        "agent_type": agent_type,
                        "task_type": task_type,
                        "status": "running",
                        "input": _safe(input_data or {}),
                        "steps": [],
                        "created_at": now,
                    },
                    "$set": {"updated_at": now},
                },
                upsert=True,
            )
            return rid

        return self._run(op)

    def append_step(
        self,
        run_id: str,
        tenant_id: str,
        step_type: str,
        *,
        tool: str | None = None,
        input_data: Any = None,
        output: Any = None,
        metadata: dict[str, Any] | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> bool:
        now = utcnow()

        def op():
            step = {
                "step_id": str(uuid4()),
                "type": step_type,
                "tool": tool,
                "input": _safe(input_data),
                "output": _safe(output),
                "metadata": _safe(metadata or {}),
                "started_at": started_at or now,
                "completed_at": completed_at or now,
            }
            result = self.mongo.collection("agent_runs").update_one(
                {"run_id": run_id, "tenant_id": tenant_id},
                {"$push": {"steps": step}, "$set": {"updated_at": now}},
            )
            return result.modified_count == 1

        return bool(self._run(op, default=False))

    def complete_agent_run(
        self,
        run_id: str,
        tenant_id: str,
        *,
        status: str,
        final_output: Any = None,
        model: str | None = None,
        token_usage: dict[str, Any] | None = None,
        latency_ms: float | None = None,
        citations: list[dict[str, Any]] | None = None,
        error: str | None = None,
    ) -> bool:
        now = utcnow()

        def op():
            update = {
                "$set": {
                    "status": status,
                    "final_output": _safe(final_output),
                    "model": model,
                    "token_usage": _safe(token_usage or {}),
                    "latency_ms": latency_ms,
                    "citations": _safe(citations or []),
                    "error": error,
                    "completed_at": now,
                    "updated_at": now,
                }
            }
            result = self.mongo.collection("agent_runs").update_one(
                {"run_id": run_id, "tenant_id": tenant_id},
                update,
            )
            return result.matched_count == 1

        return bool(self._run(op, default=False))

    def get_agent_run(self, run_id: str, tenant_id: str, user_id: str | None = None) -> dict[str, Any] | None:
        def op():
            scope: dict[str, Any] = {"run_id": run_id, "tenant_id": tenant_id}
            if user_id:
                scope["user_id"] = user_id
            return self.mongo.collection("agent_runs").find_one(scope, {"_id": 0})

        return self._run(op)

    def list_agent_runs(
        self,
        tenant_id: str,
        user_id: str,
        conversation_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        def op():
            scope: dict[str, Any] = {"tenant_id": tenant_id, "user_id": user_id}
            if conversation_id:
                scope["conversation_id"] = conversation_id
            return list(
                self.mongo.collection("agent_runs")
                .find(scope, {"_id": 0})
                .sort("created_at", -1)
                .limit(limit)
            )

        return self._run(op, default=[])


def get_persistence() -> MongoPersistence:
    return MongoPersistence()
