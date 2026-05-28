from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from app.models import CropStageState, CropThermalTimeState, Farm, PlantingPlan, StagePredictionSnapshot
from app.services.stage_management import (
    MockStagePredictionClient,
    StageManagementService,
    extract_pest_disease_growth_stage,
)


@dataclass
class FakePlantingPlanRepository:
    plan: PlantingPlan

    def get(self, planting_plan_id: int) -> PlantingPlan | None:
        return self.plan if self.plan.id == planting_plan_id else None


@dataclass
class FakeFarmRepository:
    farm: Farm

    def get(self, farm_id: int) -> Farm | None:
        return self.farm if self.farm.id == farm_id else None


@dataclass
class FakeStagePredictionSnapshotRepository:
    items: list[StagePredictionSnapshot] = field(default_factory=list)
    next_id: int = 1

    def add(self, snapshot: StagePredictionSnapshot) -> StagePredictionSnapshot:
        self.items.append(snapshot)
        return snapshot

    def flush(self) -> None:
        for snapshot in self.items:
            if snapshot.id is None:
                snapshot.id = self.next_id
                self.next_id += 1

    def get_latest_by_plan(self, planting_plan_id: int) -> StagePredictionSnapshot | None:
        snapshots = [item for item in self.items if item.planting_plan_id == planting_plan_id]
        return max(snapshots, key=lambda item: (item.prediction_version, item.id or 0)) if snapshots else None


@dataclass
class FakeCropStageStateRepository:
    items: dict[int, CropStageState] = field(default_factory=dict)
    next_id: int = 1

    def add(self, state: CropStageState) -> CropStageState:
        if state.id is None:
            state.id = self.next_id
            self.next_id += 1
        self.items[state.planting_plan_id] = state
        return state

    def get_by_plan(self, planting_plan_id: int) -> CropStageState | None:
        return self.items.get(planting_plan_id)


@dataclass
class FakeCropThermalTimeStateRepository:
    items: dict[int, CropThermalTimeState] = field(default_factory=dict)
    next_id: int = 1

    def add(self, state: CropThermalTimeState) -> CropThermalTimeState:
        if state.id is None:
            state.id = self.next_id
            self.next_id += 1
        self.items[state.planting_plan_id] = state
        return state

    def get_by_plan(self, planting_plan_id: int) -> CropThermalTimeState | None:
        return self.items.get(planting_plan_id)


@dataclass
class FakeWeatherProvider:
    calls: list[tuple[date, date]] = field(default_factory=list)

    def get_daily_weather(
        self,
        planting_plan: PlantingPlan,
        start_date: date,
        end_date: date,
        *,
        as_of_date: date | None = None,
    ) -> list[dict[str, Any]]:
        self.calls.append((start_date, end_date))
        weather_data: list[dict[str, Any]] = []
        current_date = start_date
        while current_date <= end_date:
            weather_data.append(
                {
                    "DATE": current_date.strftime("%Y%m%d"),
                    "TEMP": 26,
                },
            )
            current_date = date.fromordinal(current_date.toordinal() + 1)
        return weather_data


def _make_plan() -> PlantingPlan:
    return PlantingPlan(
        id=1,
        plan_code="PLAN-001",
        plan_name="测试计划",
        farm_id=1,
        culti_type_code=5,
        planting_method_code=1,
        crop_name="水稻",
        variety_id=3,
        variety_name="黄广农占",
        sowing_date=date(2026, 4, 10),
        task_generation_window_days=14,
        metadata_payload={},
    )


def _make_farm() -> Farm:
    return Farm(
        id=1,
        farm_name="测试农场",
        province="湖南省",
        city="长沙市",
        district_county="浏阳市",
        adcode="430181",
    )


