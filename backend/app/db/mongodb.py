"""MongoDB connection and collection boundary.

MongoDB is intentionally scoped to schema-variable conversation and AI execution
data. Relational entities and vector retrieval remain in their existing stores.
"""
from __future__ import annotations

from functools import lru_cache
from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import PyMongoError

from app.core.config import settings
from app.core.logging import log


class MongoDB:
    def __init__(self, uri: str, database_name: str, client: MongoClient | None = None) -> None:
        self.uri = uri
        self.database_name = database_name
        self.client = client or MongoClient(
            uri,
            appname=settings.MONGODB_APP_NAME,
            connectTimeoutMS=settings.MONGODB_CONNECT_TIMEOUT_MS,
            serverSelectionTimeoutMS=settings.MONGODB_SERVER_SELECTION_TIMEOUT_MS,
            socketTimeoutMS=settings.MONGODB_SOCKET_TIMEOUT_MS,
            maxPoolSize=settings.MONGODB_MAX_POOL_SIZE,
            minPoolSize=settings.MONGODB_MIN_POOL_SIZE,
            retryReads=settings.MONGODB_RETRY_READS,
            retryWrites=settings.MONGODB_RETRY_WRITES,
        )
        self.database: Database = self.client[database_name]

    @property
    def configured(self) -> bool:
        return bool(self.uri)

    def ping(self) -> bool:
        try:
            self.client.admin.command("ping")
            return True
        except PyMongoError as exc:
            log.warning("mongodb.ping_failed", error=str(exc))
            return False

    def ensure_indexes(self) -> bool:
        """Create only workload-driven, idempotent indexes."""
        try:
            conversations = self.database["conversations"]
            conversations.create_index(
                [("tenant_id", ASCENDING), ("user_id", ASCENDING), ("updated_at", DESCENDING)],
                name="tenant_user_updated_at",
            )
            conversations.create_index(
                [("conversation_id", ASCENDING)],
                name="conversation_id_unique",
                unique=True,
            )
            conversations.create_index([("tenant_id", ASCENDING)], name="tenant_id")

            messages = self.database["conversation_messages"]
            messages.create_index(
                [("tenant_id", ASCENDING), ("user_id", ASCENDING), ("conversation_id", ASCENDING), ("created_at", ASCENDING)],
                name="conversation_messages_scope",
            )
            messages.create_index(
                [("conversation_id", ASCENDING), ("message_id", ASCENDING)],
                name="conversation_message_unique",
                unique=True,
            )

            runs = self.database["agent_runs"]
            runs.create_index([("run_id", ASCENDING)], name="run_id_unique", unique=True)
            runs.create_index(
                [("tenant_id", ASCENDING), ("conversation_id", ASCENDING), ("created_at", ASCENDING)],
                name="tenant_conversation_created_at",
            )
            runs.create_index(
                [("tenant_id", ASCENDING), ("created_at", ASCENDING)],
                name="tenant_created_at",
            )
            runs.create_index(
                [("tenant_id", ASCENDING), ("user_id", ASCENDING), ("created_at", ASCENDING)],
                name="tenant_user_created_at",
            )
            runs.create_index([("tenant_id", ASCENDING), ("status", ASCENDING)], name="tenant_status")
            return True
        except PyMongoError as exc:
            log.warning("mongodb.index_creation_failed", error=str(exc))
            return False

    def collection(self, name: str) -> Collection:
        return self.database[name]

    def close(self) -> None:
        self.client.close()


@lru_cache(maxsize=1)
def get_mongodb() -> MongoDB | None:
    if not settings.MONGODB_URL:
        return None
    try:
        return MongoDB(settings.MONGODB_URL, settings.MONGODB_DATABASE)
    except PyMongoError as exc:
        log.warning("mongodb.initialization_failed", error=str(exc))
        return None


def init_mongodb() -> bool:
    mongo = get_mongodb()
    if mongo is None:
        return False
    return mongo.ensure_indexes()


def mongodb_available() -> bool:
    mongo = get_mongodb()
    return bool(mongo and mongo.ping())


def close_mongodb() -> None:
    mongo = get_mongodb()
    if mongo is not None:
        mongo.close()
    get_mongodb.cache_clear()
