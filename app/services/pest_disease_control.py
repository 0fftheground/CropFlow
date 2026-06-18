from __future__ import annotations

import json
import logging
import socket
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Protocol
from urllib import error, request
from urllib.parse import urlsplit

from app.core.constants import (
    TASK_SUBTYPE_REGULAR_DISEASE_PEST_SURVEY,
    TASK_SUBTYPE_SUDDEN_DISEASE_PEST_SURVEY,
)
from app.core.logging import LogTimer, summarize_for_log
from app.models import CalendarItem, Farm, FarmingTask, OperationPlan, PlantingPlan
from app.repositories import (
    CalendarItemRepository,
    FarmRepository,
    OperationPlanRepository,
    PlantingPlanRepository,
    RiceControlWindowLevel1Repository,
    StagePredictionSnapshotRepository,
)
from app.services.calendar_tasks import PlantProtectionPlanContextResolver, WeatherProvider
from app.services.stage_management import extract_pest_disease_growth_stage

logger = logging.getLogger(__name__)


PEST_DISEASE_SURVEY_DEFAULTS: dict[str, dict[str, Any]] = {
    "ErHuaMing": {
        "dead_sheath_rate": 0,
        "dead_heart_rate": 0,
        "main_larval_instars": 0,
        "damaged_plant_rate": 0,
    },
    "DaoFeiShi": {
        "insects_per_100_hills": 0,
    },
    "DaoWenBing": {
        "acute_lesion": False,
        "diseased_leaf_rate": 0,
    },
    "WenKuBing": {
        "lesion_on_upper_leaf_sheath": False,
        "diseased_hill_rate": 0,
    },
    "DaoZongJuanYeMing": {
        "rolled_leaf_tips_per_100_hills": 0,
        "larvae_count": 0,
        "moths_per_square_meter": 0,
    },
}


class PestDiseaseControlClient(Protocol):
    def generate_theory_control_plan(
        self,
        *,
        control_type: str,
        province: str,
        plant_info: dict[str, Any],
        survey_data: dict[str, Any],
        spray_info: dict[str, Any] | None,
        spray_info_list: list[dict[str, Any]] | None,
        level1_window: list[str] | None,
        herb_control_date: list[str] | None,
        harvest_date: str | None,
    ) -> "PestDiseaseTheoryControlResult": ...

    def adjust_control_window(
        self,
        *,
        control_type: str,
        theory_plan: dict[str, Any],
        spray_suitability_data: list[dict[str, Any]],
        plant_info: dict[str, Any] | None = None,
    ) -> "PestDiseaseAdjustedControlResult": ...

    def get_merge_spray_suitability_range(
        self,
        *,
        regular_theory: dict[str, Any],
        emergency_theory: dict[str, Any],
        extend_days: int | None = None,
        plant_info: dict[str, Any] | None = None,
    ) -> "PestDiseaseMergeRangeResult": ...

    def merge_control_plan(
        self,
        *,
        regular_theory: dict[str, Any],
        emergency_theory: dict[str, Any],
        spray_suitability_data: list[dict[str, Any]],
        min_gap_days: int | None = None,
        merge_gap_days: int | None = None,
        extend_days: int | None = None,
        plant_info: dict[str, Any] | None = None,
    ) -> "PestDiseaseMergedControlResult": ...


@dataclass(slots=True)
class PestDiseaseTheoryRound:
    round: int
    theory_window: tuple[date, date]
    targets: dict[str, Any]
    prescription: dict[str, Any]


@dataclass(slots=True)
class PestDiseaseTheoryControlResult:
    control_type: str
    control_mode: str
    status: str | None
    rounds: list[PestDiseaseTheoryRound]
    spray_suitability_required_range: tuple[date, date] | None
    flags: dict[str, Any]
    raw_data: dict[str, Any]
    raw_response: dict[str, Any]


@dataclass(slots=True)
class PestDiseaseAdjustedRound:
    round: int
    theory_window: tuple[date, date]
    final_window: tuple[date, date] | None
    targets: dict[str, Any]
    suitability_dates: dict[str, list[str]]
    weather_adjust_reason: str | None


@dataclass(slots=True)
class PestDiseaseAdjustedControlResult:
    control_type: str
    control_mode: str
    status: str | None
    rounds: list[PestDiseaseAdjustedRound]
    weather_adjust: dict[str, Any]
    raw_data: dict[str, Any]
    raw_response: dict[str, Any]


@dataclass(slots=True)
class PestDiseaseMergeRangeResult:
    spray_suitability_required_range: tuple[date, date]
    raw_data: dict[str, Any]
    raw_response: dict[str, Any]


@dataclass(slots=True)
class PestDiseaseMergedControlEvent:
    event_type: str
    round: int
    theory_window: tuple[date, date]
    final_window: tuple[date, date] | None
    targets: dict[str, Any]
    suitability_dates: dict[str, list[str]]


@dataclass(slots=True)
class PestDiseaseMergedControlResult:
    merged: bool
    message: str
    events: list[PestDiseaseMergedControlEvent]
    raw_data: dict[str, Any]
    raw_response: dict[str, Any]


@dataclass(slots=True)
class PestDiseaseTheoryPlanningResult:
    control_type: str
    task_subtype: str
    branch_type: str
    title: str
    suggested_action: str
    review_type: str
    review_title: str
    review_description: str
    request_payload: dict[str, Any]
    theory_result: PestDiseaseTheoryControlResult
    spray_suitability_data: list[dict[str, Any]]
    adjusted_result: PestDiseaseAdjustedControlResult


@dataclass(slots=True)
class PestDiseaseMergePlanningResult:
    title: str
    suggested_action: str
    review_type: str
    review_title: str
    review_description: str
    regular_theory: dict[str, Any]
    emergency_theory: dict[str, Any]
    merge_range_result: PestDiseaseMergeRangeResult
    spray_suitability_data: list[dict[str, Any]]
    merged_result: PestDiseaseMergedControlResult


@dataclass(slots=True)
class PestDiseaseReviewAdjustmentResult:
    spray_suitability_required_range: tuple[date, date]
    spray_suitability_data: list[dict[str, Any]]
    adjusted_result: PestDiseaseAdjustedControlResult


