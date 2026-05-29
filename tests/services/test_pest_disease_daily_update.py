from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from app.models import CalendarItem, CodeDict, PlantingPlan, RiceVariety
from app.services.calendar_tasks import (
    PestDiseaseDailyUpdateResult,
    SurveyDateRecommendationService,
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
class FakeEventRecordRepository:
    items: list[object] = field(default_factory=list)

    def add(self, item: object) -> object:
        self.items.append(item)
        return item


class FakeWeatherProvider:
    def __init__(self) -> None:
        self.daily_requests: list[tuple[date, date]] = []
        self.hourly_requests: list[datetime] = []
        self.alert_requests: list[int] = []

    def get_daily_weather(self, planting_plan: PlantingPlan, start_date: date, end_date: date, *, as_of_date=None):
        raise AssertionError("get_daily_weather should not be used for pest disease daily update.")

    def get_pest_disease_daily_weather(
        self,
        planting_plan: PlantingPlan,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, object]]:
        self.daily_requests.append((start_date, end_date))
        return [{"DATE": "20260529", "TMAX": 30.5, "RAIN": 1.2, "SUN": 4.0}]

    def get_hourly_weather_72h(
        self,
        planting_plan: PlantingPlan,
        *,
        as_of_datetime: datetime | None = None,
    ) -> list[dict[str, object]]:
        assert as_of_datetime is not None
        self.hourly_requests.append(as_of_datetime)
        return [{"datetime": "2026-05-29 00:00:00", "pre": 1.0, "wins": 5.0, "gust": 7.0, "wp": "阵雨"}]

    def get_typhoon_alerts(self, planting_plan: PlantingPlan) -> list[dict[str, object]]:
        self.alert_requests.append(planting_plan.id)
        return [{"eventType": "台风预警", "effective": "20260529080000"}]


class FakeDiagnosisClient:
    pass


class FakePestDiseaseClient:
    def __init__(self) -> None:
        self.daily_update_calls: list[dict[str, object]] = []

    def init_regular_surveys(self, **kwargs):
        raise AssertionError("init_regular_surveys should not be used when active regular survey items exist.")

    def daily_update_surveys(
        self,
        *,
        growth_stage: dict[str, str],
        regular_plans: list[dict[str, object]],
        weather_data: list[dict[str, object]],
        typhoon_data: dict[str, object],
        actual_control_date: date | None = None,
    ) -> PestDiseaseDailyUpdateResult:
        self.daily_update_calls.append(
            {
                "growth_stage": growth_stage,
                "regular_plans": regular_plans,
                "weather_data": weather_data,
                "typhoon_data": typhoon_data,
                "actual_control_date": actual_control_date,
            },
        )
        return PestDiseaseDailyUpdateResult(
            status="new_emergency",
            message="已识别到临时调查触发条件，建议开展临时调查",
            survey_window=(date(2026, 6, 1), date(2026, 6, 2)),
            spray_stage="突发病虫防治",
            targets=["稻飞虱"],
            exclude_reasons={},
            source="emergency",
            raw_result={"mock": True},
            raw_response={"code": 200},
        )


def _make_plan() -> PlantingPlan:
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
        metadata_payload={
            "pestDisease": {
                "growth_stage": {
                    "tillering_date": "2026-04-20",
                    "pokou_date": "2026-06-10",
                    "heading_date": "2026-06-18",
                    "maturity_date": "2026-07-20",
                },
                "level1_of_year": {
                    "1": ["0509", "0513"],
                },
            },
        },
    )


def _make_variety() -> RiceVariety:
    return RiceVariety(id=1, name="黄广农占", sub_type_code=9)


def _make_code_dicts() -> dict[int, CodeDict]:
    return {
        1: CodeDict(id=1, code=1, code_name="直播", category="sowingmtd"),
        5: CodeDict(id=5, code=5, code_name="早稻", category="culti_type"),
        9: CodeDict(id=9, code=9, code_name="籼", category="sub_type"),
    }


