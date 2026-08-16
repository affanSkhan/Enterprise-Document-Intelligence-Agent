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
- [ ] Celery/Redis worker with resumable checkpoints
- [ ] PostgreSQL migrations
- [x] authenticated identity and persistent RBAC foundation
- [x] document ACL filtering before retrieval
- [x] tenant isolation in authenticated requests
- [ ] idempotency and dead-letter handling
- [ ] audit events for security-sensitive actions

## Intelligence
- [ ] structured table/layout extraction
- [ ] semantic document diff
- [ ] contradiction detection
- [ ] calculation/tool traces
- [ ] evidence graph and citation verifier
- [ ] multimodal/OCR pipeline

## Platform
- [ ] OpenTelemetry traces
- [ ] metrics dashboard
- [ ] model router and cost controls
- [ ] cache layers
- [ ] load tests
- [ ] security benchmark
- [ ] CI evaluation regression
- [ ] workflow engine + human approval
