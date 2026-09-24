# Security

## Required production controls

- Enable authentication and replace `SECRET_KEY`.
- Use PostgreSQL and Redis credentials from a secret manager.
- Restrict `CORS_ORIGINS` to trusted frontend origins.
- Enforce tenant IDs from authenticated identity rather than user-supplied headers.
- Enforce document-level ACLs before retrieval results enter the LLM context.
- Treat every retrieved document as untrusted data.
- Allow-list tools and require role checks for mutating operations.
- Apply upload size/type validation and store files outside the web root.
- Redact credentials and sensitive payloads from logs.

## Threat cases

1. Prompt injection inside a document.
2. Cross-tenant retrieval.
3. Unauthorized tool invocation.
4. Data exfiltration through generated output.
5. Malicious/oversized uploads.
6. Model/provider outage.

## Security tests

The security suite should include benign text, instruction-like document text, cross-tenant fixtures and unauthorized role/tool combinations. Security regressions should fail CI.

## MongoDB persistence security

- MongoDB is not an authorization mechanism.
- Conversation and agent-run reads/writes are always scoped by `tenant_id` and `user_id` from the application security context.
- API consumers cannot submit arbitrary MongoDB filters or collection names.
- Variable AI payloads are stored through a repository abstraction rather than direct API-to-database access.
- MongoDB connection credentials belong only in deployment secrets/environment variables.
- Persistence failures are logged without leaking credentials or full sensitive prompts.
- Production authentication must derive tenant/user identity from verified credentials rather than trusting the development headers.