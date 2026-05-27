from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

import pytest

from app.models import (
    CalendarItem,
    CodeDict,
    EventRecord,
    Execution,
    ExecutionRecord,
    FarmingTask,
    PlantingPlan,
    ReviewRequest,
    OperationPlan,
    RiceVariety,
    TaskIntent,
)
from app.orchestrator import build_plan_orchestrator
from app.services import (
    MockWeatherProvider,
    MockWeedDiagnosisClient,
    PlantProtectionPlanContextResolver,
    SurveyDateRecommendationService,
    SurveyResultService,
)


@dataclass
class FakePlantingPlanRepository:
    plan: PlantingPlan

    def get(self, planting_plan_id: int) -> PlantingPlan | None:
        return self.plan if self.plan.id == planting_plan_id else None


@dataclass
class FakeFarmingTaskRepository:
    tasks: dict[int, FarmingTask]
    items: list[FarmingTask] = field(default_factory=list)
    next_id: int = 11

    def get(self, farming_task_id: int) -> FarmingTask | None:
        return self.tasks.get(farming_task_id)

    def add(self, farming_task: FarmingTask) -> FarmingTask:
        self.items.append(farming_task)
        return farming_task

    def flush(self) -> None:
        for farming_task in self.items:
            if farming_task.id is None:
                farming_task.id = self.next_id
                self.next_id += 1
            self.tasks[farming_task.id] = farming_task


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
class FakeTaskIntentRepository:
    items: list[TaskIntent] = field(default_factory=list)
    next_id: int = 1

    def add(self, task_intent: TaskIntent) -> TaskIntent:
        self.items.append(task_intent)
        return task_intent

    def flush(self) -> None:
        for task_intent in self.items:
            if task_intent.id is None:
                task_intent.id = self.next_id
                self.next_id += 1


@dataclass
class FakeReviewRequestRepository:
    items: list[ReviewRequest] = field(default_factory=list)
    next_id: int = 1

    def add(self, review_request: ReviewRequest) -> ReviewRequest:
        self.items.append(review_request)
        return review_request

    def flush(self) -> None:
        for review_request in self.items:
            if review_request.id is None:
                review_request.id = self.next_id
                self.next_id += 1


@dataclass
class FakeOperationPlanRepository:
    items: list[OperationPlan] = field(default_factory=list)

    def add(self, operation_plan: OperationPlan) -> OperationPlan:
        self.items.append(operation_plan)
        return operation_plan

    def flush(self) -> None:
        return None


@dataclass
class FakeRiceVarietyRepository:
    variety: RiceVariety

    def get(self, rice_variety_id: int) -> RiceVariety | None:
        return self.variety if self.variety.id == rice_variety_id else None


@dataclass
class FakeCodeDictRepository:
    items: dict[int, CodeDict]

    def get_by_code(self, code: int) -> CodeDict | None:
        return self.items.get(code)


@dataclass
class FakeCalendarItemRepository:
    items: list[CalendarItem] = field(default_factory=list)
    next_id: int = 1

    def add(self, item: CalendarItem) -> CalendarItem:
        if item.id is None:
            item.id = self.next_id
            self.next_id += 1
        self.items.append(item)
        return item

    def list_active_by_plan_and_subtype(
        self,
        planting_plan_id: int,
        task_subtype: str,
        *,
        parent_task_id: int | None = None,
        source_execution_record_id: int | None = None,
    ) -> list[CalendarItem]:
        return [
            item
            for item in self.items
            if item.planting_plan_id == planting_plan_id
            and item.task_subtype == task_subtype
            and item.status == "active"
            and item.parent_task_id == parent_task_id
            and item.source_execution_record_id == source_execution_record_id
        ]


