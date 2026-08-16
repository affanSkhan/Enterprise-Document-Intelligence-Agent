from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.models import Document
from app.db.session import get_db
from app.security.acl import can_read_document
from app.security.dependencies import CurrentUser, get_current_user, get_tenant_id, require_role
from app.services.document_diff import semantic_diff
from app.services.multimodal import artifact_path, build_artifact, load_artifact
from app.services.versioning import upload_new_version, version_artifact_path

router = APIRouter(prefix="/multimodal", tags=["multimodal"])


@router.post("/documents/{doc_id}/build")
async def build_multimodal_artifact(
    doc_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = db.query(Document).filter(Document.id == doc_id, Document.tenant_id == tenant_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if not can_read_document(db, document_id=doc_id, tenant_id=tenant_id, user_id=current.id, role=current.role):
        raise HTTPException(status_code=403, detail="Document access denied")
    artifact = build_artifact(document.id, document.file_path)
    return {"document_id": doc_id, "version": document.current_version, "artifact": artifact}


@router.post("/documents/{doc_id}/versions", status_code=201)
async def create_document_version(
    doc_id: str,
    file: UploadFile = File(...),
    tenant_id: str = Depends(get_tenant_id),
    _: str = Depends(require_role("admin", "manager")),
    db: Session = Depends(get_db),
):
    document = db.query(Document).filter(Document.id == doc_id, Document.tenant_id == tenant_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        return upload_new_version(file, db, document=document)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/documents/{doc_id}/versions/{version}")
async def get_version_artifact(
    doc_id: str,
    version: int,
    tenant_id: str = Depends(get_tenant_id),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = db.query(Document).filter(Document.id == doc_id, Document.tenant_id == tenant_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if not can_read_document(db, document_id=doc_id, tenant_id=tenant_id, user_id=current.id, role=current.role):
        raise HTTPException(status_code=403, detail="Document access denied")
    if version < 1 or version > document.current_version:
        raise HTTPException(status_code=404, detail="Version not found")
    artifact = load_artifact(f"{doc_id}.v{version}")
    if not artifact:
        raise HTTPException(status_code=404, detail="Multimodal artifact not built for this version")
    return {"document_id": doc_id, "version": version, "artifact": artifact}


@router.get("/documents/{doc_id}/diff")
async def diff_document_versions(
    doc_id: str,
    from_version: int,
    to_version: int,
    tenant_id: str = Depends(get_tenant_id),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = db.query(Document).filter(Document.id == doc_id, Document.tenant_id == tenant_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if not can_read_document(db, document_id=doc_id, tenant_id=tenant_id, user_id=current.id, role=current.role):
        raise HTTPException(status_code=403, detail="Document access denied")
    if from_version < 1 or to_version < 1 or from_version > document.current_version or to_version > document.current_version:
        raise HTTPException(status_code=404, detail="Version not found")
    old_artifact = load_artifact(f"{doc_id}.v{from_version}")
    new_artifact = load_artifact(f"{doc_id}.v{to_version}")
    if not old_artifact or not new_artifact:
        raise HTTPException(status_code=404, detail="Build multimodal artifacts for both versions first")
    return {"document_id": doc_id, "from_version": from_version, "to_version": to_version, "diff": semantic_diff(old_artifact, new_artifact)}
