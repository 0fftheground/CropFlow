from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from app.core.constants import EVENT_TYPE_PLAN_CREATED, EVENT_TYPE_WEATHER_UPDATED
from app.models import CalendarItem, CodeDict, EventRecord, Farm, PlantingPlan, RiceControlWindowLevel1, ReviewRequest, RiceVariety, TaskIntent
from app.orchestrator.core import PlanCalendarRefreshHandler
from app.services.calendar_tasks import (
    MockWeatherProvider,
    MockWeedDiagnosisClient,
    PlantProtectionPlanContextResolver,
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

    def list_current_by_plan(self, planting_plan_id: int) -> list[TaskIntent]:
        return [
            item
            for item in self.items
            if item.planting_plan_id == planting_plan_id and item.status not in {"converted", "rejected", "no_action"}
        ]


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

    def list_current_by_plan(self, planting_plan_id: int) -> list[ReviewRequest]:
        return [
            item
            for item in self.items
            if item.planting_plan_id == planting_plan_id and item.status not in {"resolved", "cancelled"}
        ]


def _make_plan(*, metadata_payload: dict | None = None) -> PlantingPlan:
    return PlantingPlan(
        id=1,
        plan_code="PLAN-001",
        plan_name="测试计划",
        farm_id=1,
        year=2026,
        culti_type_code=5,
        planting_method_code=1,
        crop_name="水稻",
        variety_id=1,
        variety_name="黄广农占",
        sowing_date=date(2026, 4, 10),
        task_generation_window_days=14,
        metadata_payload=metadata_payload or {"province": "湖南省"},
    )


def _make_variety() -> RiceVariety:
    return RiceVariety(id=1, name="黄广农占", sub_type_code=9)


def _make_code_dicts() -> dict[int, CodeDict]:
    return {
        1: CodeDict(id=1, code=1, code_name="直播", category="sowingmtd"),
        5: CodeDict(id=5, code=5, code_name="早稻", category="culti_type"),
        9: CodeDict(id=9, code=9, code_name="籼", category="sub_type"),
    }


def _make_farm() -> Farm:
    return Farm(
        id=1,
        farm_name="测试农场",
        province="湖南省",
        city="益阳市",
        district_county="桃江县",
    )


def _make_control_window() -> RiceControlWindowLevel1:
    return RiceControlWindowLevel1(
        id=1,
        province="湖南省",
        city="益阳市",
        county="桃江县",
        data_year=2026,
        detail={"1": ["0509", "0513"]},
    )


def test_plan_refresh_creates_soil_treatment_review_and_pre_survey_calendar_item() -> None:
    calendar_repo = FakeCalendarItemRepository()
    event_repo = FakeEventRecordRepository()
    task_intent_repo = FakeTaskIntentRepository()
    review_repo = FakeReviewRequestRepository()
    service = SurveyDateRecommendationService(
        planting_plan_repository=FakePlantingPlanRepository(_make_plan()),
        farm_repository=FakeFarmRepository(_make_farm()),
        rice_variety_repository=FakeRiceVarietyRepository(_make_variety()),
        code_dict_repository=FakeCodeDictRepository(_make_code_dicts()),
        rice_control_window_level1_repository=FakeRiceControlWindowLevel1Repository(_make_control_window()),
        calendar_item_repository=calendar_repo,
        event_record_repository=event_repo,
        weather_provider=MockWeatherProvider(),
        diagnosis_client=MockWeedDiagnosisClient(),
    )
    handler = PlanCalendarRefreshHandler(
        survey_date_recommendation_service=service,
        event_record_repository=event_repo,
        task_intent_repository=task_intent_repo,
        review_request_repository=review_repo,
    )

    result = handler.handle(
        EventRecord(
            planting_plan_id=1,
            event_type=EVENT_TYPE_PLAN_CREATED,
            event_category="plan",
            event_source="api",
            source_system="cropflow",
            payload={"planCode": "PLAN-001"},
            occurred_at=datetime.now(UTC).replace(tzinfo=None),
            processing_status="received",
            idempotency_key="plan-created:1",
            created_by_type="user",
            created_by_id="api",
        ),
    )

    assert [item.task_subtype for item in result.calendar_items] == ["plant_protection.stem_leaf_weed_pre_survey"]
    assert len(result.task_intents) == 1
    assert result.task_intents[0].task_subtype == "plant_protection.soil_sealing_weed_control"
    assert result.task_intents[0].rule_result["algorithmCode"] == "soil_treatment_diagnosis"
    assert result.task_intents[0].rule_result["proposedPlan"]["operationAction"] == "苗后封闭"
    assert len(result.review_requests) == 1
    assert result.review_requests[0].review_type == "soil_treatment_recommendation"
    assert result.review_requests[0].source_entity_id == result.task_intents[0].id


def test_forecast_weather_update_does_not_refresh_calendar() -> None:
    calendar_repo = FakeCalendarItemRepository()
    event_repo = FakeEventRecordRepository()
    task_intent_repo = FakeTaskIntentRepository()
    review_repo = FakeReviewRequestRepository()
    service = SurveyDateRecommendationService(
        planting_plan_repository=FakePlantingPlanRepository(_make_plan()),
        farm_repository=FakeFarmRepository(_make_farm()),
        rice_variety_repository=FakeRiceVarietyRepository(_make_variety()),
        code_dict_repository=FakeCodeDictRepository(_make_code_dicts()),
        rice_control_window_level1_repository=FakeRiceControlWindowLevel1Repository(_make_control_window()),
        calendar_item_repository=calendar_repo,
        event_record_repository=event_repo,
        weather_provider=MockWeatherProvider(),
        diagnosis_client=MockWeedDiagnosisClient(),
    )
    handler = PlanCalendarRefreshHandler(
        survey_date_recommendation_service=service,
        event_record_repository=event_repo,
        task_intent_repository=task_intent_repo,
        review_request_repository=review_repo,
    )

    result = handler.handle(
        EventRecord(
            planting_plan_id=1,
            event_type=EVENT_TYPE_WEATHER_UPDATED,
            event_category="job",
            event_source="background_job",
            source_system="cropflow",
            payload={"weatherDate": "2026-05-29", "sourceType": "forecast"},
            occurred_at=datetime.now(UTC).replace(tzinfo=None),
            processing_status="received",
            idempotency_key="weather-updated:forecast:1",
            created_by_type="system",
            created_by_id="DailyWeatherCheckJob",
        ),
    )

    assert result.calendar_items == []
    assert result.task_intents == []
    assert result.review_requests == []


def test_weather_update_with_pest_metadata_creates_sudden_disease_pest_calendar_item() -> None:
    class TyphoonWeatherProvider(MockWeatherProvider):
        def get_typhoon_alerts(self, planting_plan: PlantingPlan) -> list[dict[str, object]]:
            return [{"eventType": "台风预警", "effective": "20260529080000"}]

    calendar_repo = FakeCalendarItemRepository()
    event_repo = FakeEventRecordRepository()
    task_intent_repo = FakeTaskIntentRepository()
    review_repo = FakeReviewRequestRepository()
    service = SurveyDateRecommendationService(
        planting_plan_repository=FakePlantingPlanRepository(
            _make_plan(
                metadata_payload={
                    "province": "湖南省",
                    "pestDisease": {
                        "growth_stage": {
                            "tillering_date": "2026-04-20",
                            "pokou_date": "2026-06-10",
                            "heading_date": "2026-06-18",
                            "maturity_date": "2026-07-20",
                        },
                    },
                },
            ),
        ),
        farm_repository=FakeFarmRepository(_make_farm()),
        rice_variety_repository=FakeRiceVarietyRepository(_make_variety()),
        code_dict_repository=FakeCodeDictRepository(_make_code_dicts()),
        rice_control_window_level1_repository=FakeRiceControlWindowLevel1Repository(_make_control_window()),
        calendar_item_repository=calendar_repo,
        event_record_repository=event_repo,
        weather_provider=TyphoonWeatherProvider(),
        diagnosis_client=MockWeedDiagnosisClient(),
    )
    handler = PlanCalendarRefreshHandler(
        survey_date_recommendation_service=service,
        event_record_repository=event_repo,
        task_intent_repository=task_intent_repo,
        review_request_repository=review_repo,
    )

    result = handler.handle(
        EventRecord(
            planting_plan_id=1,
            event_type=EVENT_TYPE_WEATHER_UPDATED,
            event_category="job",
            event_source="background_job",
            source_system="cropflow",
            payload={"weatherDate": "2026-05-29", "sourceType": "observed"},
            occurred_at=datetime.now(UTC).replace(tzinfo=None),
            processing_status="received",
            idempotency_key="weather-updated:observed:1",
            created_by_type="system",
            created_by_id="DailyWeatherCheckJob",
        ),
    )

    task_subtypes = [item.task_subtype for item in result.calendar_items]
    assert "plant_protection.regular_disease_pest_survey" in task_subtypes
    assert "plant_protection.sudden_disease_pest_survey" in task_subtypes
