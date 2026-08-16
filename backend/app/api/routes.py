from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.db.models import Document
from app.db.session import get_db
from app.security.dependencies import get_tenant_id, require_role
from app.services.ingestion import process_upload
from app.services.search import search_documents
from app.agents.retrieval import chat_with_docs
from app.core.security import detect_prompt_injection

router = APIRouter()


class SearchQuery(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=5, ge=1, le=50)


class ChatQuery(BaseModel):
    query: str = Field(min_length=1, max_length=8000)
    top_k: int = Field(default=6, ge=1, le=30)


@router.get("/health")
async def health():
    return {"status": "ok", "service": "enterprise-intelligence-runtime"}


@router.get("/ready")
async def ready(db: Session = Depends(get_db)):
    db.execute(__import__('sqlalchemy').text("SELECT 1"))
    return {"status": "ready"}


@router.post("/documents/upload")
async def upload_document(file: UploadFile = File(...), tenant_id: str = Depends(get_tenant_id),
                          _: str = Depends(require_role("admin", "manager")), db: Session = Depends(get_db)):
    try:
        return process_upload(file, db, tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/documents")
async def documents(tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db)):
    return db.query(Document).filter(Document.tenant_id == tenant_id).order_by(Document.created_at.desc()).all()


@router.post("/search")
async def search(request: SearchQuery, tenant_id: str = Depends(get_tenant_id)):
    return {"results": search_documents(request.query, request.top_k, tenant_id=tenant_id)}


@router.post("/chat")
async def chat(request: ChatQuery, tenant_id: str = Depends(get_tenant_id)):
    return chat_with_docs(request.query, request.top_k)


@router.post("/security/scan")
async def security_scan(request: ChatQuery):
    findings = detect_prompt_injection(request.query)
    return {"safe": not findings, "findings": findings}
