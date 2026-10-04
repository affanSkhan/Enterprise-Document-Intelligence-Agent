# Enterprise Document Intelligence Agent

> **Evidence-grounded AI for enterprise documents — with hybrid retrieval, reranking, controlled agent workflows, security boundaries, and measurable evaluation.**

<p align="center">
  <a href="https://github.com/affanSkhan/Enterprise-Document-Intelligence-Agent/actions/workflows/ci.yml"><img src="https://github.com/affanSkhan/Enterprise-Document-Intelligence-Agent/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Next.js-16-black?logo=next.js" alt="Next.js">
  <img src="https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/PostgreSQL-production-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Redis-jobs%20%26%20cache-DC382D?logo=redis&logoColor=white" alt="Redis">
  <img src="https://img.shields.io/badge/RAG-hybrid%20%2B%20reranking-7C3AED" alt="RAG">
</p>

<p align="center">
  <a href="https://enterprise-doc-intelligence-ui.onrender.com">Live Demo</a> ·
  <a href="docs/ARCHITECTURE.md">Architecture</a> ·
  <a href="docs/SECURITY.md">Security</a> ·
  <a href="docs/EVALUATION.md">Evaluation</a> ·
  <a href="docs/ROADMAP.md">Roadmap</a>
</p>

---

## Why this project?

Most document-chat demos stop at **"upload a PDF → ask a question → call an LLM."**

This project explores what is required to move that idea toward an **enterprise-grade intelligence runtime** where the system must answer a harder question:

> **Can an AI system produce useful answers while staying grounded in authorized evidence, respecting tenant/security boundaries, and remaining measurable and maintainable?**

The platform therefore treats retrieval, authorization, agent tools, verification, evaluation, observability, and asynchronous processing as first-class engineering concerns rather than UI features.

### Core principles

| Principle | What it means |
|---|---|
| **Evidence first** | Answers are generated from retrieved evidence rather than unconstrained model knowledge. |
| **Security outside the model** | Authorization and tenant boundaries are enforced by application code. |
| **Untrusted documents** | Retrieved text is treated as data, never as trusted instructions. |
| **Controlled agents** | Agent capabilities are exposed through explicit tools and permission boundaries. |
| **Async by design** | Long-running document work is designed around jobs instead of blocking requests. |
| **Measurable AI** | Retrieval, generation, security, latency, and cost are intended to be evaluated systematically. |
| **Reproducible engineering** | Configuration, dependencies, tests, CI, architecture, and evaluation contracts live in the repository. |

---

## Product overview

The application provides an enterprise workspace for:

- 📄 **Document ingestion** — PDF, DOCX, PPTX, and XLSX
- 🔎 **Hybrid search** — dense semantic retrieval + sparse BM25 retrieval
- 🏆 **Reranking** — optional cross-encoder reranking after retrieval fusion
- 💬 **Grounded chat** — answers backed by retrieved document evidence
- 🤖 **Specialized agents** — reporting, document comparison, BOM extraction, and presentation generation
- 🔐 **Security boundaries** — tenant-aware access, role checks, document authorization primitives, and prompt-injection detection
- ⚙️ **Production data path** — PostgreSQL/SQLite metadata and Redis-oriented job/cache architecture
- 📊 **Evaluation** — retrieval and generation evaluation contracts plus regression-oriented CI foundations
- 🧭 **Observability foundations** — structured logging, audit-oriented events, tracing/cost-control architecture

> **Status note:** this is a production-oriented engineering project, not a claim that every production control is already complete. The repository intentionally distinguishes implemented foundations from remaining hardening work in `docs/ROADMAP.md`.

---

## Architecture at a glance

