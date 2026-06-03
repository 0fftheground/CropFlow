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
    Farm,
    FarmingTask,
    RiceControlWindowLevel1,
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
    MockPestDiseaseControlClient,
    PestDiseaseControlPlanningService,
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

    def list_current_by_plan(self, planting_plan_id: int) -> list[FarmingTask]:
        return [item for item in self.tasks.values() if item.planting_plan_id == planting_plan_id]


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

    def get(self, task_intent_id: int) -> TaskIntent | None:
        for item in self.items:
            if item.id == task_intent_id:
                return item
        return None

    def add(self, task_intent: TaskIntent) -> TaskIntent:
        self.items.append(task_intent)
        return task_intent

    def flush(self) -> None:
        for task_intent in self.items:
            if task_intent.id is None:
                task_intent.id = self.next_id
                self.next_id += 1

    def list_current_by_plan(self, planting_plan_id: int) -> list[TaskIntent]:
        return [
            item
            for item in self.items
            if item.planting_plan_id == planting_plan_id
            and item.status not in {"converted", "rejected", "no_action"}
        ]


@dataclass
class FakeReviewRequestRepository:
    items: list[ReviewRequest] = field(default_factory=list)
    next_id: int = 1

    def get(self, review_request_id: int) -> ReviewRequest | None:
        for item in self.items:
            if item.id == review_request_id:
                return item
        return None

    def add(self, review_request: ReviewRequest) -> ReviewRequest:
        self.items.append(review_request)
        return review_request

    def flush(self) -> None:
        for review_request in self.items:
            if review_request.id is None:
                review_request.id = self.next_id
                self.next_id += 1

    def list_current_by_plan(self, planting_plan_id: int) -> list[ReviewRequest]:
        return [
            item
            for item in self.items
            if item.planting_plan_id == planting_plan_id and item.status not in {"resolved", "cancelled"}
        ]


@dataclass
class FakeOperationPlanRepository:
    items: list[OperationPlan] = field(default_factory=list)

    def add(self, operation_plan: OperationPlan) -> OperationPlan:
        self.items.append(operation_plan)
        return operation_plan

    def flush(self) -> None:
        return None

    def list_by_plan(self, planting_plan_id: int) -> list[OperationPlan]:
        return [item for item in self.items if item.planting_plan_id == planting_plan_id]

    def get_active_by_task(self, farming_task_id: int) -> OperationPlan | None:
        for item in self.items:
            if item.farming_task_id == farming_task_id and item.status == "active":
                return item
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

    def get(self, calendar_item_id: int) -> CalendarItem | None:
        for item in self.items:
            if item.id == calendar_item_id:
                return item
        return None

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


@dataclass
class FakeFarmRepository:
    farm: Farm

    def get(self, farm_id: int) -> Farm | None:
        return self.farm if self.farm.id == farm_id else None


@dataclass
class FakeRiceControlWindowLevel1Repository:
    item: RiceControlWindowLevel1

    def get_by_region_and_year(
        self,
        *,
        province: str,
        city: str,
        county: str,
        data_year: int,
    ) -> RiceControlWindowLevel1 | None:
        if (
            self.item.province == province
            and self.item.city == city
            and self.item.county == county
            and self.item.data_year == data_year
        ):
            return self.item
        return None


class CancelAfterAdjustPestDiseaseControlClient(MockPestDiseaseControlClient):
    def adjust_control_window(
        self,
        *,
        control_type: str,
        theory_plan: dict[str, Any],
        spray_suitability_data: list[dict[str, Any]],
        plant_info: dict[str, Any] | None = None,
    ):
        return super().adjust_control_window(
            control_type=control_type,
            theory_plan={"mock_mode": "cancel_after_adjust", **theory_plan},
            spray_suitability_data=spray_suitability_data,
            plant_info=plant_info,
        )


