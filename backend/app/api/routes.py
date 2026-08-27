from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.agents.retrieval import chat_with_docs
from app.agents.specialized import compare_documents, extract_bom, generate_presentation, generate_report
from app.core.config import settings
from app.core.security import detect_prompt_injection
from app.db.models import Document, DocumentPermission, Job, User
from app.db.session import get_db
from app.security.acl import allowed_document_ids, can_read_document
from app.security.dependencies import CurrentUser, get_current_user, get_tenant_id, require_role
from app.services.evidence_graph import build_document_graph, detect_contradictions, graph_snapshot, verify_claims
from app.services.ingestion import stage_upload
from app.services.jobs import enqueue_ingestion, job_payload
from app.services.search import search_documents
from app.vectorstore.client import get_chroma_client

router = APIRouter()
class SearchQuery(BaseModel):
    query: str = Field(min_length=1, max_length=4000); top_k: int = Field(default=5, ge=1, le=50); mode: str = Field(default="hybrid", pattern="^(dense|sparse|hybrid)$"); rerank: bool = False
class ChatQuery(BaseModel): query: str = Field(min_length=1, max_length=8000); top_k: int = Field(default=6, ge=1, le=30)
class ACLRequest(BaseModel): user_id: str = Field(min_length=1, max_length=36); permission: str = Field(default="read", pattern="^read$")
class AgentTopic(BaseModel): topic: str = Field(min_length=1, max_length=4000)
class AgentBOM(BaseModel): doc_id: str = Field(min_length=1, max_length=200)
class AgentCompare(BaseModel):
    doc_id_1: str = Field(min_length=1, max_length=200); doc_id_2: str = Field(min_length=1, max_length=200); query: str = Field(min_length=1, max_length=4000)
class ClaimVerification(BaseModel): claims: list[str] = Field(min_length=1, max_length=50)

@router.get("/health")
async def health(): return {"status":"ok","service":"enterprise-intelligence-runtime"}
@router.get("/ready")
async def ready(db: Session = Depends(get_db)): db.execute(text("SELECT 1")); return {"status":"ready"}
@router.post("/documents/upload", status_code=202)
async def upload_document(file: UploadFile = File(...), tenant_id: str = Depends(get_tenant_id), _: str = Depends(require_role("admin","manager")), db: Session = Depends(get_db)):
    try:
        document, job, duplicate = stage_upload(file, db, tenant_id)
        if not duplicate and job.status == "queued":
            try: celery_id = enqueue_ingestion(job)
            except Exception as exc: return {"document_id":document.id,"job_id":job.id,"status":job.status,"checkpoint":job.checkpoint,"queued":False,"error":f"Worker unavailable; job remains durable and can be retried: {exc}"}
            return {"document_id":document.id,"job_id":job.id,"celery_task_id":celery_id,"status":job.status,"checkpoint":job.checkpoint,"queued":True}
        return {"document_id":document.id,"job_id":job.id,"status":job.status,"checkpoint":job.checkpoint,"queued":job.status=="queued","duplicate":duplicate}
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc
@router.get("/jobs/{job_id}")
async def get_job(job_id: str, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db)):
    job=db.query(Job).filter(Job.id==job_id,Job.tenant_id==tenant_id).first()
    if not job: raise HTTPException(status_code=404,detail="Job not found")
    payload=job_payload(job); return {"job_id":job.id,"document_id":payload.get("document_id"),"type":job.type,"status":job.status,"checkpoint":job.checkpoint,"attempts":job.attempts,"max_attempts":job.max_attempts,"error":job.error,"created_at":job.created_at,"updated_at":job.updated_at}
@router.post("/jobs/{job_id}/retry")
async def retry_job(job_id: str, tenant_id: str = Depends(get_tenant_id), _: str = Depends(require_role("admin","manager")), db: Session = Depends(get_db)):
    job=db.query(Job).filter(Job.id==job_id,Job.tenant_id==tenant_id).first()
    if not job: raise HTTPException(status_code=404,detail="Job not found")
    if job.status not in {"dead","queued"}: raise HTTPException(status_code=409,detail=f"Job is currently {job.status}")
    job.status="queued"; job.error=None; job.attempts=0; db.commit()
    try: task_id=enqueue_ingestion(job)
    except Exception as exc: raise HTTPException(status_code=503,detail=f"Worker unavailable: {exc}") from exc
    return {"job_id":job.id,"queued":True,"celery_task_id":task_id,"checkpoint":job.checkpoint}
