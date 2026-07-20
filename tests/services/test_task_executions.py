from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

import pytest

from app.models import CalendarItem, EventRecord, Execution, ExecutionRecord, FarmingTask, OperationPlan
from app.orchestrator import build_plan_orchestrator
from app.services import (
    MockWeatherProvider,
    MockWeedDiagnosisClient,
    PlantProtectionPlanContextResolver,
    SurveyDateRecommendationService,
    TaskExecutionCompleteInput,
    TaskExecutionRecordUpdateInput,
    TaskExecutionService,
)
from tests.services.test_survey_results import (
    FakeCalendarItemRepository,
    FakeCodeDictRepository,
    FakeEventRecordRepository,
    FakeFarmingTaskRepository,
    FakeOperationPlanRepository,
    FakePlantingPlanRepository,
    FakeReviewRequestRepository,
    FakeRiceVarietyRepository,
    FakeTaskIntentRepository,
    make_pre_treatment_payload,
)
from tests.services.test_calendar_tasks import make_code_dicts, make_plan, make_variety


@dataclass
class FakeExecutionRepository:
    items: list[Execution] = field(default_factory=list)
    next_id: int = 1

    def add(self, execution: Execution) -> Execution:
        self.items.append(execution)
        return execution

    def flush(self) -> None:
        for execution in self.items:
            if execution.id is None:
                execution.id = self.next_id
                self.next_id += 1

    def list_by_task(self, farming_task_id: int) -> list[Execution]:
        return [item for item in self.items if item.farming_task_id == farming_task_id]

    def get(self, execution_id: int) -> Execution | None:
        return next((item for item in self.items if item.id == execution_id), None)


@dataclass
class FakeExecutionRecordRepository:
    items: list[ExecutionRecord] = field(default_factory=list)
    next_id: int = 1

    def add(self, execution_record: ExecutionRecord) -> ExecutionRecord:
        self.items.append(execution_record)
        return execution_record

    def flush(self) -> None:
        for execution_record in self.items:
            if execution_record.id is None:
                execution_record.id = self.next_id
                self.next_id += 1

    def list_by_task(self, farming_task_id: int) -> list[ExecutionRecord]:
        return sorted(
            self.items,
            key=lambda item: (item.record_time, item.id or 0),
            reverse=True,
        )


def test_complete_stem_leaf_weed_task_schedules_post_treatment_surveys() -> None:
    plan_repo = FakePlantingPlanRepository(make_plan())
    calendar_repo = FakeCalendarItemRepository()
    event_repo = FakeEventRecordRepository()
    task_intent_repo = FakeTaskIntentRepository()
    review_repo = FakeReviewRequestRepository()
    operation_plan_repo = FakeOperationPlanRepository()
    weather_provider = MockWeatherProvider()
    diagnosis_client = MockWeedDiagnosisClient()
    code_repo = FakeCodeDictRepository(make_code_dicts())
    variety_repo = FakeRiceVarietyRepository(make_variety())
    survey_date_service = SurveyDateRecommendationService(
        planting_plan_repository=plan_repo,
        farm_repository=None,
        rice_variety_repository=variety_repo,
        code_dict_repository=code_repo,
        rice_control_window_level1_repository=None,
        calendar_item_repository=calendar_repo,
        event_record_repository=event_repo,
        weather_provider=weather_provider,
        diagnosis_client=diagnosis_client,
    )
    farming_task = FarmingTask(
        id=10,
        planting_plan_id=1,
        task_category="plant_protection",
        task_subtype="plant_protection.stem_leaf_weed_control",
        title="茎叶除草",
        execution_mode="manual",
        idempotency_key="task:10",
    )
    farming_task_repo = FakeFarmingTaskRepository({10: farming_task})
    operation_plan_repo = FakeOperationPlanRepository(
        [
            OperationPlan(
                id=20,
                planting_plan_id=1,
                farming_task_id=10,
                plan_type="plant_protection_control",
                status="active",
                version=1,
                execution_mode="manual",
                idempotency_key="operation-plan:20",
            )
        ]
    )
    plan_orchestrator = build_plan_orchestrator(
        planting_plan_repository=plan_repo,
        calendar_item_repository=calendar_repo,
        farming_task_repository=farming_task_repo,
        event_record_repository=event_repo,
        task_intent_repository=task_intent_repo,
        review_request_repository=review_repo,
        operation_plan_repository=operation_plan_repo,
        stage_management_service=object(),
        survey_date_recommendation_service=survey_date_service,
        weather_provider=weather_provider,
        diagnosis_client=diagnosis_client,
        context_resolver=PlantProtectionPlanContextResolver(code_repo, variety_repo),
        pest_disease_control_planning_service=object(),
    )
    service = TaskExecutionService(
        farming_task_repository=farming_task_repo,
        operation_plan_repository=operation_plan_repo,
        execution_repository=FakeExecutionRepository(),
        execution_record_repository=FakeExecutionRecordRepository(),
        event_record_repository=event_repo,
        plan_orchestrator=plan_orchestrator,
    )

    result = service.complete_task(
        10,
        TaskExecutionCompleteInput(
            operation_date=date(2026, 4, 20),
            result_payload={"survey_data_before_treatment": make_pre_treatment_payload()},
        ),
    )

    assert result.execution_record.record_type == "operation_result"
    assert farming_task.status == "completed"
    assert result.execution.operation_plan_id == 20
    assert [item.task_subtype for item in result.calendar_items] == [
        "plant_protection.rice_safety_survey",
        "plant_protection.control_effect_survey",
    ]
    assert [item.suggested_start_date for item in result.calendar_items] == [
        date(2026, 4, 23),
        date(2026, 4, 27),
    ]
    assert event_repo.items[0].event_type == "ExecutionCompleted"
    assert event_repo.items[-1].event_type == "CalendarItemUpdated"


