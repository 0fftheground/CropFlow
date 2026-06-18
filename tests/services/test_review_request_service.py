from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.core.constants import EVENT_TYPE_REVIEW_REQUEST_RESOLVED
from app.models import EventRecord, FarmingTask, OperationPlan, PlantingPlan, ReviewRequest, TaskIntent
from app.orchestrator.core import PlanOrchestrator, ReviewRequestResolvedHandler
from app.services.pest_disease_control import (
    PestDiseaseAdjustedControlResult,
    PestDiseaseAdjustedRound,
    PestDiseaseControlPlanningService,
    PestDiseaseReviewAdjustmentResult,
)
from app.services import ReviewRequestResolveInput, ReviewRequestService


@dataclass
class FakeReviewRequestRepository:
    item: ReviewRequest

    def get(self, review_request_id: int) -> ReviewRequest | None:
        return self.item if self.item.id == review_request_id else None


@dataclass
class FakeTaskIntentRepository:
    item: TaskIntent

    def get(self, task_intent_id: int) -> TaskIntent | None:
        return self.item if self.item.id == task_intent_id else None


@dataclass
class FakeFarmingTaskRepository:
    items: list[FarmingTask] = field(default_factory=list)
    next_id: int = 100

    def add(self, task: FarmingTask) -> FarmingTask:
        self.items.append(task)
        return task

    def flush(self) -> None:
        for task in self.items:
            if task.id is None:
                task.id = self.next_id
                self.next_id += 1


@dataclass
class FakeOperationPlanRepository:
    items: list[OperationPlan] = field(default_factory=list)
    next_id: int = 200

    def add(self, operation_plan: OperationPlan) -> OperationPlan:
        self.items.append(operation_plan)
        return operation_plan

    def flush(self) -> None:
        for operation_plan in self.items:
            if operation_plan.id is None:
                operation_plan.id = self.next_id
                self.next_id += 1


@dataclass
class FakeEventRecordRepository:
    items: list[EventRecord] = field(default_factory=list)
    next_id: int = 1

    def add(self, event_record: EventRecord) -> EventRecord:
        if event_record.id is None:
            event_record.id = self.next_id
            self.next_id += 1
        self.items.append(event_record)
        return event_record

    def flush(self) -> None:
        return None


@dataclass
class FakePestDiseaseControlPlanningService:
    calls: list[dict[str, object]] = field(default_factory=list)

    def adjust_theory_plan_for_review(
        self,
        *,
        planting_plan_id: int,
        control_type: str,
        theory_plan: dict[str, Any],
    ) -> PestDiseaseReviewAdjustmentResult:
        self.calls.append(
            {
                "planting_plan_id": planting_plan_id,
                "control_type": control_type,
                "theory_plan": theory_plan,
            },
        )
        return PestDiseaseReviewAdjustmentResult(
            spray_suitability_required_range=(date(2026, 6, 27), date(2026, 8, 1)),
            spray_suitability_data=[{"date": "20260701", "dy_ws": 1.0}],
            adjusted_result=PestDiseaseAdjustedControlResult(
                control_type=control_type,
                control_mode="单次防治",
                status="normal",
                rounds=[
                    PestDiseaseAdjustedRound(
                        round=1,
                        theory_window=(date(2026, 6, 30), date(2026, 7, 2)),
                        final_window=(date(2026, 7, 1), date(2026, 7, 1)),
                        targets={"二化螟": "重点防治", "稻纵卷叶螟": "兼治"},
                        suitability_dates={"standard": ["20260701"]},
                        weather_adjust_reason="理论窗口变更后重新气象调整。",
                    ),
                ],
                weather_adjust={"adjusted": True},
                raw_data={
                    "control_type": control_type,
                    "control_mode": "单次防治",
                    "status": "normal",
                    "rounds": [
                        {
                            "round": 1,
                            "theory_window": ["20260630", "20260702"],
                            "final_window": ["20260701"],
                        },
                    ],
                    "weather_adjust": {"adjusted": True},
                },
                raw_response={"mock": True},
            ),
        )


class FakePlanRepository:
    def __init__(self, planting_plan: PlantingPlan) -> None:
        self.planting_plan = planting_plan

    def get(self, planting_plan_id: int) -> PlantingPlan | None:
        return self.planting_plan if self.planting_plan.id == planting_plan_id else None


class FakeContextResolver:
    def resolve(self, planting_plan: PlantingPlan):
        return type(
            "Context",
            (),
            {
                "cultivation_system": "single",
                "cultivation_pattern": "direct",
            },
        )()


class RecordingWeatherProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[date, date]] = []

    def get_spray_suitability_weather(
        self,
        planting_plan: PlantingPlan,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, object]]:
        self.calls.append((start_date, end_date))
        return [
            {"DATE": "20260627", "wins": 1.0, "pre": 0.0, "rh": 70.0, "tAvg": 25.0},
            {"DATE": "20260801", "wins": 1.0, "pre": 0.0, "rh": 70.0, "tAvg": 25.0},
        ]


class RecordingPestDiseaseControlClient:
    def __init__(self) -> None:
        self.adjust_calls: list[dict[str, object]] = []

    def adjust_control_window(
        self,
        *,
        control_type: str,
        theory_plan: dict[str, object],
        spray_suitability_data: list[dict[str, object]],
        plant_info: dict[str, object] | None = None,
    ) -> PestDiseaseAdjustedControlResult:
        self.adjust_calls.append(
            {
                "control_type": control_type,
                "theory_plan": theory_plan,
                "spray_suitability_data": spray_suitability_data,
                "plant_info": plant_info,
            },
        )
        return PestDiseaseAdjustedControlResult(
            control_type=control_type,
            control_mode="单次防治",
            status="normal",
            rounds=[
                PestDiseaseAdjustedRound(
                    round=1,
                    theory_window=(date(2026, 6, 30), date(2026, 7, 2)),
                    final_window=(date(2026, 7, 1), date(2026, 7, 1)),
                    targets={},
                    suitability_dates={},
                    weather_adjust_reason=None,
                ),
            ],
            weather_adjust={},
            raw_data={"rounds": [{"round": 1, "final_window": ["20260701"]}]},
            raw_response={"mock": True},
        )


def make_service() -> tuple[
    ReviewRequestService,
    TaskIntent,
    ReviewRequest,
    FakeFarmingTaskRepository,
    FakeOperationPlanRepository,
    FakeEventRecordRepository,
]:
    return make_service_with_adjustment_service(None)


def make_service_with_adjustment_service(
    pest_disease_control_planning_service: FakePestDiseaseControlPlanningService | None,
) -> tuple[
    ReviewRequestService,
    TaskIntent,
    ReviewRequest,
    FakeFarmingTaskRepository,
    FakeOperationPlanRepository,
    FakeEventRecordRepository,
]:
    task_intent = TaskIntent(
        id=10,
        planting_plan_id=1,
        task_category="plant_protection",
        task_subtype="plant_protection.stem_leaf_weed_control",
        status="pending",
        trigger_type="SurveyResultRecorded",
        trigger_summary="药前调查达到防治条件。",
        suggested_action="建议执行茎叶除草",
        parent_task_id=5,
        source_execution_id=6,
        source_execution_record_id=7,
        rule_result={
            "algorithmCode": "weed_treatment_diagnosis",
            "proposedTask": {
                "title": "茎叶除草",
                "recommendedControlDate": ["2026-04-20", "2026-04-20"],
            },
            "proposedPlan": {
                "controlPlan": {
                    "prescriptions": [{"pesticide": "示例农药"}],
                    "waterAmount": "30L/亩",
                },
                "basis": "杂草密度达到阈值。",
            },
        },
        idempotency_key="task-intent:10",
    )
    review_request = ReviewRequest(
        id=20,
        planting_plan_id=1,
        review_type="weed_control_recommendation",
        status="open",
        source_entity_type="task_intent",
        source_entity_id=10,
        title="茎叶除草建议待审核",
        decision_payload={},
        idempotency_key="review-request:20",
    )
    task_intent_repo = FakeTaskIntentRepository(task_intent)
    review_repo = FakeReviewRequestRepository(review_request)
    farming_task_repo = FakeFarmingTaskRepository()
    operation_plan_repo = FakeOperationPlanRepository()
    event_repo = FakeEventRecordRepository()
    orchestrator = PlanOrchestrator(
        {
            EVENT_TYPE_REVIEW_REQUEST_RESOLVED: ReviewRequestResolvedHandler(
                task_intent_repository=task_intent_repo,
                review_request_repository=review_repo,
                farming_task_repository=farming_task_repo,
                operation_plan_repository=operation_plan_repo,
                event_record_repository=event_repo,
                pest_disease_control_planning_service=pest_disease_control_planning_service,
            ),
        },
    )
    service = ReviewRequestService(
        review_request_repository=review_repo,
        event_record_repository=event_repo,
        plan_orchestrator=orchestrator,
    )
    return service, task_intent, review_request, farming_task_repo, operation_plan_repo, event_repo