def make_service(task_subtype: str) -> tuple[SurveyResultService, FakeTaskIntentRepository, FakeReviewRequestRepository, FakeCalendarItemRepository]:
    plan = PlantingPlan(
        id=1,
        plan_code="PLAN-001",
        plan_name="测试计划",
        farm_id=1,
        culti_type_code=5,
        planting_method_code=1,
        crop_name="水稻",
        variety_id=1,
        variety_name="黄广农占",
        sowing_date=date(2026, 4, 10),
        task_generation_window_days=14,
        metadata_payload={},
    )
    task = FarmingTask(
        id=10,
        planting_plan_id=1,
        task_category="plant_protection",
        task_subtype=task_subtype,
        title="调查任务",
        status="pending",
        execution_mode="manual",
        idempotency_key=f"task:{task_subtype}",
    )
    plan_repo = FakePlantingPlanRepository(plan)
    variety_repo = FakeRiceVarietyRepository(RiceVariety(id=1, name="黄广农占", sub_type_code=9))
    code_repo = FakeCodeDictRepository(
        {
            1: CodeDict(id=1, code=1, code_name="直播", category="sowingmtd"),
            5: CodeDict(id=5, code=5, code_name="早稻", category="culti_type"),
            9: CodeDict(id=9, code=9, code_name="籼", category="sub_type"),
        },
    )
    calendar_repo = FakeCalendarItemRepository()
    event_repo = FakeEventRecordRepository()
    task_intent_repo = FakeTaskIntentRepository()
    review_repo = FakeReviewRequestRepository()
    weather_provider = MockWeatherProvider()
    diagnosis_client = MockWeedDiagnosisClient()
    survey_date_service = SurveyDateRecommendationService(
        planting_plan_repository=plan_repo,
        rice_variety_repository=variety_repo,
        code_dict_repository=code_repo,
        calendar_item_repository=calendar_repo,
        event_record_repository=event_repo,
        weather_provider=weather_provider,
        diagnosis_client=diagnosis_client,
    )
    farming_task_repo = FakeFarmingTaskRepository({10: task})
    plan_orchestrator = build_plan_orchestrator(
        planting_plan_repository=plan_repo,
        calendar_item_repository=calendar_repo,
        farming_task_repository=farming_task_repo,
        event_record_repository=event_repo,
        task_intent_repository=task_intent_repo,
        review_request_repository=review_repo,
        operation_plan_repository=FakeOperationPlanRepository(),
        stage_management_service=object(),
        survey_date_recommendation_service=survey_date_service,
        weather_provider=weather_provider,
        diagnosis_client=diagnosis_client,
        context_resolver=PlantProtectionPlanContextResolver(code_repo, variety_repo),
    )
    service = SurveyResultService(
        farming_task_repository=farming_task_repo,
        execution_repository=FakeExecutionRepository(),
        execution_record_repository=FakeExecutionRecordRepository(),
        event_record_repository=event_repo,
        plan_orchestrator=plan_orchestrator,
    )
    return service, task_intent_repo, review_repo, calendar_repo


def make_pre_treatment_payload(**extra: Any) -> dict[str, Any]:
    payload = {
        "survey_date": "20260418",
        "rice_leaf_age": 4.5,
        "BaiCao": {"leaf_age": 2, "mass": 100},
        "QianJinZi": {"leaf_age": 0, "mass": 0},
        "KuoYeCao": {"mass": 0},
        "SuoCao": {"mass": 0},
    }
    payload.update(extra)
    return payload


def test_pre_treatment_survey_creates_task_intent_and_review_request() -> None:
    service, task_intent_repo, review_repo, _ = make_service("plant_protection.stem_leaf_weed_pre_survey")

    result = service.record_survey_result(10, make_pre_treatment_payload())

    assert result.execution_record.id == 1
    assert task_intent_repo.items[0].task_subtype == "plant_protection.stem_leaf_weed_control"
    assert task_intent_repo.items[0].status == "pending"
    assert review_repo.items[0].source_entity_id == task_intent_repo.items[0].id


def test_rice_safety_survey_records_no_action_when_no_mitigation_needed() -> None:
    service, task_intent_repo, review_repo, _ = make_service("plant_protection.rice_safety_survey")

    service.record_survey_result(10, {"survey_date": "20260423", "rice_injury_level": "无"})

    assert task_intent_repo.items[0].status == "no_action"
    assert task_intent_repo.items[0].no_action_reason == "安全性调查后诊断无需药害缓解。"
    assert review_repo.items == []


