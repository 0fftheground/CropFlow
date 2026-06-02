from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date, timedelta

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
            while current_date <= date(2026, 6, 11):
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
        if path.endswith("getAvgTemAndPre") and payload["startDate"] == "2023-06-12":
            return [
                {"dt": "06-12", "temAvg": 28.1, "preAvg": 0.0},
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
    assert {item["source_type"] for item in weather_data[1:16]} == {"forecast"}
    assert [item["source_type"] for item in weather_data[-2:]] == ["climatology", "climatology"]
    assert weather_data[-3]["date"] == "2026-06-12"
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
                "startDate": "2023-06-12",
                "endDate": "2025-06-14",
            },
        ),
    ]


def test_http_weather_provider_imputes_missing_observed_temavg_from_neighboring_days() -> None:
    provider = HttpWeatherProvider(
        farm_repository=FakeFarmRepository(_make_farm()),
        base_url="http://weather.local",
        auth_token="token",
    )

    def fake_post_json(path: str, payload: dict[str, str]) -> list[dict[str, object]]:
        assert path == "/weather/v1/getAvgTemAndPre"
        assert payload == {
            "farmId": "84911829811210",
            "startDate": "2026-04-10",
            "endDate": "2026-04-12",
        }
        return [
            {"dt": "04-10", "temAvg": 20, "preAvg": 0},
            {"dt": "04-11", "temAvg": None, "preAvg": 1.2},
            {"dt": "04-12", "temAvg": 24, "preAvg": 0.4},
        ]

    provider._post_json = fake_post_json  # type: ignore[method-assign]

    weather_data = provider.get_daily_weather(
        _make_plan(),
        date(2026, 4, 10),
        date(2026, 4, 12),
        as_of_date=date(2026, 4, 13),
    )

    assert [item["avg_temp"] for item in weather_data] == [20.0, 22.0, 24.0]
    assert {item["source_type"] for item in weather_data} == {"observed"}


def test_http_weather_provider_builds_pest_disease_daily_weather_from_farm_daily_forecast() -> None:
    provider = HttpWeatherProvider(
        farm_repository=FakeFarmRepository(_make_farm()),
        base_url="http://weather.local",
        auth_token="token",
    )

    def fake_post_json(path: str, payload: dict[str, str]) -> list[dict[str, object]]:
        assert path == "/weather/v1/getForecast10DaysBeforeAnd15DaysAfter"
        assert payload == {"farmID": "84911829811210"}
        return [
            {"datatime": "2026-05-28", "tMax": 31.2, "pre": 2.5, "ssh": 4.2},
            {"datatime": "2026-05-29", "tMax": 30.8, "pre": 0.0, "ssh": 6.1},
            {"datatime": "2026-05-30", "tMax": 29.4, "pre": 1.0, "ssh": 5.3},
        ]

    provider._post_json = fake_post_json  # type: ignore[method-assign]

    weather_data = provider.get_pest_disease_daily_weather(
        _make_plan(),
        date(2026, 5, 28),
        date(2026, 5, 30),
    )

    assert weather_data == [
        {"DATE": "20260528", "TMAX": 31.2, "RAIN": 2.5, "SUN": 4.2},
        {"DATE": "20260529", "TMAX": 30.8, "RAIN": 0.0, "SUN": 6.1},
        {"DATE": "20260530", "TMAX": 29.4, "RAIN": 1.0, "SUN": 5.3},
    ]


def test_http_weather_provider_builds_hourly_weather_and_filters_typhoon_alerts() -> None:
    provider = HttpWeatherProvider(
        farm_repository=FakeFarmRepository(_make_farm()),
        base_url="http://weather.local",
        auth_token="token",
        alert_base_url="http://alerts.local",
    )

    def fake_post_json(path: str, payload: dict[str, str]) -> list[dict[str, object]]:
        assert path == "/algBaseDataApi/v1/getForecast10DaysBeforeAndAfter"
        assert payload == {"farmId": "84911829811210"}
        rows: list[dict[str, object]] = []
        start = datetime(2026, 5, 29, 0, 0, 0)
        for offset in range(80):
            current = start + timedelta(hours=offset)
            rows.append(
                {
                    "datatime": current.strftime("%Y-%m-%d %H:%M:%S"),
                    "pre": str(offset / 10),
                    "wins": "5.5",
                    "gust": "8.2",
                    "wp": "阵雨",
                },
            )
        return rows

    def fake_get_json(
        base_url: str,
        path: str,
        *,
        query_params=None,
        token=None,
    ) -> list[dict[str, object]]:
        assert base_url == "http://alerts.local"
        assert path == "/Zoomlion/alert"
        assert query_params is None
        assert token is None
        return [
            {"eventType": "台风预警", "effective": "20260529080000", "affectedArea": "430100,440100"},
            {"eventType": "暴雨事件", "effective": "20260529090000", "affectedArea": "430100"},
            {
                "eventType": "热带低压预警",
                "effective": "20260529100000",
                "affectedArea": "350100",
                "msgType": "解除",
                "msgTypeCode": "Cancel",
            },
        ]

    provider._post_json = fake_post_json  # type: ignore[method-assign]
    provider._get_json = fake_get_json  # type: ignore[method-assign]

    hourly_weather = provider.get_hourly_weather_72h(
        _make_plan(),
        as_of_datetime=datetime(2026, 5, 29, 0, 0, 0),
    )
    alerts = provider.get_typhoon_alerts(_make_plan())

    assert len(hourly_weather) == 72
    assert hourly_weather[0] == {
        "datetime": "2026-05-29 00:00:00",
        "pre": 0.0,
        "wins": 5.5,
        "gust": 8.2,
        "wp": "阵雨",
    }
    assert hourly_weather[-1]["datetime"] == "2026-05-31 23:00:00"
    assert alerts == [{"eventType": "台风预警", "effective": "20260529080000"}]
