from time import perf_counter
from typing import Any, Callable

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.agents.retrieval import chat_with_docs
from app.agents.specialized import compare_documents, extract_bom, generate_presentation, generate_report
from app.core.security import detect_prompt_injection
from app.db.models import Document
from app.db.mongodb import mongodb_available
from app.db.session import get_db
from app.security.dependencies import get_tenant_id, get_user_id, require_role
from app.services.ingestion import process_upload
from app.services.mongo_persistence import MongoPersistence, get_persistence
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
    conversation_id: str | None = Field(default=None, max_length=200)


class AgentTopic(BaseModel):
    topic: str = Field(min_length=1, max_length=4000)


class AgentBOM(BaseModel):
    doc_id: str = Field(min_length=1, max_length=200)


class AgentCompare(BaseModel):
    doc_id_1: str = Field(min_length=1, max_length=200)
    doc_id_2: str = Field(min_length=1, max_length=200)
    query: str = Field(min_length=1, max_length=4000)


def _start_run(
    persistence: MongoPersistence,
    tenant_id: str,
    user_id: str,
    agent_type: str,
    task_type: str,
    conversation_id: str | None,
    input_data: dict[str, Any],
) -> str | None:
    return persistence.start_agent_run(
        tenant_id=tenant_id,
        user_id=user_id,
        agent_type=agent_type,
        task_type=task_type,
        conversation_id=conversation_id,
        input_data=input_data,
    )


def _finish_run(
    persistence: MongoPersistence,
    run_id: str | None,
    tenant_id: str,
    started: float,
    *,
    status: str,
    output: Any = None,
    model: str | None = None,
    citations: list[dict[str, Any]] | None = None,
    error: str | None = None,
) -> None:
    if not run_id:
        return
    persistence.complete_agent_run(
        run_id,
        tenant_id,
        status=status,
        final_output=output,
        model=model,
        citations=citations,
        latency_ms=round((perf_counter() - started) * 1000, 2),
        error=error,
    )


@router.get("/health")
async def health():
    return {"status": "ok", "service": "enterprise-intelligence-runtime"}


@router.get("/ready")
async def ready(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ready"}


@router.get("/ready/mongodb")
async def mongodb_ready():
    if not mongodb_available():
        raise HTTPException(status_code=503, detail="MongoDB is not configured or unavailable")
    return {"status": "ready", "database": "mongodb"}


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
async def documents(tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db)):
    return db.query(Document).filter(Document.tenant_id == tenant_id).order_by(Document.created_at.desc()).all()


@router.post("/search")
async def search(request: SearchQuery, tenant_id: str = Depends(get_tenant_id)):
    return {"results": search_documents(request.query, request.top_k, tenant_id=tenant_id, mode=request.mode, rerank=request.rerank)}


@router.post("/chat")
async def chat(
    request: ChatQuery,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_user_id),
):
    persistence = get_persistence()
    conversation_id = persistence.create_or_get_conversation(
        tenant_id, user_id, request.conversation_id
    )
    if conversation_id:
        persistence.append_message(
            tenant_id,
            user_id,
            conversation_id,
            "user",
            request.query,
        )

    started = perf_counter()
    run_id = _start_run(
        persistence,
        tenant_id,
        user_id,
        "grounded_document_chat",
        "chat",
        conversation_id,
        {"query": request.query, "top_k": request.top_k},
    )

    try:
        result = chat_with_docs(request.query, request.top_k, tenant_id=tenant_id)
        evidence = result.get("evidence", [])
        if run_id:
            persistence.append_step(
                run_id,
                tenant_id,
                "retrieval",
                tool="search_documents",
                input_data={"query": request.query, "top_k": request.top_k, "mode": "hybrid", "rerank": True},
                output={"result_count": len(evidence), "evidence_ids": [item.get("id") for item in evidence]},
                metadata=result.get("retrieval", {}),
            )
            persistence.append_step(
                run_id,
                tenant_id,
                "model_call",
                tool="llm",
                input_data={"model": result.get("model")},
                output={"answer_length": len(result.get("answer", ""))},
                metadata={"grounded": result.get("verified", False)},
            )

        if conversation_id:
            persistence.append_message(
                tenant_id,
                user_id,
                conversation_id,
                "assistant",
                result.get("answer", ""),
                citations=evidence,
                metadata={
                    "model": result.get("model"),
                    "verified": result.get("verified"),
                    "abstained": result.get("abstained"),
                },
            )

        _finish_run(
            persistence,
            run_id,
            tenant_id,
            started,
            status="completed",
            output=result,
            model=result.get("model"),
            citations=evidence,
        )
        return {**result, "conversation_id": conversation_id, "run_id": run_id}
    except Exception as exc:
        _finish_run(
            persistence,
            run_id,
            tenant_id,
            started,
            status="failed",
            error=str(exc)[:4000],
        )
        raise


