from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import os

# Ensure db directory exists
os.makedirs(os.path.dirname(settings.SQLITE_DB_URL.replace("sqlite:///", "")), exist_ok=True)

engine = create_engine(
    settings.SQLITE_DB_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