```mermaid
flowchart TB
    U[User / Enterprise Workspace] --> UI[Next.js UI]
    UI --> API[FastAPI API]

    API --> AUTH[Auth / Tenant / Role Boundary]
    API --> ING[Ingestion Service]
    API --> RET[Retrieval Service]
    API --> AG[Agent Runtime]

    ING --> PARSE[Format-specific Parsers]
    PARSE --> CHUNK[Normalize + Chunk]
    CHUNK --> EMB[Embeddings]
    EMB --> VS[(Vector Store)]
    CHUNK --> META[(PostgreSQL / SQLite)]

    RET --> DENSE[Dense Retrieval]
    RET --> SPARSE[BM25 Sparse Retrieval]
    DENSE --> FUSE[Reciprocal Rank Fusion]
    SPARSE --> FUSE
    FUSE --> RERANK[Cross-Encoder Reranker]
    RERANK --> EVID[Authorized Evidence]

    AG --> TOOLS[Allow-listed Tools]
    AG --> VERIFY[Verification / Guardrails]
    EVID --> AG
    AG --> LLM[LLM]
    LLM --> VERIFY
    VERIFY --> OUT[Grounded Answer]

    API --> REDIS[(Redis / Jobs / Cache)]
    API --> OBS[Logs / Traces / Metrics]
    OBS --> AUDIT[(Audit Events)]
```

### Request lifecycle

```mermaid
sequenceDiagram
    participant User
    participant UI as Next.js
    participant API as FastAPI
    participant Sec as Security Boundary
    participant Search as Retrieval
    participant Agent as Agent Runtime
    participant LLM

    User->>UI: Ask question
    UI->>API: Authenticated request
    API->>Sec: Establish tenant + role context
    Sec-->>API: Authorized context
    API->>Search: Retrieve relevant evidence
    Search->>Search: Dense + BM25 → RRF → rerank
    Search-->>API: Evidence candidates
    API->>Agent: Execute controlled reasoning
    Agent->>LLM: Generate from evidence
    LLM-->>Agent: Candidate answer
    Agent->>Agent: Verify grounding / constraints
    Agent-->>API: Answer + evidence
    API-->>UI: Grounded response
    UI-->>User: Answer with provenance
```

---

## Document ingestion pipeline

The ingestion architecture separates **file handling**, **content extraction**, **normalization**, **chunking**, and **indexing** so each stage can evolve independently.

```mermaid
flowchart LR
    A[Upload] --> B[Validate type / size]
    B --> C[Checksum]
    C --> D[Version metadata]
    D --> E{Parser Factory}
    E --> P1[PDF]
    E --> P2[DOCX]
    E --> P3[PPTX]
    E --> P4[XLSX]
    P1 --> N[Normalize]
    P2 --> N
    P3 --> N
    P4 --> N
    N --> CH[Chunk]
    CH --> EM[Embed]
    CH --> BM[BM25 Index]
    EM --> VI[Vector Index]
    BM --> READY[Searchable Evidence]
    VI --> READY
```

Supported formats currently include **PDF, DOCX, PPTX, and XLSX**. The parser factory provides a format-specific extension point, while ingestion records metadata such as checksum, tenant, version, and processing state.

---

## Retrieval: from naive RAG to hybrid search

A central engineering goal is to avoid relying on one retrieval signal.

### Retrieval stack

```text
                         ┌──────────────────┐
                         │   User Query     │
                         └────────┬─────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
             Dense Retrieval              BM25 Retrieval
             semantic similarity          lexical matching
                    │                           │
                    └─────────────┬─────────────┘
                                  ▼
                         Reciprocal Rank Fusion
                                  │
                                  ▼
                         Cross-Encoder Rerank
                                  │
                                  ▼
                         Authorized Evidence
                                  │
                                  ▼
                         Grounded Generation
```

The repository contains separate retrieval components for BM25, fusion, reranking, and the document-chat path. This makes retrieval quality independently testable and allows retrieval configuration to evolve without coupling it to the UI.

### Why hybrid retrieval?

