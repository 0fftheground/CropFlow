from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from app.models import CalendarItem, EventRecord, Execution, ExecutionRecord, FarmingTask
from app.orchestrator import build_plan_orchestrator
from app.services import (
    MockWeatherProvider,
    MockWeedDiagnosisClient,
    PlantProtectionPlanContextResolver,
    SurveyDateRecommendationService,
    TaskExecutionCompleteInput,
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
