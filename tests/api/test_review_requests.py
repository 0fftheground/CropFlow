from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from fastapi.testclient import TestClient

from app.api.deps import get_review_request_query_service, get_review_request_service
from app.db.session import get_db
from app.main import app
from app.models import EventRecord, ExecutionRecord, FarmingTask, OperationPlan, ReviewRequest, TaskIntent, User
from app.services import ReviewRequestDetail, ReviewRequestQueryService, ReviewRequestResolveInput, ReviewRequestResolveResult


@dataclass
class FakeReviewRequestService:
    last_payload: ReviewRequestResolveInput | None = None

    def resolve(self, review_request_id: int, payload: ReviewRequestResolveInput) -> ReviewRequestResolveResult:
        self.last_payload = payload
        if review_request_id == 404:
            raise LookupError("missing")
        if payload.decision == "invalid":
            raise ValueError("bad decision")
        return ReviewRequestResolveResult(
            review_request=ReviewRequest(
                id=review_request_id,
                planting_plan_id=1,
                review_type="weed_control_recommendation",
                status="resolved",
                source_entity_type="task_intent",
                source_entity_id=10,
                title="待审核",
                decision=payload.decision,
                decision_payload={},
                resolved_by=payload.resolved_by,
                resolved_at=datetime(2026, 5, 22, 11, 0, 0),
                idempotency_key=f"review:{review_request_id}",
            ),
            event_record=EventRecord(
                id=30,
                event_type="ReviewRequestResolved",
                event_category="review",
                event_source="api",
                payload={},
                occurred_at=datetime(2026, 5, 22, 11, 0, 0),
                idempotency_key="event:30",
            ),
            task_intents=[
                TaskIntent(
                    id=10,
                    planting_plan_id=1,
                    task_category="plant_protection",
                    task_subtype="plant_protection.stem_leaf_weed_control",
                    trigger_type="SurveyResultRecorded",
                    rule_result={},
                    idempotency_key="task-intent:10",
                ),
            ],
            farming_tasks=[
                FarmingTask(
                    id=40,
                    planting_plan_id=1,
                    task_category="plant_protection",
                    task_subtype="plant_protection.stem_leaf_weed_control",
                    title="茎叶除草",
                    idempotency_key="task:40",
                ),
            ],
            operation_plans=[
                OperationPlan(
                    id=50,
                    planting_plan_id=1,
                    farming_task_id=40,
                    plan_type="plant_protection.stem_leaf_weed_control",
                    idempotency_key="operation-plan:50",
                ),
            ],
        )


@dataclass
class FakeReviewRequestQueryService:
    def get_detail(self, review_request_id: int) -> ReviewRequestDetail:
        if review_request_id == 404:
            raise LookupError("missing")
        review_request = ReviewRequest(
            id=review_request_id,
            planting_plan_id=1,
            review_type="weed_control_recommendation",
            status="open",
            source_entity_type="task_intent",
            source_entity_id=10,
            title="待审核",
            decision_payload={"contextRefs": {"sourceExecutionRecordId": 99}},
            idempotency_key=f"review:{review_request_id}",
        )
        return ReviewRequestDetail(
            review_request=review_request,
            source_task_intent=TaskIntent(
                id=10,
                planting_plan_id=1,
                task_category="plant_protection",
                task_subtype="plant_protection.stem_leaf_weed_control",
                status="pending",
                trigger_type="SurveyResultRecorded",
                trigger_summary="药前调查触发",
                rule_result={"branchType": "control"},
                source_execution_record_id=99,
                idempotency_key="intent:10",
            ),
            linked_farming_task=FarmingTask(
                id=40,
                planting_plan_id=1,
                task_category="plant_protection",
                task_subtype="plant_protection.stem_leaf_weed_control",
                title="茎叶除草",
                status="pending",
                execution_mode="manual",
                idempotency_key="task:40",
            ),
            operation_plans=[
                OperationPlan(
                    id=50,
                    planting_plan_id=1,
                    farming_task_id=40,
                    plan_type="plant_protection.stem_leaf_weed_control",
                    status="active",
                    version=1,
                    execution_mode="manual",
                    parameters={"controlTarget": ["稗草"]},
                    idempotency_key="operation-plan:50",
                ),
            ],
            source_execution_record=ExecutionRecord(
                id=99,
                planting_plan_id=1,
                execution_id=88,
                record_type="survey_result",
                record_time=datetime(2026, 5, 22, 9, 0, 0),
                result_payload={"survey_date": "20260418"},
                attachments=[],
            ),
            event_records=[
                EventRecord(
                    id=60,
                    planting_plan_id=1,
                    event_type="ReviewRequestCreated",
                    event_category="runtime",
                    event_source="orchestrator",
                    source_record_id=str(review_request_id),
                    payload={"reviewRequestId": review_request_id},
                    occurred_at=datetime(2026, 5, 22, 10, 0, 0),
                    processing_status="processed",
                    idempotency_key="event:60",
                ),
            ],
        )