def test_update_latest_execution_record_updates_latest_record_and_creates_audit_event() -> None:
    plan_repo = FakePlantingPlanRepository(make_plan())
    event_repo = FakeEventRecordRepository()
    farming_task = FarmingTask(
        id=55,
        planting_plan_id=1,
        task_category="plant_protection",
        task_subtype="plant_protection.soil_sealing_weed_control",
        title="土壤封闭除草",
        status="completed",
        execution_mode="manual",
        idempotency_key="task:55",
    )
    farming_task_repo = FakeFarmingTaskRepository({55: farming_task})
    execution = Execution(
        id=47,
        planting_plan_id=1,
        farming_task_id=55,
        status="completed",
        completed_at=datetime(2026, 5, 11, 9, 0, 0),
    )
    plan_orchestrator = build_plan_orchestrator(
        planting_plan_repository=plan_repo,
        calendar_item_repository=FakeCalendarItemRepository(),
        farming_task_repository=farming_task_repo,
        event_record_repository=event_repo,
        task_intent_repository=FakeTaskIntentRepository(),
        review_request_repository=FakeReviewRequestRepository(),
        operation_plan_repository=FakeOperationPlanRepository(),
        stage_management_service=object(),
        survey_date_recommendation_service=object(),
        weather_provider=MockWeatherProvider(),
        diagnosis_client=MockWeedDiagnosisClient(),
        context_resolver=PlantProtectionPlanContextResolver(FakeCodeDictRepository(make_code_dicts()), FakeRiceVarietyRepository(make_variety())),
        pest_disease_control_planning_service=object(),
    )
    service = TaskExecutionService(
        farming_task_repository=farming_task_repo,
        operation_plan_repository=FakeOperationPlanRepository(),
        execution_repository=FakeExecutionRepository([execution]),
        execution_record_repository=FakeExecutionRecordRepository(
            [
                ExecutionRecord(
                    id=52,
                    planting_plan_id=1,
                    execution_id=47,
                    record_type="operation_result",
                    record_time=datetime(2026, 5, 11, 9, 0, 0),
                    actual_start_at=datetime(2026, 5, 11, 8, 0, 0),
                    actual_end_at=datetime(2026, 5, 11, 9, 0, 0),
                    actual_area=Decimal("5.5000"),
                    actual_amount=Decimal("12.0000"),
                    amount_unit="kg",
                    result_payload={"note": "old"},
                    attachments=[],
                )
            ]
        ),
        event_record_repository=FakeEventRecordRepository(
            [
                EventRecord(
                    id=60,
                    planting_plan_id=1,
                    event_type="ExecutionCompleted",
                    event_category="execution",
                    event_source="api",
                    source_record_id="52",
                    payload={
                        "taskId": 55,
                        "executionId": 47,
                        "executionRecordId": 52,
                        "operationDate": "2026-05-11",
                    },
                    occurred_at=datetime(2026, 5, 11, 9, 0, 0),
                    processing_status="processed",
                    idempotency_key="execution-completed:52",
                )
            ]
        ),
        plan_orchestrator=plan_orchestrator,
    )

    result = service.update_latest_execution_record(
        55,
        TaskExecutionRecordUpdateInput(
            operation_date=date(2026, 5, 12),
            actual_end_at=datetime(2026, 5, 11, 9, 30, 0),
            actual_amount=Decimal("10.5000"),
            result_payload={"note": "corrected"},
        ),
    )

    execution_completed_event = service.event_record_repository.items[0]
    assert result.execution_record.actual_end_at == datetime(2026, 5, 11, 9, 30, 0)
    assert result.execution_record.actual_amount == Decimal("10.5000")
    assert result.execution_record.result_payload == {"note": "corrected"}
    assert result.operation_date == date(2026, 5, 12)
    assert result.execution.completed_at == datetime(2026, 5, 11, 9, 30, 0)
    assert execution_completed_event.payload["operationDate"] == "2026-05-12"
    assert set(result.updated_fields) == {
        "operation_date",
        "actual_end_at",
        "actual_amount",
        "result_payload",
        "record_time",
    }
    assert service.event_record_repository.items[-1].event_type == "ExecutionRecordUpdated"