def make_service(
    task_subtype: str,
    *,
    control_client: MockPestDiseaseControlClient | None = None,
) -> tuple[SurveyResultService, FakeTaskIntentRepository, FakeReviewRequestRepository, FakeCalendarItemRepository]:
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
        metadata_payload={
            "growth_stage": {
                "tillering_date": "2026-05-18",
                "pokou_date": "2026-06-20",
                "heading_date": "2026-06-27",
            },
        },
    )
    task = FarmingTask(
        id=10,
        planting_plan_id=1,
        calendar_item_id=1 if task_subtype == "plant_protection.regular_disease_pest_survey" else None,
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
    if task_subtype == "plant_protection.regular_disease_pest_survey":
        calendar_repo.add(
            CalendarItem(
                planting_plan_id=1,
                task_category="plant_protection",
                task_subtype="plant_protection.regular_disease_pest_survey",
                title="常规病虫调查",
                description="测试用常规病虫调查",
                suggested_start_date=date(2026, 6, 28),
                suggested_end_date=date(2026, 6, 28),
                status="active",
                generation_condition={
                    "sprayStage": "封行药",
                    "rawPlan": {"spray_stage": "封行药"},
                },
                idempotency_key="calendar:regular-disease-pest-survey:1",
            ),
        )
    event_repo = FakeEventRecordRepository()
    task_intent_repo = FakeTaskIntentRepository()
    review_repo = FakeReviewRequestRepository()
    operation_plan_repo = FakeOperationPlanRepository()
    weather_provider = MockWeatherProvider()
    diagnosis_client = MockWeedDiagnosisClient()
    farm_repo = FakeFarmRepository(
        Farm(
            id=1,
            farm_name="测试农场",
            external_farm_id="farm-1",
            province="湖南省",
            city="益阳市",
            district_county="桃江县",
        ),
    )
    rice_control_window_repo = FakeRiceControlWindowLevel1Repository(
        RiceControlWindowLevel1(
            id=1,
            province="湖南省",
            city="益阳市",
            county="桃江县",
            data_year=2026,
            detail={"1": ["0702", "0706"], "2": ["0720", "0724"]},
        ),
    )
    survey_date_service = SurveyDateRecommendationService(
        planting_plan_repository=plan_repo,
        farm_repository=farm_repo,
        rice_variety_repository=variety_repo,
        code_dict_repository=code_repo,
        rice_control_window_level1_repository=rice_control_window_repo,
        calendar_item_repository=calendar_repo,
        event_record_repository=event_repo,
        weather_provider=weather_provider,
        diagnosis_client=diagnosis_client,
    )
    pest_disease_control_planning_service = PestDiseaseControlPlanningService(
        planting_plan_repository=plan_repo,
        farm_repository=farm_repo,
        rice_control_window_level1_repository=rice_control_window_repo,
        stage_prediction_snapshot_repository=None,
        calendar_item_repository=calendar_repo,
        operation_plan_repository=operation_plan_repo,
        context_resolver=PlantProtectionPlanContextResolver(code_repo, variety_repo),
        weather_provider=weather_provider,
        control_client=control_client or MockPestDiseaseControlClient(),
    )
    farming_task_repo = FakeFarmingTaskRepository({10: task})
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
        pest_disease_control_planning_service=pest_disease_control_planning_service,
    )
    service = SurveyResultService(
        farming_task_repository=farming_task_repo,
        execution_repository=FakeExecutionRepository(),
        execution_record_repository=FakeExecutionRecordRepository(),
        event_record_repository=event_repo,
        plan_orchestrator=plan_orchestrator,
    )
    return service, task_intent_repo, review_repo, calendar_repo