@router.get("/documents")
async def documents(tenant_id: str = Depends(get_tenant_id), current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    query=db.query(Document).filter(Document.tenant_id==tenant_id)
    if current.role not in {"admin","manager"}: query=query.join(DocumentPermission).filter(DocumentPermission.user_id==current.id,DocumentPermission.permission=="read")
    return query.order_by(Document.created_at.desc()).all()
@router.post("/documents/{doc_id}/permissions")
async def grant_document_permission(doc_id: str, request: ACLRequest, tenant_id: str = Depends(get_tenant_id), _: str = Depends(require_role("admin","manager")), db: Session = Depends(get_db)):
    document=db.query(Document).filter(Document.id==doc_id,Document.tenant_id==tenant_id).first(); user=db.query(User).filter(User.id==request.user_id,User.tenant_id==tenant_id,User.is_active.is_(True)).first()
    if not document or not user: raise HTTPException(status_code=404,detail="Document or user not found in tenant")
    permission=db.query(DocumentPermission).filter(DocumentPermission.document_id==doc_id,DocumentPermission.user_id==user.id).first()
    if permission: permission.permission=request.permission
    else: db.add(DocumentPermission(document_id=doc_id,user_id=user.id,permission=request.permission))
    db.commit(); return {"document_id":doc_id,"user_id":user.id,"permission":request.permission}
@router.delete("/documents/{doc_id}/permissions/{user_id}")
async def revoke_document_permission(doc_id: str,user_id: str,tenant_id: str=Depends(get_tenant_id),_: str=Depends(require_role("admin","manager")),db:Session=Depends(get_db)):
    permission=db.query(DocumentPermission).join(Document).filter(DocumentPermission.document_id==doc_id,DocumentPermission.user_id==user_id,Document.tenant_id==tenant_id).first()
    if not permission: raise HTTPException(status_code=404,detail="Permission not found")
    db.delete(permission);db.commit();return {"revoked":True,"document_id":doc_id,"user_id":user_id}
@router.post("/search")
async def search(request: SearchQuery,tenant_id:str=Depends(get_tenant_id),current:CurrentUser=Depends(get_current_user),db:Session=Depends(get_db)): return {"results":search_documents(request.query,request.top_k,tenant_id=tenant_id,mode=request.mode,rerank=request.rerank,db=db,user_id=current.id,role=current.role)}
@router.post("/chat")
async def chat(request:ChatQuery,tenant_id:str=Depends(get_tenant_id),current:CurrentUser=Depends(get_current_user),db:Session=Depends(get_db)): return chat_with_docs(request.query,request.top_k,tenant_id=tenant_id,db=db,user_id=current.id,role=current.role)
@router.post("/security/scan")
async def security_scan(request:ChatQuery):
    findings=detect_prompt_injection(request.query);return {"safe":not findings,"findings":findings}
@router.post("/evidence/documents/{doc_id}/build")
async def build_evidence(doc_id:str,tenant_id:str=Depends(get_tenant_id),current:CurrentUser=Depends(get_current_user),db:Session=Depends(get_db)):
    if not can_read_document(db,document_id=doc_id,tenant_id=tenant_id,user_id=current.id,role=current.role): raise HTTPException(status_code=403,detail="Document access denied")
    collection=get_chroma_client().get_collection(settings.VECTOR_COLLECTION_NAME)
    payload=collection.get(where={"$and":[{"tenant_id":tenant_id},{"doc_id":doc_id}]},include=["documents","metadatas"])
    chunks=payload.get("documents") or []
    if not chunks: raise HTTPException(status_code=409,detail="Document has not been indexed yet")
    return build_document_graph(db,tenant_id=tenant_id,document_id=doc_id,text="\n".join(chunks))
@router.get("/evidence/graph")
async def evidence_graph(entity:str|None=None,tenant_id:str=Depends(get_tenant_id),_:CurrentUser=Depends(get_current_user),db:Session=Depends(get_db)): return graph_snapshot(db,tenant_id=tenant_id,entity=entity)
@router.post("/evidence/verify")
async def evidence_verify(request:ClaimVerification,tenant_id:str=Depends(get_tenant_id),_:CurrentUser=Depends(get_current_user),db:Session=Depends(get_db)): return {"verification":verify_claims(db,tenant_id=tenant_id,claims=request.claims)}
@router.get("/evidence/contradictions")
async def evidence_contradictions(tenant_id:str=Depends(get_tenant_id),_:CurrentUser=Depends(get_current_user),db:Session=Depends(get_db)): return {"contradictions":detect_contradictions(db,tenant_id=tenant_id)}
@router.post("/agents/compare")
async def compare_agent(request:AgentCompare,tenant_id:str=Depends(get_tenant_id),current:CurrentUser=Depends(get_current_user),db:Session=Depends(get_db)):
    if not can_read_document(db,document_id=request.doc_id_1,tenant_id=tenant_id,user_id=current.id,role=current.role) or not can_read_document(db,document_id=request.doc_id_2,tenant_id=tenant_id,user_id=current.id,role=current.role): raise HTTPException(status_code=403,detail="Document access denied")
    return {"result":compare_documents(request.doc_id_1,request.doc_id_2,request.query,tenant_id=tenant_id,allowed_ids=allowed_document_ids(db,tenant_id=tenant_id,user_id=current.id,role=current.role))}
@router.post("/agents/report")
async def report_agent(request:AgentTopic,tenant_id:str=Depends(get_tenant_id),current:CurrentUser=Depends(get_current_user),db:Session=Depends(get_db)): return {"result":generate_report(request.topic,tenant_id=tenant_id,allowed_ids=allowed_document_ids(db,tenant_id=tenant_id,user_id=current.id,role=current.role))}
@router.post("/agents/bom")
async def bom_agent(request:AgentBOM,tenant_id:str=Depends(get_tenant_id),current:CurrentUser=Depends(get_current_user),db:Session=Depends(get_db)):
    if not can_read_document(db,document_id=request.doc_id,tenant_id=tenant_id,user_id=current.id,role=current.role): raise HTTPException(status_code=403,detail="Document access denied")
    return {"result":extract_bom(request.doc_id,tenant_id=tenant_id,allowed_ids=allowed_document_ids(db,tenant_id=tenant_id,user_id=current.id,role=current.role))}
@router.post("/agents/presentation")
async def presentation_agent(request:AgentTopic,tenant_id:str=Depends(get_tenant_id),current:CurrentUser=Depends(get_current_user),db:Session=Depends(get_db)): return {"result":generate_presentation(request.topic,tenant_id=tenant_id,allowed_ids=allowed_document_ids(db,tenant_id=tenant_id,user_id=current.id,role=current.role))}
