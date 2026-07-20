from __future__ import annotations

from fastapi.testclient import TestClient

from app.agent_runtime.contracts import ModelTurnResult, ToolCall
from app.agent_runtime.ontology import CropFlowOntology
from app.agent_runtime.runtime import AgentRuntime
from app.api.deps import get_agent_runtime
from app.db.session import get_db
from app.main import app
from tests.agent_runtime.fakes import (
    DummyDb,
    FakeActionExecutor,
    FakeContextBuilder,
    MemoryRepository,
    SequenceProvider,
)


client = TestClient(app)


def make_runtime(*, role: str, turns: list[ModelTurnResult]):
    repository = MemoryRepository(role=role)
    ontology = CropFlowOntology()
    context_builder = FakeContextBuilder(repository, ontology)
    executor = FakeActionExecutor(context_builder, ontology)
    provider = SequenceProvider(turns)
    return (
        AgentRuntime(
            repository=repository,
            context_builder=context_builder,
            action_executor=executor,
            model_provider=provider,
            max_iterations=5,
        ),
        repository,
        executor,
    )


def test_create_agent_run_and_replay_persisted_events() -> None:
    runtime, _, _ = make_runtime(
        role="observer",
        turns=[
            ModelTurnResult(
                tool_calls=(ToolCall(call_id="call-view-api", name="view_plan_context", arguments={}),),
                finish_reason="tool_calls",
            ),
            ModelTurnResult(text="计划上下文读取完成"),
        ],
    )
    db = DummyDb()
    app.dependency_overrides[get_agent_runtime] = lambda: runtime
    app.dependency_overrides[get_db] = lambda: db
    try:
        response = client.post(
            "/api/agent/runs",
            json={
                "user_id": "user-1",
                "planting_plan_id": 1,
                "message": "查看当前计划",
                "session_id": "session-api",
                "role": "observer",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "completed"
        assert body["pending_approvals"] == []
        assert db.commits > 2

        events = client.get(body["events_url"])
        assert events.status_code == 200
        assert events.headers["content-type"].startswith("text/event-stream")
        assert "event: tool_execution_completed" in events.text
        assert "event: run_completed" in events.text
    finally:
        app.dependency_overrides.clear()


def test_agent_side_effect_requires_api_approval_before_execution() -> None:
    runtime, _, executor = make_runtime(
        role="operator",
        turns=[
            ModelTurnResult(
                tool_calls=(
                    ToolCall(
                        call_id="call-complete-api",
                        name="complete_farming_task",
                        arguments={"task_id": 10, "operation_date": "2026-07-18", "result_payload": {}},
                    ),
                ),
                finish_reason="tool_calls",
            ),
            ModelTurnResult(text="任务已完成"),
        ],
    )
    db = DummyDb()
    app.dependency_overrides[get_agent_runtime] = lambda: runtime
    app.dependency_overrides[get_db] = lambda: db
    try:
        created = client.post(
            "/api/agent/runs",
            json={
                "user_id": "user-1",
                "planting_plan_id": 1,
                "message": "完成任务 10",
                "session_id": "session-approval-api",
                "role": "operator",
            },
        )
        assert created.status_code == 200
        run = created.json()
        assert run["status"] == "waiting_approval"
        assert executor.executed == []

        approval_id = run["pending_approvals"][0]["approval_id"]
        decided = client.post(
            f"/api/agent/approvals/{approval_id}/decide",
            json={"decision": "approved", "decided_by": "user-1", "decision_note": "确认"},
        )
        assert decided.status_code == 200
        assert decided.json()["status"] == "completed"
        assert executor.executed == ["complete_farming_task"]
    finally:
        app.dependency_overrides.clear()


def test_stream_agent_run_emits_sse() -> None:
    runtime, _, _ = make_runtime(
        role="observer",
        turns=[
            ModelTurnResult(
                tool_calls=(ToolCall(call_id="call-view-stream", name="view_plan_context", arguments={}),),
                finish_reason="tool_calls",
            ),
            ModelTurnResult(text="流式运行完成"),
        ],
    )
    db = DummyDb()
    app.dependency_overrides[get_agent_runtime] = lambda: runtime
    app.dependency_overrides[get_db] = lambda: db
    try:
        response = client.post(
            "/api/agent/runs/stream",
            json={"user_id": "user-1", "planting_plan_id": 1, "message": "查看计划", "role": "observer"},
        )
        assert response.status_code == 200
        assert response.text.startswith("retry: 3000")
        assert "event: run_started" in response.text
        assert "event: run_completed" in response.text
    finally:
        app.dependency_overrides.clear()
