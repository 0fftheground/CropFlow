from __future__ import annotations

import argparse
import copy
import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any

from app.api.deps import build_survey_date_recommendation_service
from app.core.config import get_settings
from app.db.session import get_session_factory
from app.services import HttpPestDiseaseSurveyWindowClient


@dataclass(slots=True)
class ReplayScenario:
    name: str
    as_of_date: date
    actual_control_date: date | None
    trigger_date: date
    weather_data: list[dict[str, Any]]
    typhoon_data: dict[str, Any]


class SyntheticPestDiseaseWeatherProvider:
    def __init__(
        self,
        *,
        weather_data: list[dict[str, Any]],
        typhoon_data: dict[str, Any],
    ) -> None:
        self.weather_data = [copy.deepcopy(item) for item in weather_data]
        self.typhoon_data = copy.deepcopy(typhoon_data)

    def get_daily_weather(self, *args, **kwargs):  # pragma: no cover - not used by this replay
        raise AssertionError("get_daily_weather should not be used in pest disease daily update replay.")

    def get_pest_disease_daily_weather(self, *args, **kwargs) -> list[dict[str, Any]]:
        return [copy.deepcopy(item) for item in self.weather_data]

    def get_hourly_weather_72h(self, *args, **kwargs) -> list[dict[str, Any]]:
        return [copy.deepcopy(item) for item in self.typhoon_data["hourly_weather_72h"]]

    def get_typhoon_alerts(self, *args, **kwargs) -> list[dict[str, Any]]:
        return [copy.deepcopy(item) for item in self.typhoon_data["alerts"]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay pest disease daily-update-survey with synthetic weather data.")
    parser.add_argument("--plan-id", type=int, default=19, help="Planting plan id to replay against.")
    parser.add_argument(
        "--window-index",
        type=int,
        default=0,
        help="Which regular survey window to target from regular_plans (0-based).",
    )
    parser.add_argument(
        "--include-typhoon",
        action="store_true",
        help="Also probe a typhoon-style hourly weather variant for each trigger day.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()
    session_factory = get_session_factory()

    with session_factory() as session:
        service = build_survey_date_recommendation_service(session, settings)
        if service is None:
            raise RuntimeError("SurveyDateRecommendationService is not available.")

        base_payload = service.build_pest_disease_daily_update_payload(args.plan_id)
        if base_payload is None:
            raise RuntimeError(f"Planting plan {args.plan_id} does not have a daily-update-survey payload.")

        regular_plans = base_payload["regular_plans"]
        if not regular_plans:
            raise RuntimeError(f"Planting plan {args.plan_id} did not produce any regular plans.")
        if args.window_index < 0 or args.window_index >= len(regular_plans):
            raise RuntimeError(f"window-index {args.window_index} is out of range for {len(regular_plans)} regular plans.")

        target_plan = regular_plans[args.window_index]
        start_date, end_date = _parse_regular_window(target_plan)
        scenarios = list(
            _build_scenarios(
                base_payload=base_payload,
                start_date=start_date,
                end_date=end_date,
                include_typhoon=args.include_typhoon,
            ),
        )
        if not scenarios:
            raise RuntimeError("No replay scenarios were generated.")

        http_client = _require_http_client(service)
        results: list[dict[str, Any]] = []

        for scenario in scenarios:
            payload = {
                "growth_stage": copy.deepcopy(base_payload["growth_stage"]),
                "regular_plans": copy.deepcopy(base_payload["regular_plans"]),
                "weather_data": copy.deepcopy(scenario.weather_data),
                "typhoon_data": copy.deepcopy(scenario.typhoon_data),
            }
            result = http_client.daily_update_surveys(
                growth_stage=payload["growth_stage"],
                regular_plans=payload["regular_plans"],
                weather_data=payload["weather_data"],
                typhoon_data=payload["typhoon_data"],
                actual_control_date=scenario.actual_control_date,
            )
            row: dict[str, Any] = {
                "scenario": scenario.name,
                "as_of_date": scenario.as_of_date.isoformat(),
                "actual_control_date": scenario.actual_control_date.isoformat() if scenario.actual_control_date else None,
                "trigger_date": scenario.trigger_date.isoformat(),
                "status": result.status,
                "source": result.source,
                "survey_window": [
                    result.survey_window[0].isoformat(),
                    result.survey_window[1].isoformat(),
                ]
                if result.survey_window
                else None,
                "message": result.message,
                "raw_merge": result.raw_result.get("merge") if isinstance(result.raw_result, dict) else None,
                "raw_emergency": result.raw_result.get("emergency") if isinstance(result.raw_result, dict) else None,
            }
            if result.status == "merged_into_regular":
                row["local_mapping"] = _validate_local_mapping(
                    args.plan_id,
                    scenario=scenario,
                    settings=settings,
                )
            results.append(row)

    print(json.dumps({"plan_id": args.plan_id, "target_window": [start_date.isoformat(), end_date.isoformat()], "results": results}, ensure_ascii=False, indent=2))


def _parse_regular_window(regular_plan: dict[str, Any]) -> tuple[date, date]:
    raw_window = regular_plan.get("调查日期")
    if not isinstance(raw_window, list) or len(raw_window) != 2:
        raise RuntimeError(f"Regular plan is missing 调查日期: {regular_plan}")
    return (_parse_compact_date(raw_window[0]), _parse_compact_date(raw_window[1]))


def _build_scenarios(
    *,
    base_payload: dict[str, Any],
    start_date: date,
    end_date: date,
    include_typhoon: bool,
) -> list[ReplayScenario]:
    base_weather = _deepcopy_rows(base_payload["weather_data"])
    scenarios: list[ReplayScenario] = []
    for current in _date_range(start_date, end_date):
        scenarios.append(
            ReplayScenario(
                name=f"bad-stretch:{current.isoformat()}:no-typhoon",
                as_of_date=current,
                actual_control_date=current - timedelta(days=1),
                trigger_date=current,
                weather_data=_make_bad_stretch_weather(base_weather, trigger_date=current),
                typhoon_data=_make_hourly_weather(current, typhoon=False),
            ),
        )
        if include_typhoon:
            scenarios.append(
                ReplayScenario(
                    name=f"bad-stretch:{current.isoformat()}:typhoon",
                    as_of_date=current,
                    actual_control_date=current - timedelta(days=1),
                    trigger_date=current,
                    weather_data=_make_bad_stretch_weather(base_weather, trigger_date=current),
                    typhoon_data=_make_hourly_weather(current, typhoon=True),
                ),
            )
    return scenarios


def _make_bad_stretch_weather(
    base_weather: list[dict[str, Any]],
    *,
    trigger_date: date,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    bad_start = trigger_date - timedelta(days=7)
    for item in base_weather:
        row = copy.deepcopy(item)
        row_date = _parse_compact_date(str(row["DATE"]))
        if bad_start <= row_date <= trigger_date:
            row["TMAX"] = 22.0
            row["RAIN"] = 22.0
            row["SUN"] = 0.2
        else:
            row["TMAX"] = max(float(row.get("TMAX", 30.0)), 31.0)
            row["RAIN"] = 0.0
            row["SUN"] = max(float(row.get("SUN", 8.0)), 10.0)
        rows.append(row)
    return rows


def _make_hourly_weather(as_of_date: date, *, typhoon: bool) -> dict[str, Any]:
    start = datetime.combine(as_of_date, time(hour=0))
    if typhoon:
        alerts = [{"eventType": "台风预警", "effective": start.strftime("%Y%m%d%H%M%S")}]
        hourly_rows = [
            {
                "datetime": (start + timedelta(hours=index)).strftime("%Y-%m-%d %H:%M:%S"),
                "pre": 8.0,
                "wins": 9.5,
                "gust": 13.0,
                "wp": "暴雨",
            }
            for index in range(72)
        ]
    else:
        alerts = []
        hourly_rows = [
            {
                "datetime": (start + timedelta(hours=index)).strftime("%Y-%m-%d %H:%M:%S"),
                "pre": 0.0,
                "wins": 2.0,
                "gust": 3.0,
                "wp": "多云",
            }
            for index in range(72)
        ]
    return {"alerts": alerts, "hourly_weather_72h": hourly_rows}


def _validate_local_mapping(
    planting_plan_id: int,
    *,
    scenario: ReplayScenario,
    settings,
) -> dict[str, Any]:
    session_factory = get_session_factory()
    with session_factory() as session:
        replay_service = build_survey_date_recommendation_service(session, settings)
        if replay_service is None:
            raise RuntimeError("SurveyDateRecommendationService is not available for mapping validation.")
        replay_service.weather_provider = SyntheticPestDiseaseWeatherProvider(
            weather_data=scenario.weather_data,
            typhoon_data=scenario.typhoon_data,
        )
        items = replay_service.recommend_pest_disease_daily_update_surveys(
            planting_plan_id,
            as_of_date=scenario.as_of_date,
            actual_control_date=scenario.actual_control_date,
        )
        summary = {
            "returned_item_count": len(items),
            "returned_subtypes": [item.task_subtype for item in items],
            "generation_condition_summaries": [
                {
                    "status": item.generation_condition.get("status"),
                    "source": item.generation_condition.get("source"),
                    "surveyType": item.generation_condition.get("surveyType"),
                    "checkDate": item.generation_condition.get("checkDate"),
                    "sprayStage": item.generation_condition.get("sprayStage"),
                }
                for item in items
            ],
        }
        session.rollback()
        return summary


def _require_http_client(service) -> HttpPestDiseaseSurveyWindowClient:
    client = service.pest_disease_client
    if not isinstance(client, HttpPestDiseaseSurveyWindowClient):
        raise RuntimeError("This replay requires CROPFLOW_PEST_DISEASE_SURVEY_BASE_URL to use the real HTTP client.")
    return client


def _date_range(start_date: date, end_date: date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def _deepcopy_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [copy.deepcopy(item) for item in rows]


def _parse_compact_date(value: str) -> date:
    return datetime.strptime(value, "%Y%m%d").date()


if __name__ == "__main__":
    main()
