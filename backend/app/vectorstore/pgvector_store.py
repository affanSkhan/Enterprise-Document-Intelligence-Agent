from __future__ import annotations

from typing import Any

from langchain_core.documents import Document as LCDocument
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import DocumentChunk
from app.vectorstore.client import get_embeddings


def _metadata(row: DocumentChunk) -> dict[str, Any]:
    return {
        "chunk_id": row.id,
        "doc_id": row.doc_id,
        "tenant_id": row.tenant_id,
        "filename": row.filename,
        "version": row.version,
        "chunk_idx": row.chunk_idx,
    }


def dense_search(
    db: Session,
    query: str,
    top_k: int,
    tenant_id: str,
    allowed_ids: list[str] | None,
) -> list[tuple[LCDocument, float]]:
    if allowed_ids is not None and not allowed_ids:
        return []
    vector = get_embeddings().embed_query(query)
    stmt = select(DocumentChunk).where(DocumentChunk.tenant_id == tenant_id, DocumentChunk.embedding.is_not(None))
    if allowed_ids is not None:
        stmt = stmt.where(DocumentChunk.doc_id.in_(allowed_ids))
    stmt = stmt.order_by(DocumentChunk.embedding.cosine_distance(vector)).limit(top_k)
    rows = db.execute(stmt).scalars().all()
    return [
        (LCDocument(page_content=row.content, metadata=_metadata(row)), float(row.embedding.cosine_distance(vector)))
        for row in rows
    ]


def tenant_documents(
    db: Session,
    tenant_id: str,
    allowed_ids: list[str] | None,
) -> list[LCDocument]:
    if allowed_ids is not None and not allowed_ids:
        return []
    stmt = select(DocumentChunk).where(DocumentChunk.tenant_id == tenant_id)
    if allowed_ids is not None:
        stmt = stmt.where(DocumentChunk.doc_id.in_(allowed_ids))
    rows = db.execute(stmt.order_by(DocumentChunk.doc_id, DocumentChunk.chunk_idx)).scalars().all()
    return [LCDocument(page_content=row.content, metadata=_metadata(row)) for row in rows]


def replace_document_chunks(db: Session, document_id: str, tenant_id: str, filename: str, version: int, chunks: list[str]) -> None:
    existing = {row.id: row for row in db.execute(select(DocumentChunk).where(DocumentChunk.doc_id == document_id)).scalars().all()}
    for idx, content in enumerate(chunks):
        chunk_id = f"{document_id}:v{version}:c{idx}"
        row = existing.get(chunk_id)
        if row is None:
            row = DocumentChunk(
                id=chunk_id,
                tenant_id=tenant_id,
                doc_id=document_id,
                filename=filename,
                version=version,
                chunk_idx=idx,
                content=content,
            )
            db.add(row)
        else:
            row.content = content
    db.commit()


def index_document_chunks(db: Session, document_id: str, tenant_id: str, filename: str, version: int) -> None:
    rows = db.execute(
        select(DocumentChunk).where(
            DocumentChunk.doc_id == document_id,
            DocumentChunk.tenant_id == tenant_id,
            DocumentChunk.version == version,
        ).order_by(DocumentChunk.chunk_idx)
    ).scalars().all()
    missing = [row for row in rows if row.embedding is None]
    if not missing:
        return
    vectors = get_embeddings().embed_documents([row.content for row in missing])
    for row, vector in zip(missing, vectors):
        row.embedding = vector
    db.commit()