@router.get("/conversations")
async def list_conversations(
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_user_id),
    limit: int = 50,
):
    if not mongodb_available():
        raise HTTPException(status_code=503, detail="Conversation persistence is unavailable")
    return {"conversations": get_persistence().list_conversations(tenant_id, user_id, min(limit, 100))}


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_user_id),
):
    if not mongodb_available():
        raise HTTPException(status_code=503, detail="Conversation persistence is unavailable")
    result = get_persistence().get_conversation(tenant_id, user_id, conversation_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return result


@router.get("/agent-runs/{run_id}")
async def get_agent_run(
    run_id: str,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_user_id),
):
    if not mongodb_available():
        raise HTTPException(status_code=503, detail="Agent-run persistence is unavailable")
    result = get_persistence().get_agent_run(run_id, tenant_id, user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return result


@router.get("/conversations/{conversation_id}/agent-runs")
async def list_conversation_runs(
    conversation_id: str,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_user_id),
):
    if not mongodb_available():
        raise HTTPException(status_code=503, detail="Agent-run persistence is unavailable")
    return {
        "runs": get_persistence().list_agent_runs(
            tenant_id, user_id, conversation_id=conversation_id
        )
    }


@router.post("/security/scan")
async def security_scan(request: ChatQuery):
    findings = detect_prompt_injection(request.query)
    return {"safe": not findings, "findings": findings}


def _run_specialized_agent(
    *,
    persistence: MongoPersistence,
    tenant_id: str,
    user_id: str,
    agent_type: str,
    task_type: str,
    input_data: dict[str, Any],
    fn: Callable[[], Any],
) -> tuple[Any, str | None]:
    started = perf_counter()
    run_id = _start_run(
        persistence,
        tenant_id,
        user_id,
        agent_type,
        task_type,
        None,
        input_data,
    )
    try:
        output = fn()
        if run_id:
            persistence.append_step(
                run_id,
                tenant_id,
                "agent_action",
                tool=task_type,
                input_data=input_data,
                output=output,
            )
        _finish_run(
            persistence,
            run_id,
            tenant_id,
            started,
            status="completed",
            output=output,
            model="gemini",
        )
        return output, run_id
    except Exception as exc:
        _finish_run(
            persistence,
            run_id,
            tenant_id,
            started,
            status="failed",
            error=str(exc)[:4000],
        )
        raise


@router.post("/agents/compare")
async def compare_agent(
    request: AgentCompare,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_user_id),
):
    output, run_id = _run_specialized_agent(
        persistence=get_persistence(),
        tenant_id=tenant_id,
        user_id=user_id,
        agent_type="document_comparison",
        task_type="compare_documents",
        input_data=request.model_dump(),
        fn=lambda: compare_documents(
            request.doc_id_1, request.doc_id_2, request.query, tenant_id=tenant_id
        ),
    )
    return {"result": output, "run_id": run_id}


@router.post("/agents/report")
async def report_agent(
    request: AgentTopic,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_user_id),
):
    output, run_id = _run_specialized_agent(
        persistence=get_persistence(),
        tenant_id=tenant_id,
        user_id=user_id,
        agent_type="reporting",
        task_type="generate_report",
        input_data=request.model_dump(),
        fn=lambda: generate_report(request.topic, tenant_id=tenant_id),
    )
    return {"result": output, "run_id": run_id}


@router.post("/agents/bom")
async def bom_agent(
    request: AgentBOM,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_user_id),
):
    output, run_id = _run_specialized_agent(
        persistence=get_persistence(),
        tenant_id=tenant_id,
        user_id=user_id,
        agent_type="bom_extraction",
        task_type="extract_bom",
        input_data=request.model_dump(),
        fn=lambda: extract_bom(request.doc_id, tenant_id=tenant_id),
    )
    return {"result": output, "run_id": run_id}


@router.post("/agents/presentation")
async def presentation_agent(
    request: AgentTopic,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_user_id),
):
    output, run_id = _run_specialized_agent(
        persistence=get_persistence(),
        tenant_id=tenant_id,
        user_id=user_id,
        agent_type="presentation_generation",
        task_type="generate_presentation",
        input_data=request.model_dump(),
        fn=lambda: generate_presentation(request.topic, tenant_id=tenant_id),
    )
    return {"result": output, "run_id": run_id}
