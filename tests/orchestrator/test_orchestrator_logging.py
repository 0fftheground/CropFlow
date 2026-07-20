from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from app.models import EventRecord
from app.orchestrator.core import OrchestratorResult, PlanOrchestrator


@dataclass
class FakeHandler:
    def handle(self, event_record: EventRecord) -> OrchestratorResult:
        return OrchestratorResult(farming_tasks=[object()], review_requests=[object()])


def test_plan_orchestrator_logs_event_result(caplog) -> None:
    orchestrator = PlanOrchestrator({"PlanCreated": FakeHandler()})
    event_record = EventRecord(
        id=1,
        planting_plan_id=2,
        event_type="PlanCreated",
        event_category="plan",
        event_source="api",
        payload={"source": "test"},
        occurred_at=datetime(2026, 5, 26, 10, 0, 0),
        idempotency_key="event:1",
    )

    with caplog.at_level(logging.INFO):
        result = orchestrator.handle(event_record)

    assert len(result.farming_tasks) == 1
    assert "Handling orchestrator event" in caplog.text
    assert "Orchestrator event handled" in caplog.text
    assert "farming_tasks" in caplog.text
