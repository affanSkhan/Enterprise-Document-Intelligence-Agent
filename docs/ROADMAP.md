# Roadmap

## Foundation
- [x] configuration and environment separation
- [x] typed relational domain model
- [x] database abstraction
- [x] structured logging foundation
- [x] upload validation and checksums
- [x] tenant-aware API boundary
- [x] security primitives
- [x] evaluation contract
- [x] architecture/security documentation

## Retrieval 2.0
- [x] sparse BM25 index
- [x] reciprocal-rank fusion
- [x] cross-encoder reranking
- [x] retrieval benchmark framework
- [ ] domain benchmark expansion and regression gate

## Enterprise runtime
- [x] Celery/Redis worker with resumable checkpoints
- [ ] PostgreSQL migrations
- [x] authenticated identity and persistent RBAC foundation
- [x] document ACL filtering before retrieval
- [x] tenant isolation in authenticated requests
- [x] idempotent ingestion and dead-letter handling
- [x] tenant-scoped audit event storage and audit API

## Intelligence
- [x] structured table/layout extraction baseline
- [x] provenance-preserving multimodal artifacts
- [x] version-aware document artifacts
- [x] semantic document diff
- [x] numeric/date/risk change classification
- [x] evidence graph baseline
- [x] claim verification baseline
- [x] contradiction detection baseline
- [x] contradiction benchmark fixtures and runner
- [ ] calculation/tool traces
- [ ] LLM claim extraction and relation extraction
- [ ] advanced OCR and visual understanding
- [ ] chart/figure semantic extraction

## Platform
- [x] OpenTelemetry-compatible tracing foundation
- [x] Prometheus request/retrieval/LLM metrics
- [ ] metrics dashboard
- [x] deterministic cost-aware model policy foundation
- [x] fail-open Redis cache abstraction
- [x] reproducible API smoke load test
- [x] prompt-injection evaluation primitives and baseline fixtures
- [x] deterministic CI evaluation regression gate
- [x] workflow engine + human approval baseline
- [x] non-destructive backup connectivity verification
- [ ] isolated database restore drill