def make_merge_service() -> tuple[SurveyResultService, FakeTaskIntentRepository, FakeReviewRequestRepository]:
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
        metadata_payload={
            "growth_stage": {
                "tillering_date": "2026-05-18",
                "pokou_date": "2026-06-20",
                "heading_date": "2026-06-27",
            },
        },
    )
    regular_task = FarmingTask(
        id=10,
        planting_plan_id=1,
        calendar_item_id=1,
        task_category="plant_protection",
        task_subtype="plant_protection.regular_disease_pest_survey",
        title="常规病虫调查",
        status="pending",
        execution_mode="manual",
        idempotency_key="task:regular-disease-pest-survey",
    )
    emergency_task = FarmingTask(
        id=11,
        planting_plan_id=1,
        task_category="plant_protection",
        task_subtype="plant_protection.sudden_disease_pest_survey",
        title="突发病虫调查",
        status="pending",
        execution_mode="manual",
        idempotency_key="task:sudden-disease-pest-survey",
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
    calendar_repo.add(
        CalendarItem(
            planting_plan_id=1,
            task_category="plant_protection",
            task_subtype="plant_protection.regular_disease_pest_survey",
            title="常规病虫调查",
            description="测试用常规病虫调查",
            suggested_start_date=date(2026, 6, 28),
            suggested_end_date=date(2026, 6, 28),
            status="active",
            generation_condition={
                "sprayStage": "封行药",
                "rawPlan": {"spray_stage": "封行药"},
            },
            idempotency_key="calendar:regular-disease-pest-survey:1",
        ),
    )
    event_repo = FakeEventRecordRepository()
    task_intent_repo = FakeTaskIntentRepository()
    review_repo = FakeReviewRequestRepository()
    operation_plan_repo = FakeOperationPlanRepository()
    weather_provider = MockWeatherProvider()
    diagnosis_client = MockWeedDiagnosisClient()
    farm_repo = FakeFarmRepository(
        Farm(
            id=1,
            farm_name="测试农场",
            external_farm_id="farm-1",
            province="湖南省",
            city="益阳市",
            district_county="桃江县",
        ),
    )
    rice_control_window_repo = FakeRiceControlWindowLevel1Repository(
        RiceControlWindowLevel1(
            id=1,
            province="湖南省",
            city="益阳市",
            county="桃江县",
            data_year=2026,
            detail={"1": ["0702", "0706"], "2": ["0720", "0724"]},
        ),
    )
    survey_date_service = SurveyDateRecommendationService(
        planting_plan_repository=plan_repo,
        farm_repository=farm_repo,
        rice_variety_repository=variety_repo,
        code_dict_repository=code_repo,
        rice_control_window_level1_repository=rice_control_window_repo,
        calendar_item_repository=calendar_repo,
        event_record_repository=event_repo,
        weather_provider=weather_provider,
        diagnosis_client=diagnosis_client,
    )
    pest_disease_control_planning_service = PestDiseaseControlPlanningService(
        planting_plan_repository=plan_repo,
        farm_repository=farm_repo,
        rice_control_window_level1_repository=rice_control_window_repo,
        stage_prediction_snapshot_repository=None,
        calendar_item_repository=calendar_repo,
        operation_plan_repository=operation_plan_repo,
        context_resolver=PlantProtectionPlanContextResolver(code_repo, variety_repo),
        weather_provider=weather_provider,
        control_client=MockPestDiseaseControlClient(),
    )
    farming_task_repo = FakeFarmingTaskRepository({10: regular_task, 11: emergency_task})
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
        pest_disease_control_planning_service=pest_disease_control_planning_service,
    )
    service = SurveyResultService(
        farming_task_repository=farming_task_repo,
        execution_repository=FakeExecutionRepository(),
        execution_record_repository=FakeExecutionRecordRepository(),
        event_record_repository=event_repo,
        plan_orchestrator=plan_orchestrator,
    )
    return service, task_intent_repo, review_repo


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
    assert service.farming_task_repository.get(10).status == "completed"
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


def test_regular_disease_pest_survey_creates_control_task_intent_and_review_request() -> None:
    service, task_intent_repo, review_repo, _ = make_service("plant_protection.regular_disease_pest_survey")

    service.record_survey_result(
        10,
        {
            "survey_date": "20260628",
            "survey_method": "一级理论防治日期",
            "bbch_stage": 23,
            "DaoFeiShi": {"insects_per_100_hills": 12},
        },
    )

    assert task_intent_repo.items[0].task_subtype == "plant_protection.disease_pest_control"
    assert task_intent_repo.items[0].status == "pending"
    assert task_intent_repo.items[0].rule_result["algorithmCode"] == "pest_disease.generate_theory_control_plan"
    assert task_intent_repo.items[0].rule_result["proposedPlan"]["controlType"] == "regular"
    assert task_intent_repo.items[0].rule_result["proposedPlan"]["requestPayload"]["spray_info"]["stage"] == "封行药"
    assert task_intent_repo.items[0].rule_result["proposedPlan"]["requestPayload"]["level1_window"] == ["0702", "0706"]
    assert task_intent_repo.items[0].rule_result["proposedTask"]["recommendedControlDate"] == ["2026-06-29", "2026-06-29"]
    assert task_intent_repo.items[0].rule_result["proposedPlan"]["operationWindow"] == ["2026-06-29", "2026-06-29"]
    assert task_intent_repo.items[0].rule_result["proposedPlan"]["spraySuitabilityRequiredRange"] == ["2026-06-29", "2026-07-10"]
    assert task_intent_repo.items[0].rule_result["proposedPlan"]["spraySuitabilityData"][0] == {
        "date": "20260629",
        "dy_ws": 1.0,
    }
    assert task_intent_repo.items[0].rule_result["proposedPlan"]["adjustedPlan"]["rounds"][0]["final_window"] == ["20260629"]
    assert task_intent_repo.items[0].rule_result["proposedPlan"]["weatherAdjust"]["adjusted"] is True
    assert task_intent_repo.items[0].rule_result["proposedPlan"]["controlPlan"]["rounds"][0]["prescription"] == {
        "chemicals": [],
        "water_volume": "3 L/亩",
    }
    assert review_repo.items[0].source_entity_id == task_intent_repo.items[0].id