def test_review_theory_window_adjustment_fetches_weather_from_expanded_window() -> None:
    planting_plan = PlantingPlan(
        id=1,
        plan_code="PLAN-001",
        plan_name="测试计划",
        farm_id=1,
        crop_name="水稻",
        sowing_date=date(2026, 4, 10),
        metadata_payload={
            "growth_stage": {
                "tillering_date": "2026-05-20",
                "pokou_date": "2026-07-05",
                "heading_date": "2026-07-12",
            },
        },
    )
    weather_provider = RecordingWeatherProvider()
    control_client = RecordingPestDiseaseControlClient()
    service = PestDiseaseControlPlanningService(
        planting_plan_repository=FakePlanRepository(planting_plan),
        farm_repository=None,
        rice_control_window_level1_repository=None,
        stage_prediction_snapshot_repository=None,
        calendar_item_repository=None,
        operation_plan_repository=None,
        context_resolver=FakeContextResolver(),
        weather_provider=weather_provider,
        control_client=control_client,
    )

    result = service.adjust_theory_plan_for_review(
        planting_plan_id=1,
        control_type="regular",
        theory_plan={
            "rounds": [
                {
                    "round": 1,
                    "theory_window": ["20260630", "20260702"],
                    "targets": {"二化螟": "重点防治"},
                },
            ],
        },
    )

    assert weather_provider.calls == [(date(2026, 6, 27), date(2026, 8, 1))]
    assert result.spray_suitability_required_range == (date(2026, 6, 27), date(2026, 8, 1))
    assert control_client.adjust_calls[0]["spray_suitability_data"] == [
        {"date": "20260627", "dy_ws": 1.0},
        {"date": "20260801", "dy_ws": 1.0},
    ]


def test_approve_review_request_converts_task_intent_to_task_and_operation_plan() -> None:
    service, task_intent, review_request, farming_task_repo, operation_plan_repo, event_repo = make_service()

    result = service.resolve(
        20,
        ReviewRequestResolveInput(
            decision="approve",
            decision_payload={},
            decision_note="同意执行",
            resolved_by="agronomist-1",
        ),
    )

    assert review_request.status == "resolved"
    assert task_intent.status == "converted"
    assert task_intent.converted_task_id == 100
    assert farming_task_repo.items[0].task_intent_id == 10
    assert farming_task_repo.items[0].review_request_id == 20
    assert farming_task_repo.items[0].planned_start_at.date() == date(2026, 4, 20)
    assert operation_plan_repo.items[0].farming_task_id == 100
    assert operation_plan_repo.items[0].algorithm_code == "weed_treatment_diagnosis"
    assert result.farming_tasks == farming_task_repo.items
    assert [item.event_type for item in event_repo.items] == [
        "ReviewRequestResolved",
        "FarmingTaskCreated",
        "OperationPlanCreated",
    ]


def test_adjust_review_request_applies_operation_plan_overrides() -> None:
    service, task_intent, review_request, farming_task_repo, operation_plan_repo, _ = make_service()

    result = service.resolve(
        20,
        ReviewRequestResolveInput(
            decision="adjust",
            decision_payload={
                "proposedTask": {
                    "recommendedControlDate": ["2026-04-22", "2026-04-23"],
                    "executionMode": "assisted",
                },
                "proposedPlan": {
                    "operationWindow": ["2026-04-22", "2026-04-23"],
                    "controlPlan": {"waterAmount": "45L/亩"},
                    "operationArea": {"plotCodes": ["A-01"]},
                    "acceptanceCriteria": {"coverage": ">=90%"},
                },
            },
            decision_note="调整用水量和作业窗口",
            resolved_by="agronomist-1",
        ),
    )

    farming_task = farming_task_repo.items[0]
    operation_plan = operation_plan_repo.items[0]

    assert task_intent.status == "converted"
    assert review_request.decision == "adjust"
    assert farming_task.planned_start_at.date() == date(2026, 4, 22)
    assert farming_task.planned_end_at.date() == date(2026, 4, 23)
    assert farming_task.execution_mode == "assisted"
    assert operation_plan.operation_window_start.date() == date(2026, 4, 22)
    assert operation_plan.operation_window_end.date() == date(2026, 4, 23)
    assert operation_plan.parameters["basis"] == "杂草密度达到阈值。"
    assert operation_plan.parameters["controlPlan"] == {
        "prescriptions": [{"pesticide": "示例农药"}],
        "waterAmount": "45L/亩",
    }
    assert operation_plan.operation_area == {"plotCodes": ["A-01"]}
    assert operation_plan.acceptance_criteria == {"coverage": ">=90%"}
    assert operation_plan.prescription_map == operation_plan.parameters["controlPlan"]
    assert result.operation_plans == [operation_plan]