class HttpPestDiseaseControlClient:
    def __init__(self, base_url: str, timeout_seconds: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def generate_theory_control_plan(
        self,
        *,
        control_type: str,
        province: str,
        plant_info: dict[str, Any],
        survey_data: dict[str, Any],
        spray_info: dict[str, Any] | None,
        spray_info_list: list[dict[str, Any]] | None,
        level1_window: list[str] | None,
        herb_control_date: list[str] | None,
        harvest_date: str | None,
    ) -> PestDiseaseTheoryControlResult:
        payload: dict[str, Any] = {
            "control_type": control_type,
            "province": province,
            "plant_info": plant_info,
            "survey_data": survey_data,
        }
        if spray_info is not None:
            payload["spray_info"] = spray_info
        if spray_info_list is not None:
            payload["spray_info_list"] = spray_info_list
        if level1_window is not None:
            payload["level1_window"] = level1_window
        if herb_control_date is not None:
            payload["herb_control_date"] = herb_control_date
        if harvest_date is not None:
            payload["harvest_date"] = harvest_date
        response = self._post_json("/pestDisease/control/generate-theory-control-plan", payload)
        data = self._get_response_data(response, "generate-theory-control-plan")
        return _parse_theory_control_result(data, response)

    def adjust_control_window(
        self,
        *,
        control_type: str,
        theory_plan: dict[str, Any],
        spray_suitability_data: list[dict[str, Any]],
        plant_info: dict[str, Any] | None = None,
    ) -> PestDiseaseAdjustedControlResult:
        payload: dict[str, Any] = {
            "control_type": control_type,
            "theory_plan": theory_plan,
            "spray_suitability_data": spray_suitability_data,
        }
        if plant_info is not None:
            payload["plant_info"] = plant_info
        response = self._post_json("/pestDisease/control/adjust-control-window", payload)
        data = self._get_response_data(response, "adjust-control-window")
        return _parse_adjusted_control_result(data, response)

    def get_merge_spray_suitability_range(
        self,
        *,
        regular_theory: dict[str, Any],
        emergency_theory: dict[str, Any],
        extend_days: int | None = None,
        plant_info: dict[str, Any] | None = None,
    ) -> PestDiseaseMergeRangeResult:
        payload: dict[str, Any] = {
            "regular_theory": regular_theory,
            "emergency_theory": emergency_theory,
        }
        if extend_days is not None:
            payload["extend_days"] = extend_days
        if plant_info is not None:
            payload["plant_info"] = plant_info
        response = self._post_json("/pestDisease/control/get-merge-spray-suitability-range", payload)
        data = self._get_response_data(response, "get-merge-spray-suitability-range")
        return _parse_merge_range_result(data, response)

    def merge_control_plan(
        self,
        *,
        regular_theory: dict[str, Any],
        emergency_theory: dict[str, Any],
        spray_suitability_data: list[dict[str, Any]],
        min_gap_days: int | None = None,
        merge_gap_days: int | None = None,
        extend_days: int | None = None,
        plant_info: dict[str, Any] | None = None,
    ) -> PestDiseaseMergedControlResult:
        payload: dict[str, Any] = {
            "regular_theory": regular_theory,
            "emergency_theory": emergency_theory,
            "spray_suitability_data": spray_suitability_data,
        }
        if min_gap_days is not None:
            payload["min_gap_days"] = min_gap_days
        if merge_gap_days is not None:
            payload["merge_gap_days"] = merge_gap_days
        if extend_days is not None:
            payload["extend_days"] = extend_days
        if plant_info is not None:
            payload["plant_info"] = plant_info
        response = self._post_json("/pestDisease/control/merge-control-plan", payload)
        data = self._get_response_data(response, "merge-control-plan")
        return _parse_merged_control_result(data, response)

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        url = f"{self.base_url}{path}"
        http_request = request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        timer = LogTimer()
        logger.info(
            "Calling pest disease control API path=%s host=%s payload=%s",
            path,
            urlsplit(url).netloc,
            summarize_for_log(payload),
        )
        try:
            with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
                logger.info(
                    "Pest disease control API succeeded path=%s status=%s duration_ms=%.2f response=%s",
                    path,
                    getattr(response, "status", 200),
                    timer.elapsed_ms,
                    summarize_for_log(response_payload),
                )
                return response_payload
        except error.HTTPError as exc:
            raw_response = exc.read().decode("utf-8", errors="replace")
            logger.warning(
                "Pest disease control API returned HTTP error path=%s status=%s duration_ms=%.2f payload=%s response=%s",
                path,
                exc.code,
                timer.elapsed_ms,
                summarize_for_log(payload),
                summarize_for_log(raw_response),
            )
            message = f"Pest disease control API {path} returned HTTP {exc.code}"
            if raw_response:
                message = f"{message}: {raw_response}"
            raise ValueError(message) from exc
        except error.URLError as exc:
            logger.error(
                "Pest disease control API is unreachable path=%s duration_ms=%.2f payload=%s reason=%s",
                path,
                timer.elapsed_ms,
                summarize_for_log(payload),
                exc.reason,
            )
            raise RuntimeError(f"Pest disease control API {path} is unreachable: {exc.reason}") from exc
        except (TimeoutError, socket.timeout) as exc:
            logger.error(
                "Pest disease control API timed out path=%s duration_ms=%.2f payload=%s",
                path,
                timer.elapsed_ms,
                summarize_for_log(payload),
            )
            raise RuntimeError(f"Pest disease control API {path} timed out.") from exc

    def _get_response_data(self, response: dict[str, Any], api_name: str) -> dict[str, Any]:
        data = response.get("data")
        if not isinstance(data, dict):
            raise ValueError(f"{api_name} did not return a valid data object.")
        return data


class MockPestDiseaseControlClient:
    def generate_theory_control_plan(
        self,
        *,
        control_type: str,
        province: str,
        plant_info: dict[str, Any],
        survey_data: dict[str, Any],
        spray_info: dict[str, Any] | None,
        spray_info_list: list[dict[str, Any]] | None,
        level1_window: list[str] | None,
        herb_control_date: list[str] | None,
        harvest_date: str | None,
    ) -> PestDiseaseTheoryControlResult:
        survey_date = _parse_payload_date(survey_data, "survey_date", "surveyDate")
        if str(survey_data.get("mock_mode") or "") == "no_action":
            data = {
                "control_type": control_type,
                "control_mode": "无需防治",
                "status": None,
                "rounds": [],
                "spray_suitability_required_range": [],
                "flags": {"mock": True},
            }
            response = {"mock": True, "code": 200, "msg": "无需防治", "data": data}
            return _parse_theory_control_result(data, response)

        start_date = survey_date + timedelta(days=1)
        end_date = survey_date + timedelta(days=2)
        round_payload = {
            "round": 1,
            "theory_window": [start_date.strftime("%Y%m%d"), end_date.strftime("%Y%m%d")],
            "targets": _extract_mock_targets(survey_data, control_type),
            "prescription": {
                "chemicals": [],
                "water_volume": "3 L/亩",
            },
        }
        data = {
            "control_type": control_type,
            "control_mode": "单次防治",
            "status": "normal",
            "rounds": [round_payload],
            "spray_suitability_required_range": [
                start_date.strftime("%Y%m%d"),
                (end_date + timedelta(days=10)).strftime("%Y%m%d"),
            ],
            "flags": {
                "mock": True,
                "province": province,
                "has_level1_window": level1_window is not None,
                "has_spray_info": spray_info is not None,
                "spray_info_list_count": len(spray_info_list or []),
                "has_herb_control_date": herb_control_date is not None,
                "has_harvest_date": harvest_date is not None,
            },
        }
        response = {"mock": True, "code": 200, "msg": "单次防治", "data": data}
        return _parse_theory_control_result(data, response)

    def adjust_control_window(
        self,
        *,
        control_type: str,
        theory_plan: dict[str, Any],
        spray_suitability_data: list[dict[str, Any]],
        plant_info: dict[str, Any] | None = None,
    ) -> PestDiseaseAdjustedControlResult:
        normalized_theory_plan = _unwrap_theory_plan_payload(theory_plan)
        if str(normalized_theory_plan.get("mock_mode") or "") == "cancel_after_adjust":
            data = {
                "control_type": control_type,
                "control_mode": str(normalized_theory_plan.get("control_mode") or "单次防治"),
                "status": "取消防治",
                "rounds": [],
                "weather_adjust": {
                    "adjusted": False,
                    "reason": "气象调整后无可用日期",
                    "round_reasons": [],
                },
            }
            response = {"mock": True, "code": 200, "msg": "取消防治", "data": data}
            return _parse_adjusted_control_result(data, response)

        rows_by_date = {str(item["date"]): dict(item) for item in spray_suitability_data}
        adjusted_rounds: list[dict[str, Any]] = []
        round_reasons: list[dict[str, Any]] = []
        for round_item in list(normalized_theory_plan.get("rounds") or []):
            theory_window = _parse_api_date_range(round_item.get("theory_window"), "theory_window")
            candidate_dates = _build_closed_date_range(theory_window[0], theory_window[1])
            standard_dates = [
                day.strftime("%Y%m%d")
                for day in candidate_dates
                if float(rows_by_date.get(day.strftime("%Y%m%d"), {}).get("dy_ws", 0.0)) >= 1.0
            ]
            moderate_dates = [
                day.strftime("%Y%m%d")
                for day in candidate_dates
                if 0.0 < float(rows_by_date.get(day.strftime("%Y%m%d"), {}).get("dy_ws", 0.0)) < 1.0
            ]
            if standard_dates:
                final_window = [standard_dates[0]]
                reason = "理论防治时机中存在标准适宜打药日期"
            elif moderate_dates:
                final_window = [moderate_dates[0]]
                reason = "理论防治时机中存在一般适宜打药日期"
            else:
                continue
            adjusted_rounds.append(
                {
                    "round": int(round_item.get("round") or len(adjusted_rounds) + 1),
                    "theory_window": list(round_item.get("theory_window") or []),
                    "final_window": final_window,
                    "targets": dict(round_item.get("targets") or {}),
                    "suitability_dates": {
                        "standard": standard_dates,
                        "moderate": moderate_dates,
                    },
                    "weather_adjust_reason": reason,
                },
            )
            round_reasons.append({"round": adjusted_rounds[-1]["round"], "reason": reason})

        if not adjusted_rounds:
            data = {
                "control_type": control_type,
                "control_mode": str(normalized_theory_plan.get("control_mode") or "单次防治"),
                "status": "取消防治",
                "rounds": [],
                "weather_adjust": {
                    "adjusted": False,
                    "reason": "气象调整后无可用日期",
                    "round_reasons": [],
                },
            }
            response = {"mock": True, "code": 200, "msg": "取消防治", "data": data}
            return _parse_adjusted_control_result(data, response)

        data = {
            "control_type": control_type,
            "control_mode": str(normalized_theory_plan.get("control_mode") or "单次防治"),
            "status": str(normalized_theory_plan.get("status") or "normal"),
            "rounds": adjusted_rounds,
            "weather_adjust": {
                "adjusted": True,
                "reason": round_reasons[0]["reason"] if len(round_reasons) == 1 else "已按气象适宜度完成防治窗口调整",
                "round_reasons": round_reasons,
            },
        }
        response = {"mock": True, "code": 200, "msg": data["control_mode"], "data": data}
        return _parse_adjusted_control_result(data, response)

    def get_merge_spray_suitability_range(
        self,
        *,
        regular_theory: dict[str, Any],
        emergency_theory: dict[str, Any],
        extend_days: int | None = None,
        plant_info: dict[str, Any] | None = None,
    ) -> PestDiseaseMergeRangeResult:
        del plant_info
        extend_span = 2 * int(extend_days or 10) + 30
        regular_plan = _unwrap_theory_plan_payload(regular_theory)
        emergency_plan = _unwrap_theory_plan_payload(emergency_theory)
        regular_windows = [
            _parse_api_date_range(item.get("theory_window"), "regular_theory.rounds[].theory_window")
            for item in list(regular_plan.get("rounds") or [])
        ]
        emergency_windows = [
            _parse_api_date_range(item.get("theory_window"), "emergency_theory.rounds[].theory_window")
            for item in list(emergency_plan.get("rounds") or [])
        ]
        if not regular_windows or not emergency_windows:
            raise ValueError("Merged control range requires both regular and emergency theory rounds.")
        range_start = min(
            min(window[0] - timedelta(days=3) for window in regular_windows),
            min(window[0] for window in emergency_windows),
        )
        range_end = max(
            max(window[1] + timedelta(days=extend_span) for window in regular_windows),
            max(window[1] + timedelta(days=25) for window in emergency_windows),
        )
        data = {
            "spray_suitability_required_range": [
                range_start.strftime("%Y%m%d"),
                range_end.strftime("%Y%m%d"),
            ],
        }
        response = {"mock": True, "code": 200, "msg": "success", "data": data}
        return _parse_merge_range_result(data, response)

    def merge_control_plan(
        self,
        *,
        regular_theory: dict[str, Any],
        emergency_theory: dict[str, Any],
        spray_suitability_data: list[dict[str, Any]],
        min_gap_days: int | None = None,
        merge_gap_days: int | None = None,
        extend_days: int | None = None,
        plant_info: dict[str, Any] | None = None,
    ) -> PestDiseaseMergedControlResult:
        del min_gap_days, extend_days, plant_info
        gap_days = int(merge_gap_days or 3)
        rows_by_date = {str(item["date"]): dict(item) for item in spray_suitability_data}
        regular_plan = _unwrap_theory_plan_payload(regular_theory)
        emergency_plan = _unwrap_theory_plan_payload(emergency_theory)
        regular_rounds = list(regular_plan.get("rounds") or [])
        emergency_rounds = list(emergency_plan.get("rounds") or [])
        if not regular_rounds or not emergency_rounds:
            raise ValueError("merge-control-plan requires both regular and emergency theory rounds.")

        regular_window = _parse_api_date_range(regular_rounds[0].get("theory_window"), "regular_theory.rounds[0].theory_window")
        emergency_window = _parse_api_date_range(
            emergency_rounds[0].get("theory_window"),
            "emergency_theory.rounds[0].theory_window",
        )
        should_merge = emergency_window[0] <= regular_window[1] + timedelta(days=gap_days) and regular_window[0] <= emergency_window[1] + timedelta(days=gap_days)
        if should_merge:
            merged_window = (
                min(regular_window[0], emergency_window[0]),
                max(regular_window[1], emergency_window[1]),
            )
            merged_event = _build_mock_merged_event(
                event_type="merged",
                round_number=1,
                theory_window=merged_window,
                targets={
                    **dict(regular_rounds[0].get("targets") or {}),
                    **dict(emergency_rounds[0].get("targets") or {}),
                },
                rows_by_date=rows_by_date,
            )
            message = "常规防治与突发防治时间邻近，已合并为一次打药安排；理论防治时机中存在标准适宜打药日期"
            data = {"merged": True, "events": [merged_event]}
            response = {"mock": True, "code": 200, "msg": message, "data": data}
            return _parse_merged_control_result(data, response)

        events = [
            _build_mock_merged_event(
                event_type="regular",
                round_number=int(item.get("round") or index + 1),
                theory_window=_parse_api_date_range(item.get("theory_window"), "regular_theory.rounds[].theory_window"),
                targets=dict(item.get("targets") or {}),
                rows_by_date=rows_by_date,
            )
            for index, item in enumerate(regular_rounds)
        ]
        events.extend(
            _build_mock_merged_event(
                event_type="emergency",
                round_number=int(item.get("round") or index + 1),
                theory_window=_parse_api_date_range(item.get("theory_window"), "emergency_theory.rounds[].theory_window"),
                targets=dict(item.get("targets") or {}),
                rows_by_date=rows_by_date,
            )
            for index, item in enumerate(emergency_rounds)
        )
        message = "常规防治与突发防治无需合并，已分别保留最终打药安排"
        data = {"merged": False, "events": events}
        response = {"mock": True, "code": 200, "msg": message, "data": data}
        return _parse_merged_control_result(data, response)


class PestDiseaseControlPlanningService:
    REGULAR_TASK_SUBTYPE = "plant_protection.disease_pest_control"
    EMERGENCY_TASK_SUBTYPE = "plant_protection.disease_pest_control"

    def __init__(
        self,
        planting_plan_repository: PlantingPlanRepository,
        farm_repository: FarmRepository,
        rice_control_window_level1_repository: RiceControlWindowLevel1Repository,
        stage_prediction_snapshot_repository: StagePredictionSnapshotRepository | None,
        calendar_item_repository: CalendarItemRepository,
        operation_plan_repository: OperationPlanRepository,
        context_resolver: PlantProtectionPlanContextResolver,
        weather_provider: WeatherProvider,
        control_client: PestDiseaseControlClient | None = None,
    ) -> None:
        self.planting_plan_repository = planting_plan_repository
        self.farm_repository = farm_repository
        self.rice_control_window_level1_repository = rice_control_window_level1_repository
        self.stage_prediction_snapshot_repository = stage_prediction_snapshot_repository
        self.calendar_item_repository = calendar_item_repository
        self.operation_plan_repository = operation_plan_repository
        self.context_resolver = context_resolver
        self.weather_provider = weather_provider
        self.control_client = control_client or MockPestDiseaseControlClient()

    def generate_theory_plan_for_survey(
        self,
        *,
        farming_task: FarmingTask,
        survey_data: dict[str, Any],
    ) -> PestDiseaseTheoryPlanningResult:
        planting_plan = self._get_plan(farming_task.planting_plan_id)
        farm = self._get_farm(planting_plan.farm_id)
        context = self.context_resolver.resolve(planting_plan)
        control_type = self._resolve_control_type(farming_task.task_subtype)
        plant_info = self._build_plant_info(planting_plan, context.cultivation_system, context.cultivation_pattern)
        herb_control_date = self._resolve_herb_control_date(planting_plan)
        harvest_date = self._resolve_harvest_date(planting_plan)
        normalized_survey_data = _normalize_survey_data_payload(survey_data)
        if control_type == "regular":
            spray_info = self._build_regular_spray_info(planting_plan.id, farming_task)
            spray_info_list = None
            survey_date = _parse_payload_date(normalized_survey_data, "survey_date", "surveyDate")
            level1_window = self._resolve_level1_window(
                planting_plan,
                farm,
                survey_date=survey_date,
            )
        else:
            spray_info = None
            spray_info_list = self._build_emergency_spray_info_list(planting_plan.id)
            level1_window = None

        request_payload = {
            "control_type": control_type,
            "province": str(farm.province or "").strip(),
            "plant_info": plant_info,
            "survey_data": normalized_survey_data,
            "spray_info": spray_info,
            "spray_info_list": spray_info_list,
            "level1_window": level1_window,
            "herb_control_date": herb_control_date,
            "harvest_date": harvest_date,
        }
        theory_result = self.control_client.generate_theory_control_plan(
            control_type=control_type,
            province=request_payload["province"],
            plant_info=plant_info,
            survey_data=normalized_survey_data,
            spray_info=spray_info,
            spray_info_list=spray_info_list,
            level1_window=level1_window,
            herb_control_date=herb_control_date,
            harvest_date=harvest_date,
        )
        if theory_result.spray_suitability_required_range is not None:
            weather_rows = self.weather_provider.get_spray_suitability_weather(
                planting_plan,
                theory_result.spray_suitability_required_range[0],
                theory_result.spray_suitability_required_range[1],
            )
            spray_suitability_data = build_spray_suitability_data(weather_rows)
        else:
            spray_suitability_data = []
        adjusted_result = self.control_client.adjust_control_window(
            control_type=control_type,
            theory_plan=dict(theory_result.raw_data),
            spray_suitability_data=spray_suitability_data,
            plant_info=plant_info if control_type == "emergency" else None,
        )
        title = "病虫常规防治" if control_type == "regular" else "病虫突发防治"
        title_rounds = adjusted_result.rounds or theory_result.rounds
        if title_rounds:
            target_summary = _summarize_target_names(title_rounds[0].targets)
            if target_summary:
                title = f"{title}（{target_summary}）"
        return PestDiseaseTheoryPlanningResult(
            control_type=control_type,
            task_subtype=(
                self.REGULAR_TASK_SUBTYPE if control_type == "regular" else self.EMERGENCY_TASK_SUBTYPE
            ),
            branch_type=f"disease_pest_{control_type}_theory_control",
            title=title,
            suggested_action="建议执行病虫害防治",
            review_type="disease_pest_control_recommendation",
            review_title="病虫防治建议待审核",
            review_description="病虫调查结果已生成理论防治方案，需审核后再生成正式防治任务。",
            request_payload=request_payload,
            theory_result=theory_result,
            spray_suitability_data=spray_suitability_data,
            adjusted_result=adjusted_result,
        )

    def merge_theory_plans(
        self,
        *,
        planting_plan_id: int,
        regular_theory: dict[str, Any],
        emergency_theory: dict[str, Any],
    ) -> PestDiseaseMergePlanningResult:
        planting_plan = self._get_plan(planting_plan_id)
        context = self.context_resolver.resolve(planting_plan)
        plant_info = self._build_plant_info(planting_plan, context.cultivation_system, context.cultivation_pattern)
        merge_range_result = self.control_client.get_merge_spray_suitability_range(
            regular_theory=regular_theory,
            emergency_theory=emergency_theory,
            plant_info=plant_info,
        )
        weather_rows = self.weather_provider.get_spray_suitability_weather(
            planting_plan,
            merge_range_result.spray_suitability_required_range[0],
            merge_range_result.spray_suitability_required_range[1],
        )
        spray_suitability_data = build_spray_suitability_data(weather_rows)
        merged_result = self.control_client.merge_control_plan(
            regular_theory=regular_theory,
            emergency_theory=emergency_theory,
            spray_suitability_data=spray_suitability_data,
            plant_info=plant_info,
        )
        title = "病虫合并防治"
        if merged_result.events:
            target_summary = _summarize_target_names(merged_result.events[0].targets)
            if target_summary:
                title = f"{title}（{target_summary}）"
        return PestDiseaseMergePlanningResult(
            title=title,
            suggested_action="建议执行病虫合并防治",
            review_type="disease_pest_control_recommendation",
            review_title="病虫合并防治建议待审核",
            review_description="常规与突发病虫调查结果已合并生成防治方案，需审核后再生成正式防治任务。",
            regular_theory=dict(regular_theory),
            emergency_theory=dict(emergency_theory),
            merge_range_result=merge_range_result,
            spray_suitability_data=spray_suitability_data,
            merged_result=merged_result,
        )

    def adjust_theory_plan_for_review(
        self,
        *,
        planting_plan_id: int,
        control_type: str,
        theory_plan: dict[str, Any],
    ) -> PestDiseaseReviewAdjustmentResult:
        planting_plan = self._get_plan(planting_plan_id)
        context = self.context_resolver.resolve(planting_plan)
        plant_info = self._build_plant_info(planting_plan, context.cultivation_system, context.cultivation_pattern)
        normalized_theory_plan = _unwrap_theory_plan_payload(theory_plan)
        spray_suitability_required_range = _resolve_review_spray_suitability_required_range(normalized_theory_plan)
        weather_rows = self.weather_provider.get_spray_suitability_weather(
            planting_plan,
            spray_suitability_required_range[0],
            spray_suitability_required_range[1],
        )
        spray_suitability_data = build_spray_suitability_data(weather_rows)
        adjusted_result = self.control_client.adjust_control_window(
            control_type=control_type,
            theory_plan=dict(normalized_theory_plan),
            spray_suitability_data=spray_suitability_data,
            plant_info=plant_info if control_type == "emergency" else None,
        )
        return PestDiseaseReviewAdjustmentResult(
            spray_suitability_required_range=spray_suitability_required_range,
            spray_suitability_data=spray_suitability_data,
            adjusted_result=adjusted_result,
        )

    def _get_plan(self, planting_plan_id: int) -> PlantingPlan:
        planting_plan = self.planting_plan_repository.get(planting_plan_id)
        if planting_plan is None:
            raise LookupError(f"Planting plan {planting_plan_id} does not exist.")
        return planting_plan

    def _get_farm(self, farm_id: int) -> Farm:
        farm = self.farm_repository.get(farm_id)
        if farm is None:
            raise LookupError(f"Farm {farm_id} does not exist.")
        province = str(farm.province or "").strip()
        if not province:
            raise ValueError(f"Farm {farm.id} is missing province for pest disease control planning.")
        return farm

    def _resolve_control_type(self, survey_task_subtype: str) -> str:
        if survey_task_subtype == TASK_SUBTYPE_REGULAR_DISEASE_PEST_SURVEY:
            return "regular"
        if survey_task_subtype == TASK_SUBTYPE_SUDDEN_DISEASE_PEST_SURVEY:
            return "emergency"
        raise ValueError(f"Unsupported survey task subtype for pest disease control planning: {survey_task_subtype}.")

    def _build_plant_info(
        self,
        planting_plan: PlantingPlan,
        cultivation_system: str,
        cultivation_pattern: str,
    ) -> dict[str, Any]:
        growth_stage = self._resolve_growth_stage(planting_plan)
        return {
            "year": str(planting_plan.year or planting_plan.sowing_date.year),
            "cultivation_system": cultivation_system,
            "cultivation_pattern": cultivation_pattern,
            "growth_stage": {
                key: growth_stage[key]
                for key in ("tillering_date", "pokou_date", "heading_date")
                if key in growth_stage
            },
        }

    def _resolve_growth_stage(self, planting_plan: PlantingPlan) -> dict[str, str]:
        metadata_payload = planting_plan.metadata_payload or {}
        pest_disease_payload = (
            metadata_payload.get("pestDisease")
            or metadata_payload.get("pest_disease")
            or metadata_payload.get("pest_disease_control")
            or {}
        )
        raw_growth_stage = None
        if isinstance(pest_disease_payload, dict):
            raw_growth_stage = pest_disease_payload.get("growth_stage")
        if raw_growth_stage is None:
            raw_growth_stage = metadata_payload.get("growth_stage")
        if raw_growth_stage is None and self.stage_prediction_snapshot_repository is not None:
            latest_snapshot = self.stage_prediction_snapshot_repository.get_latest_by_plan(planting_plan.id)
            if latest_snapshot is not None:
                raw_growth_stage = extract_pest_disease_growth_stage(latest_snapshot.stage_timeline)
        if not isinstance(raw_growth_stage, dict):
            raise ValueError(f"Planting plan {planting_plan.id} is missing pest disease growth_stage data.")
        required_fields = ("tillering_date", "pokou_date", "heading_date")
        normalized = {field_name: _normalize_iso_date_string(raw_growth_stage.get(field_name), field_name) for field_name in required_fields}
        missing_fields = [field_name for field_name, value in normalized.items() if not value]
        if missing_fields:
            raise ValueError(f"Pest disease control growth_stage is missing fields: {sorted(missing_fields)}.")
        return normalized

    def _resolve_level1_window(self, planting_plan: PlantingPlan, farm: Farm, *, survey_date: date) -> list[str]:
        city = str(farm.city or "").strip()
        county = str(farm.district_county or "").strip()
        missing_fields = [
            field_name
            for field_name, value in (("city", city), ("district_county", county))
            if not value
        ]
        if missing_fields:
            raise ValueError(
                "Pest disease control window lookup requires Farm region fields: " + ", ".join(missing_fields) + ".",
            )
        control_window = self.rice_control_window_level1_repository.get_by_region_and_year(
            province=str(farm.province or "").strip(),
            city=city,
            county=county,
            data_year=int(planting_plan.year or planting_plan.sowing_date.year),
        )
        if control_window is None:
            raise ValueError(
                "Pest disease control window level1 is missing for "
                f"{farm.province}/{city}/{county}/{int(planting_plan.year or planting_plan.sowing_date.year)}.",
            )
        detail = control_window.detail or {}
        if not isinstance(detail, dict) or not detail:
            raise ValueError("Pest disease control window level1 detail must be a non-empty object.")
        normalized_detail = json.loads(json.dumps(detail, ensure_ascii=False))
        return _select_closest_level1_window(
            normalized_detail,
            survey_date=survey_date,
            data_year=int(control_window.data_year),
        )

    def _build_regular_spray_info(self, planting_plan_id: int, farming_task: FarmingTask) -> dict[str, Any]:
        spray_stage = "常规病虫预防"
        round_number = 1
        if farming_task.calendar_item_id is not None:
            calendar_item = self.calendar_item_repository.get(farming_task.calendar_item_id)
            if calendar_item is not None:
                spray_stage = self._resolve_regular_spray_stage(calendar_item)
                round_number = self._resolve_regular_round_number(planting_plan_id, calendar_item)
        return {
            "round": round_number,
            "stage": spray_stage,
        }

    def _resolve_regular_spray_stage(self, calendar_item: CalendarItem) -> str:
        generation_condition = dict(calendar_item.generation_condition or {})
        raw_plan = dict(generation_condition.get("rawPlan") or {})
        return str(
            generation_condition.get("sprayStage")
            or raw_plan.get("spray_stage")
            or "常规病虫预防",
        )

    def _resolve_regular_round_number(self, planting_plan_id: int, current_item: CalendarItem) -> int:
        active_items = self.calendar_item_repository.list_active_by_plan_and_subtype(
            planting_plan_id,
            TASK_SUBTYPE_REGULAR_DISEASE_PEST_SURVEY,
        )
        active_items = sorted(
            active_items,
            key=lambda item: (item.suggested_start_date, item.suggested_end_date, int(item.id or 0)),
        )
        for index, item in enumerate(active_items, start=1):
            if item.id == current_item.id:
                return index
        return 1

    def _build_emergency_spray_info_list(self, planting_plan_id: int) -> list[dict[str, Any]]:
        operation_plans = self.operation_plan_repository.list_by_plan(planting_plan_id)
        spray_info_list: list[dict[str, Any]] = []
        for operation_plan in reversed(operation_plans):
            parameters = dict(operation_plan.parameters or {})
            control_type = parameters.get("controlType")
            if control_type not in {"regular", "emergency", "merged"}:
                continue
            window = _serialize_datetime_window(operation_plan.operation_window_start, operation_plan.operation_window_end)
            spray_info_list.append(
                {
                    "stage": self._resolve_historical_spray_stage(parameters),
                    "control_type": control_type,
                    "plan_type": operation_plan.plan_type,
                    "operation_window": window,
                    "targets": parameters.get("targets") or parameters.get("targetSummary") or {},
                },
            )
        return spray_info_list

    def _resolve_historical_spray_stage(self, parameters: dict[str, Any]) -> str:
        request_payload = dict(parameters.get("requestPayload") or {})
        spray_info = dict(request_payload.get("spray_info") or {})
        stage = str(spray_info.get("stage") or "").strip()
        if stage:
            return stage

        spray_info_list = request_payload.get("spray_info_list")
        if isinstance(spray_info_list, list):
            for item in spray_info_list:
                if not isinstance(item, dict):
                    continue
                stage = str(item.get("stage") or "").strip()
                if stage:
                    return stage

        explicit_stage = str(parameters.get("sprayStage") or parameters.get("spray_stage") or "").strip()
        if explicit_stage:
            return explicit_stage

        control_type = str(parameters.get("controlType") or "").strip()
        if control_type == "regular":
            return "常规病虫预防"
        if control_type == "emergency":
            return "突发病虫防治"
        if control_type == "merged":
            return "常规+突发合并防治"
        return "历史病虫防治"

    def _resolve_herb_control_date(self, planting_plan: PlantingPlan) -> list[str] | None:
        metadata_payload = planting_plan.metadata_payload or {}
        herb_control_window = metadata_payload.get("herb_control_date") or metadata_payload.get("herbControlDate")
        if not isinstance(herb_control_window, list) or len(herb_control_window) != 2:
            return None
        return [
            _normalize_basic_date_string(herb_control_window[0], "herb_control_date[0]"),
            _normalize_basic_date_string(herb_control_window[1], "herb_control_date[1]"),
        ]

    def _resolve_harvest_date(self, planting_plan: PlantingPlan) -> str | None:
        harvest_date = planting_plan.expected_harvest_date or planting_plan.harvest_date
        return harvest_date.strftime("%Y%m%d") if harvest_date is not None else None


def calculate_spray_suitability_score(
    *,
    wins: float,
    pre: float,
    rh: float,
    tavg: float,
) -> float:
    if pre <= 2:
        prez = 1.0
    elif pre < 10:
        prez = 0.5
    else:
        return 0.0

    if wins >= 3:
        return 0.0
    winz = 1.0

    if 40 <= rh <= 95:
        rhz = 1.0
    elif 30 <= rh < 40:
        rhz = 0.5
    else:
        return 0.0

    if 15 <= tavg <= 30:
        tmpz = 1.0
    elif 10 < tavg < 15:
        tmpz = 0.5
    else:
        return 0.0

    return round((3 / 9) * prez + (3 / 9) * winz + (1 / 9) * rhz + (2 / 9) * tmpz, 2)


def build_spray_suitability_data(weather_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    suitability_rows: list[dict[str, Any]] = []
    for row in weather_rows:
        date_str = _normalize_basic_date_string(row.get("DATE") or row.get("date"), "date")
        suitability_rows.append(
            {
                "date": date_str,
                "dy_ws": calculate_spray_suitability_score(
                    wins=float(row["wins"]),
                    pre=float(row["pre"]),
                    rh=float(row["rh"]),
                    tavg=float(row.get("tAvg", row.get("tmp"))),
                ),
            },
        )
    return suitability_rows


def _parse_adjusted_control_result(
    raw_result: dict[str, Any],
    raw_response: dict[str, Any],
) -> PestDiseaseAdjustedControlResult:
    raw_rounds = raw_result.get("rounds")
    if not isinstance(raw_rounds, list):
        raise ValueError("adjust-control-window did not return rounds.")
    rounds: list[PestDiseaseAdjustedRound] = []
    for raw_round in raw_rounds:
        if not isinstance(raw_round, dict):
            raise ValueError("adjust-control-window returned invalid round item.")
        raw_final_window = raw_round.get("final_window")
        final_window = None
        if isinstance(raw_final_window, list) and raw_final_window:
            final_dates = [_parse_api_date(item) for item in raw_final_window]
            final_window = (min(final_dates), max(final_dates))
        rounds.append(
            PestDiseaseAdjustedRound(
                round=int(raw_round.get("round") or len(rounds) + 1),
                theory_window=_parse_api_date_range(raw_round.get("theory_window"), "theory_window"),
                final_window=final_window,
                targets=dict(raw_round.get("targets") or {}),
                suitability_dates=_normalize_suitability_dates(raw_round.get("suitability_dates")),
                weather_adjust_reason=(
                    str(raw_round["weather_adjust_reason"])
                    if raw_round.get("weather_adjust_reason") is not None
                    else None
                ),
            ),
        )
    return PestDiseaseAdjustedControlResult(
        control_type=str(raw_result.get("control_type") or ""),
        control_mode=str(raw_result.get("control_mode") or raw_response.get("msg") or ""),
        status=str(raw_result["status"]) if raw_result.get("status") is not None else None,
        rounds=rounds,
        weather_adjust=dict(raw_result.get("weather_adjust") or {}),
        raw_data=dict(raw_result),
        raw_response=raw_response,
    )


def _resolve_review_spray_suitability_required_range(theory_plan: dict[str, Any]) -> tuple[date, date]:
    raw_rounds = theory_plan.get("rounds")
    if not isinstance(raw_rounds, list) or not raw_rounds:
        raise ValueError("Review adjusted theory plan does not contain rounds.")
    theory_windows = []
    for raw_round in raw_rounds:
        if not isinstance(raw_round, dict):
            raise ValueError("Review adjusted theory plan contains invalid round item.")
        theory_windows.append(_parse_api_date_range(raw_round.get("theory_window"), "theory_window"))
    return (
        min(item[0] for item in theory_windows) - timedelta(days=3),
        max(item[1] for item in theory_windows) + timedelta(days=15),
    )


def _parse_merge_range_result(
    raw_result: dict[str, Any],
    raw_response: dict[str, Any],
) -> PestDiseaseMergeRangeResult:
    return PestDiseaseMergeRangeResult(
        spray_suitability_required_range=_parse_api_date_range(
            raw_result.get("spray_suitability_required_range"),
            "spray_suitability_required_range",
        ),
        raw_data=dict(raw_result),
        raw_response=raw_response,
    )


def _parse_merged_control_result(
    raw_result: dict[str, Any],
    raw_response: dict[str, Any],
) -> PestDiseaseMergedControlResult:
    raw_events = raw_result.get("events")
    if not isinstance(raw_events, list):
        raise ValueError("merge-control-plan did not return events.")
    events: list[PestDiseaseMergedControlEvent] = []
    for raw_event in raw_events:
        if not isinstance(raw_event, dict):
            raise ValueError("merge-control-plan returned invalid event item.")
        raw_final_window = raw_event.get("final_window")
        final_window = None
        if isinstance(raw_final_window, list) and raw_final_window:
            final_dates = [_parse_api_date(item) for item in raw_final_window]
            final_window = (min(final_dates), max(final_dates))
        events.append(
            PestDiseaseMergedControlEvent(
                event_type=str(raw_event.get("type") or "merged"),
                round=int(raw_event.get("round") or len(events) + 1),
                theory_window=_parse_api_date_range(raw_event.get("theory_window"), "theory_window"),
                final_window=final_window,
                targets=dict(raw_event.get("targets") or {}),
                suitability_dates=_normalize_suitability_dates(raw_event.get("suitability_dates")),
            ),
        )
    return PestDiseaseMergedControlResult(
        merged=bool(raw_result.get("merged")),
        message=str(raw_response.get("msg") or ""),
        events=events,
        raw_data=dict(raw_result),
        raw_response=raw_response,
    )


def _parse_theory_control_result(
    raw_result: dict[str, Any],
    raw_response: dict[str, Any],
) -> PestDiseaseTheoryControlResult:
    raw_rounds = raw_result.get("rounds")
    if not isinstance(raw_rounds, list):
        raise ValueError("generate-theory-control-plan did not return rounds.")
    rounds: list[PestDiseaseTheoryRound] = []
    for raw_round in raw_rounds:
        if not isinstance(raw_round, dict):
            raise ValueError("generate-theory-control-plan returned invalid round item.")
        rounds.append(
            PestDiseaseTheoryRound(
                round=int(raw_round.get("round") or len(rounds) + 1),
                theory_window=_parse_api_date_range(raw_round.get("theory_window"), "theory_window"),
                targets=dict(raw_round.get("targets") or {}),
                prescription=dict(raw_round.get("prescription") or {}),
            ),
        )
    raw_required_range = raw_result.get("spray_suitability_required_range")
    required_range = None
    if raw_required_range:
        required_range = _parse_api_date_range(raw_required_range, "spray_suitability_required_range")
    return PestDiseaseTheoryControlResult(
        control_type=str(raw_result.get("control_type") or ""),
        control_mode=str(raw_result.get("control_mode") or raw_response.get("msg") or ""),
        status=str(raw_result["status"]) if raw_result.get("status") is not None else None,
        rounds=rounds,
        spray_suitability_required_range=required_range,
        flags=dict(raw_result.get("flags") or {}),
        raw_data=dict(raw_result),
        raw_response=raw_response,
    )


def _extract_mock_targets(survey_data: dict[str, Any], control_type: str) -> dict[str, str]:
    targets = {
        key: "防治"
        for key, value in survey_data.items()
        if key not in {"survey_date", "surveyDate", "bbch_stage", "bbchStage", "survey_method", "surveyMethod", "mock_mode"}
        and isinstance(value, dict)
        and _survey_object_has_signal(value)
    }
    if targets:
        return targets
    return {"纹枯病" if control_type == "emergency" else "二化螟": "防治"}


def _survey_object_has_signal(payload: dict[str, Any]) -> bool:
    for value in payload.values():
        if isinstance(value, bool):
            if value:
                return True
            continue
        if isinstance(value, (int, float)):
            if value != 0:
                return True
            continue
        if value not in {None, ""}:
            return True
    return False


def _build_mock_merged_event(
    *,
    event_type: str,
    round_number: int,
    theory_window: tuple[date, date],
    targets: dict[str, Any],
    rows_by_date: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    candidate_dates = _build_closed_date_range(theory_window[0], theory_window[1])
    standard_dates = [
        day.strftime("%Y%m%d")
        for day in candidate_dates
        if float(rows_by_date.get(day.strftime("%Y%m%d"), {}).get("dy_ws", 0.0)) >= 1.0
    ]
    moderate_dates = [
        day.strftime("%Y%m%d")
        for day in candidate_dates
        if 0.0 < float(rows_by_date.get(day.strftime("%Y%m%d"), {}).get("dy_ws", 0.0)) < 1.0
    ]
    final_window = standard_dates[:1] or moderate_dates[:1]
    return {
        "type": event_type,
        "round": round_number,
        "theory_window": [theory_window[0].strftime("%Y%m%d"), theory_window[1].strftime("%Y%m%d")],
        "final_window": final_window,
        "targets": targets,
        "suitability_dates": {
            "standard": standard_dates,
            "moderate": moderate_dates,
        },
    }


def _summarize_target_names(targets: dict[str, Any]) -> str:
    names = [str(name).strip() for name in targets if str(name).strip()]
    return "、".join(names[:3])


def _normalize_survey_data_payload(survey_data: dict[str, Any]) -> dict[str, Any]:
    payload = dict(survey_data or {})
    if "survey_date" not in payload and "surveyDate" in payload:
        payload["survey_date"] = _normalize_basic_date_string(payload["surveyDate"], "surveyDate")
    elif "survey_date" in payload:
        payload["survey_date"] = _normalize_basic_date_string(payload["survey_date"], "survey_date")
    if "survey_method" not in payload and "surveyMethod" in payload:
        payload["survey_method"] = str(payload["surveyMethod"])
    if "bbch_stage" not in payload and "bbchStage" in payload:
        payload["bbch_stage"] = payload["bbchStage"]
    for object_key, default_fields in PEST_DISEASE_SURVEY_DEFAULTS.items():
        raw_value = payload.get(object_key)
        if raw_value is None:
            payload[object_key] = dict(default_fields)
            continue
        if not isinstance(raw_value, dict):
            raise ValueError(f"{object_key} must be an object.")
        normalized_fields = dict(default_fields)
        normalized_fields.update(raw_value)
        payload[object_key] = normalized_fields
    return payload


def _normalize_suitability_dates(raw_value: Any) -> dict[str, list[str]]:
    if not isinstance(raw_value, dict):
        return {"standard": [], "moderate": []}
    return {
        "standard": [str(item) for item in list(raw_value.get("standard") or [])],
        "moderate": [str(item) for item in list(raw_value.get("moderate") or [])],
    }


def _unwrap_theory_plan_payload(theory_plan: dict[str, Any]) -> dict[str, Any]:
    data = theory_plan.get("data")
    if isinstance(data, dict):
        return dict(data)
    return dict(theory_plan)


def _select_closest_level1_window(
    detail: dict[str, Any],
    *,
    survey_date: date,
    data_year: int,
) -> list[str]:
    closest_window: list[str] | None = None
    closest_sort_key: tuple[int, int, date] | None = None
    for sequence, raw_window in detail.items():
        if not isinstance(raw_window, list) or len(raw_window) != 2:
            raise ValueError(f"Pest disease control window level1 detail[{sequence!r}] must be a two-item MMDD list.")
        start_text = _normalize_month_day_string(raw_window[0], f"level1_window[{sequence!r}][0]")
        end_text = _normalize_month_day_string(raw_window[1], f"level1_window[{sequence!r}][1]")
        start_date = _parse_month_day_for_year(data_year, start_text)
        end_date = _parse_month_day_for_year(data_year, end_text)
        if end_date < start_date:
            raise ValueError(f"Pest disease control window level1 detail[{sequence!r}] has end before start.")
        if survey_date < start_date:
            distance = (start_date - survey_date).days
        elif survey_date > end_date:
            distance = (survey_date - end_date).days
        else:
            distance = 0
        # Prefer upcoming or current windows when the date gap is tied.
        sort_key = (distance, 0 if survey_date <= end_date else 1, start_date)
        if closest_sort_key is None or sort_key < closest_sort_key:
            closest_sort_key = sort_key
            closest_window = [start_text, end_text]
    if closest_window is None:
        raise ValueError("Pest disease control window level1 detail must be a non-empty object.")
    return closest_window


def _build_closed_date_range(start_date: date, end_date: date) -> list[date]:
    if start_date > end_date:
        return []
    values: list[date] = []
    current_date = start_date
    while current_date <= end_date:
        values.append(current_date)
        current_date += timedelta(days=1)
    return values


def _parse_payload_date(payload: dict[str, Any], *keys: str) -> date:
    for key in keys:
        if key not in payload:
            continue
        raw_value = payload[key]
        if isinstance(raw_value, date):
            return raw_value
        if isinstance(raw_value, str):
            if "-" in raw_value:
                return date.fromisoformat(raw_value)
            return date.fromisoformat(
                f"{raw_value[:4]}-{raw_value[4:6]}-{raw_value[6:8]}",
            )
    raise ValueError(f"Missing required date payload field. expected one of {keys!r}.")


def _normalize_month_day_string(raw_value: Any, field_name: str) -> str:
    value = str(raw_value)
    if len(value) != 4 or not value.isdigit():
        raise ValueError(f"{field_name} must use MMDD format.")
    _parse_month_day_for_year(2000, value)
    return value


def _parse_month_day_for_year(year: int, raw_value: str) -> date:
    return datetime.strptime(f"{year}{raw_value}", "%Y%m%d").date()


def _normalize_iso_date_string(raw_value: Any, field_name: str) -> str:
    if raw_value is None:
        return ""
    if isinstance(raw_value, date):
        return raw_value.isoformat()
    raw_text = str(raw_value).strip()
    if not raw_text:
        return ""
    if "-" in raw_text:
        return date.fromisoformat(raw_text).isoformat()
    return date.fromisoformat(f"{raw_text[:4]}-{raw_text[4:6]}-{raw_text[6:8]}").isoformat()


def _normalize_basic_date_string(raw_value: Any, field_name: str) -> str:
    if raw_value is None:
        raise ValueError(f"{field_name} is required.")
    if isinstance(raw_value, date):
        return raw_value.strftime("%Y%m%d")
    raw_text = str(raw_value).strip()
    if not raw_text:
        raise ValueError(f"{field_name} is required.")
    if "-" in raw_text:
        return date.fromisoformat(raw_text).strftime("%Y%m%d")
    if len(raw_text) != 8 or not raw_text.isdigit():
        raise ValueError(f"{field_name} must be in YYYYMMDD format.")
    return raw_text


def _parse_api_date_range(raw_value: Any, field_name: str) -> tuple[date, date]:
    if not isinstance(raw_value, list) or len(raw_value) != 2:
        raise ValueError(f"{field_name} must be a 2-item date range.")
    return (_parse_api_date(raw_value[0]), _parse_api_date(raw_value[1]))


def _parse_api_date(raw_value: Any) -> date:
    if isinstance(raw_value, date):
        return raw_value
    raw_text = str(raw_value).strip()
    if "-" in raw_text:
        return date.fromisoformat(raw_text)
    return date.fromisoformat(f"{raw_text[:4]}-{raw_text[4:6]}-{raw_text[6:8]}")


def _serialize_datetime_window(start_at: Any, end_at: Any) -> list[str]:
    if start_at is None and end_at is None:
        return []
    if start_at is None or end_at is None:
        boundary = start_at or end_at
        return [boundary.date().isoformat() if hasattr(boundary, "date") else str(boundary)]
    start_value = start_at.date().isoformat() if hasattr(start_at, "date") else str(start_at)
    end_value = end_at.date().isoformat() if hasattr(end_at, "date") else str(end_at)
    return [start_value, end_value]
