from __future__ import annotations

from typing import Any

from langchain_core.documents import Document as LCDocument
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import DocumentChunk
from app.vectorstore.client import get_embeddings


def _metadata(row: DocumentChunk) -> dict[str, Any]:
    return {"chunk_id": row.id, "doc_id": row.doc_id, "tenant_id": row.tenant_id, "filename": row.filename, "version": row.version, "chunk_idx": row.chunk_idx}


def dense_search(db: Session, query: str, top_k: int, tenant_id: str, allowed_ids: list[str] | None) -> list[tuple[LCDocument, float]]:
    if allowed_ids is not None and not allowed_ids:
        return []

    vector = get_embeddings().embed_query(query)
    distance_expr = DocumentChunk.embedding.cosine_distance(vector).label("distance")
    stmt = select(DocumentChunk, distance_expr).where(
        DocumentChunk.tenant_id == tenant_id,
        DocumentChunk.embedding.is_not(None),
    )
    if allowed_ids is not None:
        stmt = stmt.where(DocumentChunk.doc_id.in_(allowed_ids))
    stmt = stmt.order_by(distance_expr).limit(top_k)

    # The distance is a SQL expression, not a Python method on the returned
    # pgvector list. Selecting it explicitly avoids attempting to call
    # cosine_distance() on the deserialized embedding value.
    rows = db.execute(stmt).all()
    return [
        (LCDocument(page_content=row.content, metadata=_metadata(row)), float(distance))
        for row, distance in rows
    ]


def tenant_documents(db: Session, tenant_id: str, allowed_ids: list[str] | None) -> list[LCDocument]:
    if allowed_ids is not None and not allowed_ids:
        return []
    stmt = select(DocumentChunk).where(DocumentChunk.tenant_id == tenant_id)
    if allowed_ids is not None:
        stmt = stmt.where(DocumentChunk.doc_id.in_(allowed_ids))
    rows = db.execute(stmt.order_by(DocumentChunk.doc_id, DocumentChunk.chunk_idx)).scalars().all()
    return [LCDocument(page_content=row.content, metadata=_metadata(row)) for row in rows]


def persist_chunks(db: Session, document_id: str, tenant_id: str, filename: str, version: int, chunks: list[str]) -> None:
    existing = {row.id: row for row in db.execute(select(DocumentChunk).where(DocumentChunk.doc_id == document_id)).scalars().all()}
    active_ids: set[str] = set()
    for idx, content in enumerate(chunks):
        chunk_id = f"{document_id}:v{version}:c{idx}"
        active_ids.add(chunk_id)
        row = existing.get(chunk_id)
        if row is None:
            db.add(DocumentChunk(id=chunk_id, tenant_id=tenant_id, doc_id=document_id, filename=filename, version=version, chunk_idx=idx, content=content))
        else:
            row.content = content
            row.embedding = None
    for chunk_id, row in existing.items():
        if row.version == version and chunk_id not in active_ids:
            db.delete(row)
    db.commit()


def index_document_chunks(db: Session, document_id: str, tenant_id: str, version: int) -> None:
    rows = db.execute(select(DocumentChunk).where(DocumentChunk.doc_id == document_id, DocumentChunk.tenant_id == tenant_id, DocumentChunk.version == version).order_by(DocumentChunk.chunk_idx)).scalars().all()
    missing = [row for row in rows if row.embedding is None]
    if not missing:
        return
    vectors = get_embeddings().embed_documents([row.content for row in missing])
    for row, vector in zip(missing, vectors):
        row.embedding = vector
    db.commit()
