from functools import lru_cache

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.core.config import settings


@lru_cache(maxsize=1)
def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    """Create the Gemini embedding client only when vector access is requested."""
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is required for vector operations")
    return GoogleGenerativeAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        google_api_key=settings.GEMINI_API_KEY,
    )


@lru_cache(maxsize=1)
def get_chroma_client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(
        path=settings.CHROMA_DB_DIR,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def get_vectorstore(collection_name: str | None = None) -> Chroma:
    collection_name = collection_name or settings.VECTOR_COLLECTION_NAME
    return Chroma(
        client=get_chroma_client(),
        collection_name=collection_name,
        embedding_function=get_embeddings(),
    )
