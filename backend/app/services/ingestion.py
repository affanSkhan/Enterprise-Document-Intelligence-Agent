import os
import uuid
from langchain_text_splitters import RecursiveCharacterTextSplitter
from fastapi import UploadFile
from sqlalchemy.orm import Session
from app.db.models import Document
from app.parsers.factory import get_parser
from app.vectorstore.client import get_vectorstore
from app.core.config import settings
from datetime import datetime

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

def process_upload(file: UploadFile, db: Session):
    doc_id = str(uuid.uuid4())
    file_path = os.path.join(settings.UPLOAD_DIR, f"{doc_id}_{file.filename}")
    
    # Save file
    file.file.seek(0)
    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())
        
    db_doc = Document(
        id=doc_id,
        filename=file.filename,
        file_type=file.content_type or os.path.splitext(file.filename)[1],
        file_path=file_path,
        status="UPLOADED"
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    
    try:
        parser = get_parser(file_path)
        text = parser.parse(file_path)
        
        db_doc.status = "PARSED"
        db.commit()
        
        # Chunking
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        chunks = text_splitter.split_text(text)
        
        # Storing in ChromaDB
        if chunks:
            vectorstore = get_vectorstore()
            metadatas = [{"doc_id": doc_id, "filename": file.filename, "chunk_idx": i} for i in range(len(chunks))]
            vectorstore.add_texts(texts=chunks, metadatas=metadatas)
        
        db_doc.status = "INDEXED"
        db.commit()
        
    except Exception as e:
        db_doc.status = "ERROR"
        db_doc.error_message = str(e)
        db.commit()
    
    return db_doc
