from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.agents.retrieval import chat_with_docs
from app.agents.specialized import compare_documents, extract_bom, generate_presentation, generate_report
from app.core.security import detect_prompt_injection
from app.db.models import Document, DocumentPermission, User
from app.db.session import get_db
from app.security.dependencies import CurrentUser, get_current_user, get_tenant_id, require_role
from app.services.ingestion import process_upload
from app.services.search import search_documents

router = APIRouter()


class SearchQuery(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=5, ge=1, le=50)
    mode: str = Field(default="hybrid", pattern="^(dense|sparse|hybrid)$")
    rerank: bool = False


class ChatQuery(BaseModel):
    query: str = Field(min_length=1, max_length=8000)
    top_k: int = Field(default=6, ge=1, le=30)


class ACLRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=36)
    permission: str = Field(default="read", pattern="^read$")


class AgentTopic(BaseModel):
    topic: str = Field(min_length=1, max_length=4000)


class AgentBOM(BaseModel):
    doc_id: str = Field(min_length=1, max_length=200)


class AgentCompare(BaseModel):
    doc_id_1: str = Field(min_length=1, max_length=200)
    doc_id_2: str = Field(min_length=1, max_length=200)
    query: str = Field(min_length=1, max_length=4000)


@router.get("/health")
async def health():
    return {"status": "ok", "service": "enterprise-intelligence-runtime"}


@router.get("/ready")
async def ready(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ready"}


@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...), tenant_id: str = Depends(get_tenant_id),
    _: str = Depends(require_role("admin", "manager")), db: Session = Depends(get_db),
):
    try:
        return process_upload(file, db, tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/documents")
async def documents(tenant_id: str = Depends(get_tenant_id), current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Document).filter(Document.tenant_id == tenant_id)
    if current.role not in {"admin", "manager"}:
        query = query.join(DocumentPermission).filter(DocumentPermission.user_id == current.id, DocumentPermission.permission == "read")
    return query.order_by(Document.created_at.desc()).all()


@router.post("/documents/{doc_id}/permissions")
async def grant_document_permission(
    doc_id: str, request: ACLRequest, tenant_id: str = Depends(get_tenant_id),
    _: str = Depends(require_role("admin", "manager")), db: Session = Depends(get_db),
):
    document = db.query(Document).filter(Document.id == doc_id, Document.tenant_id == tenant_id).first()
    user = db.query(User).filter(User.id == request.user_id, User.tenant_id == tenant_id, User.is_active.is_(True)).first()
    if not document or not user:
        raise HTTPException(status_code=404, detail="Document or user not found in tenant")
    permission = db.query(DocumentPermission).filter(DocumentPermission.document_id == doc_id, DocumentPermission.user_id == user.id).first()
    if permission:
        permission.permission = request.permission
    else:
        db.add(DocumentPermission(document_id=doc_id, user_id=user.id, permission=request.permission))
    db.commit()
    return {"document_id": doc_id, "user_id": user.id, "permission": request.permission}


@router.delete("/documents/{doc_id}/permissions/{user_id}")
async def revoke_document_permission(
    doc_id: str, user_id: str, tenant_id: str = Depends(get_tenant_id),
    _: str = Depends(require_role("admin", "manager")), db: Session = Depends(get_db),
):
    permission = db.query(DocumentPermission).join(Document).filter(
        DocumentPermission.document_id == doc_id,
        DocumentPermission.user_id == user_id,
        Document.tenant_id == tenant_id,
    ).first()
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")
    db.delete(permission)
    db.commit()
    return {"revoked": True, "document_id": doc_id, "user_id": user_id}


@router.post("/search")
async def search(request: SearchQuery, tenant_id: str = Depends(get_tenant_id), current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"results": search_documents(request.query, request.top_k, tenant_id=tenant_id, mode=request.mode, rerank=request.rerank, db=db, user_id=current.id, role=current.role)}


@router.post("/chat")
async def chat(request: ChatQuery, tenant_id: str = Depends(get_tenant_id), current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return chat_with_docs(request.query, request.top_k, tenant_id=tenant_id, db=db, user_id=current.id, role=current.role)


@router.post("/security/scan")
async def security_scan(request: ChatQuery):
    findings = detect_prompt_injection(request.query)
    return {"safe": not findings, "findings": findings}


@router.post("/agents/compare")
async def compare_agent(request: AgentCompare, tenant_id: str = Depends(get_tenant_id)):
    return {"result": compare_documents(request.doc_id_1, request.doc_id_2, request.query, tenant_id=tenant_id)}


@router.post("/agents/report")
async def report_agent(request: AgentTopic, tenant_id: str = Depends(get_tenant_id)):
    return {"result": generate_report(request.topic, tenant_id=tenant_id)}


@router.post("/agents/bom")
async def bom_agent(request: AgentBOM, tenant_id: str = Depends(get_tenant_id)):
    return {"result": extract_bom(request.doc_id, tenant_id=tenant_id)}


@router.post("/agents/presentation")
async def presentation_agent(request: AgentTopic, tenant_id: str = Depends(get_tenant_id)):
    return {"result": generate_presentation(request.topic, tenant_id=tenant_id)}
