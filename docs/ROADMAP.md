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
- [ ] audit events for security-sensitive actions

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
- [ ] OpenTelemetry traces
- [x] Prometheus request/retrieval/LLM metrics
- [ ] metrics dashboard
- [ ] model router and cost controls
- [ ] cache layers
- [ ] load tests
- [x] prompt-injection evaluation primitives and baseline fixtures
- [ ] CI evaluation regression gate
- [ ] workflow engine + human approval
- [ ] disaster recovery / backup verification