def test_sudden_disease_pest_survey_theory_no_action_creates_no_action_intent() -> None:
    service, task_intent_repo, review_repo, _ = make_service("plant_protection.sudden_disease_pest_survey")

    service.record_survey_result(
        10,
        {
            "survey_date": "20260703",
            "mock_mode": "no_action",
            "DaoWenBing": {"acute_lesion": False, "diseased_leaf_rate": 0},
        },
    )

    assert task_intent_repo.items[0].task_subtype == "plant_protection.disease_pest_control"
    assert task_intent_repo.items[0].status == "no_action"
    assert task_intent_repo.items[0].no_action_reason == "病虫调查后理论防治结果为无需防治。"
    assert review_repo.items == []


def test_regular_disease_pest_survey_adjust_no_action_creates_no_action_intent() -> None:
    service, task_intent_repo, review_repo, _ = make_service(
        "plant_protection.regular_disease_pest_survey",
        control_client=CancelAfterAdjustPestDiseaseControlClient(),
    )

    service.record_survey_result(
        10,
        {
            "survey_date": "20260628",
            "survey_method": "一级理论防治日期",
            "bbch_stage": 23,
            "DaoFeiShi": {"insects_per_100_hills": 12},
        },
    )

    assert task_intent_repo.items[0].task_subtype == "plant_protection.disease_pest_control"
    assert task_intent_repo.items[0].status == "no_action"
    assert task_intent_repo.items[0].rule_result["algorithmCode"] == "pest_disease.adjust_control_window"
    assert task_intent_repo.items[0].rule_result["rawResponse"]["data"]["status"] == "取消防治"
    assert task_intent_repo.items[0].no_action_reason == "病虫调查后气象调整结果为无可执行防治日期。"
    assert review_repo.items == []


def test_sudden_disease_pest_survey_merges_with_existing_regular_control_recommendation() -> None:
    service, task_intent_repo, review_repo = make_merge_service()

    service.record_survey_result(
        10,
        {
            "survey_date": "20260628",
            "survey_method": "一级理论防治日期",
            "bbch_stage": 23,
            "DaoFeiShi": {"insects_per_100_hills": 12},
        },
    )
    merge_result = service.record_survey_result(
        11,
        {
            "survey_date": "20260629",
            "bbch_stage": 45,
            "DaoWenBing": {"acute_lesion": True, "diseased_leaf_rate": 5},
        },
    )

    assert task_intent_repo.items[0].status == "rejected"
    assert task_intent_repo.items[0].no_action_reason == "Superseded by merged disease pest control recommendation."
    assert review_repo.items[0].status == "cancelled"

    merged_task_intent = task_intent_repo.items[-1]
    merged_review_request = review_repo.items[-1]

    assert merged_task_intent.status == "pending"
    assert merged_task_intent.rule_result["algorithmCode"] == "pest_disease.merge_control_plan"
    assert merged_task_intent.rule_result["proposedPlan"]["controlType"] == "merged"
    assert merged_task_intent.rule_result["proposedPlan"]["mergeRequiredRange"] == ["2026-06-26", "2026-08-19"]
    assert merged_task_intent.rule_result["proposedPlan"]["mergedPlan"]["merged"] is True
    assert merged_task_intent.rule_result["proposedPlan"]["events"][0]["type"] == "merged"
    assert merged_task_intent.rule_result["proposedPlan"]["events"][0]["finalWindow"] == ["2026-06-29", "2026-06-29"]
    assert merged_task_intent.rule_result["proposedPlan"]["targets"] == {
        "DaoFeiShi": "防治",
        "DaoWenBing": "防治",
    }
    assert merged_task_intent.rule_result["proposedPlan"]["spraySuitabilityData"][0] == {
        "date": "20260626",
        "dy_ws": 1.0,
    }
    assert merged_review_request.status == "open"
    assert merged_review_request.source_entity_id == merged_task_intent.id
    assert merge_result.task_intents[-1].id == merged_task_intent.id
