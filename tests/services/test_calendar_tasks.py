from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from io import BytesIO
from typing import Any
from urllib.error import HTTPError, URLError

import pytest

from app.core.constants import (
    CALENDAR_STATUS_GENERATED,
    EVENT_TYPE_CALENDAR_ITEM_UPDATED,
    EVENT_TYPE_TASK_DUE_CHECK_TRIGGERED,
    TASK_SUBTYPE_CONTROL_EFFECT_SURVEY,
    TASK_SUBTYPE_RICE_SAFETY_SURVEY,
    TASK_SUBTYPE_STEM_LEAF_WEED_PRE_SURVEY,
)
from app.models import CalendarItem, CodeDict, EventRecord, FarmingTask, PlantingPlan, RiceVariety
from app.orchestrator.core import PlanOrchestrator, TaskDueCheckTriggeredHandler
from app.services.calendar_tasks import (
    HttpWeedDiagnosisClient,
    MockWeatherProvider,
    PostTreatmentSurveyRecommendation,
    PreTreatmentSurveyRecommendation,
    SoilTreatmentDiagnosisResult,
    SurveyDateRecommendationService,
    TaskGenerationService,
)


@dataclass
class FakePlantingPlanRepository:
    plan: PlantingPlan

    def get(self, planting_plan_id: int) -> PlantingPlan | None:
        return self.plan if self.plan.id == planting_plan_id else None


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

    def list_due_for_generation(
        self,
        planting_plan_id: int,
        *,
        check_date: date,
        window_days: int,
    ) -> list[CalendarItem]:
        latest_start_date = check_date.fromordinal(check_date.toordinal() + window_days)
        return [
            item
            for item in self.items
            if item.planting_plan_id == planting_plan_id
            and item.status == "active"
            and item.generated_task_id is None
            and item.suggested_start_date <= latest_start_date
        ]


@dataclass
class FakeEventRecordRepository:
    items: list[EventRecord] = field(default_factory=list)

    def add(self, event_record: EventRecord) -> EventRecord:
        self.items.append(event_record)
        return event_record


@dataclass
class FakeFarmingTaskRepository:
    items: list[FarmingTask] = field(default_factory=list)
    next_id: int = 1

    def add(self, task: FarmingTask) -> FarmingTask:
        self.items.append(task)
        return task

    def flush(self) -> None:
        for task in self.items:
            if task.id is None:
                task.id = self.next_id
                self.next_id += 1


