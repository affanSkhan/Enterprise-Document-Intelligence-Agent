from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.core.config import settings
import chromadb
from chromadb.config import Settings as ChromaSettings

# We use Gemini's text embedding model
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2", google_api_key=settings.GEMINI_API_KEY)

# Direct ChromaDB client
chroma_client = chromadb.PersistentClient(
    path=settings.CHROMA_DB_DIR,
    settings=ChromaSettings(anonymized_telemetry=False)
)

def get_vectorstore(collection_name: str = "documents") -> Chroma:
    return Chroma(
        client=chroma_client,
        collection_name=collection_name,
        embedding_function=embeddings
    )
