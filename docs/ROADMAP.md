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
- [ ] cross-encoder reranking
- [ ] retrieval benchmark and regression gate

## Enterprise runtime
- [ ] Celery/Redis worker with resumable checkpoints
- [ ] PostgreSQL migrations
- [ ] authenticated identity and persistent RBAC
- [ ] document ACL filtering before retrieval
- [ ] idempotency and dead-letter handling

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