| Retrieval method | Strength |
|---|---|
| **Dense** | Captures semantic similarity and paraphrases. |
| **BM25** | Strong for exact terminology, identifiers, names, and lexical matches. |
| **RRF** | Combines independent ranking signals without requiring them to share the same score scale. |
| **Cross-encoder** | Performs a more expensive query/document relevance pass on the fused candidates. |

---

## Evidence-grounded generation

The application is designed around an **evidence-first contract**:

```mermaid
flowchart LR
    Q[Question] --> R[Retrieve]
    R --> A[Authorization Filter]
    A --> E[Evidence Set]
    E --> G[Generate]
    G --> V[Verify]
    V -->|supported| S[Grounded Answer]
    V -->|insufficient / unsafe| X[Abstain or Constrain]
```

This matters because a high-quality enterprise answer is not simply a fluent answer. It should also be possible to answer:

- **Where did this claim come from?**
- **Was the evidence authorized for this tenant/user?**
- **Was the evidence sufficient to answer?**
- **Can the system safely abstain when it is not?**

The architecture therefore treats evidence objects and provenance as more important than passing raw strings directly into the model.

---

## Controlled agent runtime

The project extends beyond chat by exposing specialized capabilities through explicit application routes and agent functions.

```mermaid
flowchart TD
    Q[User Task] --> ROUTER[Agent / Task Router]
    ROUTER --> R[Retrieval]
    ROUTER --> REPORT[Report Agent]
    ROUTER --> COMPARE[Document Compare]
    ROUTER --> BOM[BOM Extraction]
    ROUTER --> PPT[Presentation Generation]

    REPORT --> PERM[Permission Boundary]
    COMPARE --> PERM
    BOM --> PERM
    PPT --> PERM
    R --> PERM
    PERM --> VERIFY[Verification / Output Checks]
    VERIFY --> RESULT[Controlled Result]
```

The important design choice is that **the model is not the authorization layer**. Tool access and tenant/role checks belong in deterministic application code.

---

## Security model

Security is treated as a trust-boundary problem rather than only a prompt-engineering problem.

```mermaid
flowchart TB
    USER[User Input] --> API[API Boundary]
    API --> TENANT[Tenant Context]
    API --> ROLE[Role Check]
    API --> ACL[Document Authorization]
    ACL --> RET[Retrieval]
    DOC[Retrieved Document] --> UNTRUSTED[UNTRUSTED DATA]
    UNTRUSTED --> PROMPT[LLM Context]
    PROMPT --> LLM[Model]
    LLM --> VERIFY[Verification]
    TOOLS[Tools] --> ALLOW[Allow-list + Role Check]
    ALLOW --> EXEC[Execution]
```

Threat cases explicitly considered by the project include:

- prompt injection inside documents
- cross-tenant retrieval
- unauthorized tool invocation
- data exfiltration through generated output
- malicious or oversized uploads
- model/provider failures

See [`docs/SECURITY.md`](docs/SECURITY.md) for the security contract and required production controls.

---

## Data and infrastructure

```mermaid
erDiagram
    TENANT ||--o{ DOCUMENT : owns
    DOCUMENT ||--o{ DOCUMENT_VERSION : has
    DOCUMENT ||--o{ CHUNK : produces
    DOCUMENT ||--o{ AUDIT_EVENT : affects
    TENANT ||--o{ JOB : schedules

    TENANT {
      string id
    }
    DOCUMENT {
      string id
      string tenant_id
      string checksum
      string status
    }
    DOCUMENT_VERSION {
      string document_id
      int version
    }
    CHUNK {
      string document_id
      string identity
    }
    JOB {
      string id
      string tenant_id
      string status
    }
    AUDIT_EVENT {
      string tenant_id
      string action
    }
```

### Runtime responsibilities