@dataclass
class FakeWeatherProvider:
    requests: list[tuple[date, date]] = field(default_factory=list)

    def get_daily_weather(
        self,
        planting_plan: PlantingPlan,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        self.requests.append((start_date, end_date))
        return [{"DATE": start_date.strftime("%Y%m%d"), "TEMP": 26}]


class FakeDiagnosisClient:
    def diagnose_soil_treatment(
        self,
        *,
        province: str,
        cultivation_system: str,
        cultivation_pattern: str,
        cultivation_date: date,
    ) -> SoilTreatmentDiagnosisResult:
        assert province == "湖南省"
        assert cultivation_system == "早稻"
        assert cultivation_pattern == "直播"
        assert cultivation_date == date(2026, 4, 10)
        return SoilTreatmentDiagnosisResult(
            recommended_date=(date(2026, 4, 12), date(2026, 4, 15)),
            farming_operation="苗后封闭",
            control_plan={"water_volume": "3 L/亩"},
            raw_response={
                "code": 200,
                "data": {
                    "soil_treatment_recommended_date": ["20260412", "20260415"],
                    "farming_operation": "苗后封闭",
                    "control_plan": {"water_volume": "3 L/亩"},
                },
            },
        )

    def recommend_pre_treatment_survey_date(
        self,
        *,
        weather_data: list[dict[str, Any]],
        rice_type: str,
        cultivation_system: str,
        cultivation_pattern: str,
        cultivation_date: date,
    ) -> PreTreatmentSurveyRecommendation:
        assert rice_type == "籼稻"
        assert cultivation_system == "早稻"
        assert cultivation_pattern == "直播"
        assert weather_data
        return PreTreatmentSurveyRecommendation(
            recommendation_date=date(2026, 4, 18),
            raw_response={"code": 200, "data": {"pre_stem_leaf_herbicide_survey_date": "20260418"}},
        )

    def recommend_post_treatment_survey_dates(
        self,
        *,
        operation_date: date,
    ) -> PostTreatmentSurveyRecommendation:
        assert operation_date == date(2026, 4, 20)
        return PostTreatmentSurveyRecommendation(
            rice_safety_survey_date=date(2026, 4, 23),
            control_effect_survey_date=date(2026, 4, 27),
            raw_response={
                "code": 200,
                "data": {
                    "rice_safety_survey_date": "20260423",
                    "control_effect_survey_date": "20260427",
                },
            },
        )


def make_plan() -> PlantingPlan:
    return PlantingPlan(
        id=1,
        plan_code="PLAN-001",
        plan_name="Test Plan",
        farm_id=1,
        culti_type_code=5,
        planting_method_code=1,
        crop_name="水稻",
        variety_id=1,
        variety_name="黄广农占",
        sowing_date=date(2026, 4, 10),
        task_generation_window_days=14,
    )


def make_variety() -> RiceVariety:
    return RiceVariety(id=1, name="黄广农占", sub_type_code=9)


def make_code_dicts() -> dict[int, CodeDict]:
    return {
        1: CodeDict(id=1, code=1, code_name="直播", category="sowingmtd"),
        5: CodeDict(id=5, code=5, code_name="早稻", category="culti_type"),
        9: CodeDict(id=9, code=9, code_name="籼", category="sub_type"),
    }


def test_recommend_pre_treatment_survey_creates_calendar_item_and_event() -> None:
    calendar_repo = FakeCalendarItemRepository()
    event_repo = FakeEventRecordRepository()
    weather_provider = FakeWeatherProvider()
    service = SurveyDateRecommendationService(
        planting_plan_repository=FakePlantingPlanRepository(make_plan()),
        rice_variety_repository=FakeRiceVarietyRepository(make_variety()),
        code_dict_repository=FakeCodeDictRepository(make_code_dicts()),
        calendar_item_repository=calendar_repo,
        event_record_repository=event_repo,
        weather_provider=weather_provider,
        diagnosis_client=FakeDiagnosisClient(),
    )

    item = service.recommend_pre_treatment_survey(1, check_date=date(2026, 4, 10))

    assert item.task_subtype == TASK_SUBTYPE_STEM_LEAF_WEED_PRE_SURVEY
    assert item.suggested_start_date == date(2026, 4, 18)
    assert item.title == "茎叶除草药前调查"
    assert event_repo.items[-1].event_type == EVENT_TYPE_CALENDAR_ITEM_UPDATED
    assert weather_provider.requests == [(date(2026, 4, 9), date(2026, 5, 24))]

def test_recommend_post_treatment_surveys_creates_two_traceable_calendar_items() -> None:
    calendar_repo = FakeCalendarItemRepository()
    service = SurveyDateRecommendationService(
        planting_plan_repository=FakePlantingPlanRepository(make_plan()),
        rice_variety_repository=FakeRiceVarietyRepository(make_variety()),
        code_dict_repository=FakeCodeDictRepository(make_code_dicts()),
        calendar_item_repository=calendar_repo,
        event_record_repository=FakeEventRecordRepository(),
        weather_provider=FakeWeatherProvider(),
        diagnosis_client=FakeDiagnosisClient(),
    )

    safety_item, effect_item = service.recommend_post_treatment_surveys(
        1,
        operation_date=date(2026, 4, 20),
        parent_task_id=100,
        source_execution_id=200,
        source_execution_record_id=300,
    )

    assert safety_item.task_subtype == TASK_SUBTYPE_RICE_SAFETY_SURVEY
    assert effect_item.task_subtype == TASK_SUBTYPE_CONTROL_EFFECT_SURVEY
    assert safety_item.parent_task_id == 100
    assert effect_item.source_execution_record_id == 300


def test_generate_due_tasks_marks_calendar_item_generated() -> None:
    calendar_item = CalendarItem(
        id=1,
        planting_plan_id=1,
        task_category="plant_protection",
        task_subtype=TASK_SUBTYPE_STEM_LEAF_WEED_PRE_SURVEY,
        title="茎叶除草药前调查",
        description="调查杂草情况",
        suggested_start_date=date(2026, 4, 18),
        suggested_end_date=date(2026, 4, 18),
        status="active",
        idempotency_key="calendar-item:1:test",
    )
    calendar_repo = FakeCalendarItemRepository(items=[calendar_item], next_id=2)
    farming_task_repo = FakeFarmingTaskRepository()
    event_repo = FakeEventRecordRepository()
    plan_orchestrator = PlanOrchestrator(
        {
            EVENT_TYPE_TASK_DUE_CHECK_TRIGGERED: TaskDueCheckTriggeredHandler(
                planting_plan_repository=FakePlantingPlanRepository(make_plan()),
                calendar_item_repository=calendar_repo,
                farming_task_repository=farming_task_repo,
                event_record_repository=event_repo,
            ),
        },
    )
    service = TaskGenerationService(
        planting_plan_repository=FakePlantingPlanRepository(make_plan()),
        event_record_repository=event_repo,
        plan_orchestrator=plan_orchestrator,
    )

    tasks = service.generate_due_tasks(1, check_date=date(2026, 4, 10))

    assert len(tasks) == 1
    assert tasks[0].calendar_item_id == 1
    assert tasks[0].task_subtype == TASK_SUBTYPE_STEM_LEAF_WEED_PRE_SURVEY
    assert calendar_item.status == CALENDAR_STATUS_GENERATED
    assert calendar_item.generated_task_id == tasks[0].id


def test_mock_weather_provider_returns_closed_interval_weather_data() -> None:
    provider = MockWeatherProvider()
    planting_plan = make_plan()

    weather_data = provider.get_daily_weather(
        planting_plan,
        start_date=date(2026, 4, 10),
        end_date=date(2026, 4, 12),
    )

    assert [item["DATE"] for item in weather_data] == ["20260410", "20260411", "20260412"]
    assert {item["TEMP"] for item in weather_data} == {26}


def test_http_weed_diagnosis_client_surfaces_http_error_body(monkeypatch: pytest.MonkeyPatch) -> None:
    client = HttpWeedDiagnosisClient("http://diagnosis.local")

    def fake_urlopen(*args, **kwargs):
        raise HTTPError(
            url="http://diagnosis.local/api/injury_mitigation_diagnosis",
            code=400,
            msg="Bad Request",
            hdrs=None,
            fp=BytesIO(b'{"code":400,"msg":"bad payload"}'),
        )

    monkeypatch.setattr("app.services.calendar_tasks.request.urlopen", fake_urlopen)

    with pytest.raises(ValueError, match='HTTP 400: \\{"code":400,"msg":"bad payload"\\}'):
        client.diagnose_injury_mitigation(
            survey_date=date(2026, 4, 22),
            rice_injury_level="无",
        )


def test_http_weed_diagnosis_client_surfaces_connectivity_error(monkeypatch: pytest.MonkeyPatch) -> None:
    client = HttpWeedDiagnosisClient("http://diagnosis.local")

    def fake_urlopen(*args, **kwargs):
        raise URLError("connection refused")

    monkeypatch.setattr("app.services.calendar_tasks.request.urlopen", fake_urlopen)

    with pytest.raises(RuntimeError, match="connection refused"):
        client.diagnose_injury_mitigation(
            survey_date=date(2026, 4, 22),
            rice_injury_level="无",
        )
