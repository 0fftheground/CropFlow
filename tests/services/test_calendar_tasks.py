from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from io import BytesIO
from typing import Any
from urllib.error import HTTPError, URLError

import pytest

from app.core.constants import (
    CALENDAR_STATUS_GENERATED,
    CALENDAR_STATUS_INVALIDATED,
    EVENT_TYPE_CALENDAR_ITEM_UPDATED,
    EVENT_TYPE_TASK_DUE_CHECK_TRIGGERED,
    TASK_SUBTYPE_CONTROL_EFFECT_SURVEY,
    TASK_SUBTYPE_RICE_SAFETY_SURVEY,
    TASK_SUBTYPE_REGULAR_DISEASE_PEST_SURVEY,
    TASK_SUBTYPE_STEM_LEAF_WEED_PRE_SURVEY,
)
from app.models import CalendarItem, CodeDict, EventRecord, Farm, FarmingTask, PlantingPlan, RiceControlWindowLevel1, RiceVariety
from app.models import StagePredictionSnapshot
from app.orchestrator.core import PlanOrchestrator, TaskDueCheckTriggeredHandler
from app.services.calendar_tasks import (
    HttpWeedDiagnosisClient,
    MockWeatherProvider,
    PostTreatmentSurveyRecommendation,
    PreTreatmentSurveyRecommendation,
    PestDiseaseRegularSurveyInitResult,
    PestDiseaseRegularSurveyPlan,
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
class FakeFarmRepository:
    farm: Farm

    def get(self, farm_id: int) -> Farm | None:
        return self.farm if self.farm.id == farm_id else None


@dataclass
class FakeRiceControlWindowLevel1Repository:
    record: RiceControlWindowLevel1 | None

    def get_by_region_and_year(self, *, province: str, city: str, county: str, data_year: int) -> RiceControlWindowLevel1 | None:
        if self.record is None:
            return None
        if (
            self.record.province == province
            and self.record.city == city
            and self.record.county == county
            and self.record.data_year == data_year
        ):
            return self.record
        return None


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

    def get_by_idempotency_key(self, idempotency_key: str) -> CalendarItem | None:
        return next((item for item in self.items if item.idempotency_key == idempotency_key), None)

    def list_by_plan_and_subtype(
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
            and item.parent_task_id == parent_task_id
            and item.source_execution_record_id == source_execution_record_id
        ]

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
class FakeStagePredictionSnapshotRepository:
    latest_snapshot: StagePredictionSnapshot | None = None

    def get_latest_by_plan(self, planting_plan_id: int) -> StagePredictionSnapshot | None:
        if self.latest_snapshot is None:
            return None
        return self.latest_snapshot if self.latest_snapshot.planting_plan_id == planting_plan_id else None


@dataclass
class FakeFarmingTaskRepository:
    items: list[FarmingTask] = field(default_factory=list)
    next_id: int = 1

    def add(self, task: FarmingTask) -> FarmingTask:
        self.items.append(task)
        return task

    def get(self, farming_task_id: int) -> FarmingTask | None:
        return next((task for task in self.items if task.id == farming_task_id), None)

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


class FakePestDiseaseSurveyWindowClient:
    def init_regular_surveys(
        self,
        *,
        cultivation_type: str,
        growth_stage: dict[str, str],
        level1_of_year: dict[str, list[str]],
    ) -> PestDiseaseRegularSurveyInitResult:
        assert cultivation_type == "早稻"
        assert growth_stage["tillering_date"] == "2026-04-20"
        assert level1_of_year == {"1": ["0509", "0513"], "2": ["0607", "0611"]}
        first_plan = {
            "status": "need_survey",
            "survey_window": ["20260502", "20260504"],
            "spray_stage": "封行药",
            "survey_method": "一级理论防治日期",
            "targets": ["二化螟"],
            "exclude_reasons": {
                "稻飞虱": "早稻不调查稻飞虱",
                "稻曲病": "当前一级理论防治日期不在目标防治范围内",
            },
            "msg": "当前处于可防治周期，建议按调查日期开展调查",
        }
        second_plan = {
            "status": "need_survey",
            "survey_window": ["20260601", "20260603"],
            "spray_stage": "破口药",
            "survey_method": "生育期",
            "targets": ["稻瘟病", "纹枯病"],
            "exclude_reasons": {},
            "msg": "当前处于可防治周期，建议按调查日期开展调查",
        }
        return PestDiseaseRegularSurveyInitResult(
            regular_plans=[
                PestDiseaseRegularSurveyPlan(
                    survey_window=(date(2026, 5, 2), date(2026, 5, 4)),
                    targets=["二化螟"],
                    exclude_reasons={
                        "稻飞虱": "早稻不调查稻飞虱",
                        "稻曲病": "当前一级理论防治日期不在目标防治范围内",
                    },
                    status="need_survey",
                    message="当前处于可防治周期，建议按调查日期开展调查",
                    spray_stage="封行药",
                    survey_method="一级理论防治日期",
                    adjusted=False,
                    raw_plan=first_plan,
                ),
                PestDiseaseRegularSurveyPlan(
                    survey_window=(date(2026, 6, 1), date(2026, 6, 3)),
                    targets=["稻瘟病", "纹枯病"],
                    exclude_reasons={},
                    status="need_survey",
                    message="当前处于可防治周期，建议按调查日期开展调查",
                    spray_stage="破口药",
                    survey_method="生育期",
                    adjusted=False,
                    raw_plan=second_plan,
                ),
            ],
            raw_response={
                "code": 200,
                "msg": "已生成2个常规调查任务",
                "data": {
                    "count": 2,
                    "regular_plans": [first_plan, second_plan],
                },
            },
        )


def make_plan(
    *,
    planting_method_code: int = 1,
    transplant_date: date | None = None,
) -> PlantingPlan:
    return PlantingPlan(
        id=1,
        plan_code="PLAN-001",
        plan_name="Test Plan",
        farm_id=1,
        year=2026,
        culti_type_code=5,
        planting_method_code=planting_method_code,
        crop_name="水稻",
        variety_id=1,
        variety_name="黄广农占",
        sowing_date=date(2026, 4, 10),
        transplant_date=transplant_date,
        task_generation_window_days=14,
    )


def make_plan_with_pest_disease_metadata() -> PlantingPlan:
    plan = make_plan()
    plan.metadata_payload = {
        "pestDisease": {
            "growth_stage": {
                "tillering_date": "2026-04-20",
                "pokou_date": "2026-06-10",
                "heading_date": "2026-06-18",
                "maturity_date": "2026-07-20",
            },
        },
    }
    return plan


def make_plan_with_pest_disease_growth_stage_only() -> PlantingPlan:
    plan = make_plan()
    plan.metadata_payload = {
        "pestDisease": {
            "growth_stage": {
                "tillering_date": "2026-04-20",
                "pokou_date": "2026-06-10",
                "heading_date": "2026-06-18",
                "maturity_date": "2026-07-20",
            },
        },
    }
    return plan


def make_farm() -> Farm:
    return Farm(
        id=1,
        farm_name="测试农场",
        province="湖南省",
        city="益阳市",
        district_county="桃江县",
    )


def make_control_window() -> RiceControlWindowLevel1:
    return RiceControlWindowLevel1(
        id=1,
        province="湖南省",
        city="益阳市",
        county="桃江县",
        data_year=2026,
        detail={"1": ["0509", "0513"], "2": ["0607", "0611"]},
    )


def make_variety() -> RiceVariety:
    return RiceVariety(id=1, name="黄广农占", sub_type_code=9)


def make_code_dicts() -> dict[int, CodeDict]:
    return {
        1: CodeDict(id=1, code=1, code_name="直播", category="sowingmtd"),
        3: CodeDict(id=3, code=3, code_name="插秧", category="sowingmtd"),
        4: CodeDict(id=4, code=4, code_name="抛秧", category="sowingmtd"),
        5: CodeDict(id=5, code=5, code_name="早稻", category="culti_type"),
        9: CodeDict(id=9, code=9, code_name="籼", category="sub_type"),
    }


def test_recommend_pre_treatment_survey_creates_calendar_item_and_event() -> None:
    calendar_repo = FakeCalendarItemRepository()
    event_repo = FakeEventRecordRepository()
    weather_provider = FakeWeatherProvider()
    service = SurveyDateRecommendationService(
        planting_plan_repository=FakePlantingPlanRepository(make_plan()),
        farm_repository=None,
        rice_variety_repository=FakeRiceVarietyRepository(make_variety()),
        code_dict_repository=FakeCodeDictRepository(make_code_dicts()),
        rice_control_window_level1_repository=None,
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


class PatternAwareDiagnosisClient(FakeDiagnosisClient):
    def __init__(self, expected_pattern: str, expected_cultivation_date: date) -> None:
        self.expected_pattern = expected_pattern
        self.expected_cultivation_date = expected_cultivation_date

    def recommend_pre_treatment_survey_date(
        self,
        *,
        weather_data: list[dict[str, Any]],
        rice_type: str,
        cultivation_system: str,
        cultivation_pattern: str,
        cultivation_date: date,
    ) -> PreTreatmentSurveyRecommendation:
        assert weather_data
        assert rice_type == "籼稻"
        assert cultivation_system == "早稻"
        assert cultivation_pattern == self.expected_pattern
        assert cultivation_date == self.expected_cultivation_date
        return PreTreatmentSurveyRecommendation(
            recommendation_date=date(2026, 4, 26),
            raw_response={"code": 200, "data": {"pre_stem_leaf_herbicide_survey_date": "20260426"}},
        )


def test_recommend_pre_treatment_survey_for_transplanting_includes_previous_day_weather() -> None:
    calendar_repo = FakeCalendarItemRepository()
    event_repo = FakeEventRecordRepository()
    weather_provider = FakeWeatherProvider()
    service = SurveyDateRecommendationService(
        planting_plan_repository=FakePlantingPlanRepository(
            make_plan(planting_method_code=3, transplant_date=date(2026, 4, 18)),
        ),
        farm_repository=None,
        rice_variety_repository=FakeRiceVarietyRepository(make_variety()),
        code_dict_repository=FakeCodeDictRepository(make_code_dicts()),
        rice_control_window_level1_repository=None,
        calendar_item_repository=calendar_repo,
        event_record_repository=event_repo,
        weather_provider=weather_provider,
        diagnosis_client=PatternAwareDiagnosisClient("插秧", date(2026, 4, 18)),
    )

    service.recommend_pre_treatment_survey(1, check_date=date(2026, 4, 18))

    assert weather_provider.requests == [(date(2026, 4, 17), date(2026, 6, 1))]


def test_recommend_pre_treatment_survey_for_throw_transplanting_includes_previous_day_weather() -> None:
    calendar_repo = FakeCalendarItemRepository()
    event_repo = FakeEventRecordRepository()
    weather_provider = FakeWeatherProvider()
    service = SurveyDateRecommendationService(
        planting_plan_repository=FakePlantingPlanRepository(
            make_plan(planting_method_code=4, transplant_date=date(2026, 4, 18)),
        ),
        farm_repository=None,
        rice_variety_repository=FakeRiceVarietyRepository(make_variety()),
        code_dict_repository=FakeCodeDictRepository(make_code_dicts()),
        rice_control_window_level1_repository=None,
        calendar_item_repository=calendar_repo,
        event_record_repository=event_repo,
        weather_provider=weather_provider,
        diagnosis_client=PatternAwareDiagnosisClient("抛秧", date(2026, 4, 18)),
    )

    service.recommend_pre_treatment_survey(1, check_date=date(2026, 4, 18))

    assert weather_provider.requests == [(date(2026, 4, 17), date(2026, 6, 1))]


def test_recommend_pre_treatment_survey_reuses_generated_item_with_same_idempotency_key() -> None:
    generated_item = CalendarItem(
        id=10,
        planting_plan_id=1,
        task_category="plant_protection",
        task_subtype=TASK_SUBTYPE_STEM_LEAF_WEED_PRE_SURVEY,
        title="旧标题",
        description="旧描述",
        suggested_start_date=date(2026, 4, 18),
        suggested_end_date=date(2026, 4, 18),
        status=CALENDAR_STATUS_GENERATED,
        generation_condition={"stale": True},
        idempotency_key="calendar-item:1:plant_protection.stem_leaf_weed_pre_survey:2026-04-18",
        generated_task_id=88,
    )
    calendar_repo = FakeCalendarItemRepository(items=[generated_item], next_id=11)
    event_repo = FakeEventRecordRepository()
    weather_provider = FakeWeatherProvider()
    service = SurveyDateRecommendationService(
        planting_plan_repository=FakePlantingPlanRepository(make_plan()),
        farm_repository=None,
        rice_variety_repository=FakeRiceVarietyRepository(make_variety()),
        code_dict_repository=FakeCodeDictRepository(make_code_dicts()),
        rice_control_window_level1_repository=None,
        calendar_item_repository=calendar_repo,
        event_record_repository=event_repo,
        weather_provider=weather_provider,
        diagnosis_client=FakeDiagnosisClient(),
    )

    item = service.recommend_pre_treatment_survey(1, check_date=date(2026, 4, 10))

    assert item is generated_item
    assert item.status == CALENDAR_STATUS_GENERATED
    assert item.generated_task_id == 88
    assert item.title == "茎叶除草药前调查"
    assert item.description == "由 weed_survey_date_diagnosis 推荐的茎叶除草药前调查日期。"
    assert item.generation_condition["algorithmCode"] == "weed_survey_date_diagnosis"
    assert len(calendar_repo.items) == 1


def test_recommend_pre_treatment_survey_reactivates_invalidated_item_with_same_idempotency_key() -> None:
    invalidated_item = CalendarItem(
        id=11,
        planting_plan_id=1,
        task_category="plant_protection",
        task_subtype=TASK_SUBTYPE_STEM_LEAF_WEED_PRE_SURVEY,
        title="旧标题",
        description="旧描述",
        suggested_start_date=date(2026, 4, 18),
        suggested_end_date=date(2026, 4, 18),
        status="invalidated",
        generation_condition={"stale": True},
        idempotency_key="calendar-item:1:plant_protection.stem_leaf_weed_pre_survey:2026-04-18",
        invalidated_reason="recommendation_date_changed",
    )
    calendar_repo = FakeCalendarItemRepository(items=[invalidated_item], next_id=12)
    service = SurveyDateRecommendationService(
        planting_plan_repository=FakePlantingPlanRepository(make_plan()),
        farm_repository=None,
        rice_variety_repository=FakeRiceVarietyRepository(make_variety()),
        code_dict_repository=FakeCodeDictRepository(make_code_dicts()),
        rice_control_window_level1_repository=None,
        calendar_item_repository=calendar_repo,
        event_record_repository=FakeEventRecordRepository(),
        weather_provider=FakeWeatherProvider(),
        diagnosis_client=FakeDiagnosisClient(),
    )

    item = service.recommend_pre_treatment_survey(1, check_date=date(2026, 4, 10))

    assert item is invalidated_item
    assert item.status == "active"
    assert item.invalidated_reason is None
    assert item.title == "茎叶除草药前调查"
    assert item.generation_condition["algorithmCode"] == "weed_survey_date_diagnosis"
    assert len(calendar_repo.items) == 1


def test_recommend_post_treatment_surveys_creates_two_traceable_calendar_items() -> None:
    calendar_repo = FakeCalendarItemRepository()
    service = SurveyDateRecommendationService(
        planting_plan_repository=FakePlantingPlanRepository(make_plan()),
        farm_repository=None,
        rice_variety_repository=FakeRiceVarietyRepository(make_variety()),
        code_dict_repository=FakeCodeDictRepository(make_code_dicts()),
        rice_control_window_level1_repository=None,
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


def test_recommend_regular_disease_pest_surveys_creates_multiple_calendar_items() -> None:
    calendar_repo = FakeCalendarItemRepository()
    event_repo = FakeEventRecordRepository()
    service = SurveyDateRecommendationService(
        planting_plan_repository=FakePlantingPlanRepository(make_plan_with_pest_disease_metadata()),
        farm_repository=FakeFarmRepository(make_farm()),
        rice_variety_repository=FakeRiceVarietyRepository(make_variety()),
        code_dict_repository=FakeCodeDictRepository(make_code_dicts()),
        rice_control_window_level1_repository=FakeRiceControlWindowLevel1Repository(make_control_window()),
        calendar_item_repository=calendar_repo,
        event_record_repository=event_repo,
        weather_provider=FakeWeatherProvider(),
        diagnosis_client=FakeDiagnosisClient(),
        pest_disease_client=FakePestDiseaseSurveyWindowClient(),
    )

    items = service.recommend_regular_disease_pest_surveys(1)

    assert [item.task_subtype for item in items] == [
        TASK_SUBTYPE_REGULAR_DISEASE_PEST_SURVEY,
        TASK_SUBTYPE_REGULAR_DISEASE_PEST_SURVEY,
    ]
    assert [(item.suggested_start_date, item.suggested_end_date) for item in items] == [
        (date(2026, 5, 2), date(2026, 5, 4)),
        (date(2026, 6, 1), date(2026, 6, 3)),
    ]
    assert items[0].generation_condition["targets"] == ["二化螟"]
    assert items[0].generation_condition["sprayStage"] == "封行药"
    assert items[1].generation_condition["surveyMethod"] == "生育期"
    assert "regular:1:" not in items[0].idempotency_key
    assert "regular:2:" not in items[1].idempotency_key
    assert event_repo.items[-1].payload["algorithmCode"] == "pestDisease.init_regular_survey"


def test_recommend_regular_disease_pest_surveys_reuses_legacy_generated_item_and_invalidates_duplicate_active_item() -> None:
    generated_item = CalendarItem(
        id=10,
        planting_plan_id=1,
        task_category="plant_protection",
        task_subtype=TASK_SUBTYPE_REGULAR_DISEASE_PEST_SURVEY,
        title="旧破口药调查",
        description="旧描述",
        suggested_start_date=date(2026, 6, 1),
        suggested_end_date=date(2026, 6, 3),
        status=CALENDAR_STATUS_GENERATED,
        generation_condition={"sprayStage": "破口药"},
        idempotency_key=(
            "calendar-item:1:plant_protection.regular_disease_pest_survey:"
            "regular:1:2026-06-01:2026-06-03"
        ),
        generated_task_id=67,
    )
    duplicate_active_item = CalendarItem(
        id=11,
        planting_plan_id=1,
        task_category="plant_protection",
        task_subtype=TASK_SUBTYPE_REGULAR_DISEASE_PEST_SURVEY,
        title="重复破口药调查",
        description="重复描述",
        suggested_start_date=date(2026, 6, 1),
        suggested_end_date=date(2026, 6, 3),
        status="active",
        generation_condition={"sprayStage": "破口药"},
        idempotency_key=(
            "calendar-item:1:plant_protection.regular_disease_pest_survey:"
            "regular:2:2026-06-01:2026-06-03"
        ),
    )
    calendar_repo = FakeCalendarItemRepository(items=[generated_item, duplicate_active_item], next_id=12)
    event_repo = FakeEventRecordRepository()
    service = SurveyDateRecommendationService(
        planting_plan_repository=FakePlantingPlanRepository(make_plan_with_pest_disease_metadata()),
        farm_repository=FakeFarmRepository(make_farm()),
        rice_variety_repository=FakeRiceVarietyRepository(make_variety()),
        code_dict_repository=FakeCodeDictRepository(make_code_dicts()),
        rice_control_window_level1_repository=FakeRiceControlWindowLevel1Repository(make_control_window()),
        calendar_item_repository=calendar_repo,
        event_record_repository=event_repo,
        weather_provider=FakeWeatherProvider(),
        diagnosis_client=FakeDiagnosisClient(),
        pest_disease_client=FakePestDiseaseSurveyWindowClient(),
    )

    items = service.recommend_regular_disease_pest_surveys(1)

    assert len(items) == 2
    assert items[1] is generated_item
    assert generated_item.status == CALENDAR_STATUS_GENERATED
    assert generated_item.generated_task_id == 67
    assert "regular:1:" not in generated_item.idempotency_key
    assert "regular:2:" not in generated_item.idempotency_key
    assert duplicate_active_item.status == "invalidated"
    assert duplicate_active_item.invalidated_reason == "regular_disease_pest_survey_window_changed"
    assert len(calendar_repo.items) == 3


def test_recommend_regular_disease_pest_surveys_reuses_generated_item_when_spray_stage_changes_for_same_window() -> None:
    generated_item = CalendarItem(
        id=10,
        planting_plan_id=1,
        task_category="plant_protection",
        task_subtype=TASK_SUBTYPE_REGULAR_DISEASE_PEST_SURVEY,
        title="旧常规病虫调查",
        description="旧描述",
        suggested_start_date=date(2026, 5, 2),
        suggested_end_date=date(2026, 5, 4),
        status=CALENDAR_STATUS_GENERATED,
        generation_condition={"sprayStage": "常规病虫预防"},
        idempotency_key=(
            "calendar-item:1:plant_protection.regular_disease_pest_survey:"
            "regular:2026-05-02:2026-05-04:legacy"
        ),
        generated_task_id=67,
    )
    calendar_repo = FakeCalendarItemRepository(items=[generated_item], next_id=11)
    event_repo = FakeEventRecordRepository()
    service = SurveyDateRecommendationService(
        planting_plan_repository=FakePlantingPlanRepository(make_plan_with_pest_disease_metadata()),
        farm_repository=FakeFarmRepository(make_farm()),
        rice_variety_repository=FakeRiceVarietyRepository(make_variety()),
        code_dict_repository=FakeCodeDictRepository(make_code_dicts()),
        rice_control_window_level1_repository=FakeRiceControlWindowLevel1Repository(make_control_window()),
        calendar_item_repository=calendar_repo,
        event_record_repository=event_repo,
        weather_provider=FakeWeatherProvider(),
        diagnosis_client=FakeDiagnosisClient(),
        pest_disease_client=FakePestDiseaseSurveyWindowClient(),
    )

    items = service.recommend_regular_disease_pest_surveys(1)

    assert len(items) == 2
    assert items[0] is generated_item
    assert generated_item.status == CALENDAR_STATUS_GENERATED
    assert generated_item.generated_task_id == 67
    assert generated_item.generation_condition["sprayStage"] == "封行药"
    assert generated_item.generation_condition["rawPlan"]["spray_stage"] == "封行药"
    assert len(calendar_repo.items) == 2


def test_recommend_regular_disease_pest_surveys_does_not_reactivate_invalidated_duplicate() -> None:
    generated_item = CalendarItem(
        id=10,
        planting_plan_id=1,
        task_category="plant_protection",
        task_subtype=TASK_SUBTYPE_REGULAR_DISEASE_PEST_SURVEY,
        title="已生成封行药调查",
        description="旧描述",
        suggested_start_date=date(2026, 5, 2),
        suggested_end_date=date(2026, 5, 4),
        status=CALENDAR_STATUS_GENERATED,
        generation_condition={"sprayStage": "封行药"},
        idempotency_key=(
            "calendar-item:1:plant_protection.regular_disease_pest_survey:"
            "regular:2026-05-02:2026-05-04:legacy"
        ),
        generated_task_id=67,
    )
    invalidated_duplicate = CalendarItem(
        id=11,
        planting_plan_id=1,
        task_category="plant_protection",
        task_subtype=TASK_SUBTYPE_REGULAR_DISEASE_PEST_SURVEY,
        title="已作废重复封行药调查",
        description="旧重复描述",
        suggested_start_date=date(2026, 5, 2),
        suggested_end_date=date(2026, 5, 4),
        status=CALENDAR_STATUS_INVALIDATED,
        invalidated_reason="regular_disease_pest_survey_reused_generated_task",
        generation_condition={"sprayStage": "封行药"},
        idempotency_key="placeholder",
    )
    calendar_repo = FakeCalendarItemRepository(items=[generated_item, invalidated_duplicate], next_id=12)
    event_repo = FakeEventRecordRepository()
    service = SurveyDateRecommendationService(
        planting_plan_repository=FakePlantingPlanRepository(make_plan_with_pest_disease_metadata()),
        farm_repository=FakeFarmRepository(make_farm()),
        rice_variety_repository=FakeRiceVarietyRepository(make_variety()),
        code_dict_repository=FakeCodeDictRepository(make_code_dicts()),
        rice_control_window_level1_repository=FakeRiceControlWindowLevel1Repository(make_control_window()),
        calendar_item_repository=calendar_repo,
        event_record_repository=event_repo,
        weather_provider=FakeWeatherProvider(),
        diagnosis_client=FakeDiagnosisClient(),
        pest_disease_client=FakePestDiseaseSurveyWindowClient(),
    )
    current_plan = PestDiseaseRegularSurveyPlan(
        survey_window=(date(2026, 5, 2), date(2026, 5, 4)),
        targets=["二化螟"],
        exclude_reasons={},
        status="need_survey",
        message="当前处于可防治周期，建议按调查日期开展调查",
        spray_stage="封行药",
        survey_method="一级理论防治日期",
        adjusted=False,
        raw_plan={},
    )
    invalidated_duplicate.idempotency_key = (
        f"calendar-item:1:{service._build_regular_disease_pest_survey_idempotency_scope(current_plan)}"
    )

    items = service.recommend_regular_disease_pest_surveys(1)

    assert len(items) == 2
    assert items[0] is generated_item
    assert generated_item.status == CALENDAR_STATUS_GENERATED
    assert generated_item.idempotency_key.startswith(
        "calendar-item:1:plant_protection.regular_disease_pest_survey:regular:",
    )
    assert invalidated_duplicate.idempotency_key.startswith("retired-calendar-item:11:")
    assert invalidated_duplicate.status == CALENDAR_STATUS_INVALIDATED
    assert invalidated_duplicate.invalidated_reason == "regular_disease_pest_survey_reused_generated_task"
    assert len(calendar_repo.items) == 3


def test_recommend_regular_disease_pest_surveys_invalidates_active_duplicate_with_current_key() -> None:
    generated_item = CalendarItem(
        id=10,
        planting_plan_id=1,
        task_category="plant_protection",
        task_subtype=TASK_SUBTYPE_REGULAR_DISEASE_PEST_SURVEY,
        title="已生成封行药调查",
        description="旧描述",
        suggested_start_date=date(2026, 5, 2),
        suggested_end_date=date(2026, 5, 4),
        status=CALENDAR_STATUS_GENERATED,
        generation_condition={"sprayStage": "封行药"},
        idempotency_key=(
            "calendar-item:1:plant_protection.regular_disease_pest_survey:"
            "regular:2026-05-02:2026-05-04:legacy"
        ),
        generated_task_id=67,
    )
    active_duplicate = CalendarItem(
        id=11,
        planting_plan_id=1,
        task_category="plant_protection",
        task_subtype=TASK_SUBTYPE_REGULAR_DISEASE_PEST_SURVEY,
        title="重复封行药调查",
        description="旧重复描述",
        suggested_start_date=date(2026, 5, 2),
        suggested_end_date=date(2026, 5, 4),
        status="active",
        generation_condition={"sprayStage": "封行药"},
        idempotency_key="placeholder",
    )
    calendar_repo = FakeCalendarItemRepository(items=[generated_item, active_duplicate], next_id=12)
    service = SurveyDateRecommendationService(
        planting_plan_repository=FakePlantingPlanRepository(make_plan_with_pest_disease_metadata()),
        farm_repository=FakeFarmRepository(make_farm()),
        rice_variety_repository=FakeRiceVarietyRepository(make_variety()),
        code_dict_repository=FakeCodeDictRepository(make_code_dicts()),
        rice_control_window_level1_repository=FakeRiceControlWindowLevel1Repository(make_control_window()),
        calendar_item_repository=calendar_repo,
        event_record_repository=FakeEventRecordRepository(),
        weather_provider=FakeWeatherProvider(),
        diagnosis_client=FakeDiagnosisClient(),
        pest_disease_client=FakePestDiseaseSurveyWindowClient(),
    )
    current_plan = PestDiseaseRegularSurveyPlan(
        survey_window=(date(2026, 5, 2), date(2026, 5, 4)),
        targets=["二化螟"],
        exclude_reasons={},
        status="need_survey",
        message="当前处于可防治周期，建议按调查日期开展调查",
        spray_stage="封行药",
        survey_method="一级理论防治日期",
        adjusted=False,
        raw_plan={},
    )
    active_duplicate.idempotency_key = (
        f"calendar-item:1:{service._build_regular_disease_pest_survey_idempotency_scope(current_plan)}"
    )

    items = service.recommend_regular_disease_pest_surveys(1)

    assert len(items) == 2
    assert items[0] is generated_item
    assert generated_item.status == CALENDAR_STATUS_GENERATED
    assert active_duplicate.status == CALENDAR_STATUS_INVALIDATED
    assert active_duplicate.invalidated_reason == "regular_disease_pest_survey_window_changed"
    assert active_duplicate.idempotency_key.startswith("retired-calendar-item:11:")
    assert len(calendar_repo.items) == 3


def test_recommend_regular_disease_pest_surveys_reuses_generated_item_when_window_shifts_for_same_spray_stage() -> None:
    generated_item = CalendarItem(
        id=10,
        planting_plan_id=1,
        task_category="plant_protection",
        task_subtype=TASK_SUBTYPE_REGULAR_DISEASE_PEST_SURVEY,
        title="旧破口药调查",
        description="旧描述",
        suggested_start_date=date(2026, 6, 2),
        suggested_end_date=date(2026, 6, 4),
        status=CALENDAR_STATUS_GENERATED,
        generation_condition={"sprayStage": "破口药"},
        idempotency_key=(
            "calendar-item:1:plant_protection.regular_disease_pest_survey:"
            "regular:2026-06-02:2026-06-04:legacy"
        ),
        generated_task_id=67,
    )
    calendar_repo = FakeCalendarItemRepository(items=[generated_item], next_id=11)
    event_repo = FakeEventRecordRepository()
    service = SurveyDateRecommendationService(
        planting_plan_repository=FakePlantingPlanRepository(make_plan_with_pest_disease_metadata()),
        farm_repository=FakeFarmRepository(make_farm()),
        rice_variety_repository=FakeRiceVarietyRepository(make_variety()),
        code_dict_repository=FakeCodeDictRepository(make_code_dicts()),
        rice_control_window_level1_repository=FakeRiceControlWindowLevel1Repository(make_control_window()),
        calendar_item_repository=calendar_repo,
        event_record_repository=event_repo,
        weather_provider=FakeWeatherProvider(),
        diagnosis_client=FakeDiagnosisClient(),
        pest_disease_client=FakePestDiseaseSurveyWindowClient(),
    )

    items = service.recommend_regular_disease_pest_surveys(1)

    assert len(items) == 2
    assert items[1] is generated_item
    assert generated_item.status == CALENDAR_STATUS_GENERATED
    assert generated_item.generated_task_id == 67
    assert generated_item.suggested_start_date == date(2026, 6, 1)
    assert generated_item.suggested_end_date == date(2026, 6, 3)
    assert generated_item.generation_condition["sprayStage"] == "破口药"
    assert len(calendar_repo.items) == 2


def test_recommend_regular_disease_pest_surveys_updates_pending_task_when_generated_window_changes() -> None:
    generated_item = CalendarItem(
        id=10,
        planting_plan_id=1,
        task_category="plant_protection",
        task_subtype=TASK_SUBTYPE_REGULAR_DISEASE_PEST_SURVEY,
        title="旧破口药调查",
        description="旧描述",
        suggested_start_date=date(2026, 6, 2),
        suggested_end_date=date(2026, 6, 4),
        status=CALENDAR_STATUS_GENERATED,
        generation_condition={"sprayStage": "破口药"},
        idempotency_key=(
            "calendar-item:1:plant_protection.regular_disease_pest_survey:"
            "regular:2026-06-02:2026-06-04:legacy"
        ),
        generated_task_id=67,
    )
    generated_task = FarmingTask(
        id=67,
        planting_plan_id=1,
        calendar_item_id=10,
        task_category="plant_protection",
        task_subtype=TASK_SUBTYPE_REGULAR_DISEASE_PEST_SURVEY,
        title="旧破口药调查",
        description="旧描述",
        planned_start_at=datetime(2026, 6, 2),
        planned_end_at=datetime(2026, 6, 4, 23, 59, 59),
        status="pending",
        priority="normal",
        execution_mode="manual",
        idempotency_key="farming-task:calendar-item:10",
        created_by_type="system",
        created_by_id="TaskDueCheckJob",
    )
    calendar_repo = FakeCalendarItemRepository(items=[generated_item], next_id=11)
    farming_task_repo = FakeFarmingTaskRepository(items=[generated_task])
    service = SurveyDateRecommendationService(
        planting_plan_repository=FakePlantingPlanRepository(make_plan_with_pest_disease_metadata()),
        farm_repository=FakeFarmRepository(make_farm()),
        rice_variety_repository=FakeRiceVarietyRepository(make_variety()),
        code_dict_repository=FakeCodeDictRepository(make_code_dicts()),
        rice_control_window_level1_repository=FakeRiceControlWindowLevel1Repository(make_control_window()),
        calendar_item_repository=calendar_repo,
        event_record_repository=FakeEventRecordRepository(),
        weather_provider=FakeWeatherProvider(),
        diagnosis_client=FakeDiagnosisClient(),
        pest_disease_client=FakePestDiseaseSurveyWindowClient(),
        farming_task_repository=farming_task_repo,
    )

    items = service.recommend_regular_disease_pest_surveys(1)

    assert items[1] is generated_item
    assert generated_item.suggested_start_date == date(2026, 6, 1)
    assert generated_item.suggested_end_date == date(2026, 6, 3)
    assert generated_task.planned_start_at.date() == date(2026, 6, 1)
    assert generated_task.planned_end_at.date() == date(2026, 6, 3)
    assert generated_task.title == "病虫害常规调查"
    assert "pestDisease init-regular-survey" in generated_task.description
    assert len(calendar_repo.items) == 2


def test_recommend_regular_disease_pest_surveys_keeps_completed_task_when_generated_window_changes() -> None:
    generated_item = CalendarItem(
        id=10,
        planting_plan_id=1,
        task_category="plant_protection",
        task_subtype=TASK_SUBTYPE_REGULAR_DISEASE_PEST_SURVEY,
        title="旧破口药调查",
        description="旧描述",
        suggested_start_date=date(2026, 6, 2),
        suggested_end_date=date(2026, 6, 4),
        status=CALENDAR_STATUS_GENERATED,
        generation_condition={"sprayStage": "破口药"},
        idempotency_key=(
            "calendar-item:1:plant_protection.regular_disease_pest_survey:"
            "regular:2026-06-02:2026-06-04:legacy"
        ),
        generated_task_id=67,
    )
    generated_task = FarmingTask(
        id=67,
        planting_plan_id=1,
        calendar_item_id=10,
        task_category="plant_protection",
        task_subtype=TASK_SUBTYPE_REGULAR_DISEASE_PEST_SURVEY,
        title="已完成破口药调查",
        description="已完成描述",
        planned_start_at=datetime(2026, 6, 2),
        planned_end_at=datetime(2026, 6, 4, 23, 59, 59),
        status="completed",
        priority="normal",
        execution_mode="manual",
        idempotency_key="farming-task:calendar-item:10",
        created_by_type="system",
        created_by_id="TaskDueCheckJob",
    )
    calendar_repo = FakeCalendarItemRepository(items=[generated_item], next_id=11)
    farming_task_repo = FakeFarmingTaskRepository(items=[generated_task])
    service = SurveyDateRecommendationService(
        planting_plan_repository=FakePlantingPlanRepository(make_plan_with_pest_disease_metadata()),
        farm_repository=FakeFarmRepository(make_farm()),
        rice_variety_repository=FakeRiceVarietyRepository(make_variety()),
        code_dict_repository=FakeCodeDictRepository(make_code_dicts()),
        rice_control_window_level1_repository=FakeRiceControlWindowLevel1Repository(make_control_window()),
        calendar_item_repository=calendar_repo,
        event_record_repository=FakeEventRecordRepository(),
        weather_provider=FakeWeatherProvider(),
        diagnosis_client=FakeDiagnosisClient(),
        pest_disease_client=FakePestDiseaseSurveyWindowClient(),
        farming_task_repository=farming_task_repo,
    )

    items = service.recommend_regular_disease_pest_surveys(1)

    assert items[1] is generated_item
    assert generated_item.suggested_start_date == date(2026, 6, 2)
    assert generated_item.suggested_end_date == date(2026, 6, 4)
    assert generated_task.planned_start_at.date() == date(2026, 6, 2)
    assert generated_task.planned_end_at.date() == date(2026, 6, 4)
    assert len(calendar_repo.items) == 2


def test_recommend_regular_disease_pest_surveys_skips_plan_without_metadata() -> None:
    service = SurveyDateRecommendationService(
        planting_plan_repository=FakePlantingPlanRepository(make_plan()),
        farm_repository=FakeFarmRepository(make_farm()),
        rice_variety_repository=FakeRiceVarietyRepository(make_variety()),
        code_dict_repository=FakeCodeDictRepository(make_code_dicts()),
        rice_control_window_level1_repository=FakeRiceControlWindowLevel1Repository(make_control_window()),
        calendar_item_repository=FakeCalendarItemRepository(),
        event_record_repository=FakeEventRecordRepository(),
        weather_provider=FakeWeatherProvider(),
        diagnosis_client=FakeDiagnosisClient(),
        pest_disease_client=FakePestDiseaseSurveyWindowClient(),
    )

    assert service.recommend_regular_disease_pest_surveys(1) == []


def test_recommend_regular_disease_pest_surveys_uses_latest_stage_snapshot_growth_stage() -> None:
    calendar_repo = FakeCalendarItemRepository()
    event_repo = FakeEventRecordRepository()
    snapshot_repo = FakeStagePredictionSnapshotRepository(
        latest_snapshot=StagePredictionSnapshot(
            id=10,
            planting_plan_id=1,
            prediction_version=2,
            prediction_source="plan_change",
            algorithm_code="stage_prediction_algorithm",
            algorithm_version="v1.0.0",
            stage_timeline={
                "stages": [
                    {
                        "stage_code": "tillering",
                        "stage_name": "分蘖期",
                        "start_date": "2026-04-20",
                        "end_date": "2026-06-09",
                        "key_date": "2026-04-20",
                    },
                    {
                        "stage_code": "pokou",
                        "stage_name": "破口期",
                        "start_date": "2026-06-10",
                        "end_date": "2026-06-17",
                        "key_date": "2026-06-10",
                    },
                    {
                        "stage_code": "heading",
                        "stage_name": "齐穗期",
                        "start_date": "2026-06-18",
                        "end_date": "2026-07-19",
                        "key_date": "2026-06-18",
                    },
                    {
                        "stage_code": "maturity",
                        "stage_name": "成熟期",
                        "start_date": "2026-07-20",
                        "end_date": "2026-07-20",
                        "key_date": "2026-07-20",
                    },
                ],
            },
            thermal_thresholds={},
        ),
    )
    service = SurveyDateRecommendationService(
        planting_plan_repository=FakePlantingPlanRepository(make_plan_with_pest_disease_growth_stage_only()),
        farm_repository=FakeFarmRepository(make_farm()),
        rice_variety_repository=FakeRiceVarietyRepository(make_variety()),
        code_dict_repository=FakeCodeDictRepository(make_code_dicts()),
        rice_control_window_level1_repository=FakeRiceControlWindowLevel1Repository(make_control_window()),
        calendar_item_repository=calendar_repo,
        event_record_repository=event_repo,
        weather_provider=FakeWeatherProvider(),
        diagnosis_client=FakeDiagnosisClient(),
        pest_disease_client=FakePestDiseaseSurveyWindowClient(),
        stage_prediction_snapshot_repository=snapshot_repo,
    )

    items = service.recommend_regular_disease_pest_surveys(1)

    assert len(items) == 2
    assert items[0].generation_condition["targets"] == ["二化螟"]


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


def test_generate_due_tasks_handles_regular_disease_pest_survey_calendar_item() -> None:
    calendar_item = CalendarItem(
        id=1,
        planting_plan_id=1,
        task_category="plant_protection",
        task_subtype=TASK_SUBTYPE_REGULAR_DISEASE_PEST_SURVEY,
        title="病虫害常规调查",
        description="调查病虫害情况",
        suggested_start_date=date(2026, 5, 2),
        suggested_end_date=date(2026, 5, 4),
        status="active",
        idempotency_key="calendar-item:1:pest-disease",
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

    tasks = service.generate_due_tasks(1, check_date=date(2026, 4, 20))

    assert len(tasks) == 1
    assert tasks[0].task_subtype == TASK_SUBTYPE_REGULAR_DISEASE_PEST_SURVEY
    assert tasks[0].planned_start_at.date() == date(2026, 5, 2)
    assert tasks[0].planned_end_at.date() == date(2026, 5, 4)
    assert calendar_item.status == CALENDAR_STATUS_GENERATED


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


def test_http_weed_diagnosis_client_normalizes_internal_weather_rows_for_pre_survey(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = HttpWeedDiagnosisClient("http://diagnosis.local")
    captured_payload: dict[str, Any] = {}

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return b'{"code":200,"data":{"pre_stem_leaf_herbicide_survey_date":"20260418"}}'

    def fake_urlopen(req, timeout):
        del timeout
        captured_payload.update(__import__("json").loads(req.data.decode("utf-8")))
        return FakeResponse()

    monkeypatch.setattr("app.services.calendar_tasks.request.urlopen", fake_urlopen)

    result = client.recommend_pre_treatment_survey_date(
        weather_data=[
            {
                "date": "2026-04-09",
                "avg_temp": 24.5,
                "source_type": "observed",
                "data_version": "weather-observed:2026-04-09:2026-04-09",
            },
        ],
        rice_type="籼稻",
        cultivation_system="早稻",
        cultivation_pattern="直播",
        cultivation_date=date(2026, 4, 10),
    )

    assert result.recommendation_date == date(2026, 4, 18)
    assert captured_payload["weather_data"] == [{"DATE": "20260409", "TEMP": 24.5}]


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


def test_http_weed_diagnosis_client_logs_response_summary(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = HttpWeedDiagnosisClient("http://diagnosis.local")

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return b'{"code":200,"data":{"need_mitigation":true,"measures":["\\u5c3f\\u7d203\\u516c\\u65a4/\\u4ea9"]}}'

    monkeypatch.setattr("app.services.calendar_tasks.request.urlopen", lambda *args, **kwargs: FakeResponse())

    with caplog.at_level(logging.INFO):
        result = client.diagnose_injury_mitigation(
            survey_date=date(2026, 4, 22),
            rice_injury_level="中",
        )

    assert result.need_mitigation is True
    assert "Calling weed diagnosis API" in caplog.text
    assert "Weed diagnosis API succeeded" in caplog.text
    assert "need_mitigation" in caplog.text


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


def test_http_weed_diagnosis_client_surfaces_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    client = HttpWeedDiagnosisClient("http://diagnosis.local")

    def fake_urlopen(*args, **kwargs):
        raise TimeoutError("timed out")

    monkeypatch.setattr("app.services.calendar_tasks.request.urlopen", fake_urlopen)

    with pytest.raises(RuntimeError, match="timed out"):
        client.diagnose_injury_mitigation(
            survey_date=date(2026, 4, 22),
            rice_injury_level="无",
        )


def test_http_weed_diagnosis_client_surfaces_missing_required_field(monkeypatch: pytest.MonkeyPatch) -> None:
    client = HttpWeedDiagnosisClient("http://diagnosis.local")

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return b'{"code":200,"data":{}}'

    monkeypatch.setattr("app.services.calendar_tasks.request.urlopen", lambda *args, **kwargs: FakeResponse())

    with pytest.raises(ValueError, match="did not return need_mitigation"):
        client.diagnose_injury_mitigation(
            survey_date=date(2026, 4, 22),
            rice_injury_level="无",
        )