def test_refresh_prediction_creates_stage_snapshot_and_states() -> None:
    snapshot_repo = FakeStagePredictionSnapshotRepository()
    stage_repo = FakeCropStageStateRepository()
    thermal_repo = FakeCropThermalTimeStateRepository()
    weather_provider = FakeWeatherProvider()
    service = StageManagementService(
        planting_plan_repository=FakePlantingPlanRepository(_make_plan()),
        farm_repository=FakeFarmRepository(_make_farm()),
        stage_prediction_snapshot_repository=snapshot_repo,
        crop_stage_state_repository=stage_repo,
        crop_thermal_time_state_repository=thermal_repo,
        stage_prediction_client=MockStagePredictionClient(),
        weather_provider=weather_provider,
    )

    result = service.refresh_prediction(
        1,
        prediction_source="initial",
        source_event_id=99,
        as_of_date=date(2026, 5, 27),
    )

    assert result.snapshot.prediction_version == 1
    assert result.snapshot.algorithm_code == "stage_prediction_algorithm"
    assert result.crop_stage_state.current_stage_code == "tillering"
    assert result.crop_stage_state.source_snapshot_id == result.snapshot.id
    assert result.crop_thermal_time_state.accumulated_thermal_time == Decimal("780")
    assert result.crop_thermal_time_state.threshold_snapshot_id == result.snapshot.id
    assert result.stage_changed is False
    assert result.snapshot.input_payload["location"]["adcode"] == "430181"
    assert result.snapshot.input_payload["weather_data"][0]["date"] == "2026-04-10"
    assert result.snapshot.input_payload["weather_data"][0]["source_type"] == "observed"
    assert weather_provider.calls == [(date(2026, 4, 10), date(2026, 10, 7))]


def test_refresh_prediction_updates_existing_state_and_detects_stage_change() -> None:
    snapshot_repo = FakeStagePredictionSnapshotRepository()
    stage_repo = FakeCropStageStateRepository(
        {
            1: CropStageState(
                id=1,
                planting_plan_id=1,
                current_stage_code="seedling",
                current_stage_name="苗期",
                stage_source="predicted",
                effective_date=date(2026, 4, 10),
                source_snapshot_id=1,
                version=1,
            ),
        },
    )
    thermal_repo = FakeCropThermalTimeStateRepository(
        {
            1: CropThermalTimeState(
                id=1,
                planting_plan_id=1,
                accumulated_thermal_time=Decimal("100"),
                thermal_time_unit="degree_day",
                base_temperature=Decimal("10"),
                start_date=date(2026, 4, 10),
                last_calculated_date=date(2026, 4, 15),
                threshold_snapshot_id=1,
                data_version="old-v1",
            ),
        },
    )
    weather_provider = FakeWeatherProvider()
    service = StageManagementService(
        planting_plan_repository=FakePlantingPlanRepository(_make_plan()),
        farm_repository=FakeFarmRepository(_make_farm()),
        stage_prediction_snapshot_repository=snapshot_repo,
        crop_stage_state_repository=stage_repo,
        crop_thermal_time_state_repository=thermal_repo,
        stage_prediction_client=MockStagePredictionClient(),
        weather_provider=weather_provider,
    )

    result = service.refresh_prediction(
        1,
        prediction_source="plan_change",
        as_of_date=date(2026, 5, 27),
    )

    assert result.previous_stage_code == "seedling"
    assert result.crop_stage_state.current_stage_code == "tillering"
    assert result.crop_stage_state.version == 2
    assert result.stage_changed is True


def test_extract_pest_disease_growth_stage_from_timeline() -> None:
    stage_timeline = MockStagePredictionClient().predict_stage(
        request_payload={
            "sowing_date": "2026-04-10",
            "as_of_date": "2026-05-27",
        },
    ).stage_timeline

    growth_stage = extract_pest_disease_growth_stage(stage_timeline)

    assert growth_stage == {
        "tillering_date": "2026-04-20",
        "pokou_date": "2026-06-09",
        "heading_date": "2026-06-17",
        "maturity_date": "2026-07-19",
    }