| Layer | Responsibility |
|---|---|
| **Next.js** | Enterprise workspace, document UI, chat, workflows, typed API integration |
| **FastAPI** | Stable API contracts, request validation, security dependencies, orchestration |
| **PostgreSQL / SQLite** | Relational metadata and local-development persistence |
| **Redis** | Job/cache architecture for production-oriented asynchronous workflows |
| **Vector store** | Dense retrieval index behind an abstraction boundary |
| **BM25** | Sparse lexical retrieval |
| **LLM** | Evidence-grounded generation and specialized intelligence tasks |
| **OpenTelemetry-compatible layer** | Tracing/observability foundation |

---

## Repository structure

```text
.
├── .github/
│   └── workflows/
│       └── ci.yml                 # Backend + frontend CI
│
├── backend/
│   ├── app/
│   │   ├── agents/                # Retrieval + specialized agents
│   │   ├── api/                   # FastAPI routes/contracts
│   │   ├── core/                  # Config, security, logging, types
│   │   ├── db/                    # SQLAlchemy models/session
│   │   ├── evaluation/            # Evaluation metrics + retrieval eval
│   │   ├── parsers/               # PDF/DOCX/PPTX/XLSX parsers
│   │   ├── retrieval/             # BM25, RRF fusion, reranking
│   │   ├── security/              # Tenant/role dependencies
│   │   └── services/              # Ingestion/search services
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                      # Next.js application
├── docs/
│   ├── ARCHITECTURE.md
│   ├── SECURITY.md
│   ├── EVALUATION.md
│   └── ROADMAP.md
│
└── README.md
```

---

## Local development

### 1. Clone

```bash
git clone https://github.com/affanSkhan/Enterprise-Document-Intelligence-Agent.git
cd Enterprise-Document-Intelligence-Agent
```

### 2. Backend

```bash
cd backend
python -m venv .venv
```

**Windows**

```bash
.venv\Scripts\activate
```

**Linux/macOS**

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create `backend/.env` and configure the required model/database settings. For a zero-friction local setup, SQLite is supported; production deployments should use PostgreSQL and Redis.

Start the API:

```bash
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd ../frontend
npm install
npm run dev
```

The frontend can then be opened at the local Next.js development address shown by the terminal.

---

## API smoke tests

Once the backend is running:

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/ready
```

Expected health response shape:

```json
{
  "status": "ok",
  "service": "enterprise-intelligence-runtime"
}
```

The API exposes routes for document upload/listing, search, grounded chat, security scanning, and specialized agents.

---

## Evaluation and benchmarking

Evaluation is deliberately kept inside the product repository rather than relying only on subjective demo quality.

### Evaluation dimensions

```text
                 AI QUALITY
                     │
       ┌─────────────┼─────────────┐
       ▼             ▼             ▼
   Retrieval      Generation      Agent
   Recall/MRR     Grounding       Completion
   nDCG/Latency   Citations       Tool choice
       │             │             │
       └─────────────┼─────────────┘
                     ▼
                  Security
          Injection / Tenant / Tools
                     │
                     ▼
             Regression Decision
```

The evaluation contract includes:

- Recall@1 / @5 / @10
- MRR and nDCG
- P50/P95 latency
- answer relevance
- faithfulness / groundedness
- citation precision and recall
- abstention accuracy
- agent task completion and tool-selection accuracy
- prompt-injection attack success rate
- cross-tenant retrieval violations
- unauthorized tool execution

> **No invented benchmark numbers.** The repository's evaluation documentation explicitly requires results to come from reproducible runs with model/version/configuration metadata.

See [`docs/EVALUATION.md`](docs/EVALUATION.md).

---

## CI/CD

GitHub Actions validates both major application surfaces.

```mermaid
flowchart LR
    PUSH[Push / Pull Request] --> B[Backend]
    PUSH --> F[Frontend]
    B --> B1[Install dependencies]
    B1 --> B2[Compile checks]
    B2 --> B3[Pytest]
    F --> F1[npm ci]
    F1 --> F2[Lint]
    F2 --> F3[Production build]
    B3 --> G[Quality Gate]
    F3 --> G