@dataclass
class FakeDiseasePestReviewRequestQueryService:
    def get_detail(self, review_request_id: int) -> ReviewRequestDetail:
        review_request = ReviewRequest(
            id=review_request_id,
            planting_plan_id=1,
            review_type="disease_pest_control_recommendation",
            status="open",
            source_entity_type="task_intent",
            source_entity_id=11,
            title="病虫害防治待审核",
            idempotency_key=f"review:{review_request_id}",
        )
        return ReviewRequestDetail(
            review_request=review_request,
            source_task_intent=TaskIntent(
                id=11,
                planting_plan_id=1,
                task_category="plant_protection",
                task_subtype="plant_protection.disease_pest_control",
                status="pending",
                trigger_type="SurveyResultRecorded",
                trigger_summary="病虫害调查触发",
                rule_result={
                    "proposedPlan": {
                        "targets": {"二化螟": "防治"},
                        "theoryPlan": {
                            "rounds": [
                                {
                                    "round": 1,
                                    "targets": {"二化螟": "防治"},
                                    "theory_window": ["20260629", "20260701"],
                                },
                            ],
                        },
                    },
                },
                idempotency_key="intent:11",
            ),
            linked_farming_task=None,
            operation_plans=[],
            source_execution_record=None,
            event_records=[],
        )


class DummySession:
    def get(self, model, key):
        if model is User and key == "agronomist-1":
            return User(id="agronomist-1", username="agronomist-name", display_name="测试员")
        return None

    def execute(self, statement):
        values = set(statement.compile().params.values())

        class DummyResult:
            @staticmethod
            def scalar_one_or_none():
                if "agronomist-name" in values or "测试员" in values:
                    return User(id="agronomist-1", username="agronomist-name", display_name="测试员")
                return None

        return DummyResult()

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None


def test_resolve_review_request_route_returns_created_task_and_plan_ids() -> None:
    fake_service = FakeReviewRequestService()
    app.dependency_overrides[get_review_request_service] = lambda: fake_service
    app.dependency_overrides[get_db] = lambda: DummySession()
    client = TestClient(app)

    response = client.post(
        "/api/review-requests/20/resolve",
        json={
            "decision": "approve",
            "decision_payload": {},
            "decision_note": "同意执行",
            "resolved_by": "agronomist-1",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "review_request_id": 20,
        "event_record_id": 30,
        "decision": "approve",
        "status": "resolved",
        "task_intent_ids": [10],
        "farming_task_ids": [40],
        "operation_plan_ids": [50],
        "resolved_at": "2026-05-22T11:00:00",
    }
    assert fake_service.last_payload is not None
    assert fake_service.last_payload.resolved_by == "agronomist-1"

    app.dependency_overrides.clear()


def test_resolve_review_request_route_accepts_display_name_and_normalizes_to_user_id() -> None:
    fake_service = FakeReviewRequestService()
    app.dependency_overrides[get_review_request_service] = lambda: fake_service
    app.dependency_overrides[get_db] = lambda: DummySession()
    client = TestClient(app)

    response = client.post(
        "/api/review-requests/20/resolve",
        json={
            "decision": "approve",
            "resolved_by": "测试员",
        },
    )

    assert response.status_code == 200
    assert fake_service.last_payload is not None
    assert fake_service.last_payload.resolved_by == "agronomist-1"

    app.dependency_overrides.clear()


def test_resolve_review_request_route_maps_errors() -> None:
    app.dependency_overrides[get_review_request_service] = lambda: FakeReviewRequestService()
    app.dependency_overrides[get_db] = lambda: DummySession()
    client = TestClient(app)

    not_found_response = client.post("/api/review-requests/404/resolve", json={"decision": "approve"})
    bad_request_response = client.post("/api/review-requests/20/resolve", json={"decision": "invalid"})
    missing_user_response = client.post(
        "/api/review-requests/20/resolve",
        json={"decision": "approve", "resolved_by": "missing-user"},
    )

    assert not_found_response.status_code == 404
    assert bad_request_response.status_code == 400
    assert missing_user_response.status_code == 400

    app.dependency_overrides.clear()


def test_get_review_request_detail_route_returns_context() -> None:
    app.dependency_overrides[get_review_request_query_service] = lambda: FakeReviewRequestQueryService()
    client = TestClient(app)

    response = client.get("/api/review-requests/20")

    assert response.status_code == 200
    body = response.json()
    assert body["review_request_id"] == 20
    assert body["source_task_intent"]["id"] == 10
    assert body["linked_farming_task"]["id"] == 40
    assert body["operation_plans"][0]["id"] == 50
    assert body["source_execution_record"]["id"] == 99
    assert body["event_records"][0]["event_type"] == "ReviewRequestCreated"

    app.dependency_overrides.clear()


def test_get_review_request_detail_route_adds_available_targets_for_disease_pest_review() -> None:
    app.dependency_overrides[get_review_request_query_service] = lambda: FakeDiseasePestReviewRequestQueryService()
    client = TestClient(app)

    response = client.get("/api/review-requests/21")

    assert response.status_code == 200
    body = response.json()
    assert body["source_task_intent"]["task_subtype"] == "plant_protection.disease_pest_control"
    assert body["source_task_intent"]["rule_result"]["proposedPlan"]["targets"] == {"二化螟": "防治"}
    assert body["source_task_intent"]["rule_result"]["reviewContext"]["availableTargets"] == [
        "二化螟",
        "稻纵卷叶螟",
        "稻飞虱",
        "稻瘟病",
        "纹枯病",
    ]

    app.dependency_overrides.clear()