def _make_regular_calendar_item() -> CalendarItem:
    return CalendarItem(
        id=10,
        planting_plan_id=1,
        task_category="plant_protection",
        task_subtype="plant_protection.regular_disease_pest_survey",
        title="病虫害常规调查",
        description="调查病虫害情况",
        suggested_start_date=date(2026, 5, 30),
        suggested_end_date=date(2026, 6, 1),
        status="active",
        generation_condition={
            "rawPlan": {
                "status": "need_survey",
                "调查日期": ["20260530", "20260601"],
                "spray_stage": "封行药",
                "survey_method": "一级理论防治日期",
                "调查对象": ["二化螟", "稻飞虱"],
                "排除原因": {},
                "msg": "当前处于可防治周期，建议按调查日期开展调查",
            },
        },
        idempotency_key="calendar-item:regular:1",
    )


def test_build_pest_disease_daily_update_payload_uses_farm_hourly_and_alert_sources() -> None:
    weather_provider = FakeWeatherProvider()
    service = SurveyDateRecommendationService(
        planting_plan_repository=FakePlantingPlanRepository(_make_plan()),
        rice_variety_repository=FakeRiceVarietyRepository(_make_variety()),
        code_dict_repository=FakeCodeDictRepository(_make_code_dicts()),
        calendar_item_repository=FakeCalendarItemRepository(items=[_make_regular_calendar_item()]),
        event_record_repository=FakeEventRecordRepository(),
        weather_provider=weather_provider,
        diagnosis_client=FakeDiagnosisClient(),
        pest_disease_client=FakePestDiseaseClient(),
    )

    payload = service.build_pest_disease_daily_update_payload(
        1,
        as_of_date=date(2026, 5, 29),
        actual_control_date=date(2026, 5, 28),
    )

    assert payload is not None
    assert payload["regular_plans"] == [
        {
            "status": "need_survey",
            "调查日期": ["20260530", "20260601"],
            "spray_stage": "封行药",
            "survey_method": "一级理论防治日期",
            "调查对象": ["二化螟", "稻飞虱"],
            "排除原因": {},
            "msg": "当前处于可防治周期，建议按调查日期开展调查",
        },
    ]
    assert payload["weather_data"] == [{"DATE": "20260529", "TMAX": 30.5, "RAIN": 1.2, "SUN": 4.0}]
    assert payload["typhoon_data"]["alerts"] == [{"eventType": "台风预警", "effective": "20260529080000"}]
    assert payload["typhoon_data"]["hourly_weather_72h"] == [
        {"datetime": "2026-05-29 00:00:00", "pre": 1.0, "wins": 5.0, "gust": 7.0, "wp": "阵雨"},
    ]
    assert payload["actual_control_date"] == "20260528"
    assert weather_provider.daily_requests == [(date(2026, 5, 21), date(2026, 6, 5))]
    assert weather_provider.hourly_requests == [datetime(2026, 5, 29, 0, 0, 0)]
    assert weather_provider.alert_requests == [1]


def test_run_pest_disease_daily_update_calls_client_with_built_payload() -> None:
    weather_provider = FakeWeatherProvider()
    pest_disease_client = FakePestDiseaseClient()
    service = SurveyDateRecommendationService(
        planting_plan_repository=FakePlantingPlanRepository(_make_plan()),
        rice_variety_repository=FakeRiceVarietyRepository(_make_variety()),
        code_dict_repository=FakeCodeDictRepository(_make_code_dicts()),
        calendar_item_repository=FakeCalendarItemRepository(items=[_make_regular_calendar_item()]),
        event_record_repository=FakeEventRecordRepository(),
        weather_provider=weather_provider,
        diagnosis_client=FakeDiagnosisClient(),
        pest_disease_client=pest_disease_client,
    )

    result = service.run_pest_disease_daily_update(
        1,
        as_of_date=date(2026, 5, 29),
        actual_control_date=date(2026, 5, 28),
    )

    assert result is not None
    assert result.status == "new_emergency"
    assert result.survey_window == (date(2026, 6, 1), date(2026, 6, 2))
    assert len(pest_disease_client.daily_update_calls) == 1
    assert pest_disease_client.daily_update_calls[0]["actual_control_date"] == date(2026, 5, 28)
