from io import BytesIO
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, Tenant
from app.services.ingestion import stage_upload


def _upload(name: str, content: bytes) -> UploadFile:
    return UploadFile(filename=name, file=BytesIO(content), headers=None)


def test_upload_is_idempotent(monkeypatch, tmp_path: Path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add(Tenant(id="tenant-1", name="Tenant 1"))
    db.commit()
    monkeypatch.setattr("app.services.ingestion.settings.UPLOAD_DIR", str(tmp_path))

    first_doc, first_job, duplicate = stage_upload(_upload("a.pdf", b"same-bytes"), db, "tenant-1")
    second_doc, second_job, duplicate_again = stage_upload(_upload("renamed.pdf", b"same-bytes"), db, "tenant-1")

    assert duplicate is False
    assert duplicate_again is True
    assert first_doc.id == second_doc.id
    assert first_job.id == second_job.id
    assert first_job.idempotency_key == first_doc.checksum

    db.close()


def test_job_starts_from_uploaded_checkpoint(monkeypatch, tmp_path: Path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add(Tenant(id="tenant-2", name="Tenant 2"))
    db.commit()
    monkeypatch.setattr("app.services.ingestion.settings.UPLOAD_DIR", str(tmp_path))

    document, job, _ = stage_upload(_upload("b.docx", b"document"), db, "tenant-2")

    assert document.status == "QUEUED"
    assert job.status == "queued"
    assert job.checkpoint == "uploaded"
    assert job.attempts == 0
    db.close()