def test_update_latest_execution_record_requires_existing_record() -> None:
    plan_orchestrator = build_plan_orchestrator(
        planting_plan_repository=FakePlantingPlanRepository(make_plan()),
        calendar_item_repository=FakeCalendarItemRepository(),
        farming_task_repository=FakeFarmingTaskRepository(
            {
                55: FarmingTask(
                    id=55,
                    planting_plan_id=1,
                    task_category="plant_protection",
                    task_subtype="plant_protection.soil_sealing_weed_control",
                    title="土壤封闭除草",
                    status="completed",
                    execution_mode="manual",
                    idempotency_key="task:55",
                )
            }
        ),
        event_record_repository=FakeEventRecordRepository(),
        task_intent_repository=FakeTaskIntentRepository(),
        review_request_repository=FakeReviewRequestRepository(),
        operation_plan_repository=FakeOperationPlanRepository(),
        stage_management_service=object(),
        survey_date_recommendation_service=object(),
        weather_provider=MockWeatherProvider(),
        diagnosis_client=MockWeedDiagnosisClient(),
        context_resolver=PlantProtectionPlanContextResolver(FakeCodeDictRepository(make_code_dicts()), FakeRiceVarietyRepository(make_variety())),
        pest_disease_control_planning_service=object(),
    )
    service = TaskExecutionService(
        farming_task_repository=FakeFarmingTaskRepository(
            {
                55: FarmingTask(
                    id=55,
                    planting_plan_id=1,
                    task_category="plant_protection",
                    task_subtype="plant_protection.soil_sealing_weed_control",
                    title="土壤封闭除草",
                    status="completed",
                    execution_mode="manual",
                    idempotency_key="task:55",
                )
            }
        ),
        operation_plan_repository=FakeOperationPlanRepository(),
        execution_repository=FakeExecutionRepository(),
        execution_record_repository=FakeExecutionRecordRepository(),
        event_record_repository=FakeEventRecordRepository(),
        plan_orchestrator=plan_orchestrator,
    )

    with pytest.raises(ValueError, match="does not have any execution records"):
        service.update_latest_execution_record(
            55,
            TaskExecutionRecordUpdateInput(
                actual_amount=Decimal("1.0"),
            ),
        )


