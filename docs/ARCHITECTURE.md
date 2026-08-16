# Architecture

## System boundaries

1. **API** validates requests, establishes tenant context and exposes stable contracts.
2. **Ingestion** owns file validation, checksums, parsing and version metadata.
3. **Retrieval** owns indexing, dense/sparse search, fusion and reranking.
4. **Agent runtime** owns planning, tool permissions, evidence collection and verification.
5. **Data layer** owns relational state, jobs and audit records.
6. **Evaluation** is a first-class subsystem and must not depend on subjective UI testing.
7. **Observability** records structured events, latency, model usage and failures without storing secrets.

## Data flow

```text
upload -> validate -> checksum -> parse -> normalize -> chunk -> embed -> index
query  -> retrieve dense + sparse -> fuse -> rerank -> evidence -> generate -> verify -> answer
```

## Trust boundaries

- User input is untrusted.
- Retrieved document content is untrusted and is explicitly marked as data in prompts.
- Tool execution requires an allow-list and role/tenant checks.
- Secrets never belong in source, logs, prompts or document metadata.

## Reliability

Long-running work belongs in a queue. Every job needs a stable ID, status transitions, retry policy and idempotency key. A production worker must checkpoint expensive document processing so failures can resume.

## Architecture decisions

- Keep SQLite as a zero-friction local fallback while supporting PostgreSQL through `DATABASE_URL`.
- Keep Chroma behind `get_vectorstore()` so the retrieval layer can later switch to a managed/vector-native backend without changing API contracts.
- Prefer evidence objects over raw strings so citation verification and UI provenance remain possible.
