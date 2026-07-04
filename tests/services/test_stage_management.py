from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from app.models import CropStageDict, CropStageState, CropThermalTimeState, Farm, PlantingPlan, RiceVariety, StagePredictionSnapshot
from app.services.stage_management import (
    MockStagePredictionClient,
    StageManagementService,
    _build_stage_prediction_upstream_error_message,
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
class FakeRiceVarietyRepository:
    variety: RiceVariety

    def get(self, rice_variety_id: int) -> RiceVariety | None:
        return self.variety if self.variety.id == rice_variety_id else None


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
class FakeCropStageDictRepository:
    items: list[CropStageDict] = field(default_factory=list)

    def list_active(self) -> list[CropStageDict]:
        return sorted(
            [item for item in self.items if item.is_active],
            key=lambda item: (item.display_order, item.id or 0),
        )


@dataclass
class FakeWeatherProvider:
    calls: list[tuple[date, date, date | None]] = field(default_factory=list)

    def get_daily_weather(
        self,
        planting_plan: PlantingPlan,
        start_date: date,
        end_date: date,
        *,
        as_of_date: date | None = None,
    ) -> list[dict[str, Any]]:
        self.calls.append((start_date, end_date, as_of_date))
        weather_data: list[dict[str, Any]] = []
        current_date = start_date
        while current_date <= end_date:
            weather_data.append(
                {
                    "DATE": current_date.strftime("%Y%m%d"),
                    "TEMP": 26,
                    "data_version": f"weather-{current_date.isoformat()}",
                },
            )
            current_date = date.fromordinal(current_date.toordinal() + 1)
        return weather_data


@dataclass
class RecordingStagePredictionClient:
    result: Any
    calls: list[dict[str, Any]] = field(default_factory=list)

    def predict_stage(self, *, request_payload: dict[str, Any]):
        self.calls.append(dict(request_payload))
        return self.result


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
        metadata_payload={
            "approveRegion": "长江中下游",
            "controlSpec": "五优308",
        },
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


def _make_rice_variety() -> RiceVariety:
    return RiceVariety(
        id=3,
        name="黄广农占",
        approve_region="长江中下游",
        culti_type_code=6,
        sub_type_code=0,
        maturity_code=5,
        control_variety="五优308",
    )


def _make_legacy_code_rice_variety() -> RiceVariety:
    return RiceVariety(
        id=7569,
        name="昌盛优美特占",
        approve_region="湖南",
        culti_type_code=7,
        sub_type_code=9,
        maturity_code=13,
        control_variety="天优华占",
    )


def _make_rice_variety_without_control_variety() -> RiceVariety:
    return RiceVariety(
        id=4529,
        name="美香占2号",
        approve_region="湖南",
        culti_type_code=6,
        sub_type_code=9,
        maturity_code=17,
        control_variety=None,
    )


def test_refresh_prediction_creates_stage_snapshot_and_states() -> None:
    snapshot_repo = FakeStagePredictionSnapshotRepository()
    stage_repo = FakeCropStageStateRepository()
    thermal_repo = FakeCropThermalTimeStateRepository()
    weather_provider = FakeWeatherProvider()
    prediction_client = RecordingStagePredictionClient(MockStagePredictionClient().predict_stage(request_payload={"sowing_date": "2026-04-10"}))
    service = StageManagementService(
        planting_plan_repository=FakePlantingPlanRepository(_make_plan()),
        farm_repository=FakeFarmRepository(_make_farm()),
        rice_variety_repository=FakeRiceVarietyRepository(_make_rice_variety()),
        stage_prediction_snapshot_repository=snapshot_repo,
        crop_stage_state_repository=stage_repo,
        crop_thermal_time_state_repository=thermal_repo,
        stage_prediction_client=prediction_client,
        weather_provider=weather_provider,
    )

    result = service.refresh_prediction(
        1,
        prediction_source="initial",
        source_event_id=99,
        as_of_date=date(2026, 5, 27),
    )

    assert prediction_client.calls == [
        {
            "apprArea": "长江中下游",
            "controlSpec": "五优308",
            "maturType": 5,
            "cultiType": 4,
            "apprCultiType": 5,
            "subsType": 0,
            "variety_name": "黄广农占",
            "farm_area_name": "湖南",
        },
    ]
    assert result.snapshot.prediction_version == 1
    assert result.snapshot.algorithm_code == "growth_stage_gdd_thresholds"
    assert result.snapshot.algorithm_version is None
    assert result.crop_stage_state.current_stage_code == "tillering"
    assert result.crop_stage_state.source_snapshot_id == result.snapshot.id
    assert result.crop_thermal_time_state.accumulated_thermal_time == Decimal("672.0")
    assert result.crop_thermal_time_state.threshold_snapshot_id == result.snapshot.id
    assert result.crop_thermal_time_state.data_version == "weather-2026-05-27"
    assert result.stage_changed is False
    assert result.snapshot.input_payload["farm_area_name"] == "湖南"
    assert "weather_data" not in result.snapshot.input_payload
    assert result.snapshot.input_payload["calculation_context"]["as_of_date"] == "2026-05-27"
    assert result.snapshot.stage_timeline["stages"][1]["start_date"] == "2026-04-14"
    assert result.snapshot.stage_timeline["stages"][1]["raw_stage_code"] == "BBCH21"
    assert result.snapshot.stage_timeline["raw_stage_points"][0]["stage_code"] == "BBCH13"
    assert result.snapshot.stage_timeline["raw_stage_points"][0]["season_scope"] == "main"
    assert result.snapshot.stage_timeline["raw_stage_points"][0]["source"] == "predicted"
    assert result.snapshot.stage_timeline["raw_stage_points"][6]["stage_code"] == "BBCH45"
    assert weather_provider.calls == [(date(2026, 4, 10), date(2026, 10, 7), date(2026, 5, 27))]


def test_refresh_prediction_prefers_stage_names_from_crop_stage_dict() -> None:
    snapshot_repo = FakeStagePredictionSnapshotRepository()
    stage_repo = FakeCropStageStateRepository()
    thermal_repo = FakeCropThermalTimeStateRepository()
    weather_provider = FakeWeatherProvider()
    stage_dict_repo = FakeCropStageDictRepository(
        items=[
            CropStageDict(
                id=1,
                stage_code="BBCH13",
                stage_name="三叶一心（字典）",
                season_scope="main",
                business_stage_code=None,
                display_order=1,
                is_active=True,
            ),
            CropStageDict(
                id=2,
                stage_code="BBCH21",
                stage_name="分蘖始期（字典）",
                season_scope="main",
                business_stage_code="tillering",
                display_order=2,
                is_active=True,
            ),
            CropStageDict(
                id=3,
                stage_code="BBCH50",
                stage_name="破口期（字典）",
                season_scope="main",
                business_stage_code="pokou",
                display_order=8,
                is_active=True,
            ),
            CropStageDict(
                id=4,
                stage_code="BBCH58",
                stage_name="齐穗期（字典）",
                season_scope="main",
                business_stage_code="heading",
                display_order=11,
                is_active=True,
            ),
            CropStageDict(
                id=5,
                stage_code="BBCH89",
                stage_name="成熟期（字典）",
                season_scope="main",
                business_stage_code="maturity",
                display_order=12,
                is_active=True,
            ),
        ],
    )
    service = StageManagementService(
        planting_plan_repository=FakePlantingPlanRepository(_make_plan()),
        farm_repository=FakeFarmRepository(_make_farm()),
        rice_variety_repository=FakeRiceVarietyRepository(_make_rice_variety()),
        stage_prediction_snapshot_repository=snapshot_repo,
        crop_stage_state_repository=stage_repo,
        crop_thermal_time_state_repository=thermal_repo,
        stage_prediction_client=MockStagePredictionClient(),
        weather_provider=weather_provider,
        crop_stage_dict_repository=stage_dict_repo,
    )

    result = service.refresh_prediction(
        1,
        prediction_source="initial",
        as_of_date=date(2026, 5, 27),
    )

    raw_points = {item["stage_code"]: item for item in result.snapshot.stage_timeline["raw_stage_points"]}
    assert raw_points["BBCH13"]["stage_name"] == "三叶一心（字典）"
    assert raw_points["BBCH21"]["stage_name"] == "分蘖始期（字典）"


def test_refresh_prediction_rebases_direct_seeded_thresholds_after_three_leaf_stage() -> None:
    snapshot_repo = FakeStagePredictionSnapshotRepository()
    stage_repo = FakeCropStageStateRepository()
    thermal_repo = FakeCropThermalTimeStateRepository()
    weather_provider = FakeWeatherProvider()
    service = StageManagementService(
        planting_plan_repository=FakePlantingPlanRepository(_make_plan()),
        farm_repository=FakeFarmRepository(_make_farm()),
        rice_variety_repository=FakeRiceVarietyRepository(_make_rice_variety()),
        stage_prediction_snapshot_repository=snapshot_repo,
        crop_stage_state_repository=stage_repo,
        crop_thermal_time_state_repository=thermal_repo,
        stage_prediction_client=MockStagePredictionClient(),
        weather_provider=weather_provider,
    )

    result = service.refresh_prediction(
        1,
        prediction_source="initial",
        as_of_date=date(2026, 5, 27),
    )

    thresholds = result.snapshot.thermal_thresholds["stage_thresholds"]
    assert thresholds["BBCH13"] == 64
    assert thresholds["BBCH21"] == 64
    assert thresholds["BBCH28"] == 240
    assert thresholds["BBCH89"] == 1504
    assert result.snapshot.thermal_thresholds["direct_seeding_threshold_adjustment"] == {
        "applied": True,
        "basis": "BBCH21_minus_BBCH13",
        "thermal_time_delta": "112",
    }


def test_refresh_for_weather_update_does_not_reapply_direct_seeded_threshold_adjustment() -> None:
    snapshot_repo = FakeStagePredictionSnapshotRepository()
    stage_repo = FakeCropStageStateRepository()
    thermal_repo = FakeCropThermalTimeStateRepository()
    weather_provider = FakeWeatherProvider()
    service = StageManagementService(
        planting_plan_repository=FakePlantingPlanRepository(_make_plan()),
        farm_repository=FakeFarmRepository(_make_farm()),
        rice_variety_repository=FakeRiceVarietyRepository(_make_rice_variety()),
        stage_prediction_snapshot_repository=snapshot_repo,
        crop_stage_state_repository=stage_repo,
        crop_thermal_time_state_repository=thermal_repo,
        stage_prediction_client=MockStagePredictionClient(),
        weather_provider=weather_provider,
    )
    initial_result = service.refresh_prediction(
        1,
        prediction_source="initial",
        as_of_date=date(2026, 5, 27),
    )

    result = service.refresh_for_weather_update(
        1,
        source_event_id=101,
        as_of_date=date(2026, 6, 10),
    )

    assert initial_result.snapshot.thermal_thresholds["stage_thresholds"]["BBCH21"] == 64
    assert result.snapshot.thermal_thresholds["stage_thresholds"]["BBCH21"] == 64
    assert result.snapshot.thermal_thresholds["stage_thresholds"]["BBCH28"] == 240


def test_refresh_prediction_for_early_rice_transplanting_uses_transplant_date_as_three_leaf_anchor() -> None:
    snapshot_repo = FakeStagePredictionSnapshotRepository()
    stage_repo = FakeCropStageStateRepository()
    thermal_repo = FakeCropThermalTimeStateRepository()
    weather_provider = FakeWeatherProvider()
    plan = _make_plan()
    plan.planting_method_code = 3
    plan.transplant_date = date(2026, 4, 18)
    service = StageManagementService(
        planting_plan_repository=FakePlantingPlanRepository(plan),
        farm_repository=FakeFarmRepository(_make_farm()),
        rice_variety_repository=FakeRiceVarietyRepository(_make_rice_variety()),
        stage_prediction_snapshot_repository=snapshot_repo,
        crop_stage_state_repository=stage_repo,
        crop_thermal_time_state_repository=thermal_repo,
        stage_prediction_client=MockStagePredictionClient(),
        weather_provider=weather_provider,
    )

    result = service.refresh_prediction(
        1,
        prediction_source="initial",
        as_of_date=date(2026, 5, 27),
    )

    raw_points = {item["stage_code"]: item for item in result.snapshot.stage_timeline["raw_stage_points"]}
    assert raw_points["BBCH13"]["start_date"] == "2026-04-18"
    assert raw_points["BBCH13"]["source"] == "manual"
    assert result.snapshot.stage_timeline["stages"][1]["start_date"] == "2026-04-26"
    assert result.snapshot.stage_timeline["stages"][1]["raw_stage_code"] == "BBCH21"


def test_refresh_for_weather_update_preserves_transplant_based_three_leaf_anchor() -> None:
    snapshot_repo = FakeStagePredictionSnapshotRepository()
    stage_repo = FakeCropStageStateRepository()
    thermal_repo = FakeCropThermalTimeStateRepository()
    weather_provider = FakeWeatherProvider()
    plan = _make_plan()
    plan.planting_method_code = 3
    plan.transplant_date = date(2026, 4, 18)
    service = StageManagementService(
        planting_plan_repository=FakePlantingPlanRepository(plan),
        farm_repository=FakeFarmRepository(_make_farm()),
        rice_variety_repository=FakeRiceVarietyRepository(_make_rice_variety()),
        stage_prediction_snapshot_repository=snapshot_repo,
        crop_stage_state_repository=stage_repo,
        crop_thermal_time_state_repository=thermal_repo,
        stage_prediction_client=MockStagePredictionClient(),
        weather_provider=weather_provider,
    )
    initial_result = service.refresh_prediction(
        1,
        prediction_source="initial",
        as_of_date=date(2026, 5, 27),
    )

    result = service.refresh_for_weather_update(
        1,
        source_event_id=101,
        as_of_date=date(2026, 6, 10),
    )

    initial_raw_points = {item["stage_code"]: item for item in initial_result.snapshot.stage_timeline["raw_stage_points"]}
    refreshed_raw_points = {item["stage_code"]: item for item in result.snapshot.stage_timeline["raw_stage_points"]}
    assert initial_raw_points["BBCH13"]["start_date"] == "2026-04-18"
    assert refreshed_raw_points["BBCH13"]["start_date"] == "2026-04-18"
    assert refreshed_raw_points["BBCH13"]["source"] == "manual"
    assert result.snapshot.stage_timeline["stages"][1]["start_date"] == "2026-04-26"


def test_refresh_prediction_maps_local_stage_codes_to_algorithm_codes() -> None:
    snapshot_repo = FakeStagePredictionSnapshotRepository()
    stage_repo = FakeCropStageStateRepository()
    thermal_repo = FakeCropThermalTimeStateRepository()
    weather_provider = FakeWeatherProvider()
    plan = PlantingPlan(
        id=1,
        plan_code="PLAN-001",
        plan_name="测试计划",
        farm_id=1,
        culti_type_code=7,
        planting_method_code=1,
        crop_name="水稻",
        variety_id=7569,
        variety_name="昌盛优美特占",
        sowing_date=date(2026, 4, 10),
        task_generation_window_days=14,
        metadata_payload={},
    )
    prediction_client = RecordingStagePredictionClient(
        MockStagePredictionClient().predict_stage(request_payload={"sowing_date": "2026-04-10"}),
    )
    service = StageManagementService(
        planting_plan_repository=FakePlantingPlanRepository(plan),
        farm_repository=FakeFarmRepository(_make_farm()),
        rice_variety_repository=FakeRiceVarietyRepository(_make_legacy_code_rice_variety()),
        stage_prediction_snapshot_repository=snapshot_repo,
        crop_stage_state_repository=stage_repo,
        crop_thermal_time_state_repository=thermal_repo,
        stage_prediction_client=prediction_client,
        weather_provider=weather_provider,
    )

    service.refresh_prediction(
        1,
        prediction_source="initial",
        source_event_id=99,
        as_of_date=date(2026, 5, 27),
    )

    assert prediction_client.calls == [
        {
            "apprArea": "湖南",
            "controlSpec": "天优华占",
            "maturType": 1,
            "cultiType": 6,
            "apprCultiType": 6,
            "subsType": 0,
            "variety_name": "昌盛优美特占",
            "farm_area_name": "湖南",
        },
    ]


def test_refresh_prediction_allows_empty_control_spec() -> None:
    snapshot_repo = FakeStagePredictionSnapshotRepository()
    stage_repo = FakeCropStageStateRepository()
    thermal_repo = FakeCropThermalTimeStateRepository()
    weather_provider = FakeWeatherProvider()
    plan = PlantingPlan(
        id=1,
        plan_code="PLAN-001",
        plan_name="测试计划",
        farm_id=1,
        culti_type_code=6,
        planting_method_code=1,
        crop_name="水稻",
        variety_id=4529,
        variety_name="美香占2号",
        sowing_date=date(2026, 5, 4),
        task_generation_window_days=14,
        metadata_payload={},
    )
    prediction_client = RecordingStagePredictionClient(
        MockStagePredictionClient().predict_stage(request_payload={"sowing_date": "2026-05-04"}),
    )
    service = StageManagementService(
        planting_plan_repository=FakePlantingPlanRepository(plan),
        farm_repository=FakeFarmRepository(_make_farm()),
        rice_variety_repository=FakeRiceVarietyRepository(_make_rice_variety_without_control_variety()),
        stage_prediction_snapshot_repository=snapshot_repo,
        crop_stage_state_repository=stage_repo,
        crop_thermal_time_state_repository=thermal_repo,
        stage_prediction_client=prediction_client,
        weather_provider=weather_provider,
    )

    service.refresh_prediction(
        1,
        prediction_source="initial",
        source_event_id=99,
        as_of_date=date(2026, 5, 27),
    )

    assert prediction_client.calls == [
        {
            "apprArea": "湖南",
            "controlSpec": "",
            "maturType": 5,
            "cultiType": 5,
            "apprCultiType": 5,
            "subsType": 0,
            "variety_name": "美香占2号",
            "farm_area_name": "湖南",
        },
    ]


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
        rice_variety_repository=FakeRiceVarietyRepository(_make_rice_variety()),
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


def test_refresh_for_weather_update_reuses_latest_threshold_rule() -> None:
    initial_snapshot = StagePredictionSnapshot(
        id=10,
        planting_plan_id=1,
        prediction_version=2,
        prediction_source="plan_change",
        algorithm_code="stage_prediction_algorithm",
        algorithm_version="v2.0.0",
        input_payload={},
        stage_timeline={"stages": []},
        thermal_thresholds=MockStagePredictionClient().predict_stage(request_payload={"sowing_date": "2026-04-10"}).threshold_rule,
    )
    snapshot_repo = FakeStagePredictionSnapshotRepository(items=[initial_snapshot], next_id=11)
    stage_repo = FakeCropStageStateRepository(
        {
            1: CropStageState(
                id=1,
                planting_plan_id=1,
                current_stage_code="tillering",
                current_stage_name="分蘖期",
                stage_source="predicted",
                effective_date=date(2026, 4, 20),
                source_snapshot_id=10,
                version=1,
            ),
        },
    )
    thermal_repo = FakeCropThermalTimeStateRepository(
        {
            1: CropThermalTimeState(
                id=1,
                planting_plan_id=1,
                accumulated_thermal_time=Decimal("672.0"),
                thermal_time_unit="degree_day",
                base_temperature=Decimal("12"),
                start_date=date(2026, 4, 10),
                last_calculated_date=date(2026, 5, 27),
                threshold_snapshot_id=10,
                data_version="weather-2026-05-27",
            ),
        },
    )
    weather_provider = FakeWeatherProvider()

    @dataclass
    class FailingStagePredictionClient:
        def predict_stage(self, *, request_payload: dict[str, Any]):
            raise AssertionError("Weather update should not call stage prediction API.")

    service = StageManagementService(
        planting_plan_repository=FakePlantingPlanRepository(_make_plan()),
        farm_repository=FakeFarmRepository(_make_farm()),
        rice_variety_repository=FakeRiceVarietyRepository(_make_rice_variety()),
        stage_prediction_snapshot_repository=snapshot_repo,
        crop_stage_state_repository=stage_repo,
        crop_thermal_time_state_repository=thermal_repo,
        stage_prediction_client=FailingStagePredictionClient(),
        weather_provider=weather_provider,
    )

    result = service.refresh_for_weather_update(
        1,
        source_event_id=101,
        as_of_date=date(2026, 6, 10),
    )

    assert result.snapshot.prediction_source == "weather_update"
    assert result.snapshot.source_event_id == 101
    assert result.snapshot.input_payload["rule_snapshot_id"] == 10
    assert result.crop_stage_state.current_stage_code == "pokou"
    assert result.crop_stage_state.version == 2
    assert result.crop_thermal_time_state.accumulated_thermal_time == Decimal("868.0")
    assert result.crop_thermal_time_state.threshold_snapshot_id == result.snapshot.id
    assert result.stage_changed is True


def test_refresh_for_weather_update_uses_incremental_observed_weather() -> None:
    initial_rule = MockStagePredictionClient().predict_stage(request_payload={"sowing_date": "2026-04-10"}).threshold_rule
    initial_snapshot = StagePredictionSnapshot(
        id=10,
        planting_plan_id=1,
        prediction_version=2,
        prediction_source="initial",
        algorithm_code="stage_prediction_algorithm",
        algorithm_version="mock-v2",
        input_payload={},
        stage_timeline={
            "stages": [
                {
                    "stage_code": "seedling",
                    "stage_name": "苗期",
                    "start_date": "2026-04-10",
                    "key_date": "2026-04-10",
                },
                {
                    "stage_code": "tillering",
                    "stage_name": "分蘖期",
                    "start_date": "2026-04-20",
                    "key_date": "2026-04-20",
                },
            ],
        },
        thermal_thresholds=initial_rule,
    )
    thermal_repo = FakeCropThermalTimeStateRepository(
        {
            1: CropThermalTimeState(
                id=1,
                planting_plan_id=1,
                accumulated_thermal_time=Decimal("672.0"),
                thermal_time_unit="degree_day",
                base_temperature=Decimal("12"),
                start_date=date(2026, 4, 10),
                last_calculated_date=date(2026, 5, 27),
                threshold_snapshot_id=10,
                data_version="weather-2026-05-27",
            ),
        },
    )
    weather_provider = FakeWeatherProvider()
    service = StageManagementService(
        planting_plan_repository=FakePlantingPlanRepository(_make_plan()),
        farm_repository=FakeFarmRepository(_make_farm()),
        rice_variety_repository=FakeRiceVarietyRepository(_make_rice_variety()),
        stage_prediction_snapshot_repository=FakeStagePredictionSnapshotRepository(items=[initial_snapshot], next_id=11),
        crop_stage_state_repository=FakeCropStageStateRepository(),
        crop_thermal_time_state_repository=thermal_repo,
        stage_prediction_client=MockStagePredictionClient(),
        weather_provider=weather_provider,
    )

    result = service.refresh_for_weather_update(
        1,
        source_event_id=101,
        as_of_date=date(2026, 5, 29),
        source_event_payload={
            "weatherDate": "2026-05-29",
            "sourceType": "observed",
        },
    )

    assert weather_provider.calls == [(date(2026, 5, 28), date(2026, 10, 7), date(2026, 5, 29))]
    assert result.crop_thermal_time_state.accumulated_thermal_time == Decimal("700.0")
    assert result.snapshot.input_payload["calculation_context"]["start_date"] == "2026-05-28"
    assert result.snapshot.input_payload["rule_snapshot_id"] == 10


def test_refresh_for_weather_update_forecast_only_updates_prediction_layer() -> None:
    initial_rule = MockStagePredictionClient().predict_stage(request_payload={"sowing_date": "2026-04-10"}).threshold_rule
    initial_snapshot = StagePredictionSnapshot(
        id=10,
        planting_plan_id=1,
        prediction_version=2,
        prediction_source="weather_update",
        algorithm_code="stage_prediction_algorithm",
        algorithm_version="mock-v2",
        input_payload={},
        stage_timeline={
            "stages": [
                {"stage_code": "seedling", "stage_name": "苗期", "start_date": "2026-04-10", "key_date": "2026-04-10"},
                {"stage_code": "tillering", "stage_name": "分蘖期", "start_date": "2026-04-20", "key_date": "2026-04-20"},
            ],
        },
        thermal_thresholds=initial_rule,
    )
    stage_repo = FakeCropStageStateRepository(
        {
            1: CropStageState(
                id=1,
                planting_plan_id=1,
                current_stage_code="tillering",
                current_stage_name="分蘖期",
                stage_source="predicted",
                effective_date=date(2026, 4, 20),
                source_snapshot_id=10,
                version=1,
            ),
        },
    )
    thermal_repo = FakeCropThermalTimeStateRepository(
        {
            1: CropThermalTimeState(
                id=1,
                planting_plan_id=1,
                accumulated_thermal_time=Decimal("672.0"),
                thermal_time_unit="degree_day",
                base_temperature=Decimal("12"),
                start_date=date(2026, 4, 10),
                last_calculated_date=date(2026, 5, 27),
                threshold_snapshot_id=10,
                data_version="weather-2026-05-27",
            ),
        },
    )
    weather_provider = FakeWeatherProvider()
    service = StageManagementService(
        planting_plan_repository=FakePlantingPlanRepository(_make_plan()),
        farm_repository=FakeFarmRepository(_make_farm()),
        rice_variety_repository=FakeRiceVarietyRepository(_make_rice_variety()),
        stage_prediction_snapshot_repository=FakeStagePredictionSnapshotRepository(items=[initial_snapshot], next_id=11),
        crop_stage_state_repository=stage_repo,
        crop_thermal_time_state_repository=thermal_repo,
        stage_prediction_client=MockStagePredictionClient(),
        weather_provider=weather_provider,
    )

    result = service.refresh_for_weather_update(
        1,
        source_event_id=102,
        as_of_date=date(2026, 5, 29),
        source_event_payload={
            "weatherDate": "2026-05-29",
            "sourceType": "forecast",
            "weatherChangeType": "changed_snapshot",
        },
    )

    assert weather_provider.calls == [(date(2026, 5, 29), date(2026, 10, 7), date(2026, 5, 29))]
    assert result.crop_stage_state.current_stage_code == "tillering"
    assert result.crop_stage_state.version == 1
    assert result.crop_thermal_time_state.accumulated_thermal_time == Decimal("672.0")
    assert result.crop_thermal_time_state.last_calculated_date == date(2026, 5, 27)
    assert result.crop_thermal_time_state.data_version == "weather-2026-05-27"
    assert result.stage_changed is False
    assert result.snapshot.input_payload["recalculation_summary"]["mode"] == "forecast_projection"
    assert result.snapshot.input_payload["recalculation_summary"]["prediction_only"] is True
    assert result.snapshot.input_payload["thermal_audit_summary"]["current_stage_basis"] == "observed_only"


def test_refresh_for_weather_update_historical_observed_correction_replays_from_corrected_day() -> None:
    initial_rule = MockStagePredictionClient().predict_stage(request_payload={"sowing_date": "2026-04-10"}).threshold_rule
    initial_snapshot = StagePredictionSnapshot(
        id=10,
        planting_plan_id=1,
        prediction_version=2,
        prediction_source="weather_update",
        algorithm_code="stage_prediction_algorithm",
        algorithm_version="mock-v2",
        input_payload={},
        stage_timeline={
            "stages": [
                {"stage_code": "seedling", "stage_name": "苗期", "start_date": "2026-04-10", "key_date": "2026-04-10"},
                {"stage_code": "tillering", "stage_name": "分蘖期", "start_date": "2026-04-20", "key_date": "2026-04-20"},
            ],
        },
        thermal_thresholds=initial_rule,
    )
    thermal_repo = FakeCropThermalTimeStateRepository(
        {
            1: CropThermalTimeState(
                id=1,
                planting_plan_id=1,
                accumulated_thermal_time=Decimal("672.0"),
                thermal_time_unit="degree_day",
                base_temperature=Decimal("12"),
                start_date=date(2026, 4, 10),
                last_calculated_date=date(2026, 5, 27),
                threshold_snapshot_id=10,
                data_version="weather-2026-05-27",
            ),
        },
    )
    weather_provider = FakeWeatherProvider()
    service = StageManagementService(
        planting_plan_repository=FakePlantingPlanRepository(_make_plan()),
        farm_repository=FakeFarmRepository(_make_farm()),
        rice_variety_repository=FakeRiceVarietyRepository(_make_rice_variety()),
        stage_prediction_snapshot_repository=FakeStagePredictionSnapshotRepository(items=[initial_snapshot], next_id=11),
        crop_stage_state_repository=FakeCropStageStateRepository(),
        crop_thermal_time_state_repository=thermal_repo,
        stage_prediction_client=MockStagePredictionClient(),
        weather_provider=weather_provider,
    )

    result = service.refresh_for_weather_update(
        1,
        source_event_id=103,
        as_of_date=date(2026, 5, 29),
        source_event_payload={
            "weatherDate": "2026-05-20",
            "sourceType": "observed",
            "weatherChangeType": "changed_snapshot",
        },
    )

    assert weather_provider.calls == [
        (date(2026, 5, 20), date(2026, 10, 7), date(2026, 5, 29)),
        (date(2026, 4, 10), date(2026, 5, 19), date(2026, 5, 19)),
    ]
    assert result.crop_thermal_time_state.accumulated_thermal_time == Decimal("700.0")
    assert result.snapshot.input_payload["calculation_context"]["start_date"] == "2026-05-20"
    assert result.snapshot.input_payload["recalculation_summary"]["mode"] == "historical_observed_correction"
    assert result.snapshot.input_payload["recalculation_summary"]["recalculation_start_date"] == "2026-05-20"


def test_apply_actual_stage_recorded_creates_manual_snapshot_and_shifts_future_raw_stage_points() -> None:
    initial_result = MockStagePredictionClient().predict_stage(request_payload={"sowing_date": "2026-04-10"})
    initial_snapshot = StagePredictionSnapshot(
        id=10,
        planting_plan_id=1,
        prediction_version=2,
        prediction_source="weather_update",
        algorithm_code="stage_prediction_algorithm",
        algorithm_version="mock-v2",
        input_payload={
            "calculation_context": {
                "as_of_date": "2026-06-18",
                "start_date": "2026-04-10",
            },
        },
        stage_timeline={
            "stages": [
                {"stage_code": "seedling", "stage_name": "苗期", "start_date": "2026-04-10", "key_date": "2026-04-10"},
                {"stage_code": "tillering", "stage_name": "分蘖期", "start_date": "2026-04-20", "key_date": "2026-04-20"},
                {"stage_code": "pokou", "stage_name": "破口期", "start_date": "2026-06-09", "key_date": "2026-06-09"},
                {"stage_code": "heading", "stage_name": "齐穗期", "start_date": "2026-06-17", "key_date": "2026-06-17"},
            ],
            "raw_stage_points": [
                {"stage_code": "BBCH13", "stage_name": "三叶一心", "season_scope": "main", "start_date": "2026-04-13", "source": "predicted"},
                {"stage_code": "BBCH21", "stage_name": "分蘖始期", "season_scope": "main", "start_date": "2026-04-20", "source": "predicted"},
                {"stage_code": "BBCH28", "stage_name": "有效分蘖终止期", "season_scope": "main", "start_date": "2026-04-30", "source": "predicted"},
                {"stage_code": "BBCH41", "stage_name": "幼穗分化1期", "season_scope": "main", "start_date": "2026-05-22", "source": "predicted"},
                {"stage_code": "BBCH42", "stage_name": "幼穗分化2期", "season_scope": "main", "start_date": "2026-05-25", "source": "predicted"},
                {"stage_code": "BBCH44", "stage_name": "幼穗分化4期", "season_scope": "main", "start_date": "2026-05-31", "source": "predicted"},
                {"stage_code": "BBCH45", "stage_name": "孕穗期", "season_scope": "main", "start_date": "2026-06-05", "source": "predicted"},
                {"stage_code": "BBCH50", "stage_name": "破口期", "season_scope": "main", "start_date": "2026-06-09", "source": "predicted", "business_stage_code": "pokou"},
                {"stage_code": "BBCH51", "stage_name": "始穗期", "season_scope": "main", "start_date": "2026-06-11", "source": "predicted"},
                {"stage_code": "BBCH55", "stage_name": "抽穗期", "season_scope": "main", "start_date": "2026-06-15", "source": "predicted"},
                {"stage_code": "BBCH58", "stage_name": "齐穗期", "season_scope": "main", "start_date": "2026-06-17", "source": "predicted", "business_stage_code": "heading"},
            ],
        },
        thermal_thresholds=initial_result.threshold_rule,
    )
    snapshot_repo = FakeStagePredictionSnapshotRepository(items=[initial_snapshot], next_id=11)
    stage_repo = FakeCropStageStateRepository(
        {
            1: CropStageState(
                id=1,
                planting_plan_id=1,
                current_stage_code="tillering",
                current_stage_name="分蘖期",
                stage_source="predicted",
                effective_date=date(2026, 4, 20),
                source_snapshot_id=10,
                version=1,
            ),
        },
    )
    thermal_repo = FakeCropThermalTimeStateRepository(
        {
            1: CropThermalTimeState(
                id=1,
                planting_plan_id=1,
                accumulated_thermal_time=Decimal("1120.0"),
                thermal_time_unit="degree_day",
                base_temperature=Decimal("10"),
                start_date=date(2026, 4, 10),
                last_calculated_date=date(2026, 6, 18),
                threshold_snapshot_id=10,
                data_version="weather-2026-06-18",
            ),
        },
    )
    service = StageManagementService(
        planting_plan_repository=FakePlantingPlanRepository(_make_plan()),
        farm_repository=FakeFarmRepository(_make_farm()),
        rice_variety_repository=FakeRiceVarietyRepository(_make_rice_variety()),
        stage_prediction_snapshot_repository=snapshot_repo,
        crop_stage_state_repository=stage_repo,
        crop_thermal_time_state_repository=thermal_repo,
        stage_prediction_client=MockStagePredictionClient(),
        weather_provider=FakeWeatherProvider(),
    )

    result = service.apply_actual_stage_recorded(
        1,
        stage_code="BBCH45",
        effective_date=date(2026, 6, 10),
        source_event_id=105,
    )

    raw_points = {item["stage_code"]: item for item in result.snapshot.stage_timeline["raw_stage_points"]}
    assert result.snapshot.prediction_source == "manual_adjustment"
    assert result.snapshot.input_payload["recalculation_summary"]["mode"] == "manual_stage_override"
    assert result.crop_stage_state.current_stage_code == "BBCH45"
    assert result.crop_stage_state.stage_source == "manual"
    assert result.crop_stage_state.source_snapshot_id == result.snapshot.id
    assert raw_points["BBCH45"]["start_date"] == "2026-06-10"
    assert raw_points["BBCH45"]["source"] == "manual"
    assert raw_points["BBCH50"]["start_date"] == "2026-06-15"
    assert raw_points["BBCH58"]["start_date"] == "2026-06-24"
    assert result.snapshot.stage_timeline["stages"][2]["start_date"] == "2026-06-15"
    assert result.snapshot.stage_timeline["stages"][3]["start_date"] == "2026-06-24"
    assert result.stage_changed is True


def test_apply_actual_stage_records_preserves_intermediate_stages_between_manual_anchors() -> None:
    initial_result = MockStagePredictionClient().predict_stage(request_payload={"sowing_date": "2026-04-10"})
    initial_snapshot = StagePredictionSnapshot(
        id=10,
        planting_plan_id=1,
        prediction_version=2,
        prediction_source="weather_update",
        algorithm_code="stage_prediction_algorithm",
        algorithm_version="mock-v2",
        input_payload={
            "calculation_context": {
                "as_of_date": "2026-06-18",
                "start_date": "2026-04-10",
            },
        },
        stage_timeline={
            "stages": [
                {"stage_code": "seedling", "stage_name": "苗期", "start_date": "2026-04-10", "key_date": "2026-04-10"},
                {"stage_code": "tillering", "stage_name": "分蘖期", "start_date": "2026-04-20", "key_date": "2026-04-20"},
                {"stage_code": "pokou", "stage_name": "破口期", "start_date": "2026-06-09", "key_date": "2026-06-09"},
                {"stage_code": "heading", "stage_name": "齐穗期", "start_date": "2026-06-17", "key_date": "2026-06-17"},
            ],
            "raw_stage_points": [
                {"stage_code": "BBCH13", "stage_name": "三叶一心", "season_scope": "main", "start_date": "2026-04-13", "source": "predicted"},
                {"stage_code": "BBCH21", "stage_name": "分蘖始期", "season_scope": "main", "start_date": "2026-04-20", "source": "predicted"},
                {"stage_code": "BBCH28", "stage_name": "有效分蘖终止期", "season_scope": "main", "start_date": "2026-04-30", "source": "predicted"},
                {"stage_code": "BBCH41", "stage_name": "幼穗分化1期", "season_scope": "main", "start_date": "2026-05-22", "source": "predicted"},
                {"stage_code": "BBCH42", "stage_name": "幼穗分化2期", "season_scope": "main", "start_date": "2026-05-25", "source": "predicted"},
                {"stage_code": "BBCH44", "stage_name": "幼穗分化4期", "season_scope": "main", "start_date": "2026-05-31", "source": "predicted"},
                {"stage_code": "BBCH45", "stage_name": "孕穗期", "season_scope": "main", "start_date": "2026-06-05", "source": "predicted"},
                {"stage_code": "BBCH50", "stage_name": "破口期", "season_scope": "main", "start_date": "2026-06-09", "source": "predicted", "business_stage_code": "pokou"},
                {"stage_code": "BBCH51", "stage_name": "始穗期", "season_scope": "main", "start_date": "2026-06-11", "source": "predicted"},
                {"stage_code": "BBCH55", "stage_name": "抽穗期", "season_scope": "main", "start_date": "2026-06-15", "source": "predicted"},
                {"stage_code": "BBCH58", "stage_name": "齐穗期", "season_scope": "main", "start_date": "2026-06-17", "source": "predicted", "business_stage_code": "heading"},
            ],
        },
        thermal_thresholds=initial_result.threshold_rule,
    )
    snapshot_repo = FakeStagePredictionSnapshotRepository(items=[initial_snapshot], next_id=11)
    stage_repo = FakeCropStageStateRepository(
        {
            1: CropStageState(
                id=1,
                planting_plan_id=1,
                current_stage_code="tillering",
                current_stage_name="分蘖期",
                stage_source="predicted",
                effective_date=date(2026, 4, 20),
                source_snapshot_id=10,
                version=1,
            ),
        },
    )
    thermal_repo = FakeCropThermalTimeStateRepository(
        {
            1: CropThermalTimeState(
                id=1,
                planting_plan_id=1,
                accumulated_thermal_time=Decimal("1120.0"),
                thermal_time_unit="degree_day",
                base_temperature=Decimal("10"),
                start_date=date(2026, 4, 10),
                last_calculated_date=date(2026, 6, 18),
                threshold_snapshot_id=10,
                data_version="weather-2026-06-18",
            ),
        },
    )
    service = StageManagementService(
        planting_plan_repository=FakePlantingPlanRepository(_make_plan()),
        farm_repository=FakeFarmRepository(_make_farm()),
        rice_variety_repository=FakeRiceVarietyRepository(_make_rice_variety()),
        stage_prediction_snapshot_repository=snapshot_repo,
        crop_stage_state_repository=stage_repo,
        crop_thermal_time_state_repository=thermal_repo,
        stage_prediction_client=MockStagePredictionClient(),
        weather_provider=FakeWeatherProvider(),
    )

    result = service.apply_actual_stage_records(
        1,
        stage_dates={
            "BBCH45": date(2026, 6, 10),
            "BBCH58": date(2026, 6, 24),
        },
        source_event_id=106,
    )

    raw_points = {item["stage_code"]: item for item in result.snapshot.stage_timeline["raw_stage_points"]}
    assert result.snapshot.input_payload["recalculation_summary"]["mode"] == "manual_stage_override_batch"
    assert result.crop_stage_state.current_stage_code == "BBCH58"
    assert raw_points["BBCH45"]["start_date"] == "2026-06-10"
    assert raw_points["BBCH45"]["source"] == "manual"
    assert raw_points["BBCH50"]["start_date"] == "2026-06-09"
    assert raw_points["BBCH51"]["start_date"] == "2026-06-11"
    assert raw_points["BBCH55"]["start_date"] == "2026-06-15"
    assert raw_points["BBCH58"]["start_date"] == "2026-06-24"
    assert raw_points["BBCH58"]["source"] == "manual"
    assert raw_points["BBCH89"]["start_date"] > "2026-06-24"
    assert result.snapshot.stage_timeline["stages"][2]["start_date"] == "2026-06-09"
    assert result.snapshot.stage_timeline["stages"][3]["start_date"] == "2026-06-24"
    assert result.stage_changed is True


def test_apply_actual_stage_recorded_rejects_non_raw_stage_code() -> None:
    service = StageManagementService(
        planting_plan_repository=FakePlantingPlanRepository(_make_plan()),
        farm_repository=FakeFarmRepository(_make_farm()),
        rice_variety_repository=FakeRiceVarietyRepository(_make_rice_variety()),
        stage_prediction_snapshot_repository=FakeStagePredictionSnapshotRepository(),
        crop_stage_state_repository=FakeCropStageStateRepository(),
        crop_thermal_time_state_repository=FakeCropThermalTimeStateRepository(),
        stage_prediction_client=MockStagePredictionClient(),
        weather_provider=FakeWeatherProvider(),
    )

    with pytest.raises(ValueError, match="requires raw stage code"):
        service.apply_actual_stage_recorded(
            1,
            stage_code="heading",
            effective_date=date(2026, 6, 10),
            source_event_id=105,
        )


def test_apply_actual_stage_records_rejects_conflicting_raw_stage_date_order() -> None:
    service = StageManagementService(
        planting_plan_repository=FakePlantingPlanRepository(_make_plan()),
        farm_repository=FakeFarmRepository(_make_farm()),
        rice_variety_repository=FakeRiceVarietyRepository(_make_rice_variety()),
        stage_prediction_snapshot_repository=FakeStagePredictionSnapshotRepository(),
        crop_stage_state_repository=FakeCropStageStateRepository(),
        crop_thermal_time_state_repository=FakeCropThermalTimeStateRepository(),
        stage_prediction_client=MockStagePredictionClient(),
        weather_provider=FakeWeatherProvider(),
    )

    with pytest.raises(ValueError, match="conflict with raw stage order"):
        service.apply_actual_stage_records(
            1,
            stage_dates={
                "BBCH45": date(2026, 6, 10),
                "BBCH58": date(2026, 6, 8),
            },
            source_event_id=105,
        )


def test_extract_pest_disease_growth_stage_from_timeline() -> None:
    service = StageManagementService(
        planting_plan_repository=FakePlantingPlanRepository(_make_plan()),
        farm_repository=FakeFarmRepository(_make_farm()),
        rice_variety_repository=FakeRiceVarietyRepository(_make_rice_variety()),
        stage_prediction_snapshot_repository=FakeStagePredictionSnapshotRepository(),
        crop_stage_state_repository=FakeCropStageStateRepository(),
        crop_thermal_time_state_repository=FakeCropThermalTimeStateRepository(),
        stage_prediction_client=MockStagePredictionClient(),
        weather_provider=FakeWeatherProvider(),
    )

    result = service.refresh_prediction(
        1,
        prediction_source="initial",
        as_of_date=date(2026, 5, 27),
    )
    growth_stage = extract_pest_disease_growth_stage(result.snapshot.stage_timeline)

    assert growth_stage == {
        "tillering_date": "2026-04-14",
        "pokou_date": "2026-06-10",
        "heading_date": "2026-06-19",
        "maturity_date": "2026-07-26",
    }


def test_extract_pest_disease_growth_stage_accepts_raw_stage_codes() -> None:
    growth_stage = extract_pest_disease_growth_stage(
        {
            "stages": [
                {
                    "stage_code": "BBCH21",
                    "stage_name": "分蘖期",
                    "start_date": "2026-04-20",
                    "key_date": "2026-04-20",
                },
                {
                    "stage_code": "BBCH50",
                    "stage_name": "破口期",
                    "start_date": "2026-06-09",
                    "key_date": "2026-06-09",
                },
                {
                    "stage_code": "BBCH58",
                    "stage_name": "齐穗期",
                    "start_date": "2026-06-17",
                    "key_date": "2026-06-17",
                },
                {
                    "stage_code": "BBCH89",
                    "stage_name": "成熟期",
                    "start_date": "2026-07-19",
                    "key_date": "2026-07-19",
                },
            ],
        },
    )

    assert growth_stage == {
        "tillering_date": "2026-04-20",
        "pokou_date": "2026-06-09",
        "heading_date": "2026-06-17",
        "maturity_date": "2026-07-19",
    }


def test_stage_prediction_upstream_error_message_semanticizes_invalid_code() -> None:
    message = _build_stage_prediction_upstream_error_message(
        path="/growth-stage-gdd-thresholds",
        status_code=500,
        request_payload={
            "apprCultiType": 7,
            "subsType": 0,
            "maturType": 1,
        },
        raw_response='{"detail":"7"}',
    )

    assert "upstream rejected apprCultiType=7" in message
    assert "expected algorithm cultiType codes" in message


def test_extract_pest_disease_growth_stage_still_accepts_legacy_numeric_stage_codes() -> None:
    growth_stage = extract_pest_disease_growth_stage(
        {
            "stages": [
                {"stage_code": "21", "stage_name": "分蘖期", "start_date": "2026-04-20"},
                {"stage_code": "50", "stage_name": "破口期", "start_date": "2026-06-09"},
                {"stage_code": "58", "stage_name": "齐穗期", "start_date": "2026-06-17"},
                {"stage_code": "89", "stage_name": "成熟期", "start_date": "2026-07-19"},
            ],
        },
    )

    assert growth_stage == {
        "tillering_date": "2026-04-20",
        "pokou_date": "2026-06-09",
        "heading_date": "2026-06-17",
        "maturity_date": "2026-07-19",
    }