def test_control_effect_survey_creates_service_evaluation_calendar_item_and_no_action() -> None:
    service, task_intent_repo, review_repo, calendar_repo = make_service("plant_protection.control_effect_survey")

    service.record_survey_result(
        10,
        {
            "survey_date": "20260427",
            "control_date": "20260420",
            "previous_injury_level": "无",
            "survey_data_before_treatment": make_pre_treatment_payload(),
            "rice_leaf_age": 4.5,
            "rice_injury_level": "无",
            "BaiCao": {"control_effect": 1, "leaf_age": 0, "mass": 0},
            "QianJinZi": {"control_effect": 1, "leaf_age": 0, "mass": 0},
            "KuoYeCao": {"control_effect": 1, "mass": 0},
            "SuoCao": {"control_effect": 1, "mass": 0},
        },
    )

    assert calendar_repo.items[0].task_subtype == "plant_protection.service_effect_evaluation"
    assert task_intent_repo.items[0].status == "no_action"
    assert review_repo.items == []


def test_service_effect_evaluation_satisfied_ends_without_followup_task() -> None:
    service, task_intent_repo, review_repo, calendar_repo = make_service("plant_protection.service_effect_evaluation")

    result = service.record_survey_result(
        10,
        {
            "is_satisfied": True,
            "evaluated_at": "2026-04-30T09:30:00",
            "evaluator_name": "张三",
            "contact_info": "13800138000",
        },
    )

    assert result.farming_tasks == []
    assert task_intent_repo.items == []
    assert review_repo.items == []
    assert calendar_repo.items == []


def test_service_effect_evaluation_unsatisfied_creates_followup_task() -> None:
    service, task_intent_repo, review_repo, calendar_repo = make_service("plant_protection.service_effect_evaluation")

    result = service.record_survey_result(
        10,
        {
            "is_satisfied": False,
            "evaluated_at": "2026-04-30T09:30:00",
            "evaluator_name": "张三",
            "contact_info": "13800138000",
            "comment": "需要上门确认药后情况。",
        },
    )

    assert len(result.farming_tasks) == 1
    assert result.farming_tasks[0].task_subtype == "plant_protection.service_effect_survey"
    assert result.farming_tasks[0].title == "服务人员现场确认"
    assert result.farming_tasks[0].parent_task_id == 10
    assert result.farming_tasks[0].source_execution_record_id == result.execution_record.id
    assert task_intent_repo.items == []
    assert review_repo.items == []
    assert calendar_repo.items == []


def test_service_effect_evaluation_requires_satisfaction_field() -> None:
    service, _, _, _ = make_service("plant_protection.service_effect_evaluation")

    with pytest.raises(ValueError, match="Missing required payload field"):
        service.record_survey_result(
            10,
            {
                "evaluated_at": "2026-04-30T09:30:00",
                "evaluator_name": "张三",
                "contact_info": "13800138000",
            },
        )


def test_service_effect_survey_records_manual_result_and_ends() -> None:
    service, task_intent_repo, review_repo, calendar_repo = make_service("plant_protection.service_effect_survey")

    result = service.record_survey_result(
        10,
        {
            "survey_date": "20260501",
            "actual_situation": "现场确认局部杂草残留，未继续扩散。",
            "reason": "前期喷施覆盖不均匀。",
            "comment": "已向农户说明情况。",
        },
    )

    assert result.farming_tasks == []
    assert task_intent_repo.items == []
    assert review_repo.items == []
    assert calendar_repo.items == []


def test_service_effect_survey_requires_actual_situation_and_reason() -> None:
    service, _, _, _ = make_service("plant_protection.service_effect_survey")

    with pytest.raises(ValueError, match="Expected non-empty string payload field"):
        service.record_survey_result(
            10,
            {
                "survey_date": "20260501",
                "actual_situation": "",
                "reason": "前期喷施覆盖不均匀。",
            },
        )