```

The current workflow runs on pushes to `main`/`phase-*` and pull requests targeting `main`, with separate backend and frontend jobs.

For the exact workflow, see [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

---

## Deployment

A deployed frontend is available for demonstration:

**Live application:** https://enterprise-doc-intelligence-ui.onrender.com

Production deployment requires environment-specific configuration, including model credentials and secure PostgreSQL/Redis persistence. Secrets should never be committed to the repository.

---

## Engineering roadmap

The project is intentionally being developed in phases instead of declaring every enterprise feature complete prematurely.

### Implemented foundations

- [x] configuration and environment separation
- [x] typed relational domain model
- [x] database abstraction
- [x] structured logging foundation
- [x] upload validation and checksums
- [x] tenant-aware API boundary
- [x] security primitives
- [x] evaluation contract
- [x] architecture/security documentation
- [x] BM25 sparse retrieval
- [x] reciprocal-rank fusion
- [x] cross-encoder reranking
- [x] retrieval benchmark framework

### Next hardening layers

- [ ] resumable Celery/Redis worker execution
- [ ] complete PostgreSQL migration/deployment path
- [ ] persistent authenticated RBAC
- [ ] document ACL filtering before retrieval
- [ ] idempotency + dead-letter handling
- [ ] richer table/layout extraction
- [ ] semantic document diff and contradiction detection expansion
- [ ] calculation/tool traces and stronger citation verification
- [ ] multimodal/OCR expansion
- [ ] production OpenTelemetry/metrics dashboard
- [ ] model routing and cost controls
- [ ] load/security benchmarks
- [ ] CI evaluation regression gate
- [ ] workflow engine + human approval

For the authoritative project roadmap, see [`docs/ROADMAP.md`](docs/ROADMAP.md).

---

## Design documentation

| Document | Purpose |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System boundaries, data flow, trust boundaries, reliability decisions |
| [`docs/SECURITY.md`](docs/SECURITY.md) | Production controls, threat cases, security-test contract |
| [`docs/EVALUATION.md`](docs/EVALUATION.md) | Benchmark schema, metrics, regression policy |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Implemented foundations and remaining engineering phases |

---

## What makes this different from a basic RAG demo?

```text
Basic document chatbot

Upload → Chunk → Embed → Vector Search → LLM → Answer


Enterprise Intelligence Runtime

Upload
  ↓
Validate + checksum + version metadata
  ↓
Format-specific parsing + normalization
  ↓
Chunk + index
  ↓
┌───────────────────────────────────────────┐
│ Dense retrieval + BM25 + RRF + reranking │
└───────────────────────────────────────────┘
  ↓
Tenant / role / document authorization
  ↓
Evidence set
  ↓
Controlled agent + allow-listed tools
  ↓
LLM generation
  ↓
Verification / abstention boundary
  ↓
Grounded answer + provenance
  ↓
Evaluation + audit + observability
```

The goal is not simply to make an LLM answer questions about documents. The goal is to demonstrate the engineering required to make **document intelligence trustworthy, testable, observable, and extensible**.

---

## License

See the repository license and Git history for project provenance.

## Data architecture: intentional polyglot persistence

The platform deliberately separates data by **shape, consistency requirements, and access pattern** instead of forcing every workload into one database.

```mermaid
flowchart TB
    APP[Enterprise Intelligence Runtime]

    APP --> SQL[(PostgreSQL / SQLite)]
    APP --> MONGO[(MongoDB)]
    APP --> CHROMA[(ChromaDB)]
    APP --> REDIS[(Redis / Celery)]

    SQL --> SQL1[Tenants / Users]
    SQL --> SQL2[Documents / Versions]
    SQL --> SQL3[Jobs / Relational metadata]

    MONGO --> M1[Conversations]
    MONGO --> M2[Conversation Messages]
    MONGO --> M3[Agent Runs]
    MONGO --> M4[Nested Steps / Tool traces]

    CHROMA --> V1[Embeddings]
    CHROMA --> V2[Semantic retrieval]

    REDIS --> R1[Async jobs]
    REDIS --> R2[Task state / broker]
