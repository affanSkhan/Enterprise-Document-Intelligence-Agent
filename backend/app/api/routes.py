from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Document, Base
from app.db.session import engine
from app.services.ingestion import process_upload
from app.services.search import search_documents
from app.agents.retrieval import chat_with_docs
from app.agents.specialized import compare_documents, generate_report, extract_bom, generate_presentation
from typing import List
from pydantic import BaseModel
from datetime import datetime

# Initialize DB tables
Base.metadata.create_all(bind=engine)

router = APIRouter()

class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    upload_date: datetime
    status: str
    error_message: str | None = None

    class Config:
        from_attributes = True

@router.get("/health")
async def health_check():
    return {"status": "ok"}

@router.post("/documents/upload", response_model=DocumentResponse)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    doc = process_upload(file, db)
    return doc

@router.get("/documents", response_model=List[DocumentResponse])
async def get_documents(db: Session = Depends(get_db)):
    docs = db.query(Document).order_by(Document.upload_date.desc()).all()
    return docs

class SearchQuery(BaseModel):
    query: str
    top_k: int = 5

class ChatQuery(BaseModel):
    query: str

@router.post("/search")
async def search_endpoint(request: SearchQuery):
    results = search_documents(request.query, request.top_k)
    return {"results": results}

@router.post("/chat")
async def chat_endpoint(request: ChatQuery):
    response = chat_with_docs(request.query)
    return response

class CompareQuery(BaseModel):
    doc_id_1: str
    doc_id_2: str
    query: str

class TopicQuery(BaseModel):
    topic: str

class DocQuery(BaseModel):
    doc_id: str

@router.post("/agents/compare")
async def compare_endpoint(request: CompareQuery):
    result = compare_documents(request.doc_id_1, request.doc_id_2, request.query)
    return {"result": result}

@router.post("/agents/report")
async def report_endpoint(request: TopicQuery):
    result = generate_report(request.topic)
    return {"result": result}

@router.post("/agents/bom")
async def bom_endpoint(request: DocQuery):
    result = extract_bom(request.doc_id)
    return {"result": result}

@router.post("/agents/presentation")
async def presentation_endpoint(request: TopicQuery):
    result = generate_presentation(request.topic)
    return {"result": result}

