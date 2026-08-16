from app.evaluation.retrieval import ndcg_at_k, recall_at_k, reciprocal_rank


def test_recall_at_k():
    assert recall_at_k(["a", "b", "c"], ["b", "c"], 2) == 0.5


def test_reciprocal_rank():
    assert reciprocal_rank(["x", "b", "c"], ["b"]) == 0.5
    assert reciprocal_rank(["x", "y"], ["b"]) == 0.0


def test_ndcg_at_k_rewards_relevant_early():
    early = ndcg_at_k(["a", "x", "y"], ["a"], 3)
    late = ndcg_at_k(["x", "y", "a"], ["a"], 3)
    assert early == 1.0
    assert early > late