```

### Store responsibilities

| Store | Owns | Why |
|---|---|---|
| **PostgreSQL / SQLite** | Tenants, users, roles, documents, versions, jobs and strongly relational state | Constraints, relationships, transactions |
| **MongoDB** | Conversations, messages, agent runs, nested steps, citations, model metadata and variable AI outputs | Flexible document model for evolving execution traces |
| **ChromaDB** | Embeddings and vectorized chunks | Dense similarity retrieval |
| **Redis / Celery** | Background execution and cache foundation | Low-latency transient state and asynchronous jobs |

> MongoDB is an **additional persistence layer**. It does not replace the relational database and it is not the vector database.

---

# MongoDB: AI memory and execution telemetry

MongoDB was added specifically for the parts of the platform whose shape changes as the agent system evolves.

Relational storage remains the system of record for structured application entities. MongoDB handles **conversation history and AI execution state** where nested and agent-specific data is more natural.

## Why MongoDB?

An AI run can contain a variable sequence such as:

```text
User question
  ↓
Hybrid retrieval
  ↓
Evidence collection
  ↓
Model call
  ↓
Tool call
  ↓
Verification
  ↓
Final answer
```

Different agent types can have different steps and payloads. Encoding every future step as a rigid relational schema would create unnecessary migration pressure.

MongoDB therefore provides a flexible document-oriented boundary for:

- conversation metadata
- individual conversation messages
- citations and evidence metadata
- agent run inputs and outputs
- nested execution steps
- model identifiers
- token-usage metadata when available
- latency and completion status
- errors and diagnostic metadata

## MongoDB collection model

```mermaid
erDiagram
    CONVERSATIONS ||--o{ CONVERSATION_MESSAGES : contains
    CONVERSATIONS ||--o{ AGENT_RUNS : produces
    AGENT_RUNS ||--o{ EXECUTION_STEPS : contains

    CONVERSATIONS {
      string conversation_id PK
      string tenant_id
      string user_id
      string title
      int message_count
      datetime created_at
      datetime updated_at
    }

    CONVERSATION_MESSAGES {
      string message_id PK
      string conversation_id
      string tenant_id
      string user_id
      string role
      string content
      array citations
      object metadata
      datetime created_at
    }

    AGENT_RUNS {
      string run_id PK
      string tenant_id
      string user_id
      string conversation_id
      string agent_type
      string task_type
      string status
      object input
      array steps
      object final_output
      string model
      object token_usage
      float latency_ms
      array citations
      string error
      datetime created_at
      datetime completed_at
    }

    EXECUTION_STEPS {
      string step_id
      string type
      string tool
      object input
      object output
      object metadata
      datetime started_at
      datetime completed_at
    }
```

### 1. conversations

A conversation stores lightweight metadata. Messages are intentionally **not embedded as one unbounded array**.

```json
{
  "conversation_id": "...",
  "tenant_id": "...",
  "user_id": "...",
  "title": "New conversation",
  "message_count": 12,
  "created_at": "...",
  "updated_at": "..."
}
```

Keeping messages in a separate collection prevents one conversation document from growing without bound and makes individual messages independently addressable.

### 2. conversation_messages

Messages preserve:

- role (`user` / `assistant`)
- content
- citations
- metadata
- tenant/user scope
- creation timestamp

### 3. agent_runs

An agent run is the durable record of one specialized or conversational execution.

```json
{
  "run_id": "...",
  "agent_type": "document_comparison",
  "task_type": "compare_documents",
  "status": "completed",
  "input": {"doc_id_1": "...", "doc_id_2": "..."},
  "steps": [
    {
      "type": "retrieval",
      "tool": "hybrid_search",
      "metadata": {"reranked": true}
    },
    {
      "type": "tool_call",
      "tool": "document_comparison"
    }
  ],
  "final_output": {"answer": "..."},
  "model": "gemini-2.5-flash",
  "latency_ms": 123.4
}
```

This flexible run document is especially useful for agentic systems because a new agent can introduce a new step type without requiring a new SQL table or column for every variation.

## MongoDB execution lifecycle

```mermaid
sequenceDiagram
    participant API as FastAPI
    participant M as MongoDB
    participant R as Retrieval
    participant L as Gemini

    API->>M: Create / continue conversation
    API->>M: Persist user message
    API->>M: Start agent run
    API->>R: Search evidence
    R-->>API: Ranked evidence
    API->>M: Append retrieval step
    API->>L: Generate grounded response
    L-->>API: Answer
    API->>M: Append model step
    API->>M: Persist assistant message + citations
    API->>M: Complete agent run
```

## Tenant and user isolation

MongoDB repository methods require application-supplied `tenant_id` and `user_id` scope before reading or writing conversation history and agent runs.

```text
Tenant A + User A  →  can read their own history
Tenant A + User B  →  cannot read it
Tenant B + User A  →  cannot read it
```

The repository has explicit tests covering these isolation boundaries.

> **Important:** MongoDB is not the authorization layer. The current development security context still supports simplified header-based identity for backward compatibility. Production identity should come from a verified authentication token/session.

## MongoDB index strategy

The application creates indexes that correspond to real API access patterns:

| Collection | Index | Purpose |
|---|---|---|
| `conversations` | unique `conversation_id` | Stable conversation identity |
| `conversations` | `tenant_id + user_id + updated_at` | User history listing |
| `conversation_messages` | `tenant_id + user_id + conversation_id + created_at` | Ordered conversation reads |
| `conversation_messages` | unique `conversation_id + message_id` | Message idempotency |
| `agent_runs` | unique `run_id` | Stable execution identity |
| `agent_runs` | `tenant_id + conversation_id + created_at` | Conversation run history |
| `agent_runs` | `tenant_id + user_id + created_at` | User-scoped run history |
| `agent_runs` | `tenant_id + status` | Operational status filtering |

The index creation path is idempotent so application startup can safely ensure the required indexes exist.

## Reliability model

MongoDB persistence is intentionally treated as **non-critical history/telemetry** for the primary answer path.

```mermaid
flowchart LR
    Q[AI request] --> AI[Generate grounded response]
    AI --> OUT[Return answer]
    AI --> M[Persist history / run]
    M -->|available| STORED[Stored]
    M -->|unavailable| LOG[Log persistence failure]
    LOG -.-> OUT
```

Additional safeguards in the Mongo boundary include:

- bounded connect/server-selection/socket timeouts
- reusable MongoDB client and configurable pool limits
- optional retryable reads/writes
- idempotent indexes
- stable IDs for replay-safe message/run writes
- graceful disabled mode when `MONGODB_URL` is empty
- explicit `503` behaviour for history endpoints when the history store is unavailable

### Local MongoDB

`docker-compose.yml` provisions MongoDB 8 locally.

```bash
docker compose up --build
```

### MongoDB Atlas

For production, the intended deployment is MongoDB Atlas or another managed replica-set/sharded MongoDB deployment.

Configure:

```env
MONGODB_URL=mongodb+srv://<user>:<password>@<cluster>/
MONGODB_DATABASE=enterprise_intelligence
MONGODB_APP_NAME=enterprise-intelligence-runtime
MONGODB_CONNECT_TIMEOUT_MS=3000
MONGODB_SERVER_SELECTION_TIMEOUT_MS=3000
MONGODB_SOCKET_TIMEOUT_MS=5000
MONGODB_MAX_POOL_SIZE=20
MONGODB_MIN_POOL_SIZE=0
MONGODB_RETRY_READS=true
MONGODB_RETRY_WRITES=true
```

Never commit MongoDB credentials to the repository.

---

# AI agent execution model

```mermaid
flowchart TB
    U[User Task] --> API[FastAPI]
    API --> SEC[Tenant / User / Role Context]
    SEC --> RET[Hybrid Retrieval]
    RET --> E[Evidence]
    E --> SPEC[Specialized Agent]
    SPEC --> LLM[Gemini]
    LLM --> OUT[Grounded Output]
    OUT --> MONGO[MongoDB Agent Run]
    SPEC --> MONGO
    RET --> MONGO
```

The four specialized endpoints currently exposed by the backend are:

| Workflow | Endpoint | Output style |
|---|---|---|
| Document comparison | `POST /api/agents/compare` | Natural-language comparison |
| Report generation | `POST /api/agents/report` | Executive report |
| BOM extraction | `POST /api/agents/bom` | Structured JSON array |
| Presentation generation | `POST /api/agents/presentation` | Structured slide outline |

Each specialized workflow creates an agent-run record and can store the execution result and steps in MongoDB.

---

# Retrieval architecture

```mermaid
flowchart TB
    Q[Question] --> D[Dense Retrieval]
    Q --> S[Sparse BM25]
    D --> F[RRF Fusion]
    S --> F
    F --> RR[Cross-Encoder Rerank]
    RR --> E[Top-K Evidence]
    E --> L[Gemini Grounded Generation]
```

The current search service supports:

- `dense` retrieval
- `sparse` retrieval
- `hybrid` retrieval
- optional reranking

Default retrieval controls include configurable candidate depth, chunk size/overlap, and reranker top-K.

---

# Current implementation boundaries

The repository is intentionally explicit about what is implemented and what remains hardening work.

| Area | Current state |
|---|---|
| MongoDB conversation persistence | ✅ Implemented |
| MongoDB agent-run + nested step persistence | ✅ Implemented |
| MongoDB tenant/user scoped history | ✅ Implemented |
| MongoDB health/readiness boundary | ✅ Implemented |
| ChromaDB dense retrieval | ✅ Implemented |
| BM25 + RRF + reranking | ✅ Implemented |
| Celery/Redis foundation | ✅ Implemented |
| Production token-derived identity | ⚠️ Hardening required |
| Document-level ACL filtering before retrieval | ⚠️ Hardening required |
| Fully resumable asynchronous ingestion | ⚠️ Roadmap |
| OCR/layout-aware parsing | ⚠️ Roadmap |
| Full evaluation regression gate | ⚠️ Roadmap |

One important frontend note: the chat component reads `NEXT_PUBLIC_API_URL`, while some current document/agent components still contain localhost API URLs directly. Production frontend deployment should centralize the API base URL before considering the UI configuration deployment-complete.

---

# Interview-ready architecture summary

> **Why use MongoDB when PostgreSQL already exists?**

> PostgreSQL remains the relational system of record for tenants, users, document metadata, versions and other strongly structured entities. MongoDB stores conversations and agent execution traces because their structure is variable, nested and likely to evolve as new agents and tools are introduced. ChromaDB remains the vector store, while Redis/Celery handles asynchronous execution. This is intentional polyglot persistence by workload.

> **Why not store conversations in one MongoDB document?**

> Messages are stored separately so a conversation does not grow as one unbounded array. That gives better document growth characteristics and makes individual message records independently addressable.

> **What happens when MongoDB is down?**

> The main AI response path is designed to remain useful because MongoDB persistence is non-critical history/telemetry. Persistence errors are logged; history-specific endpoints surface the dependency failure explicitly.

> **How is tenant isolation handled?**

> MongoDB access is always scoped using tenant/user context from the application security layer. MongoDB itself is not treated as an authorization mechanism.

---

## License

See the repository license for the applicable terms.