from datetime import datetime, timezone

import mongomock

from app.db.mongodb import MongoDB
from app.services.mongo_persistence import MongoPersistence


def _repository() -> tuple[MongoPersistence, MongoDB]:
    client = mongomock.MongoClient()
    mongo = MongoDB("mongodb://test", "test", client=client)
    assert mongo.ensure_indexes()
    return MongoPersistence(mongo), mongo


def test_mongodb_indexes_are_idempotent():
    _, mongo = _repository()
    assert mongo.ensure_indexes()
    assert "conversation_id_unique" in mongo.database["conversations"].index_information()
    assert "run_id_unique" in mongo.database["agent_runs"].index_information()


def test_conversation_and_message_persistence():
    repository, mongo = _repository()
    conversation_id = repository.create_or_get_conversation("tenant-a", "user-a", title="Project chat")
    assert conversation_id

    first = repository.append_message(
        "tenant-a",
        "user-a",
        conversation_id,
        "user",
        "Compare these documents.",
    )
    second = repository.append_message(
        "tenant-a",
        "user-a",
        conversation_id,
        "assistant",
        "Here is the comparison.",
        citations=[{"metadata": {"filename": "a.pdf"}}],
    )
    assert first and second

    # Replaying the same message ID must not increment message_count twice.
    repository.append_message(
        "tenant-a",
        "user-a",
        conversation_id,
        "assistant",
        "Here is the comparison.",
        message_id=second,
    )

    conversation = repository.get_conversation("tenant-a", "user-a", conversation_id)
    assert conversation is not None
    assert conversation["message_count"] == 2
    assert [m["role"] for m in conversation["messages"]] == ["user", "assistant"]
    assert conversation["messages"][1]["citations"][0]["metadata"]["filename"] == "a.pdf"

    mongo.close()


def test_agent_run_supports_variable_nested_steps_and_is_idempotent():
    repository, mongo = _repository()
    run_id = repository.start_agent_run(
        "tenant-a",
        "user-a",
        "document_comparison",
        "compare",
        input_data={"doc_id_1": "a", "options": {"strategy": "hybrid"}},
    )
    assert run_id

    assert repository.append_step(
        run_id,
        "tenant-a",
        "retrieval",
        tool="hybrid_search",
        input_data={"filters": {"doc_id": "a"}},
        output={"chunks": [{"score": 0.91, "metadata": {"page": 3}}]},
        metadata={"reranked": True},
        started_at=datetime.now(timezone.utc),
    )
    assert repository.append_step(
        run_id,
        "tenant-a",
        "tool_call",
        tool="bom_parser",
        input_data={"mode": "strict"},
        output={"items": [{"part_number": "P-1", "quantity": 4}]},
    )
    assert repository.complete_agent_run(
        run_id,
        "tenant-a",
        status="completed",
        final_output={"answer": "done", "structured": {"confidence": 0.9}},
        model="test-model",
        token_usage={"input": 20, "output": 12, "total": 32},
        latency_ms=123.4,
    )

    result = repository.get_agent_run(run_id, "tenant-a", "user-a")
    assert result is not None
    assert result["status"] == "completed"
    assert result["token_usage"]["total"] == 32
    assert len(result["steps"]) == 2
    assert result["steps"][1]["type"] == "tool_call"

    # The same run ID is safe to initialize again and does not overwrite the run.
    repository.start_agent_run(
        "tenant-a",
        "user-a",
        "document_comparison",
        "compare",
        run_id=run_id,
        input_data={"should_not_replace": True},
    )
    result_after_retry = repository.get_agent_run(run_id, "tenant-a", "user-a")
    assert result_after_retry["status"] == "completed"
    assert len(result_after_retry["steps"]) == 2

    mongo.close()


def test_tenant_and_user_isolation():
    repository, mongo = _repository()
    conversation_id = repository.create_or_get_conversation("tenant-a", "user-a")
    repository.append_message("tenant-a", "user-a", conversation_id, "user", "secret")

    assert repository.get_conversation("tenant-a", "user-a", conversation_id) is not None
    assert repository.get_conversation("tenant-a", "user-b", conversation_id) is None
    assert repository.get_conversation("tenant-b", "user-a", conversation_id) is None

    run_id = repository.start_agent_run("tenant-a", "user-a", "chat", "chat")
    assert repository.get_agent_run(run_id, "tenant-a", "user-a") is not None
    assert repository.get_agent_run(run_id, "tenant-b", "user-a") is None
    assert repository.get_agent_run(run_id, "tenant-a", "user-b") is None

    mongo.close()


def test_graceful_disabled_repository():
    repository = MongoPersistence(mongo=None)
    assert repository.enabled is False
    assert repository.create_or_get_conversation("tenant", "user") is None
    assert repository.list_conversations("tenant", "user") == []
