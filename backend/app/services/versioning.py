import hashlib
import json
import shutil
import uuid
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Document, DocumentVersion
from app.services.multimodal import build_artifact, artifact_path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def version_artifact_path(document_id: str, version: int) -> Path:
    return Path(settings.UPLOAD_DIR) / f"{document_id}.v{version}.layout.json"


def upload_new_version(file: UploadFile, db: Session, *, document: Document) -> dict[str, Any]:
    filename = Path(file.filename or "version.bin").name
    suffix = Path(filename).suffix.lower()
    if suffix not in {".pdf", ".docx", ".pptx", ".xlsx"}:
        raise ValueError(f"Unsupported document type: {suffix}")
    settings.storage_path()
    path = Path(settings.UPLOAD_DIR) / f"{uuid.uuid4()}{suffix}"
    with path.open("wb") as output:
        while chunk := file.file.read(1024 * 1024):
            output.write(chunk)
    if path.stat().st_size > settings.MAX_UPLOAD_MB * 1024 * 1024:
        path.unlink(missing_ok=True)
        raise ValueError(f"File exceeds {settings.MAX_UPLOAD_MB} MB limit")

    checksum = _sha256(path)
    if checksum == document.checksum:
        path.unlink(missing_ok=True)
        raise ValueError("New version is byte-identical to the current document")

    version = document.current_version + 1
    artifact = build_artifact(f"{document.id}.v{version}", str(path), persist=False)
    version_path = version_artifact_path(document.id, version)
    version_path.write_text(json.dumps(artifact, ensure_ascii=False), encoding="utf-8")

    db.add(DocumentVersion(document_id=document.id, version=version, parser=Path(path).suffix[1:], page_count=artifact.get("page_count")))
    document.current_version = version
    document.filename = filename
    document.file_type = file.content_type or suffix
    document.file_path = str(path)
    document.checksum = checksum
    db.commit()

    # Preserve the current-version artifact under the generic name for consumers that don't specify a version.
    artifact_path(document.id).write_text(json.dumps(artifact, ensure_ascii=False), encoding="utf-8")
    return {"document_id": document.id, "version": version, "filename": filename, "checksum": checksum, "page_count": artifact.get("page_count"), "artifact": str(version_path)}
