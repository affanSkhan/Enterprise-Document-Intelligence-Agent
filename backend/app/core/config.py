from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    PROJECT_NAME: str = "Enterprise Intelligence Runtime"
    API_V1_PREFIX: str = "/api"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    ENABLE_AUTH: bool = False
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    GEMINI_API_KEY: str = ""
    PRIMARY_LLM_MODEL: str = "gemini-2.5-flash"
    FAST_LLM_MODEL: str = "gemini-2.5-flash-lite"

    DATABASE_URL: str = "sqlite:///./enterprise_intelligence.db"
    POSTGRES_URL: str = "postgresql+psycopg://enterprise:enterprise@postgres:5432/enterprise"
    REDIS_URL: str = "redis://redis:6379/0"
    CHROMA_DB_DIR: str = "./chroma_db"
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_MB: int = 50
    JOB_TTL_SECONDS: int = 86400

    MONGODB_URL: str = ""
    MONGODB_DATABASE: str = "enterprise_intelligence"
    MONGODB_APP_NAME: str = "enterprise-intelligence-runtime"
    MONGODB_CONNECT_TIMEOUT_MS: int = 3000
    MONGODB_SERVER_SELECTION_TIMEOUT_MS: int = 3000
    MONGODB_SOCKET_TIMEOUT_MS: int = 5000
    MONGODB_MAX_POOL_SIZE: int = 20
    MONGODB_MIN_POOL_SIZE: int = 0
    MONGODB_RETRY_READS: bool = True
    MONGODB_RETRY_WRITES: bool = True

    EMBEDDING_MODEL: str = "models/gemini-embedding-2"
    RERANKER_MODEL: str = "BAAI/bge-reranker-base"
    RETRIEVAL_TOP_K: int = 12
    RERANK_TOP_K: int = 6
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 120

    CORS_ORIGINS: str = "http://localhost:3000"
    OTEL_SERVICE_NAME: str = "enterprise-intelligence-runtime"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""

    def storage_path(self) -> Path:
        path = Path(self.UPLOAD_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
