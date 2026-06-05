import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise Document Intelligence Agent"
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    CHROMA_DB_DIR: str = "./chroma_db"
    SQLITE_DB_URL: str = "sqlite:///./enterprise_doc.db"
    UPLOAD_DIR: str = "./uploads"

    class Config:
        env_file = ".env"

settings = Settings()
