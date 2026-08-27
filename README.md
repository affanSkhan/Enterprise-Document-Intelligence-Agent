# Enterprise Intelligence Runtime

> A secure, evidence-first document intelligence workspace for enterprise knowledge.

Enterprise Intelligence combines asynchronous document processing, hybrid retrieval, cross-encoder reranking, access-controlled evidence, grounded RAG and structured AI workflows in one product.

## Product flow

```text
Upload → durable ingestion → parse/chunk → index
                         ↓
              hybrid retrieval + reranking
                         ↓
               tenant / document ACL
                         ↓
                  evidence gate
                   ↙          ↘
              enough             weak
                ↓                  ↓
             Gemini             abstain
                ↓
       answer + source evidence
```

## What is implemented

- PDF, DOCX, PPTX and XLSX ingestion with format-specific parsers.
- Durable Celery/Redis ingestion checkpoints and idempotent upload handling.
- PostgreSQL production metadata path with SQLite local fallback.
- Chroma-backed dense retrieval, BM25 sparse retrieval and reciprocal-rank fusion.
- Cross-encoder reranking with an explicit evidence admission threshold.
- Evidence-grounded Gemini answers with explicit abstention when support is insufficient.
- JWT authentication, tenant isolation, RBAC and document-level `read` ACLs.
- Prompt-injection defenses that keep retrieved content explicitly marked as untrusted data.
- Evidence graph, claim verification, contradiction detection and controlled workflow endpoints.
- Prometheus/OpenTelemetry-compatible observability and deterministic evaluation gates.
- Corporate-style Next.js workspace for authentication, documents, chat and AI workflows.

## Security posture

Authorization is enforced before retrieval, not after generation. Admin and manager roles can read documents in their tenant; viewers require explicit document permissions. Cross-tenant tenant-header mismatches are rejected. Retrieved content is treated as data and is never intended to override system instructions. These controls follow least-privilege and trust-boundary guidance for RAG applications. citehttps://genai.owasp.org/llmrisk/llm01-prompt-injection/

## Local run

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

For asynchronous ingestion:

```bash
celery -A app.worker.celery_app.celery_app worker --loglevel=INFO --queues=document-ingestion --concurrency=2
```

Set `GEMINI_API_KEY` in `backend/.env`. For a production-style local stack, use `docker compose up -d postgres redis worker backend` and keep the API and worker on the same PostgreSQL/Redis/Chroma configuration.

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

Set `NEXT_PUBLIC_API_URL` to the FastAPI base URL. See `frontend/.env.example`.

## Validation

The repository contains automated security/RAG regression tests under `backend/tests` and a deterministic evaluation gate under `evals/`. CI runs Python compile checks, Ruff, pytest, deterministic evaluation and a production frontend build. No benchmark result should be published unless it is produced by a reproducible run.

## Demo checklist

1. Sign in with an authenticated tenant user.
2. Upload a supported document and watch the ingestion status move to indexed.
3. Ask an answerable question and inspect the source evidence.
4. Ask an unsupported question and verify that the system abstains without calling the model.
5. Test a viewer before and after an explicit document permission grant.
6. Demonstrate that a different tenant cannot access the first tenant's documents.

## Architecture

```text
Next.js workspace
      |
FastAPI API ───── PostgreSQL / SQLite
      |
      +──── Redis ─── Celery workers
      |
      +──── Chroma + BM25 ─── reranker ─── ACL evidence gate
      |
      +──── Gemini generation / controlled workflows
      |
      +──── audit / metrics / tracing / evaluation
```

See `docs/ROADMAP.md`, `docs/ARCHITECTURE.md`, `docs/SECURITY.md` and `docs/EVALUATION.md` for implementation details.