def test_adjust_review_request_syncs_task_time_to_operation_window_for_supported_control_subtype() -> None:
    service, task_intent, _, farming_task_repo, operation_plan_repo, _ = make_service()
    task_intent.task_subtype = "plant_protection.soil_sealing_weed_control"
    task_intent.rule_result = {
        "algorithmCode": "soil_treatment_diagnosis",
        "proposedTask": {
            "title": "土壤封闭除草",
            "recommendedControlDate": ["2026-04-20", "2026-04-20"],
        },
        "proposedPlan": {
            "controlPlan": {"prescriptions": [{"pesticide": "封闭药剂"}]},
            "operationAction": "苗后封闭",
        },
    }

    service.resolve(
        20,
        ReviewRequestResolveInput(
            decision="adjust",
            decision_payload={
                "proposedTask": {
                    "recommendedControlDate": ["2026-04-24", "2026-04-25"],
                },
            },
            decision_note="调整封闭除草时间",
            resolved_by="agronomist-1",
        ),
    )

    assert farming_task_repo.items[0].planned_start_at.date() == date(2026, 4, 24)
    assert farming_task_repo.items[0].planned_end_at.date() == date(2026, 4, 25)
    assert operation_plan_repo.items[0].operation_window_start.date() == date(2026, 4, 24)
    assert operation_plan_repo.items[0].operation_window_end.date() == date(2026, 4, 25)
    assert operation_plan_repo.items[0].parameters["operationWindow"] == ["2026-04-24", "2026-04-25"]


def test_adjust_review_request_syncs_operation_window_to_task_time_for_supported_control_subtype() -> None:
    service, task_intent, _, farming_task_repo, operation_plan_repo, _ = make_service()

    service.resolve(
        20,
        ReviewRequestResolveInput(
            decision="adjust",
            decision_payload={
                "proposedPlan": {
                    "operationWindow": ["2026-04-26", "2026-04-27"],
                },
            },
            decision_note="调整茎叶除草窗口",
            resolved_by="agronomist-1",
        ),
    )

    assert farming_task_repo.items[0].planned_start_at.date() == date(2026, 4, 26)
    assert farming_task_repo.items[0].planned_end_at.date() == date(2026, 4, 27)
    assert operation_plan_repo.items[0].operation_window_start.date() == date(2026, 4, 26)
    assert operation_plan_repo.items[0].operation_window_end.date() == date(2026, 4, 27)
    assert operation_plan_repo.items[0].parameters["operationWindow"] == ["2026-04-26", "2026-04-27"]


