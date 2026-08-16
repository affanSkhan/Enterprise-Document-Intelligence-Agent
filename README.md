# Enterprise Intelligence Runtime

> A production-oriented document intelligence platform for heterogeneous enterprise knowledge.

This repository is being evolved from the original MVP into a measurable AI engineering system: document ingestion, structured metadata, retrieval, agent execution, security boundaries, evaluation, observability and reliable asynchronous workflows.

## Current architecture

```text
Next.js UI
    |
FastAPI API ---- PostgreSQL/SQLite metadata
    |             |
    +---- Redis / worker jobs
    |
    +---- Hybrid retrieval -> reranking -> ACL-filtered evidence
    |
    +---- Agent runtime -> tools -> verification
    |
    +---- evaluation / audit / observability
```

## Supported documents

PDF, DOCX, PPTX and XLSX. The parser factory provides a format-specific extension point. The ingestion layer records a checksum, tenant, version and processing status before indexing.

## Engineering goals

- Hybrid dense + sparse retrieval with reranking
- Evidence-first answers and explicit abstention
- JWT authentication, tenant isolation, RBAC and document ACLs
- Prompt-injection and tool-boundary defenses
- Async, resumable ingestion and idempotent jobs
- PostgreSQL + Redis production path with SQLite local fallback
- Evaluation datasets for retrieval, generation, citation and security
- OpenTelemetry-compatible tracing and structured logs
- Cost/latency accounting and regression gates in CI

## Local development

```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Set `GEMINI_API_KEY` in `backend/.env`. The application uses SQLite by default for local development. For production, set `DATABASE_URL` to PostgreSQL and `REDIS_URL` to Redis.

### Authentication

For production, set `ENABLE_AUTH=true`, replace `SECRET_KEY`, and configure `ADMIN_TENANT_ID`, `ADMIN_TENANT_NAME`, `ADMIN_EMAIL` and `ADMIN_PASSWORD`. The configured admin is bootstrapped on startup. Obtain a JWT at `POST /api/auth/token` using OAuth2 form fields `username` and `password`.

Document access is enforced before dense/sparse retrieval. `admin` and `manager` roles have tenant-wide document read access; `viewer` users require explicit `read` permissions on each document.

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## API smoke test

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/ready
```

## Evaluation

The `evals/` directory is intentionally part of the product. Add datasets with expected evidence, run retrieval/generation/security evaluations, and record latency, recall, citation correctness and cost. Do not publish invented benchmark numbers; results must come from reproducible runs.

## Security model

Retrieved documents are untrusted data, never instructions. Tenant context is propagated through API boundaries and vector metadata. Authentication and authorization are enforced before document retrieval, so unauthorized chunks are excluded from the candidate set rather than merely hidden after generation.

## Roadmap

See `docs/ROADMAP.md`, `docs/ARCHITECTURE.md`, `docs/SECURITY.md` and `docs/EVALUATION.md` for the implementation contract and benchmark plan.
