# MongoDB Persistence

MongoDB is an **additional persistence layer**, not a replacement for the existing data stores.

## Responsibility split

| Store | Responsibility |
|---|---|
| PostgreSQL / SQLite | users, tenants, permissions, document metadata, versions, jobs and other strongly relational records |
| MongoDB | conversations, conversation messages, agent runs, nested execution steps, tool traces, variable AI outputs and model/latency/evaluation metadata |
| ChromaDB | embeddings and dense retrieval |
| Redis / Celery | asynchronous jobs and cache |

This is intentional polyglot persistence: each store owns data whose access and consistency model fits it naturally.

## Collections

### conversations

Conversation-level metadata is kept separate from individual messages so a long-running conversation cannot create an unbounded MongoDB array.

Example shape: `{ _id, conversation_id, tenant_id, user_id, title, message_count, created_at, updated_at }`.

### conversation_messages

Messages remain independently addressable and are scoped by tenant and user.

Example shape: `{ _id, message_id, conversation_id, tenant_id, user_id, role, content, citations, metadata, created_at }`.

### agent_runs

Execution records intentionally use flexible nested `steps`. Different agents can emit different step shapes without forcing those structures into relational columns.

Example shape includes `run_id`, `tenant_id`, `user_id`, `conversation_id`, `agent_type`, `task_type`, `status`, `input`, `steps`, `final_output`, `citations`, `model`, `token_usage`, `latency_ms`, `error`, `created_at`, and `completed_at`.

A step can contain `step_id`, `type`, `tool`, `input`, `output`, `metadata`, `started_at`, and `completed_at`.

## Indexes

The application creates these indexes idempotently:

### Conversations
- unique `conversation_id`
- `tenant_id + user_id + updated_at`
- `tenant_id`

### Conversation messages
- `tenant_id + user_id + conversation_id + created_at`
- unique `conversation_id + message_id`

### Agent runs
- unique `run_id`
- `tenant_id + conversation_id + created_at`
- `tenant_id + created_at`
- `tenant_id + user_id + created_at`
- `tenant_id + status`

The indexes correspond to actual API access patterns rather than adding an index for every field.

## Security boundary

MongoDB is **not** an authorization system.

Every repository method that accesses tenant/user history receives tenant and user context from the application security layer. The API never exposes a raw MongoDB query interface.

The current development configuration keeps the existing header-based tenant/role behavior for backward compatibility. Production authentication should derive `tenant_id`, `user_id`, and role from a verified access token/session.

## Reliability

MongoDB persistence is treated as non-critical history/observability data for the main generation path:
- connection timeouts are bounded
- PyMongo's connection pool is reused
- retryable reads/writes can be enabled for managed replica-set deployments
- index creation is idempotent
- persistence exceptions are logged and do not destroy a successful LLM response
- stable IDs make message/run writes retry-safe
- MongoDB can be disabled by leaving `MONGODB_URL` empty

Read-only history endpoints return `503` when MongoDB is configured but unavailable instead of pretending that history does not exist.

## Local development

`docker-compose.yml` includes a MongoDB service. The local standalone deployment explicitly disables retryable writes because retryable writes require a replica set or sharded deployment.

For production, use MongoDB Atlas or another replica-set/sharded managed deployment and configure:

`MONGODB_URL=<managed MongoDB connection string>`
`MONGODB_DATABASE=enterprise_intelligence`

Keep credentials out of source control.

## Interview explanation

> PostgreSQL remains the relational system of record for transactional enterprise entities, while MongoDB stores document-oriented AI execution and conversation data whose structure varies across agents and workflows. ChromaDB remains responsible for vector retrieval. This is intentional polyglot persistence rather than replacing one database with another.

The trade-off is operational complexity: the application now has another datastore to monitor, secure, back up and operate. MongoDB is justified here because execution steps, tool payloads, citations, evaluation metadata and agent-specific outputs are naturally nested and variable, while the core business entities remain relational.