def test_adjust_disease_pest_review_updates_specific_round_fields_only() -> None:
    adjustment_service = FakePestDiseaseControlPlanningService()
    service, task_intent, review_request, farming_task_repo, operation_plan_repo, _ = make_service_with_adjustment_service(
        adjustment_service,
    )
    task_intent.task_subtype = "plant_protection.disease_pest_control"
    task_intent.rule_result = {
        "algorithmCode": "pest_disease.generate_theory_control_plan",
        "proposedTask": {
            "title": "病虫常规防治",
            "recommendedControlDate": ["2026-06-29", "2026-06-29"],
        },
        "proposedPlan": {
            "planType": "plant_protection_control",
            "controlType": "regular",
            "operationWindow": ["2026-06-29", "2026-06-29"],
            "controlPlan": {
                "rounds": [
                    {
                        "round": 1,
                        "targets": {"二化螟": "防治"},
                        "prescription": {"product": "原方案药剂", "dose": "100ml/亩"},
                    },
                    {
                        "round": 2,
                        "targets": {"纹枯病": "防治"},
                        "prescription": {"product": "第二轮药剂", "dose": "80ml/亩"},
                    },
                ],
            },
            "theoryPlan": {
                "rounds": [
                    {
                        "round": 1,
                        "targets": {"二化螟": "防治"},
                        "theory_window": ["20260629", "20260701"],
                    },
                    {
                        "round": 2,
                        "targets": {"纹枯病": "防治"},
                        "theory_window": ["20260708", "20260710"],
                    },
                ],
            },
        },
    }

    service.resolve(
        20,
        ReviewRequestResolveInput(
            decision="adjust",
            decision_payload={
                "proposedPlan": {
                    "controlPlan": {
                        "rounds": [
                            {
                                "round": 1,
                                "prescription": {"product": "人工调整药剂", "dose": "120ml/亩"},
                            },
                        ],
                    },
                    "theoryPlan": {
                        "rounds": [
                            {
                                "round": 1,
                                "targets": {"二化螟": "重点防治", "稻纵卷叶螟": "兼治"},
                                "theory_window": ["20260630", "20260702"],
                            },
                        ],
                    },
                },
            },
            decision_note="调整第一轮防治方案",
            resolved_by="agronomist-1",
        ),
    )

    proposed_plan = operation_plan_repo.items[0].parameters

    assert adjustment_service.calls == [
        {
            "planting_plan_id": 1,
            "control_type": "regular",
            "theory_plan": {
                "rounds": [
                    {
                        "round": 1,
                        "targets": {"二化螟": "重点防治", "稻纵卷叶螟": "兼治"},
                        "theory_window": ["20260630", "20260702"],
                    },
                    {
                        "round": 2,
                        "targets": {"纹枯病": "防治"},
                        "theory_window": ["20260708", "20260710"],
                    },
                ],
            },
        },
    ]
    assert farming_task_repo.items[0].planned_start_at.date() == date(2026, 7, 1)
    assert farming_task_repo.items[0].planned_end_at.date() == date(2026, 7, 1)
    assert proposed_plan["operationWindow"] == ["2026-07-01", "2026-07-01"]
    assert proposed_plan["rounds"] == [
        {
            "round": 1,
            "theoryWindow": ["2026-06-30", "2026-07-02"],
            "targets": {"二化螟": "重点防治", "稻纵卷叶螟": "兼治"},
            "suitabilityDates": {"standard": ["20260701"]},
            "weatherAdjustReason": "理论窗口变更后重新气象调整。",
            "finalWindow": ["2026-07-01", "2026-07-01"],
        },
    ]
    assert proposed_plan["spraySuitabilityRequiredRange"] == ["2026-06-27", "2026-08-01"]
    assert proposed_plan["spraySuitabilityData"] == [{"date": "20260701", "dy_ws": 1.0}]
    assert proposed_plan["adjustedPlan"]["rounds"][0]["final_window"] == ["20260701"]
    assert proposed_plan["controlPlan"]["rounds"] == [
        {
            "round": 1,
            "targets": {"二化螟": "防治"},
            "prescription": {"product": "人工调整药剂", "dose": "120ml/亩"},
        },
        {
            "round": 2,
            "targets": {"纹枯病": "防治"},
            "prescription": {"product": "第二轮药剂", "dose": "80ml/亩"},
        },
    ]
    assert proposed_plan["theoryPlan"]["rounds"] == [
        {
            "round": 1,
            "targets": {"二化螟": "重点防治", "稻纵卷叶螟": "兼治"},
            "theory_window": ["20260630", "20260702"],
        },
        {
            "round": 2,
            "targets": {"纹枯病": "防治"},
            "theory_window": ["20260708", "20260710"],
        },
    ]


def test_adjust_review_request_rejects_new_round_override() -> None:
    service, task_intent, review_request, farming_task_repo, operation_plan_repo, _ = make_service()
    task_intent.rule_result["proposedPlan"]["controlPlan"] = {
        "rounds": [{"round": 1, "prescription": {"product": "原方案药剂"}}],
    }

    try:
        service.resolve(
            20,
            ReviewRequestResolveInput(
                decision="adjust",
                decision_payload={
                    "proposedPlan": {
                        "controlPlan": {
                            "rounds": [{"round": 2, "prescription": {"product": "新增轮次药剂"}}],
                        },
                    },
                },
                decision_note="尝试新增轮次",
                resolved_by="agronomist-1",
            ),
        )
    except ValueError as exc:
        assert str(exc) == "Cannot adjust round 2; existing round does not exist."
    else:
        raise AssertionError("Expected missing round override to fail.")

    assert review_request.status == "resolved"
    assert farming_task_repo.items == []
    assert operation_plan_repo.items == []


def test_no_action_review_request_marks_task_intent_no_action() -> None:
    service, task_intent, review_request, farming_task_repo, operation_plan_repo, _ = make_service()

    result = service.resolve(
        20,
        ReviewRequestResolveInput(
            decision="no_action",
            decision_payload={},
            decision_note="现场确认无需处理",
            resolved_by="agronomist-1",
        ),
    )

    assert review_request.status == "resolved"
    assert task_intent.status == "no_action"
    assert task_intent.no_action_reason == "现场确认无需处理"
    assert farming_task_repo.items == []
    assert operation_plan_repo.items == []
    assert result.task_intents == [task_intent]