def test_complete_task_rejects_cancelled_task() -> None:
    farming_task = FarmingTask(
        id=10,
        planting_plan_id=1,
        task_category="plant_protection",
        task_subtype="plant_protection.stem_leaf_weed_control",
        title="茎叶除草",
        status="cancelled",
        execution_mode="manual",
        idempotency_key="task:10",
    )
    service = TaskExecutionService(
        farming_task_repository=FakeFarmingTaskRepository({10: farming_task}),
        operation_plan_repository=FakeOperationPlanRepository(),
        execution_repository=FakeExecutionRepository(),
        execution_record_repository=FakeExecutionRecordRepository(),
        event_record_repository=FakeEventRecordRepository(),
        plan_orchestrator=build_plan_orchestrator(
            planting_plan_repository=FakePlantingPlanRepository(make_plan()),
            calendar_item_repository=FakeCalendarItemRepository(),
            farming_task_repository=FakeFarmingTaskRepository({10: farming_task}),
            event_record_repository=FakeEventRecordRepository(),
            task_intent_repository=FakeTaskIntentRepository(),
            review_request_repository=FakeReviewRequestRepository(),
            operation_plan_repository=FakeOperationPlanRepository(),
            stage_management_service=object(),
            survey_date_recommendation_service=object(),
            weather_provider=MockWeatherProvider(),
            diagnosis_client=MockWeedDiagnosisClient(),
            context_resolver=PlantProtectionPlanContextResolver(
                FakeCodeDictRepository(make_code_dicts()),
                FakeRiceVarietyRepository(make_variety()),
            ),
            pest_disease_control_planning_service=object(),
        ),
    )

    with pytest.raises(ValueError, match="is cancelled and cannot accept execution records"):
        service.complete_task(
            10,
            TaskExecutionCompleteInput(
                operation_date=date(2026, 4, 20),
                result_payload={"actual": "completed"},
            ),
        )


def test_update_latest_execution_record_rejects_cancelled_task() -> None:
    farming_task = FarmingTask(
        id=55,
        planting_plan_id=1,
        task_category="plant_protection",
        task_subtype="plant_protection.soil_sealing_weed_control",
        title="土壤封闭除草",
        status="cancelled",
        execution_mode="manual",
        idempotency_key="task:55",
    )
    execution = Execution(
        id=47,
        planting_plan_id=1,
        farming_task_id=55,
        status="completed",
        completed_at=datetime(2026, 5, 11, 9, 0, 0),
    )
    service = TaskExecutionService(
        farming_task_repository=FakeFarmingTaskRepository({55: farming_task}),
        operation_plan_repository=FakeOperationPlanRepository(),
        execution_repository=FakeExecutionRepository([execution]),
        execution_record_repository=FakeExecutionRecordRepository(
            [
                ExecutionRecord(
                    id=52,
                    planting_plan_id=1,
                    execution_id=47,
                    record_type="operation_result",
                    record_time=datetime(2026, 5, 11, 9, 0, 0),
                    actual_end_at=datetime(2026, 5, 11, 9, 0, 0),
                    result_payload={"note": "old"},
                    attachments=[],
                )
            ]
        ),
        event_record_repository=FakeEventRecordRepository(),
        plan_orchestrator=build_plan_orchestrator(
            planting_plan_repository=FakePlantingPlanRepository(make_plan()),
            calendar_item_repository=FakeCalendarItemRepository(),
            farming_task_repository=FakeFarmingTaskRepository({55: farming_task}),
            event_record_repository=FakeEventRecordRepository(),
            task_intent_repository=FakeTaskIntentRepository(),
            review_request_repository=FakeReviewRequestRepository(),
            operation_plan_repository=FakeOperationPlanRepository(),
            stage_management_service=object(),
            survey_date_recommendation_service=object(),
            weather_provider=MockWeatherProvider(),
            diagnosis_client=MockWeedDiagnosisClient(),
            context_resolver=PlantProtectionPlanContextResolver(
                FakeCodeDictRepository(make_code_dicts()),
                FakeRiceVarietyRepository(make_variety()),
            ),
            pest_disease_control_planning_service=object(),
        ),
    )

    with pytest.raises(ValueError, match="is cancelled and cannot accept execution records"):
        service.update_latest_execution_record(
            55,
            TaskExecutionRecordUpdateInput(actual_amount=Decimal("1.0")),
        )
