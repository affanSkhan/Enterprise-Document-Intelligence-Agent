import hashlib
import json
import uuid
from pathlib import Path

from fastapi import UploadFile
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Document, DocumentVersion, Job
from app.parsers.factory import get_parser
from app.vectorstore.client import get_chroma_client, get_vectorstore

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sidecar(doc_id: str, suffix: str) -> Path:
    return settings.storage_path() / f"{doc_id}.{suffix}"


def _document_path(document: Document) -> Path:
    """Resolve a document path across host and worker processes.

    Older rows stored a relative host path such as ``uploads\\<id>.docx``.
    The API and Celery worker can have different working directories, so the
    durable database value must not be treated as an absolute filesystem
    location. Prefer the stored path when it exists; otherwise resolve the
    filename inside the configured shared storage directory.
    """
    stored = Path(document.file_path)
    if stored.exists():
        return stored
    return settings.storage_path() / stored.name


def _existing_job(db: Session, tenant_id: str, checksum: str) -> Job | None:
    return db.query(Job).filter(
        Job.tenant_id == tenant_id,
        Job.type == "document_ingestion",
        Job.idempotency_key == checksum,
    ).first()


def stage_upload(file: UploadFile, db: Session, tenant_id: str) -> tuple[Document, Job, bool]:
    filename = Path(file.filename or "upload.bin").name
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported document type: {ext}")

    storage = settings.storage_path()
    temp_id = str(uuid.uuid4())
    path = storage / f"{temp_id}{ext}"
    with path.open("wb") as buffer:
        while chunk := file.file.read(1024 * 1024):
            buffer.write(chunk)

    if path.stat().st_size > settings.MAX_UPLOAD_MB * 1024 * 1024:
        path.unlink(missing_ok=True)
        raise ValueError(f"File exceeds {settings.MAX_UPLOAD_MB} MB limit")

    checksum = sha256_file(path)
    existing = db.query(Document).filter(Document.tenant_id == tenant_id, Document.checksum == checksum).first()
    if existing:
        path.unlink(missing_ok=True)
        existing_job = _existing_job(db, tenant_id, checksum)
        if existing_job:
            return existing, existing_job, True
        checkpoint = "indexed" if existing.status == "INDEXED" else "uploaded"
        status = "succeeded" if checkpoint == "indexed" else "queued"
        job = Job(
            tenant_id=tenant_id,
            type="document_ingestion",
            status=status,
            idempotency_key=checksum,
            checkpoint=checkpoint,
            payload=json.dumps({"document_id": existing.id}),
            max_attempts=5,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return existing, job, True

    document = Document(
        id=temp_id,
        tenant_id=tenant_id,
        filename=filename,
        file_type=file.content_type or ext,
        # Store a portable storage key, not a host-specific relative path.
        # The worker resolves this key through settings.storage_path().
        file_path=path.name,
        checksum=checksum,
        status="QUEUED",
    )
    db.add(document)
    db.flush()
    job = Job(
        tenant_id=tenant_id,
        type="document_ingestion",
        status="queued",
        idempotency_key=checksum,
        checkpoint="uploaded",
        payload=json.dumps({"document_id": document.id}),
        max_attempts=5,
    )
    db.add(job)
    db.commit()
    db.refresh(document)
    db.refresh(job)
    return document, job, False


def _save_checkpoint(db: Session, job: Job, document: Document, checkpoint: str) -> None:
    job.checkpoint = checkpoint
    document.status = checkpoint.upper()
    db.commit()


def _parse(document: Document) -> str:
    parsed_path = _sidecar(document.id, "parsed.txt")
    if parsed_path.exists():
        return parsed_path.read_text(encoding="utf-8")
    document_path = _document_path(document)
    if not document_path.exists():
        raise FileNotFoundError(f"Document file not found in shared storage: {document_path}")
    parser = get_parser(str(document_path))
    text = parser.parse(str(document_path)) or ""
    parsed_path.write_text(text, encoding="utf-8")
    return text


def _chunk(document: Document, text: str) -> list[str]:
    chunks_path = _sidecar(document.id, "chunks.json")
    if chunks_path.exists():
        return json.loads(chunks_path.read_text(encoding="utf-8"))
    chunks = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
    ).split_text(text)
    chunks_path.write_text(json.dumps(chunks, ensure_ascii=False), encoding="utf-8")
    return chunks


def _index(document: Document, chunks: list[str]) -> None:
    if not chunks:
        return
    vectorstore = get_vectorstore()
    collection = get_chroma_client().get_collection("documents")
    ids = [f"{document.id}:v{document.current_version}:c{i}" for i in range(len(chunks))]
    existing = set(collection.get(ids=ids, include=[]).get("ids", []))
    missing = [(i, chunk, ids[i]) for i, chunk in enumerate(chunks) if ids[i] not in existing]
    if not missing:
        return
    vectorstore.add_texts(
        texts=[chunk for _, chunk, _ in missing],
        ids=[chunk_id for _, _, chunk_id in missing],
        metadatas=[
            {
                "chunk_id": chunk_id,
                "doc_id": document.id,
                "tenant_id": document.tenant_id,
                "filename": document.filename,
                "version": document.current_version,
                "chunk_idx": i,
            }
            for i, _, chunk_id in missing
        ],
    )


def process_document_job(job_id: str) -> None:
    from app.db.session import SessionLocal

    db = SessionLocal()
    job = None
    try:
        job = db.get(Job, job_id)
        if not job:
            return
        document_id = json.loads(job.payload)["document_id"]
        document = db.get(Document, document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")

        job.status = "running"
        job.attempts += 1
        job.error = None
        db.commit()

        if job.checkpoint == "uploaded":
            text = _parse(document)
            parser = get_parser(str(_document_path(document)))
            if not db.query(DocumentVersion).filter_by(document_id=document.id, version=1).first():
                db.add(DocumentVersion(document_id=document.id, version=1, parser=parser.__class__.__name__))
                db.commit()
            _save_checkpoint(db, job, document, "parsed")
        else:
            text = _parse(document)

        if job.checkpoint in {"uploaded", "parsed"}:
            chunks = _chunk(document, text)
            _save_checkpoint(db, job, document, "chunked")
        else:
            chunks = json.loads(_sidecar(document.id, "chunks.json").read_text(encoding="utf-8"))

        if job.checkpoint != "indexed":
            _index(document, chunks)
            _save_checkpoint(db, job, document, "indexed")

        job.status = "succeeded"
        document.status = "INDEXED"
        document.error_message = None
        db.commit()
    except Exception as exc:
        if job:
            job.status = "queued" if job.attempts < job.max_attempts else "dead"
            job.error = str(exc)[:4000]
            document_id = json.loads(job.payload).get("document_id")
            document = db.get(Document, document_id) if document_id else None
            if document:
                document.status = "RETRYING" if job.attempts < job.max_attempts else "ERROR"
                document.error_message = job.error
            db.commit()
        raise
    finally:
        db.close()


def process_upload(file: UploadFile, db: Session, tenant_id: str) -> Document:
    """Compatibility wrapper for callers that still expect synchronous ingestion."""
    document, job, _ = stage_upload(file, db, tenant_id)
    if job.status != "succeeded":
        process_document_job(job.id)
    db.refresh(document)
    return document
