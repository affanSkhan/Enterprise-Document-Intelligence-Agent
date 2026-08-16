import hashlib
import uuid
from pathlib import Path
from fastapi import UploadFile
from sqlalchemy.orm import Session
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.config import settings
from app.db.models import Document, DocumentVersion
from app.parsers.factory import get_parser
from app.vectorstore.client import get_vectorstore

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def process_upload(file: UploadFile, db: Session, tenant_id: str) -> Document:
    filename = Path(file.filename or "upload.bin").name
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported document type: {ext}")

    settings.storage_path()
    doc_id = str(uuid.uuid4())
    path = Path(settings.UPLOAD_DIR) / f"{doc_id}{ext}"
    with path.open("wb") as buffer:
        while chunk := file.file.read(1024 * 1024):
            buffer.write(chunk)

    if path.stat().st_size > settings.MAX_UPLOAD_MB * 1024 * 1024:
        path.unlink(missing_ok=True)
        raise ValueError(f"File exceeds {settings.MAX_UPLOAD_MB} MB limit")

    checksum = sha256_file(path)
    document = Document(id=doc_id, tenant_id=tenant_id, filename=filename,
                        file_type=file.content_type or ext, file_path=str(path),
                        checksum=checksum, status="UPLOADED")
    db.add(document)
    db.flush()

    try:
        parser = get_parser(str(path))
        text = parser.parse(str(path))
        document.status = "PARSED"
        db.add(DocumentVersion(document_id=doc_id, version=1,
                                parser=parser.__class__.__name__))

        chunks = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        ).split_text(text or "")
        if chunks:
            vectorstore = get_vectorstore()
            vectorstore.add_texts(
                texts=chunks,
                metadatas=[{"doc_id": doc_id, "tenant_id": tenant_id,
                             "filename": filename, "version": 1, "chunk_idx": i}
                           for i in range(len(chunks))],
            )
        document.status = "INDEXED"
        db.commit()
        db.refresh(document)
        return document
    except Exception as exc:
        db.rollback()
        document.status = "ERROR"
        document.error_message = str(exc)[:4000]
        db.add(document)
        db.commit()
        db.refresh(document)
        return document
