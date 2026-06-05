from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, index=True) # UUID string
    filename = Column(String, index=True)
    file_type = Column(String)
    file_path = Column(String)
    upload_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="UPLOADED") # UPLOADED, PARSED, INDEXED, ERROR
    error_message = Column(Text, nullable=True)
