from langchain_core.documents import Document

from app.retrieval.bm25 import BM25Index, tokenize
from app.retrieval.fusion import reciprocal_rank_fusion


def test_tokenize_is_case_insensitive():
    assert tokenize("PostgreSQL, Redis-Queue!") == ["postgresql", "redis", "queue"]


def test_bm25_prefers_exact_term_match():
    docs = [
        Document(page_content="PostgreSQL connection pooling and migrations", metadata={"chunk_id": "a"}),
        Document(page_content="Redis worker retries and dead letter queues", metadata={"chunk_id": "b"}),
    ]
    hits = BM25Index(docs).search("PostgreSQL migrations", top_k=2)
    assert hits[0].document.metadata["chunk_id"] == "a"
    assert hits[0].score > 0


def test_rrf_combines_rankings_without_score_scale_assumptions():
    a = Document(page_content="alpha", metadata={"chunk_id": "a"})
    b = Document(page_content="beta", metadata={"chunk_id": "b"})
    fused = reciprocal_rank_fusion(
        [[(a, 0.01), (b, 0.99)], [(b, 0.01), (a, 0.99)]]
    )
    assert {doc.metadata["chunk_id"] for doc, _ in fused} == {"a", "b"}
    assert fused[0][1] == fused[1][1]
