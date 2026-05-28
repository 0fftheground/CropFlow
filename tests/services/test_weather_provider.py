from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from app.models import Farm, PlantingPlan
from app.services import HttpWeatherProvider


@dataclass
class FakeFarmRepository:
    farm: Farm

    def get(self, farm_id: int) -> Farm | None:
        return self.farm if self.farm.id == farm_id else None


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
        external_farm_id="84911829811210",
        province="湖南省",
        city="长沙市",
        district_county="岳麓区",
        adcode="430104",
    )


def test_http_weather_provider_merges_observed_forecast_and_climatology_segments() -> None:
    provider = HttpWeatherProvider(
        farm_repository=FakeFarmRepository(_make_farm()),
        base_url="http://weather.local",
        auth_token="token",
        climatology_reference_years=3,
    )
    calls: list[tuple[str, dict[str, str]]] = []

    def fake_post_json(path: str, payload: dict[str, str]) -> list[dict[str, object]]:
        calls.append((path, payload))
        if path.endswith("getAvgTemAndPre") and payload["startDate"] == "2026-05-27":
            return [{"dt": "05-27", "temAvg": 21, "preAvg": 1.2}]
        if path.endswith("getForecast10DaysBeforeAnd15DaysAfter"):
            rows: list[dict[str, object]] = []
            current_date = date(2026, 5, 28)
            while current_date <= date(2026, 6, 12):
                rows.append(
                    {
                        "datatime": current_date.isoformat(),
                        "tAvg": 25,
                        "tMin": 20,
                        "tMax": 30,
                        "pre": 0,
                    },
                )
                current_date += timedelta(days=1)
            return rows
        if path.endswith("getAvgTemAndPre") and payload["startDate"] == "2023-06-13":
            return [
                {"dt": "06-13", "temAvg": 28.5, "preAvg": 0.2},
                {"dt": "06-14", "temAvg": 28.8, "preAvg": 0.1},
            ]
        raise AssertionError(f"Unexpected weather API call: {path} {payload}")

    provider._post_json = fake_post_json  # type: ignore[method-assign]

    weather_data = provider.get_daily_weather(
        _make_plan(),
        date(2026, 5, 27),
        date(2026, 6, 14),
        as_of_date=date(2026, 5, 28),
    )

    assert weather_data[0]["date"] == "2026-05-27"
    assert weather_data[0]["source_type"] == "observed"
    assert {item["source_type"] for item in weather_data[1:17]} == {"forecast"}
    assert [item["source_type"] for item in weather_data[-2:]] == ["climatology", "climatology"]
    assert weather_data[-2]["date"] == "2026-06-13"
    assert weather_data[-1]["date"] == "2026-06-14"
    assert calls == [
        (
            "/weather/v1/getAvgTemAndPre",
            {
                "farmId": "84911829811210",
                "startDate": "2026-05-27",
                "endDate": "2026-05-27",
            },
        ),
        (
            "/weather/v1/getForecast10DaysBeforeAnd15DaysAfter",
            {
                "farmID": "84911829811210",
            },
        ),
        (
            "/weather/v1/getAvgTemAndPre",
            {
                "farmId": "84911829811210",
                "startDate": "2023-06-13",
                "endDate": "2025-06-14",
            },
        ),
    ]
