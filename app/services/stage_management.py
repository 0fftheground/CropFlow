from __future__ import annotations

import json
import logging
import socket
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Protocol
from urllib import error, request
from urllib.parse import urlsplit

from app.core.logging import LogTimer, summarize_for_log
from app.models import CropStageState, CropThermalTimeState, Farm, PlantingPlan, StagePredictionSnapshot
from app.repositories import (
    CropStageDictRepository,
    CropStageStateRepository,
    CropThermalTimeStateRepository,
    FarmRepository,
    PlantingPlanRepository,
    RiceVarietyRepository,
    StagePredictionSnapshotRepository,
)

logger = logging.getLogger(__name__)
DEFAULT_STAGE_WEATHER_LOOKAHEAD_DAYS = 180
DEFAULT_THERMAL_TIME_UNIT = "degree_day"
DEFAULT_BASE_TEMPERATURE = 12
DEFAULT_UPPER_TEMPERATURE_CAP = 40
DEFAULT_LOWER_TEMPERATURE_FLOOR = 12
DEFAULT_CALCULATION_METHOD = "avg_temp_minus_base_capped"
DEFAULT_ROUNDING_RULE = "keep_1_decimal_daily_keep_1_decimal_accumulated"
DEFAULT_EFFECTIVE_DATE_RULE = "threshold_reached_same_day"
_DECIMAL_ZERO = Decimal("0")
_STAGE_SEQUENCE: list[tuple[str, str]] = [
    ("seedling", "苗期"),
    ("tillering", "分蘖期"),
    ("pokou", "破口期"),
    ("heading", "齐穗期"),
    ("maturity", "成熟期"),
]
_THRESHOLDED_STAGE_CODES = [code for code, _ in _STAGE_SEQUENCE if code != "seedling"]
_STAGE_NAME_BY_CODE = dict(_STAGE_SEQUENCE)
_STAGE_INDEX_BY_CODE = {code: index for index, (code, _) in enumerate(_STAGE_SEQUENCE)}
_DEFAULT_RAW_STAGE_SEQUENCE: list[dict[str, str | None]] = [
    {"stage_code": "BBCH13", "stage_name": "三叶一心", "season_scope": "main", "business_stage_code": None},
    {"stage_code": "BBCH21", "stage_name": "分蘖始期", "season_scope": "main", "business_stage_code": "tillering"},
    {"stage_code": "BBCH28", "stage_name": "有效分蘖终止期", "season_scope": "main", "business_stage_code": None},
    {"stage_code": "BBCH41", "stage_name": "幼穗分化1期", "season_scope": "main", "business_stage_code": None},
    {"stage_code": "BBCH42", "stage_name": "幼穗分化2期", "season_scope": "main", "business_stage_code": None},
    {"stage_code": "BBCH44", "stage_name": "幼穗分化4期", "season_scope": "main", "business_stage_code": None},
    {"stage_code": "BBCH45", "stage_name": "孕穗期", "season_scope": "main", "business_stage_code": None},
    {"stage_code": "BBCH50", "stage_name": "破口期", "season_scope": "main", "business_stage_code": "pokou"},
    {"stage_code": "BBCH51", "stage_name": "始穗期", "season_scope": "main", "business_stage_code": None},
    {"stage_code": "BBCH55", "stage_name": "抽穗期", "season_scope": "main", "business_stage_code": None},
    {"stage_code": "BBCH58", "stage_name": "齐穗期", "season_scope": "main", "business_stage_code": "heading"},
    {"stage_code": "BBCH89", "stage_name": "成熟期", "season_scope": "main", "business_stage_code": "maturity"},
    {"stage_code": "Z_BBCH51", "stage_name": "再生季始穗期", "season_scope": "ratoon", "business_stage_code": None},
    {"stage_code": "Z_BBCH58", "stage_name": "再生季齐穗期", "season_scope": "ratoon", "business_stage_code": None},
    {"stage_code": "Z_BBCH89", "stage_name": "再生季成熟期", "season_scope": "ratoon", "business_stage_code": None},
]
_RAW_STAGE_SEQUENCE: list[dict[str, str | None]] = [dict(item) for item in _DEFAULT_RAW_STAGE_SEQUENCE]
_RAW_STAGE_METADATA_BY_CODE: dict[str, dict[str, str | None]] = {}
_RAW_STAGE_NAME_BY_CODE: dict[str, str] = {}
_RAW_STAGE_ORDER_INDEX: dict[str, int] = {}
_RAW_STAGE_CODE_BY_BUSINESS_STAGE: dict[str, str] = {}
_RAW_STAGE_CODE_ALIASES_BY_BUSINESS_STAGE = {
    "tillering": ("21",),
    "pokou": ("50",),
    "heading": ("58",),
    "maturity": ("89",),
}
_BUSINESS_STAGE_BY_RAW_STAGE_CODE: dict[str, str] = {}
_LOCAL_TO_STAGE_ALGORITHM_CULTI_TYPE = {
    4: 3,  # 双季晚稻
    5: 4,  # 早稻
    6: 5,  # 一季晚稻
    7: 6,  # 中稻
    8: 8,  # 再生稻
}
_LOCAL_TO_STAGE_ALGORITHM_SUBS_TYPE = {
    9: 0,   # 籼
    10: 1,  # 粳
    11: 2,  # 籼粳交
}
_LOCAL_TO_STAGE_ALGORITHM_MATUR_TYPE = {
    12: 0,  # 早熟
    13: 1,  # 中熟
    14: 2,  # 中迟熟
    15: 3,  # 早中熟
    16: 4,  # 迟熟
    17: 5,  # -
}
_EARLY_RICE_STAGE_ALGORITHM_CULTI_TYPE = 4
_DIRECT_SEEDED_PLANTING_METHOD_CODE = 1
_THREE_LEAF_ONE_HEART_STAGE_CODE = "BBCH13"


def _rebuild_stage_registry(raw_stage_sequence: list[dict[str, str | None]]) -> None:
    global _RAW_STAGE_SEQUENCE
    global _RAW_STAGE_METADATA_BY_CODE
    global _RAW_STAGE_NAME_BY_CODE
    global _RAW_STAGE_ORDER_INDEX
    global _RAW_STAGE_CODE_BY_BUSINESS_STAGE
    global _BUSINESS_STAGE_BY_RAW_STAGE_CODE

    _RAW_STAGE_SEQUENCE = [dict(item) for item in raw_stage_sequence]
    _RAW_STAGE_METADATA_BY_CODE = {
        str(item["stage_code"]): dict(item)
        for item in _RAW_STAGE_SEQUENCE
    }
    _RAW_STAGE_NAME_BY_CODE = {
        raw_stage_code: str(metadata["stage_name"])
        for raw_stage_code, metadata in _RAW_STAGE_METADATA_BY_CODE.items()
    }
    _RAW_STAGE_ORDER_INDEX = {
        str(item["stage_code"]): index
        for index, item in enumerate(_RAW_STAGE_SEQUENCE)
    }
    _RAW_STAGE_CODE_BY_BUSINESS_STAGE = {
        str(item["business_stage_code"]): str(item["stage_code"])
        for item in _RAW_STAGE_SEQUENCE
        if item.get("business_stage_code")
    }
    _BUSINESS_STAGE_BY_RAW_STAGE_CODE = {}
    for business_stage_code, raw_stage_code in _RAW_STAGE_CODE_BY_BUSINESS_STAGE.items():
        _BUSINESS_STAGE_BY_RAW_STAGE_CODE[raw_stage_code] = business_stage_code
        for alias in _RAW_STAGE_CODE_ALIASES_BY_BUSINESS_STAGE.get(business_stage_code, ()):
            _BUSINESS_STAGE_BY_RAW_STAGE_CODE[alias] = business_stage_code


def _load_stage_registry_from_repository(
    crop_stage_dict_repository: CropStageDictRepository | None,
) -> list[dict[str, str | None]]:
    if crop_stage_dict_repository is None:
        return [dict(item) for item in _DEFAULT_RAW_STAGE_SEQUENCE]
    items = crop_stage_dict_repository.list_active()
    if not items:
        return [dict(item) for item in _DEFAULT_RAW_STAGE_SEQUENCE]
    return [
        {
            "stage_code": item.stage_code,
            "stage_name": item.stage_name,
            "season_scope": item.season_scope,
            "business_stage_code": item.business_stage_code,
        }
        for item in items
    ]


_rebuild_stage_registry(_DEFAULT_RAW_STAGE_SEQUENCE)


@dataclass(slots=True)
class StageTimelineNode:
    stage_code: str
    stage_name: str
    start_date: date
    end_date: date | None
    key_date: date | None
    raw_stage_code: str | None
    metadata: dict[str, Any]


@dataclass(slots=True)
class StagePredictionResult:
    algorithm_code: str
    algorithm_version: str | None
    threshold_rule: dict[str, Any]
    raw_response: dict[str, Any]


@dataclass(slots=True)
class StageRefreshResult:
    snapshot: StagePredictionSnapshot
    crop_stage_state: CropStageState
    crop_thermal_time_state: CropThermalTimeState
    previous_stage_code: str | None
    stage_changed: bool


@dataclass(slots=True)
class StageStateSnapshot:
    crop_stage_state: CropStageState | None
    crop_thermal_time_state: CropThermalTimeState | None
    latest_prediction_snapshot: StagePredictionSnapshot | None


@dataclass(slots=True)
class ActualStageRecordResult:
    snapshot: StagePredictionSnapshot
    crop_stage_state: CropStageState
    crop_thermal_time_state: CropThermalTimeState
    previous_stage_code: str | None
    stage_changed: bool


@dataclass(slots=True)
class StageCalculationContext:
    as_of_date: date
    start_date: date
    weather_data: list[dict[str, Any]]


@dataclass(slots=True)
class StageDerivedState:
    stage_timeline: dict[str, Any]
    current_node: StageTimelineNode
    accumulated_thermal_time: Decimal
    last_calculated_date: date
    data_version: str | None
    thermal_audit_summary: dict[str, Any]


class StagePredictionClient(Protocol):
    def predict_stage(
        self,
        *,
        request_payload: dict[str, Any],
    ) -> StagePredictionResult: ...


class StageWeatherProvider(Protocol):
    def get_daily_weather(
        self,
        planting_plan: PlantingPlan,
        start_date: date,
        end_date: date,
        *,
        as_of_date: date | None = None,
    ) -> list[dict[str, Any]]: ...


class HttpStagePredictionClient:
    def __init__(self, base_url: str, timeout_seconds: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def predict_stage(
        self,
        *,
        request_payload: dict[str, Any],
    ) -> StagePredictionResult:
        response = self._post_json("/growth-stage-gdd-thresholds", request_payload)
        data = response.get("data") if isinstance(response.get("data"), dict) else response
        if not isinstance(data, dict):
            raise ValueError("growth stage gdd API did not return a valid data object.")
        if "threshold_rule" in data and isinstance(data.get("threshold_rule"), dict):
            threshold_rule = dict(data["threshold_rule"])
        else:
            threshold_rule = {
                "stage_thresholds": {
                    key: value
                    for key, value in data.items()
                    if isinstance(key, str) and key
                },
            }
        if not isinstance(threshold_rule.get("stage_thresholds"), dict) or not threshold_rule["stage_thresholds"]:
            raise ValueError("growth stage gdd API did not return stage thresholds.")
        return StagePredictionResult(
            algorithm_code=str(data.get("algorithm_code") or "growth_stage_gdd_thresholds"),
            algorithm_version=str(data["algorithm_version"]) if data.get("algorithm_version") is not None else None,
            threshold_rule=threshold_rule,
            raw_response=response,
        )

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
            "Calling stage prediction API path=%s host=%s payload=%s",
            path,
            urlsplit(url).netloc,
            summarize_for_log(payload),
        )
        try:
            with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
                logger.info(
                    "Stage prediction API succeeded path=%s status=%s duration_ms=%.2f response=%s",
                    path,
                    getattr(response, "status", 200),
                    timer.elapsed_ms,
                    summarize_for_log(response_payload),
                )
                return response_payload
        except error.HTTPError as exc:
            raw_response = exc.read().decode("utf-8", errors="replace")
            logger.warning(
                "Stage prediction API returned HTTP error path=%s status=%s duration_ms=%.2f payload=%s response=%s",
                path,
                exc.code,
                timer.elapsed_ms,
                summarize_for_log(payload),
                summarize_for_log(raw_response),
            )
            message = _build_stage_prediction_upstream_error_message(
                path=path,
                status_code=exc.code,
                request_payload=payload,
                raw_response=raw_response,
            )
            raise ValueError(message) from exc
        except error.URLError as exc:
            logger.error(
                "Stage prediction API is unreachable path=%s duration_ms=%.2f payload=%s reason=%s",
                path,
                timer.elapsed_ms,
                summarize_for_log(payload),
                exc.reason,
            )
            raise RuntimeError(f"Stage prediction API {path} is unreachable: {exc.reason}") from exc
        except (TimeoutError, socket.timeout) as exc:
            logger.error(
                "Stage prediction API timed out path=%s duration_ms=%.2f payload=%s",
                path,
                timer.elapsed_ms,
                summarize_for_log(payload),
            )
            raise RuntimeError(f"Stage prediction API {path} timed out.") from exc


class MockStagePredictionClient:
    def predict_stage(
        self,
        *,
        request_payload: dict[str, Any],
    ) -> StagePredictionResult:
        if request_payload.get("sowing_date") is not None:
            _parse_required_iso_date(request_payload.get("sowing_date"), "sowing_date")
        else:
            if not str(request_payload.get("apprArea") or "").strip():
                raise ValueError("apprArea is required.")
        threshold_rule = {
            "stage_thresholds": {
                "BBCH13": 64,
                "BBCH21": 176,
                "BBCH28": 352,
                "BBCH41": 688,
                "BBCH42": 736,
                "BBCH44": 832,
                "BBCH45": 912,
                "BBCH50": 976,
                "BBCH51": 1008,
                "BBCH55": 1072,
                "BBCH58": 1104,
                "BBCH89": 1616,
            },
        }
        return StagePredictionResult(
            algorithm_code="growth_stage_gdd_thresholds",
            algorithm_version=None,
            threshold_rule=threshold_rule,
            raw_response={
                "mock": True,
                "data": {
                    **threshold_rule["stage_thresholds"],
                },
            },
        )


def _build_stage_prediction_upstream_error_message(
    *,
    path: str,
    status_code: int,
    request_payload: dict[str, Any],
    raw_response: str,
) -> str:
    prefix = f"Stage prediction API {path} returned HTTP {status_code}"
    parsed_response = _parse_stage_prediction_error_response(raw_response)
    detail = parsed_response.get("detail")
    semantic_hint = _build_stage_prediction_error_hint(detail=detail, request_payload=request_payload)
    if semantic_hint:
        return f"{prefix}: {semantic_hint}"
    if raw_response:
        return f"{prefix}: {raw_response}"
    return prefix


def _parse_stage_prediction_error_response(raw_response: str) -> dict[str, Any]:
    if not raw_response:
        return {}
    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _build_stage_prediction_error_hint(*, detail: Any, request_payload: dict[str, Any]) -> str | None:
    detail_text = str(detail).strip() if detail is not None else ""
    if not detail_text:
        return None
    invalid_field_name = None
    invalid_value = None
    for field_name in ("apprCultiType", "cultiType", "subsType", "maturType"):
        payload_value = request_payload.get(field_name)
        if payload_value is None:
            continue
        if str(payload_value) == detail_text:
            invalid_field_name = field_name
            invalid_value = payload_value
            break
    if invalid_field_name is None:
        return None
    expected_codes = {
        "apprCultiType": "expected algorithm cultiType codes: 3=双季晚稻, 4=早稻, 5=一季晚稻, 6=中稻, 8=再生稻",
        "cultiType": "expected algorithm cultiType codes: 3=双季晚稻, 4=早稻, 5=一季晚稻, 6=中稻, 8=再生稻",
        "subsType": "expected algorithm subsType codes: 0=籼, 1=粳, 2=籼粳交",
        "maturType": "expected algorithm maturType codes: 0=早熟, 1=中熟, 2=中迟熟, 3=早中熟, 4=迟熟, 5=-",
    }
    return (
        f"upstream rejected {invalid_field_name}={invalid_value}; "
        f"{expected_codes[invalid_field_name]}; upstream detail={detail_text}"
    )


class StageManagementService:
    def __init__(
        self,
        planting_plan_repository: PlantingPlanRepository,
        farm_repository: FarmRepository,
        rice_variety_repository: RiceVarietyRepository | None,
        stage_prediction_snapshot_repository: StagePredictionSnapshotRepository,
        crop_stage_state_repository: CropStageStateRepository,
        crop_thermal_time_state_repository: CropThermalTimeStateRepository,
        stage_prediction_client: StagePredictionClient,
        weather_provider: StageWeatherProvider,
        weather_lookahead_days: int = DEFAULT_STAGE_WEATHER_LOOKAHEAD_DAYS,
        crop_stage_dict_repository: CropStageDictRepository | None = None,
    ) -> None:
        self.planting_plan_repository = planting_plan_repository
        self.farm_repository = farm_repository
        self.rice_variety_repository = rice_variety_repository
        self.stage_prediction_snapshot_repository = stage_prediction_snapshot_repository
        self.crop_stage_state_repository = crop_stage_state_repository
        self.crop_thermal_time_state_repository = crop_thermal_time_state_repository
        self.stage_prediction_client = stage_prediction_client
        self.weather_provider = weather_provider
        self.weather_lookahead_days = weather_lookahead_days
        self.crop_stage_dict_repository = crop_stage_dict_repository
        _rebuild_stage_registry(_load_stage_registry_from_repository(crop_stage_dict_repository))

    def refresh_prediction(
        self,
        planting_plan_id: int,
        *,
        prediction_source: str,
        source_event_id: int | None = None,
        as_of_date: date | None = None,
    ) -> StageRefreshResult:
        planting_plan = self._get_plan(planting_plan_id)
        farm = self._get_farm(planting_plan.farm_id)
        effective_as_of_date = as_of_date or date.today()
        request_payload = _build_stage_rule_request_payload(
            planting_plan,
            farm=farm,
            rice_variety_repository=self.rice_variety_repository,
        )
        latest_snapshot = self.stage_prediction_snapshot_repository.get_latest_by_plan(planting_plan_id)
        prediction = self.stage_prediction_client.predict_stage(request_payload=request_payload)
        threshold_rule = _enrich_stage_threshold_rule(
            prediction.threshold_rule,
            request_payload=request_payload,
        )
        calculation_context = _build_stage_calculation_context(
            planting_plan,
            as_of_date=effective_as_of_date,
            weather_provider=self.weather_provider,
            weather_lookahead_days=self.weather_lookahead_days,
        )
        return self._refresh_from_threshold_rule(
            planting_plan=planting_plan,
            request_payload=request_payload,
            threshold_rule=threshold_rule,
            algorithm_code=prediction.algorithm_code,
            algorithm_version=prediction.algorithm_version,
            prediction_source=prediction_source,
            calculation_context=calculation_context,
            source_event_id=source_event_id,
            manual_raw_stage_dates=(
                _extract_manual_raw_stage_dates(latest_snapshot.stage_timeline) if latest_snapshot is not None else None
            ),
        )

    def refresh_for_weather_update(
        self,
        planting_plan_id: int,
        *,
        source_event_id: int | None = None,
        as_of_date: date | None = None,
        source_event_payload: dict[str, Any] | None = None,
    ) -> StageRefreshResult:
        planting_plan = self._get_plan(planting_plan_id)
        farm = self._get_farm(planting_plan.farm_id)
        latest_snapshot = self.stage_prediction_snapshot_repository.get_latest_by_plan(planting_plan_id)
        if latest_snapshot is None:
            raise LookupError(
                f"Weather-driven stage refresh requires an existing StagePredictionSnapshot for planting plan {planting_plan_id}.",
            )
        if not latest_snapshot.thermal_thresholds:
            raise ValueError(
                f"Latest StagePredictionSnapshot for planting plan {planting_plan_id} does not contain threshold rules.",
            )
        effective_as_of_date = as_of_date or date.today()
        request_payload = _build_stage_rule_request_payload(
            planting_plan,
            farm=farm,
            rice_variety_repository=self.rice_variety_repository,
        )
        threshold_rule = _enrich_stage_threshold_rule(
            latest_snapshot.thermal_thresholds or {},
            request_payload=request_payload,
        )
        existing_thermal_state = self.crop_thermal_time_state_repository.get_by_plan(planting_plan_id)
        weather_payload = dict(source_event_payload or {})
        source_type = _resolve_weather_update_source_type(weather_payload)
        manual_raw_stage_dates = _extract_manual_raw_stage_dates(latest_snapshot.stage_timeline)
        recalculation_start_date, recalculation_mode = _resolve_weather_recalculation_start_date(
            planting_plan=planting_plan,
            latest_snapshot=latest_snapshot,
            existing_thermal_state=existing_thermal_state,
            source_event_payload=weather_payload,
            as_of_date=effective_as_of_date,
        )
        calculation_context = _build_stage_calculation_context(
            planting_plan,
            as_of_date=effective_as_of_date,
            weather_provider=self.weather_provider,
            weather_lookahead_days=self.weather_lookahead_days,
            start_date=recalculation_start_date,
        )
        recalculation_seed = _build_weather_recalculation_seed(
            planting_plan=planting_plan,
            latest_snapshot=latest_snapshot,
            threshold_rule=threshold_rule,
            weather_provider=self.weather_provider,
            as_of_date=effective_as_of_date,
            recalculation_start_date=recalculation_start_date,
            recalculation_mode=recalculation_mode,
            existing_thermal_state=existing_thermal_state,
        )
        return self._refresh_from_threshold_rule(
            planting_plan=planting_plan,
            request_payload=request_payload,
            threshold_rule=threshold_rule,
            algorithm_code=latest_snapshot.algorithm_code,
            algorithm_version=latest_snapshot.algorithm_version,
            prediction_source="weather_update",
            calculation_context=calculation_context,
            source_event_id=source_event_id,
            rule_snapshot_id=latest_snapshot.id,
            initial_accumulated_thermal_time=recalculation_seed["accumulated_thermal_time"],
            initial_last_calculated_date=recalculation_seed["last_calculated_date"],
            initial_data_version=recalculation_seed["data_version"],
            initial_stage_start_dates=recalculation_seed["stage_start_dates"],
            preserve_existing_stage_state=source_type != "observed",
            manual_raw_stage_dates=manual_raw_stage_dates,
            recalculation_summary={
                "mode": recalculation_mode,
                "source_type": source_type,
                "weather_change_type": weather_payload.get("weatherChangeType")
                or weather_payload.get("weather_change_type"),
                "recalculation_start_date": (
                    recalculation_start_date.isoformat() if recalculation_start_date is not None else None
                ),
                "as_of_date": effective_as_of_date.isoformat(),
                "current_stage_basis": "observed_only",
                "prediction_only": source_type != "observed",
            },
        )

    def get_stage_snapshot(self, planting_plan_id: int) -> StageStateSnapshot:
        self._get_plan(planting_plan_id)
        return StageStateSnapshot(
            crop_stage_state=self.crop_stage_state_repository.get_by_plan(planting_plan_id),
            crop_thermal_time_state=self.crop_thermal_time_state_repository.get_by_plan(planting_plan_id),
            latest_prediction_snapshot=self.stage_prediction_snapshot_repository.get_latest_by_plan(planting_plan_id),
        )

    def apply_actual_stage_recorded(
        self,
        planting_plan_id: int,
        *,
        stage_code: str,
        effective_date: date,
        stage_name: str | None = None,
        source_event_id: int | None = None,
    ) -> ActualStageRecordResult:
        return self.apply_actual_stage_records(
            planting_plan_id,
            stage_dates={stage_code: effective_date},
            stage_names={stage_code: stage_name} if stage_name is not None else None,
            source_event_id=source_event_id,
        )

    def apply_actual_stage_records(
        self,
        planting_plan_id: int,
        *,
        stage_dates: dict[str, date],
        stage_names: dict[str, str | None] | None = None,
        source_event_id: int | None = None,
    ) -> ActualStageRecordResult:
        planting_plan = self._get_plan(planting_plan_id)
        farm = self._get_farm(planting_plan.farm_id)
        if not stage_dates:
            raise ValueError("ActualStageRecorded requires at least one raw stage code.")
        normalized_stage_dates: dict[str, date] = {}
        for stage_code, effective_date in stage_dates.items():
            normalized_input_stage_code = str(stage_code).strip()
            if not normalized_input_stage_code:
                raise ValueError("ActualStageRecorded requires stage_code.")
            if not is_raw_stage_code(normalized_input_stage_code):
                raise ValueError(f"ActualStageRecorded requires raw stage code, got: {stage_code}.")
            normalized_stage_dates[normalized_input_stage_code] = effective_date
        validate_manual_raw_stage_dates(normalized_stage_dates)
        latest_stage_code, latest_effective_date = max(
            normalized_stage_dates.items(),
            key=lambda item: (item[1], get_raw_stage_order_index(item[0]) or -1),
        )
        normalized_raw_stage_code = latest_stage_code
        normalized_stage_code = _normalize_business_stage_code(latest_stage_code, normalized_raw_stage_code)
        stage_name = stage_names.get(latest_stage_code) if stage_names is not None else None
        resolved_stage_name = (
            stage_name
            or (normalized_raw_stage_code and _RAW_STAGE_NAME_BY_CODE.get(normalized_raw_stage_code))
            or _STAGE_NAME_BY_CODE.get(normalized_stage_code)
            or normalized_stage_code
        )
        current_stage_code = normalized_raw_stage_code
        latest_snapshot = self.stage_prediction_snapshot_repository.get_latest_by_plan(planting_plan_id)
        request_payload = _build_stage_rule_request_payload(
            planting_plan,
            farm=farm,
            rice_variety_repository=self.rice_variety_repository,
        )
        if latest_snapshot is not None and dict(latest_snapshot.thermal_thresholds or {}):
            threshold_rule = dict(latest_snapshot.thermal_thresholds or {})
            algorithm_code = latest_snapshot.algorithm_code
            algorithm_version = latest_snapshot.algorithm_version
        else:
            prediction = self.stage_prediction_client.predict_stage(request_payload=request_payload)
            threshold_rule = prediction.threshold_rule
            algorithm_code = prediction.algorithm_code
            algorithm_version = prediction.algorithm_version
        existing_thermal_state = self.crop_thermal_time_state_repository.get_by_plan(planting_plan_id)
        latest_as_of_date = _resolve_snapshot_as_of_date(latest_snapshot)
        calculation_as_of_date = max(
            latest_effective_date,
            (
                existing_thermal_state.last_calculated_date
                if existing_thermal_state and existing_thermal_state.last_calculated_date
                else latest_effective_date
            ),
            latest_as_of_date or latest_effective_date,
        )
        calculation_context = _build_stage_calculation_context(
            planting_plan,
            as_of_date=calculation_as_of_date,
            weather_provider=self.weather_provider,
            weather_lookahead_days=self.weather_lookahead_days,
        )
        latest_stage_timeline = latest_snapshot.stage_timeline if latest_snapshot else {}
        manual_raw_stage_dates = _extract_manual_raw_stage_dates(latest_stage_timeline) if latest_snapshot else {}
        manual_raw_stage_dates.update(normalized_stage_dates)
        preserved_stage_start_dates = _build_preserved_manual_stage_start_dates(
            existing_raw_stage_start_dates=(
                _extract_raw_stage_start_dates(latest_stage_timeline) if latest_snapshot else {}
            ),
            manual_raw_stage_dates=manual_raw_stage_dates,
        )
        refresh_result = self._refresh_from_threshold_rule(
            planting_plan=planting_plan,
            request_payload=request_payload,
            threshold_rule=_enrich_stage_threshold_rule(threshold_rule, request_payload=request_payload),
            algorithm_code=algorithm_code,
            algorithm_version=algorithm_version,
            prediction_source="manual_adjustment",
            calculation_context=calculation_context,
            source_event_id=source_event_id,
            rule_snapshot_id=latest_snapshot.id if latest_snapshot is not None else None,
            initial_stage_start_dates=preserved_stage_start_dates,
            manual_raw_stage_dates=manual_raw_stage_dates,
            stage_state_override={
                "current_stage_code": current_stage_code,
                "current_stage_name": resolved_stage_name,
                "stage_source": "manual",
                "effective_date": latest_effective_date,
                "created_by_id": "ActualStageRecorded",
            },
            recalculation_summary={
                "mode": "manual_stage_override_batch" if len(normalized_stage_dates) > 1 else "manual_stage_override",
                "source_stage_code": latest_stage_code,
                "normalized_raw_stage_code": normalized_raw_stage_code,
                "effective_date": latest_effective_date.isoformat(),
                "manual_stage_dates": {
                    stage_code: stage_date.isoformat()
                    for stage_code, stage_date in sorted(
                        normalized_stage_dates.items(),
                        key=lambda item: (item[1], get_raw_stage_order_index(item[0]) or -1),
                    )
                },
                "current_stage_basis": "manual_priority",
            },
        )
        return ActualStageRecordResult(
            snapshot=refresh_result.snapshot,
            crop_stage_state=refresh_result.crop_stage_state,
            crop_thermal_time_state=refresh_result.crop_thermal_time_state,
            previous_stage_code=refresh_result.previous_stage_code,
            stage_changed=refresh_result.stage_changed,
        )

    def _refresh_from_threshold_rule(
        self,
        *,
        planting_plan: PlantingPlan,
        request_payload: dict[str, Any],
        threshold_rule: dict[str, Any],
        algorithm_code: str,
        algorithm_version: str | None,
        prediction_source: str,
        calculation_context: StageCalculationContext,
        source_event_id: int | None,
        rule_snapshot_id: int | None = None,
        initial_accumulated_thermal_time: Decimal | None = None,
        initial_last_calculated_date: date | None = None,
        initial_data_version: str | None = None,
        initial_stage_start_dates: dict[str, date] | None = None,
        preserve_existing_stage_state: bool = False,
        manual_raw_stage_dates: dict[str, date] | None = None,
        stage_state_override: dict[str, Any] | None = None,
        recalculation_summary: dict[str, Any] | None = None,
    ) -> StageRefreshResult:
        normalized_rule = _normalize_threshold_rule(threshold_rule)
        latest_snapshot = self.stage_prediction_snapshot_repository.get_latest_by_plan(planting_plan.id)
        existing_stage_state = self.crop_stage_state_repository.get_by_plan(planting_plan.id)
        derived_state = _derive_stage_state(
            sowing_date=planting_plan.sowing_date,
            as_of_date=calculation_context.as_of_date,
            weather_data=calculation_context.weather_data,
            threshold_rule=normalized_rule,
            initial_accumulated_thermal_time=initial_accumulated_thermal_time,
            initial_last_calculated_date=initial_last_calculated_date,
            initial_data_version=initial_data_version,
            initial_stage_start_dates=initial_stage_start_dates,
            manual_raw_stage_dates=manual_raw_stage_dates,
        )
        auto_three_leaf_override_date = _resolve_transplant_based_three_leaf_override_date(
            planting_plan=planting_plan,
            stage_timeline=derived_state.stage_timeline,
            manual_raw_stage_dates=manual_raw_stage_dates,
        )
        if auto_three_leaf_override_date is not None:
            effective_manual_raw_stage_dates = dict(manual_raw_stage_dates or {})
            effective_manual_raw_stage_dates[_THREE_LEAF_ONE_HEART_STAGE_CODE] = auto_three_leaf_override_date
            derived_state = _derive_stage_state(
                sowing_date=planting_plan.sowing_date,
                as_of_date=calculation_context.as_of_date,
                weather_data=calculation_context.weather_data,
                threshold_rule=normalized_rule,
                initial_accumulated_thermal_time=initial_accumulated_thermal_time,
                initial_last_calculated_date=initial_last_calculated_date,
                initial_data_version=initial_data_version,
                initial_stage_start_dates=initial_stage_start_dates,
                manual_raw_stage_dates=effective_manual_raw_stage_dates,
            )
        snapshot = StagePredictionSnapshot(
            planting_plan_id=planting_plan.id,
            prediction_version=(latest_snapshot.prediction_version if latest_snapshot is not None else 0) + 1,
            prediction_source=prediction_source,
            algorithm_code=algorithm_code,
            algorithm_version=algorithm_version,
            generated_at=_utcnow(),
            input_payload=_build_stage_snapshot_input_payload(
                request_payload,
                calculation_context=calculation_context,
                rule_snapshot_id=rule_snapshot_id,
                recalculation_summary=recalculation_summary,
                thermal_audit_summary=derived_state.thermal_audit_summary,
            ),
            stage_timeline=derived_state.stage_timeline,
            thermal_thresholds=normalized_rule,
            source_event_id=source_event_id,
            created_by_type="system",
            created_by_id="StageManagementService",
        )
        self.stage_prediction_snapshot_repository.add(snapshot)
        self.stage_prediction_snapshot_repository.flush()

        previous_stage_code = existing_stage_state.current_stage_code if existing_stage_state is not None else None
        stage_state_code = (
            str(stage_state_override["current_stage_code"])
            if stage_state_override is not None
            else derived_state.current_node.stage_code
        )
        stage_state_name = (
            str(stage_state_override["current_stage_name"])
            if stage_state_override is not None
            else derived_state.current_node.stage_name
        )
        stage_state_source = (
            str(stage_state_override.get("stage_source") or "predicted")
            if stage_state_override is not None
            else "predicted"
        )
        stage_effective_date = (
            _parse_required_iso_date(stage_state_override["effective_date"], "stage_state_override.effective_date")
            if stage_state_override is not None
            else derived_state.current_node.start_date
        )
        stage_created_by_id = (
            str(stage_state_override.get("created_by_id") or "StageManagementService")
            if stage_state_override is not None
            else "StageManagementService"
        )
        if existing_stage_state is None:
            stage_state = CropStageState(
                planting_plan_id=planting_plan.id,
                current_stage_code=stage_state_code,
                current_stage_name=stage_state_name,
                stage_source=stage_state_source,
                effective_date=stage_effective_date,
                source_snapshot_id=snapshot.id,
                last_updated_at=_utcnow(),
                version=1,
                created_by_type="system",
                created_by_id=stage_created_by_id,
            )
            self.crop_stage_state_repository.add(stage_state)
        elif preserve_existing_stage_state:
            stage_state = existing_stage_state
        else:
            stage_state = existing_stage_state
            stage_state.current_stage_code = stage_state_code
            stage_state.current_stage_name = stage_state_name
            stage_state.stage_source = stage_state_source
            stage_state.effective_date = stage_effective_date
            stage_state.source_snapshot_id = snapshot.id
            stage_state.last_updated_at = _utcnow()
            stage_state.version = int(stage_state.version or 0) + 1
            stage_state.updated_at = _utcnow()

        existing_thermal_state = self.crop_thermal_time_state_repository.get_by_plan(planting_plan.id)
        base_temperature_raw = normalized_rule.get("base_temperature")
        base_temperature = Decimal(str(base_temperature_raw)) if base_temperature_raw is not None else None
        if existing_thermal_state is None:
            thermal_state = CropThermalTimeState(
                planting_plan_id=planting_plan.id,
                accumulated_thermal_time=derived_state.accumulated_thermal_time,
                thermal_time_unit=str(normalized_rule.get("thermal_time_unit") or DEFAULT_THERMAL_TIME_UNIT),
                base_temperature=base_temperature,
                start_date=planting_plan.sowing_date,
                last_calculated_date=derived_state.last_calculated_date,
                threshold_snapshot_id=snapshot.id,
                data_version=derived_state.data_version,
                created_by_type="system",
                created_by_id="StageManagementService",
            )
            self.crop_thermal_time_state_repository.add(thermal_state)
        elif preserve_existing_stage_state:
            thermal_state = existing_thermal_state
        else:
            thermal_state = existing_thermal_state
            thermal_state.accumulated_thermal_time = derived_state.accumulated_thermal_time
            thermal_state.thermal_time_unit = str(normalized_rule.get("thermal_time_unit") or DEFAULT_THERMAL_TIME_UNIT)
            thermal_state.base_temperature = base_temperature
            thermal_state.start_date = planting_plan.sowing_date
            thermal_state.last_calculated_date = derived_state.last_calculated_date
            thermal_state.threshold_snapshot_id = snapshot.id
            thermal_state.data_version = derived_state.data_version
            thermal_state.updated_at = _utcnow()

        return StageRefreshResult(
            snapshot=snapshot,
            crop_stage_state=stage_state,
            crop_thermal_time_state=thermal_state,
            previous_stage_code=previous_stage_code,
            stage_changed=(
                not preserve_existing_stage_state
                and previous_stage_code is not None
                and previous_stage_code != stage_state_code
            ),
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
        return farm


def resolve_current_stage_node(stage_timeline: dict[str, Any], as_of_date: date) -> StageTimelineNode:
    nodes = parse_stage_timeline_nodes(stage_timeline)
    effective_nodes = [node for node in nodes if node.start_date <= as_of_date]
    if effective_nodes:
        return effective_nodes[-1]
    return nodes[0]


def parse_stage_timeline_nodes(stage_timeline: dict[str, Any]) -> list[StageTimelineNode]:
    raw_stages = stage_timeline.get("stages")
    if not isinstance(raw_stages, list) or not raw_stages:
        raise ValueError("stage_timeline.stages must be a non-empty array.")
    nodes: list[StageTimelineNode] = []
    for item in raw_stages:
        if not isinstance(item, dict):
            raise ValueError("stage_timeline.stages items must be objects.")
        stage_identifier = str(item.get("stage_code") or item.get("stageCode") or "").strip()
        if not stage_identifier:
            raise ValueError("stage_timeline.stages item is missing stage_code.")
        raw_stage_code = _extract_raw_stage_code(item, stage_identifier)
        stage_code = _normalize_business_stage_code(stage_identifier, raw_stage_code)
        stage_name = str(item.get("stage_name") or item.get("stageName") or _STAGE_NAME_BY_CODE.get(stage_code) or stage_code).strip()
        raw_start_date = item.get("start_date") or item.get("startDate") or item.get("key_date") or item.get("keyDate")
        if raw_start_date is None:
            raise ValueError(f"stage_timeline stage {stage_code} is missing start_date.")
        raw_end_date = item.get("end_date") or item.get("endDate")
        raw_key_date = item.get("key_date") or item.get("keyDate")
        metadata = {
            key: value
            for key, value in item.items()
            if key
            not in {
                "stage_code",
                "stageCode",
                "stage_name",
                "stageName",
                "start_date",
                "startDate",
                "end_date",
                "endDate",
                "key_date",
                "keyDate",
                "raw_stage_code",
                "rawStageCode",
            }
        }
        nodes.append(
            StageTimelineNode(
                stage_code=stage_code,
                stage_name=stage_name,
                start_date=_parse_required_iso_date(raw_start_date, f"{stage_code}.start_date"),
                end_date=_parse_optional_iso_date(raw_end_date),
                key_date=_parse_optional_iso_date(raw_key_date),
                raw_stage_code=raw_stage_code,
                metadata=metadata,
            ),
        )
    nodes.sort(key=lambda item: (item.start_date, _STAGE_INDEX_BY_CODE.get(item.stage_code, 999)))
    return nodes


def extract_pest_disease_growth_stage(stage_timeline: dict[str, Any]) -> dict[str, str]:
    nodes = parse_stage_timeline_nodes(stage_timeline)
    code_to_date = {node.stage_code: node.start_date.isoformat() for node in nodes}
    required_mapping = {
        "tillering_date": "tillering",
        "pokou_date": "pokou",
        "heading_date": "heading",
        "maturity_date": "maturity",
    }
    missing = [stage_code for stage_code in required_mapping.values() if stage_code not in code_to_date]
    if missing:
        raise ValueError(f"stage_timeline does not contain required pest-disease stage codes: {missing}.")
    return {field_name: code_to_date[stage_code] for field_name, stage_code in required_mapping.items()}


def _build_stage_rule_request_payload(
    planting_plan: PlantingPlan,
    *,
    farm: Farm,
    rice_variety_repository: RiceVarietyRepository | None,
) -> dict[str, Any]:
    metadata_payload = dict(planting_plan.metadata_payload or {})
    rice_variety = (
        rice_variety_repository.get(planting_plan.variety_id)
        if rice_variety_repository is not None
        else None
    )
    appr_area = (
        metadata_payload.get("approveRegion")
        or metadata_payload.get("approve_region")
        or (rice_variety.approve_region if rice_variety is not None else None)
    )
    control_spec = (
        metadata_payload.get("controlSpec")
        or metadata_payload.get("control_spec")
        or (rice_variety.control_variety if rice_variety is not None else None)
    )
    if not appr_area:
        raise ValueError(
            "Stage threshold request requires approveRegion. "
            "Provide it via PlantingPlan.metadata or RiceVariety.approve_region.",
        )
    matur_type = _resolve_stage_algorithm_matur_type(
        metadata_payload.get("maturType"),
        metadata_payload.get("maturity_code"),
        rice_variety.maturity_code if rice_variety is not None else None,
    )
    culti_type = _resolve_stage_algorithm_culti_type(None, planting_plan.culti_type_code)
    appr_culti_type = _resolve_stage_algorithm_culti_type(
        metadata_payload.get("apprCultiType"),
        metadata_payload.get("approve_culti_type"),
        rice_variety.culti_type_code if rice_variety is not None else None,
    )
    subs_type = _resolve_stage_algorithm_subs_type(
        metadata_payload.get("subsType"),
        metadata_payload.get("sub_type_code"),
        rice_variety.sub_type_code if rice_variety is not None else None,
    )
    farm_area_name = (
        metadata_payload.get("farm_area_name")
        or metadata_payload.get("farmAreaName")
        or _normalize_stage_farm_area_name(farm.province)
        or ""
    )
    return {
        "apprArea": str(appr_area),
        "controlSpec": str(control_spec or ""),
        "maturType": int(matur_type),
        "cultiType": int(culti_type),
        "apprCultiType": int(appr_culti_type),
        "subsType": int(subs_type),
        "variety_name": str(planting_plan.variety_name or ""),
        "farm_area_name": str(farm_area_name),
    }


def _coerce_optional_stage_algorithm_code(raw_value: Any) -> int | None:
    try:
        if raw_value is None or raw_value == "":
            return None
        return int(raw_value)
    except (TypeError, ValueError):
        return None


def _resolve_stage_algorithm_matur_type(*candidates: Any) -> int:
    explicit_value = _coerce_optional_stage_algorithm_code(candidates[0]) if candidates else None
    if explicit_value is not None:
        return explicit_value
    for raw_value in candidates[1:]:
        coerced = _coerce_optional_stage_algorithm_code(raw_value)
        if coerced is None:
            continue
        mapped_value = _LOCAL_TO_STAGE_ALGORITHM_MATUR_TYPE.get(coerced)
        if mapped_value is not None:
            logger.info("Mapped local maturity_code to stage algorithm code local=%s mapped=%s", coerced, mapped_value)
            return mapped_value
        if 0 <= coerced <= 8:
            return coerced
        logger.warning("Unsupported local maturity_code for stage algorithm; using default 5 local=%s", coerced)
        return 5
    return 5


def _resolve_stage_algorithm_culti_type(*candidates: Any) -> int:
    explicit_value = _coerce_optional_stage_algorithm_code(candidates[0]) if candidates else None
    if explicit_value is not None:
        return explicit_value
    for raw_value in candidates[1:]:
        coerced = _coerce_optional_stage_algorithm_code(raw_value)
        if coerced is None:
            continue
        mapped_value = _LOCAL_TO_STAGE_ALGORITHM_CULTI_TYPE.get(coerced)
        if mapped_value is not None:
            if mapped_value != coerced:
                logger.info("Mapped local culti_type_code to stage algorithm code local=%s mapped=%s", coerced, mapped_value)
            return mapped_value
        return coerced
    return 0


def _resolve_stage_algorithm_subs_type(*candidates: Any) -> int:
    explicit_value = _coerce_optional_stage_algorithm_code(candidates[0]) if candidates else None
    if explicit_value is not None:
        return explicit_value
    for raw_value in candidates[1:]:
        coerced = _coerce_optional_stage_algorithm_code(raw_value)
        if coerced is None:
            continue
        mapped_value = _LOCAL_TO_STAGE_ALGORITHM_SUBS_TYPE.get(coerced)
        if mapped_value is not None:
            if mapped_value != coerced:
                logger.info("Mapped local sub_type_code to stage algorithm code local=%s mapped=%s", coerced, mapped_value)
            return mapped_value
        return coerced
    return 0


def _resolve_stage_subs_type_code(raw_value: Any) -> int:
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return 0


def _resolve_stage_thermal_profile(subs_type_code: int) -> dict[str, int]:
    base_temperature = 10 if subs_type_code == 1 else 12
    return {
        "subs_type_code": subs_type_code,
        "base_temperature": base_temperature,
        "upper_temperature_cap": 40,
        "lower_temperature_floor": base_temperature,
    }


def _enrich_stage_threshold_rule(
    threshold_rule: dict[str, Any],
    *,
    request_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    enriched = dict(threshold_rule or {})
    if request_payload is None:
        subs_type_code = _resolve_stage_subs_type_code(enriched.get("subs_type_code"))
    else:
        subs_type_code = _resolve_stage_subs_type_code(request_payload.get("subsType"))
    thermal_profile = _resolve_stage_thermal_profile(subs_type_code)
    enriched["subs_type_code"] = thermal_profile["subs_type_code"]
    enriched["base_temperature"] = thermal_profile["base_temperature"]
    enriched["upper_temperature_cap"] = thermal_profile["upper_temperature_cap"]
    enriched["lower_temperature_floor"] = thermal_profile["lower_temperature_floor"]
    return enriched


def _build_stage_calculation_context(
    planting_plan: PlantingPlan,
    *,
    as_of_date: date,
    weather_provider: StageWeatherProvider,
    weather_lookahead_days: int,
    start_date: date | None = None,
) -> StageCalculationContext:
    calculation_start_date = start_date or planting_plan.sowing_date
    weather_end_date = _resolve_stage_weather_end_date(
        planting_plan,
        as_of_date=as_of_date,
        weather_lookahead_days=weather_lookahead_days,
    )
    weather_data = _load_stage_weather_window(
        planting_plan,
        start_date=calculation_start_date,
        end_date=weather_end_date,
        as_of_date=as_of_date,
        weather_provider=weather_provider,
    )
    return StageCalculationContext(as_of_date=as_of_date, start_date=calculation_start_date, weather_data=weather_data)


def _build_stage_snapshot_input_payload(
    request_payload: dict[str, Any],
    *,
    calculation_context: StageCalculationContext,
    rule_snapshot_id: int | None = None,
    recalculation_summary: dict[str, Any] | None = None,
    thermal_audit_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(request_payload)
    payload["calculation_context"] = {
        "as_of_date": calculation_context.as_of_date.isoformat(),
        "start_date": calculation_context.start_date.isoformat(),
        "weather_data": [dict(item) for item in calculation_context.weather_data],
    }
    if rule_snapshot_id is not None:
        payload["rule_snapshot_id"] = rule_snapshot_id
    if recalculation_summary is not None:
        payload["recalculation_summary"] = dict(recalculation_summary)
    if thermal_audit_summary is not None:
        payload["thermal_audit_summary"] = dict(thermal_audit_summary)
    return payload


def _build_weather_recalculation_seed(
    *,
    planting_plan: PlantingPlan,
    latest_snapshot: StagePredictionSnapshot,
    threshold_rule: dict[str, Any],
    weather_provider: StageWeatherProvider,
    as_of_date: date,
    recalculation_start_date: date | None,
    recalculation_mode: str,
    existing_thermal_state: CropThermalTimeState | None,
) -> dict[str, Any]:
    normalized_threshold_rule = _normalize_threshold_rule(threshold_rule)
    if recalculation_start_date is None:
        return {
            "accumulated_thermal_time": None,
            "last_calculated_date": None,
            "data_version": None,
            "stage_start_dates": None,
        }
    if recalculation_mode == "historical_observed_correction":
        prefix_end_date = recalculation_start_date - timedelta(days=1)
        if prefix_end_date < planting_plan.sowing_date:
            return {
                "accumulated_thermal_time": None,
                "last_calculated_date": None,
                "data_version": None,
                "stage_start_dates": None,
            }
        prefix_weather_data = _load_stage_weather_window(
            planting_plan,
            start_date=planting_plan.sowing_date,
            end_date=prefix_end_date,
            as_of_date=prefix_end_date,
            weather_provider=weather_provider,
        )
        prefix_state = _derive_stage_state(
            sowing_date=planting_plan.sowing_date,
            as_of_date=prefix_end_date,
            weather_data=prefix_weather_data,
            threshold_rule=normalized_threshold_rule,
        )
        return {
            "accumulated_thermal_time": prefix_state.accumulated_thermal_time,
            "last_calculated_date": prefix_state.last_calculated_date,
            "data_version": prefix_state.data_version,
            "stage_start_dates": _extract_stage_start_dates(prefix_state.stage_timeline),
        }
    if existing_thermal_state is None:
        return {
            "accumulated_thermal_time": None,
            "last_calculated_date": None,
            "data_version": None,
            "stage_start_dates": None,
        }
    return {
        "accumulated_thermal_time": existing_thermal_state.accumulated_thermal_time,
        "last_calculated_date": existing_thermal_state.last_calculated_date,
        "data_version": existing_thermal_state.data_version,
        "stage_start_dates": _extract_stage_start_dates(
            latest_snapshot.stage_timeline,
            before_date=recalculation_start_date,
        ),
    }


def _load_stage_weather_window(
    planting_plan: PlantingPlan,
    *,
    start_date: date,
    end_date: date,
    as_of_date: date,
    weather_provider: StageWeatherProvider,
) -> list[dict[str, Any]]:
    return _normalize_stage_weather_data(
        weather_provider.get_daily_weather(
            planting_plan,
            start_date,
            end_date,
            as_of_date=as_of_date,
        ),
        as_of_date=as_of_date,
    )


def _resolve_weather_recalculation_start_date(
    *,
    planting_plan: PlantingPlan,
    latest_snapshot: StagePredictionSnapshot,
    existing_thermal_state: CropThermalTimeState | None,
    source_event_payload: dict[str, Any],
    as_of_date: date,
) -> tuple[date | None, str]:
    manual_raw_stage_dates = _extract_manual_raw_stage_dates(latest_snapshot.stage_timeline)
    if manual_raw_stage_dates:
        return None, "manual_anchor_full_replay"
    if existing_thermal_state is None or existing_thermal_state.last_calculated_date is None:
        return None, "full_replay"
    if existing_thermal_state.start_date != planting_plan.sowing_date:
        return None, "full_replay"
    if latest_snapshot.id is None or existing_thermal_state.threshold_snapshot_id != latest_snapshot.id:
        return None, "full_replay"
    source_type = _resolve_weather_update_source_type(source_event_payload)
    if source_type == "forecast":
        return max(as_of_date, existing_thermal_state.last_calculated_date + timedelta(days=1)), "forecast_projection"
    if source_type != "observed":
        return None, "full_replay"
    raw_weather_date = source_event_payload.get("weatherDate") or source_event_payload.get("weather_date")
    if raw_weather_date is None:
        return None, "full_replay"
    weather_date = _parse_stage_weather_date(raw_weather_date)
    if weather_date > as_of_date:
        return None, "full_replay"
    if weather_date > existing_thermal_state.last_calculated_date:
        return existing_thermal_state.last_calculated_date + timedelta(days=1), "incremental_observed"
    return weather_date, "historical_observed_correction"


def _resolve_weather_update_source_type(source_event_payload: dict[str, Any]) -> str:
    source_type = str(source_event_payload.get("sourceType") or source_event_payload.get("source_type") or "").strip()
    weather_payload = source_event_payload.get("weather")
    if not source_type and isinstance(weather_payload, dict):
        source_type = str(weather_payload.get("source_type") or "").strip()
    return source_type or "observed"


def _extract_stage_start_dates(stage_timeline: dict[str, Any], *, before_date: date | None = None) -> dict[str, date]:
    return _extract_raw_stage_start_dates(stage_timeline, before_date=before_date)


def _build_stage_prediction_location_payload(farm: Farm) -> dict[str, Any]:
    adcode = farm.adcode
    province = farm.province
    city = farm.city
    district_county = farm.district_county
    missing_fields = [
        field_name
        for field_name, value in (
            ("adcode", adcode),
            ("province", province),
            ("city", city),
            ("district_county", district_county),
        )
        if not value
    ]
    if missing_fields:
        raise ValueError(
            "Stage prediction requires structured Farm location fields: "
            f"{missing_fields}. Expected values on cf_farm.",
        )

    payload = {
        "adcode": str(adcode),
        "province": str(province),
        "city": str(city),
        "district_county": str(district_county),
    }
    centroid_lat = farm.centroid_lat
    centroid_lon = farm.centroid_lon
    if centroid_lat is not None:
        payload["centroid_lat"] = _normalize_optional_float(centroid_lat)
    if centroid_lon is not None:
        payload["centroid_lon"] = _normalize_optional_float(centroid_lon)
    return payload


def _normalize_stage_farm_area_name(province: str | None) -> str:
    raw_value = str(province or "").strip()
    if raw_value.endswith("省") or raw_value.endswith("市"):
        return raw_value[:-1]
    return raw_value


def _resolve_stage_weather_end_date(
    planting_plan: PlantingPlan,
    *,
    as_of_date: date,
    weather_lookahead_days: int,
) -> date:
    candidates = [
        as_of_date,
        planting_plan.sowing_date + timedelta(days=weather_lookahead_days),
    ]
    for field_name in ("harvest_date", "expected_harvest_date", "ratoon_first_season_harvest_date"):
        field_value = getattr(planting_plan, field_name, None)
        if isinstance(field_value, date):
            candidates.append(field_value)
    return max(candidates)


def _normalize_stage_weather_data(
    weather_data: list[dict[str, Any]],
    *,
    as_of_date: date,
) -> list[dict[str, Any]]:
    if not weather_data:
        raise ValueError("Stage prediction requires non-empty weather_data prepared by the backend.")

    normalized_rows: list[dict[str, Any]] = []
    for item in weather_data:
        if not isinstance(item, dict):
            raise ValueError("Stage weather rows must be objects.")
        row_date = _parse_stage_weather_date(item.get("date") or item.get("DATE"))
        avg_temp = item.get("avg_temp")
        if avg_temp is None:
            avg_temp = item.get("avgTemperature")
        if avg_temp is None:
            avg_temp = item.get("TEMP")
        if avg_temp is None:
            avg_temp = item.get("temperature")
        if avg_temp is None:
            raise ValueError("Stage weather rows must provide avg_temp or TEMP.")

        source_type = item.get("source_type")
        normalized_row = {
            "date": row_date.isoformat(),
            "avg_temp": _normalize_optional_float(avg_temp),
            "source_type": str(source_type) if source_type is not None else ("observed" if row_date <= as_of_date else "forecast"),
        }
        min_temp = item.get("min_temp")
        if min_temp is None:
            min_temp = item.get("minTemperature")
        max_temp = item.get("max_temp")
        if max_temp is None:
            max_temp = item.get("maxTemperature")
        if min_temp is not None:
            normalized_row["min_temp"] = _normalize_optional_float(min_temp)
        if max_temp is not None:
            normalized_row["max_temp"] = _normalize_optional_float(max_temp)
        if item.get("data_version") is not None:
            normalized_row["data_version"] = str(item["data_version"])
        normalized_rows.append(normalized_row)

    normalized_rows.sort(key=lambda row: row["date"])
    return normalized_rows


def _derive_stage_state(
    *,
    sowing_date: date,
    as_of_date: date,
    weather_data: list[dict[str, Any]],
    threshold_rule: dict[str, Any],
    initial_accumulated_thermal_time: Decimal | None = None,
    initial_last_calculated_date: date | None = None,
    initial_data_version: str | None = None,
    initial_stage_start_dates: dict[str, date] | None = None,
    manual_raw_stage_dates: dict[str, date] | None = None,
) -> StageDerivedState:
    raw_stage_thresholds = _parse_raw_stage_thresholds(threshold_rule.get("stage_thresholds"))
    calculation_method = str(threshold_rule.get("calculation_method") or DEFAULT_CALCULATION_METHOD)
    rounding_rule = str(threshold_rule.get("rounding_rule") or DEFAULT_ROUNDING_RULE)
    effective_date_rule = str(threshold_rule.get("effective_date_rule") or DEFAULT_EFFECTIVE_DATE_RULE)
    accumulated_all = initial_accumulated_thermal_time or _DECIMAL_ZERO
    accumulated_as_of = initial_accumulated_thermal_time or _DECIMAL_ZERO
    raw_stage_start_dates: dict[str, date] = dict(initial_stage_start_dates or {})
    normalized_manual_raw_stage_dates = {
        raw_stage_code: stage_date
        for raw_stage_code, stage_date in (manual_raw_stage_dates or {}).items()
        if raw_stage_code in _RAW_STAGE_METADATA_BY_CODE
    }
    last_calculated_date = initial_last_calculated_date or sowing_date
    data_version: str | None = initial_data_version
    audit_rows: list[dict[str, Any]] = []
    accumulated_by_date: dict[date, Decimal] = {}

    for row in weather_data:
        row_date = _parse_stage_weather_date(row["date"])
        avg_temp = Decimal(str(row["avg_temp"]))
        source_type = str(row.get("source_type") or "unknown")
        daily_thermal_time = _calculate_daily_thermal_time(
            avg_temp=avg_temp,
            threshold_rule=threshold_rule,
            calculation_method=calculation_method,
        )
        accumulated_all = _apply_accumulation_rounding(
            accumulated_all,
            daily_thermal_time,
            rounding_rule=rounding_rule,
        )
        if source_type == "observed" and row_date <= as_of_date:
            accumulated_as_of = _apply_accumulation_rounding(
                accumulated_as_of,
                daily_thermal_time,
                rounding_rule=rounding_rule,
            )
            last_calculated_date = row_date
            if row.get("data_version") is not None:
                data_version = str(row["data_version"])
        accumulated_by_date[row_date] = accumulated_all
        audit_rows.append(
            {
                "date": row_date.isoformat(),
                "source_type": source_type,
                "avg_temp": _normalize_decimal_for_json(avg_temp),
                "daily_thermal_time": _normalize_decimal_for_json(daily_thermal_time),
                "accumulated_thermal_time": _normalize_decimal_for_json(accumulated_all),
                "data_version": str(row["data_version"]) if row.get("data_version") is not None else None,
            },
        )
    raw_stage_start_dates.update(
        _derive_raw_stage_start_dates(
            raw_stage_thresholds=raw_stage_thresholds,
            accumulated_by_date=accumulated_by_date,
            effective_date_rule=effective_date_rule,
            initial_raw_stage_start_dates=raw_stage_start_dates,
            manual_raw_stage_dates=normalized_manual_raw_stage_dates,
        ),
    )
    business_stage_start_dates = _derive_business_stage_start_dates(raw_stage_start_dates)
    stage_timeline = _build_stage_timeline(
        sowing_date=sowing_date,
        stage_start_dates=business_stage_start_dates,
        raw_stage_start_dates=raw_stage_start_dates,
        manual_raw_stage_dates=normalized_manual_raw_stage_dates,
    )
    current_node = resolve_current_stage_node(stage_timeline, as_of_date)
    return StageDerivedState(
        stage_timeline=stage_timeline,
        current_node=current_node,
        accumulated_thermal_time=accumulated_as_of,
        last_calculated_date=last_calculated_date,
        data_version=data_version,
        thermal_audit_summary=_build_thermal_audit_summary(
            audit_rows=audit_rows,
            stage_start_dates=raw_stage_start_dates,
            recalculation_start_date=_parse_stage_weather_date(weather_data[0]["date"]),
            as_of_date=as_of_date,
        ),
    )


def _build_thermal_audit_summary(
    *,
    audit_rows: list[dict[str, Any]],
    stage_start_dates: dict[str, date],
    recalculation_start_date: date,
    as_of_date: date,
) -> dict[str, Any]:
    key_dates = {recalculation_start_date.isoformat(), as_of_date.isoformat()}
    key_dates.update(stage_date.isoformat() for stage_date in stage_start_dates.values())
    key_rows = [row for row in audit_rows if str(row.get("date")) in key_dates]
    return {
        "current_stage_basis": "observed_only",
        "recalculation_start_date": recalculation_start_date.isoformat(),
        "as_of_date": as_of_date.isoformat(),
        "projected_row_count": len(audit_rows),
        "key_rows": key_rows,
    }


def _normalize_decimal_for_json(raw_value: Decimal) -> str:
    return format(raw_value.normalize(), "f")


def _parse_raw_stage_thresholds(raw_thresholds: Any) -> dict[str, Decimal]:
    if not isinstance(raw_thresholds, dict) or not raw_thresholds:
        raise ValueError("threshold_rule.stage_thresholds must be a non-empty object.")
    thresholds: dict[str, Decimal] = {}
    for raw_stage_code in _RAW_STAGE_METADATA_BY_CODE:
        for threshold_key in _iter_threshold_keys(raw_stage_code):
            raw_value = raw_thresholds.get(threshold_key)
            if raw_value is None:
                continue
            thresholds[raw_stage_code] = Decimal(str(raw_value))
            break
    return thresholds


def _iter_threshold_keys(stage_code: str) -> tuple[str, ...]:
    keys = [stage_code]
    business_stage_code = _BUSINESS_STAGE_BY_RAW_STAGE_CODE.get(stage_code)
    if business_stage_code is not None:
        keys.append(business_stage_code)
        keys.extend(_RAW_STAGE_CODE_ALIASES_BY_BUSINESS_STAGE.get(business_stage_code, ()))
    else:
        raw_stage_code = _RAW_STAGE_CODE_BY_BUSINESS_STAGE.get(stage_code)
        if raw_stage_code is not None:
            keys.append(raw_stage_code)
        keys.extend(_RAW_STAGE_CODE_ALIASES_BY_BUSINESS_STAGE.get(stage_code, ()))
    return tuple(keys)


def _normalize_threshold_rule(threshold_rule: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(threshold_rule or {})
    if not normalized:
        raise ValueError("Stage threshold rule must not be empty.")
    if not isinstance(normalized.get("stage_thresholds"), dict) or not normalized["stage_thresholds"]:
        raise ValueError("Stage threshold rule must provide stage_thresholds.")
    thermal_profile = _resolve_stage_thermal_profile(
        _resolve_stage_subs_type_code(normalized.get("subs_type_code")),
    )
    normalized.setdefault("thermal_time_unit", DEFAULT_THERMAL_TIME_UNIT)
    normalized.setdefault("subs_type_code", thermal_profile["subs_type_code"])
    normalized.setdefault("base_temperature", thermal_profile["base_temperature"])
    normalized.setdefault("upper_temperature_cap", thermal_profile["upper_temperature_cap"])
    normalized.setdefault("lower_temperature_floor", thermal_profile["lower_temperature_floor"])
    normalized.setdefault("calculation_method", DEFAULT_CALCULATION_METHOD)
    normalized.setdefault("rounding_rule", DEFAULT_ROUNDING_RULE)
    normalized.setdefault("effective_date_rule", DEFAULT_EFFECTIVE_DATE_RULE)
    return normalized


def _calculate_daily_thermal_time(
    *,
    avg_temp: Decimal,
    threshold_rule: dict[str, Any],
    calculation_method: str,
) -> Decimal:
    base_temperature = Decimal(str(threshold_rule.get("base_temperature") or 0))
    lower_floor_raw = threshold_rule.get("lower_temperature_floor")
    if lower_floor_raw is not None and avg_temp <= Decimal(str(lower_floor_raw)):
        return _DECIMAL_ZERO

    effective_avg_temp = avg_temp
    upper_cap_raw = threshold_rule.get("upper_temperature_cap")
    if calculation_method == "avg_temp_minus_base_capped" and upper_cap_raw is not None:
        effective_avg_temp = min(avg_temp, Decimal(str(upper_cap_raw)))
    if calculation_method not in {"avg_temp_minus_base_capped", "avg_temp_minus_base_uncapped"}:
        raise ValueError(f"Unsupported stage thermal calculation_method: {calculation_method}.")
    return max(effective_avg_temp - base_temperature, _DECIMAL_ZERO)


def _apply_accumulation_rounding(
    accumulated: Decimal,
    daily_thermal_time: Decimal,
    *,
    rounding_rule: str,
) -> Decimal:
    if rounding_rule == "keep_1_decimal_daily_keep_1_decimal_accumulated":
        daily = _quantize_decimal(daily_thermal_time, "0.1")
        return _quantize_decimal(accumulated + daily, "0.1")
    if rounding_rule == "keep_2_decimal_daily_keep_2_decimal_accumulated":
        daily = _quantize_decimal(daily_thermal_time, "0.01")
        return _quantize_decimal(accumulated + daily, "0.01")
    if rounding_rule == "keep_raw_daily_keep_1_decimal_accumulated":
        return _quantize_decimal(accumulated + daily_thermal_time, "0.1")
    raise ValueError(f"Unsupported stage thermal rounding_rule: {rounding_rule}.")


def _has_reached_stage_threshold(
    *,
    accumulated_thermal_time: Decimal,
    threshold: Decimal,
    effective_date_rule: str,
) -> bool:
    if effective_date_rule == "threshold_strictly_exceeded_same_day":
        return accumulated_thermal_time > threshold
    if effective_date_rule in {"threshold_reached_same_day", "threshold_reached_next_day"}:
        return accumulated_thermal_time >= threshold
    raise ValueError(f"Unsupported stage effective_date_rule: {effective_date_rule}.")


def _resolve_stage_effective_date(
    row_date: date,
    *,
    effective_date_rule: str,
) -> date:
    if effective_date_rule in {"threshold_reached_same_day", "threshold_strictly_exceeded_same_day"}:
        return row_date
    if effective_date_rule == "threshold_reached_next_day":
        return row_date + timedelta(days=1)
    raise ValueError(f"Unsupported stage effective_date_rule: {effective_date_rule}.")


def _build_stage_timeline(
    *,
    sowing_date: date,
    stage_start_dates: dict[str, date],
    raw_stage_start_dates: dict[str, date] | None = None,
    manual_raw_stage_dates: dict[str, date] | None = None,
) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = [
        {
            "stage_code": "seedling",
            "stage_name": _STAGE_NAME_BY_CODE["seedling"],
            "start_date": sowing_date.isoformat(),
            "key_date": sowing_date.isoformat(),
            "season_scope": "main",
            "source": "predicted",
        },
    ]
    normalized_manual_raw_stage_dates = {
        raw_stage_code: stage_date
        for raw_stage_code, stage_date in (manual_raw_stage_dates or {}).items()
        if raw_stage_code in _RAW_STAGE_METADATA_BY_CODE
    }
    for stage_code in _THRESHOLDED_STAGE_CODES:
        start_date = stage_start_dates.get(stage_code)
        if start_date is None:
            continue
        node = {
            "stage_code": stage_code,
            "stage_name": _STAGE_NAME_BY_CODE[stage_code],
            "start_date": start_date.isoformat(),
            "key_date": start_date.isoformat(),
            "season_scope": "main",
            "source": (
                "manual"
                if _RAW_STAGE_CODE_BY_BUSINESS_STAGE.get(stage_code) in normalized_manual_raw_stage_dates
                else "predicted"
            ),
        }
        raw_stage_code = _RAW_STAGE_CODE_BY_BUSINESS_STAGE.get(stage_code)
        if raw_stage_code is not None:
            node["raw_stage_code"] = raw_stage_code
        nodes.append(node)
    nodes.sort(
        key=lambda item: (
            date.fromisoformat(str(item["start_date"])),
            _STAGE_INDEX_BY_CODE.get(str(item["stage_code"]), 999),
        ),
    )
    for index, node in enumerate(nodes):
        if index + 1 < len(nodes):
            next_start = date.fromisoformat(str(nodes[index + 1]["start_date"]))
            end_date = max(date.fromisoformat(str(node["start_date"])), next_start - timedelta(days=1))
        else:
            end_date = date.fromisoformat(str(node["start_date"]))
        node["end_date"] = end_date.isoformat()
    raw_stage_points: list[dict[str, Any]] = []
    for raw_stage_code, metadata in _RAW_STAGE_METADATA_BY_CODE.items():
        start_date = (raw_stage_start_dates or {}).get(raw_stage_code)
        if start_date is None:
            continue
        point = {
            "stage_code": raw_stage_code,
            "stage_name": _RAW_STAGE_NAME_BY_CODE[raw_stage_code],
            "season_scope": str(metadata["season_scope"]),
            "start_date": start_date.isoformat(),
            "key_date": start_date.isoformat(),
            "source": "manual" if raw_stage_code in normalized_manual_raw_stage_dates else "predicted",
        }
        business_stage_code = metadata.get("business_stage_code")
        if business_stage_code is not None:
            point["business_stage_code"] = str(business_stage_code)
        raw_stage_points.append(point)
    raw_stage_points.sort(
        key=lambda item: (
            date.fromisoformat(str(item["start_date"])),
            _RAW_STAGE_ORDER_INDEX.get(str(item["stage_code"]), 999),
        ),
    )
    return {"stages": nodes, "raw_stage_points": raw_stage_points}


def _quantize_decimal(raw_value: Decimal, quantizer: str) -> Decimal:
    return raw_value.quantize(Decimal(quantizer), rounding=ROUND_HALF_UP)


def _parse_stage_weather_date(raw_value: Any) -> date:
    if isinstance(raw_value, date):
        return raw_value
    if not isinstance(raw_value, str):
        raise ValueError(f"Unsupported stage weather date value: {raw_value!r}.")
    if len(raw_value) == 8 and raw_value.isdigit():
        return datetime.strptime(raw_value, "%Y%m%d").date()
    return date.fromisoformat(raw_value)


def _parse_required_iso_date(raw_value: Any, field_name: str) -> date:
    parsed = _parse_optional_iso_date(raw_value)
    if parsed is None:
        raise ValueError(f"{field_name} must be a valid ISO date.")
    return parsed


def _parse_optional_iso_date(raw_value: Any) -> date | None:
    if raw_value is None:
        return None
    if isinstance(raw_value, date):
        return raw_value
    if not isinstance(raw_value, str):
        raise ValueError(f"Unsupported date value: {raw_value!r}.")
    return date.fromisoformat(raw_value)


def _extract_raw_stage_code(item: dict[str, Any], stage_identifier: str) -> str | None:
    explicit_raw_stage_code = item.get("raw_stage_code") or item.get("rawStageCode")
    if explicit_raw_stage_code is not None:
        return _normalize_raw_stage_code(str(explicit_raw_stage_code).strip())
    normalized_raw_stage_code = _normalize_raw_stage_code(stage_identifier)
    if normalized_raw_stage_code is not None:
        return normalized_raw_stage_code
    return _RAW_STAGE_CODE_BY_BUSINESS_STAGE.get(stage_identifier)


def _normalize_business_stage_code(stage_identifier: str, raw_stage_code: str | None) -> str:
    if stage_identifier in _STAGE_NAME_BY_CODE:
        return stage_identifier
    if raw_stage_code is not None and raw_stage_code in _BUSINESS_STAGE_BY_RAW_STAGE_CODE:
        return _BUSINESS_STAGE_BY_RAW_STAGE_CODE[raw_stage_code]
    return stage_identifier


def is_raw_stage_code(stage_identifier: str) -> bool:
    return stage_identifier in _RAW_STAGE_METADATA_BY_CODE


def get_raw_stage_season_scope(stage_identifier: str) -> str | None:
    metadata = _RAW_STAGE_METADATA_BY_CODE.get(stage_identifier)
    if metadata is None:
        return None
    season_scope = metadata.get("season_scope")
    return str(season_scope) if season_scope is not None else None


def get_raw_stage_order_index(stage_identifier: str) -> int | None:
    return _RAW_STAGE_ORDER_INDEX.get(stage_identifier)


def validate_manual_raw_stage_dates(stage_dates: dict[str, date]) -> None:
    previous_by_season: dict[str, tuple[str, date]] = {}
    for raw_stage_code in _RAW_STAGE_METADATA_BY_CODE:
        effective_date = stage_dates.get(raw_stage_code)
        if effective_date is None:
            continue
        season_scope = get_raw_stage_season_scope(raw_stage_code)
        if season_scope is None:
            continue
        previous = previous_by_season.get(season_scope)
        if previous is not None and effective_date < previous[1]:
            raise ValueError(
                "Actual stage dates conflict with raw stage order: "
                f"{raw_stage_code} ({effective_date.isoformat()}) is earlier than "
                f"{previous[0]} ({previous[1].isoformat()}).",
            )
        previous_by_season[season_scope] = (raw_stage_code, effective_date)


def _normalize_raw_stage_code(stage_identifier: str) -> str | None:
    if stage_identifier in _RAW_STAGE_METADATA_BY_CODE:
        return stage_identifier
    if stage_identifier in _BUSINESS_STAGE_BY_RAW_STAGE_CODE:
        return stage_identifier
    if stage_identifier in _RAW_STAGE_CODE_BY_BUSINESS_STAGE:
        return _RAW_STAGE_CODE_BY_BUSINESS_STAGE[stage_identifier]
    for business_stage_code, aliases in _RAW_STAGE_CODE_ALIASES_BY_BUSINESS_STAGE.items():
        if stage_identifier in aliases:
            return _RAW_STAGE_CODE_BY_BUSINESS_STAGE[business_stage_code]
    return None


def _derive_raw_stage_start_dates(
    *,
    raw_stage_thresholds: dict[str, Decimal],
    accumulated_by_date: dict[date, Decimal],
    effective_date_rule: str,
    initial_raw_stage_start_dates: dict[str, date],
    manual_raw_stage_dates: dict[str, date],
) -> dict[str, date]:
    if not accumulated_by_date:
        return {}
    raw_stage_start_dates = dict(initial_raw_stage_start_dates)
    sorted_dates = sorted(accumulated_by_date)
    current_anchor_raw_stage_code: str | None = None
    current_anchor_accumulated: Decimal | None = None
    current_anchor_threshold: Decimal | None = None
    for raw_stage_code in _RAW_STAGE_METADATA_BY_CODE:
        threshold = raw_stage_thresholds.get(raw_stage_code)
        if threshold is None:
            continue
        manual_stage_date = manual_raw_stage_dates.get(raw_stage_code)
        if manual_stage_date is not None:
            raw_stage_start_dates[raw_stage_code] = manual_stage_date
            current_anchor_raw_stage_code = raw_stage_code
            current_anchor_threshold = threshold
            current_anchor_accumulated = _resolve_accumulated_on_or_before(
                accumulated_by_date,
                manual_stage_date,
            )
            continue
        if raw_stage_code in raw_stage_start_dates:
            continue
        target_threshold = threshold
        if (
            current_anchor_raw_stage_code is not None
            and current_anchor_accumulated is not None
            and current_anchor_threshold is not None
            and _RAW_STAGE_METADATA_BY_CODE[raw_stage_code]["season_scope"]
            == _RAW_STAGE_METADATA_BY_CODE[current_anchor_raw_stage_code]["season_scope"]
        ):
            target_threshold = current_anchor_accumulated + (threshold - current_anchor_threshold)
        for row_date in sorted_dates:
            accumulated_thermal_time = accumulated_by_date[row_date]
            if _has_reached_stage_threshold(
                accumulated_thermal_time=accumulated_thermal_time,
                threshold=target_threshold,
                effective_date_rule=effective_date_rule,
            ):
                raw_stage_start_dates[raw_stage_code] = _resolve_stage_effective_date(
                    row_date,
                    effective_date_rule=effective_date_rule,
                )
                break
    return raw_stage_start_dates


def _derive_business_stage_start_dates(raw_stage_start_dates: dict[str, date]) -> dict[str, date]:
    business_stage_start_dates: dict[str, date] = {}
    for business_stage_code, raw_stage_code in _RAW_STAGE_CODE_BY_BUSINESS_STAGE.items():
        start_date = raw_stage_start_dates.get(raw_stage_code)
        if start_date is not None:
            business_stage_start_dates[business_stage_code] = start_date
    return business_stage_start_dates


def _build_preserved_manual_stage_start_dates(
    *,
    existing_raw_stage_start_dates: dict[str, date],
    manual_raw_stage_dates: dict[str, date],
) -> dict[str, date]:
    if not existing_raw_stage_start_dates:
        return {}
    manual_anchor_indices_by_season: dict[str, list[int]] = {}
    for raw_stage_code in manual_raw_stage_dates:
        season_scope = get_raw_stage_season_scope(raw_stage_code)
        order_index = get_raw_stage_order_index(raw_stage_code)
        if season_scope is None or order_index is None:
            continue
        manual_anchor_indices_by_season.setdefault(season_scope, []).append(order_index)
    for indices in manual_anchor_indices_by_season.values():
        indices.sort()

    preserved_stage_start_dates: dict[str, date] = {}
    for raw_stage_code, start_date in existing_raw_stage_start_dates.items():
        season_scope = get_raw_stage_season_scope(raw_stage_code)
        order_index = get_raw_stage_order_index(raw_stage_code)
        if season_scope is None or order_index is None:
            continue
        manual_anchor_indices = manual_anchor_indices_by_season.get(season_scope)
        if not manual_anchor_indices:
            preserved_stage_start_dates[raw_stage_code] = start_date
            continue
        if order_index < manual_anchor_indices[0]:
            preserved_stage_start_dates[raw_stage_code] = start_date
            continue
        for left_anchor_index, right_anchor_index in zip(manual_anchor_indices, manual_anchor_indices[1:]):
            if left_anchor_index < order_index < right_anchor_index:
                preserved_stage_start_dates[raw_stage_code] = start_date
                break
    return preserved_stage_start_dates


def _extract_raw_stage_start_dates(
    stage_timeline: dict[str, Any],
    *,
    before_date: date | None = None,
) -> dict[str, date]:
    stage_start_dates: dict[str, date] = {}
    for point in _iter_stage_timeline_raw_stage_points(stage_timeline):
        if before_date is None or point["start_date"] < before_date:
            stage_start_dates[point["stage_code"]] = point["start_date"]
    if stage_start_dates:
        return stage_start_dates
    for node in parse_stage_timeline_nodes(stage_timeline):
        raw_stage_code = node.raw_stage_code or _normalize_raw_stage_code(node.stage_code)
        if raw_stage_code is None:
            continue
        if before_date is None or node.start_date < before_date:
            stage_start_dates[raw_stage_code] = node.start_date
    return stage_start_dates


def _extract_manual_raw_stage_dates(stage_timeline: dict[str, Any]) -> dict[str, date]:
    return {
        point["stage_code"]: point["start_date"]
        for point in _iter_stage_timeline_raw_stage_points(stage_timeline)
        if point.get("source") == "manual"
    }


def _resolve_transplant_based_three_leaf_override_date(
    *,
    planting_plan: PlantingPlan,
    stage_timeline: dict[str, Any],
    manual_raw_stage_dates: dict[str, date] | None,
) -> date | None:
    if planting_plan.transplant_date is None:
        return None
    if manual_raw_stage_dates and _THREE_LEAF_ONE_HEART_STAGE_CODE in manual_raw_stage_dates:
        return None
    culti_type = _resolve_stage_algorithm_culti_type(None, planting_plan.culti_type_code)
    if culti_type != _EARLY_RICE_STAGE_ALGORITHM_CULTI_TYPE:
        return None
    if planting_plan.planting_method_code == _DIRECT_SEEDED_PLANTING_METHOD_CODE:
        return None
    predicted_raw_stage_dates = _extract_raw_stage_start_dates(stage_timeline)
    predicted_three_leaf_date = predicted_raw_stage_dates.get(_THREE_LEAF_ONE_HEART_STAGE_CODE)
    if predicted_three_leaf_date is None:
        return None
    if planting_plan.transplant_date <= predicted_three_leaf_date:
        return None
    return planting_plan.transplant_date


def _iter_stage_timeline_raw_stage_points(stage_timeline: dict[str, Any]) -> list[dict[str, Any]]:
    raw_points = stage_timeline.get("raw_stage_points")
    if not isinstance(raw_points, list):
        return []
    normalized_points: list[dict[str, Any]] = []
    for item in raw_points:
        if not isinstance(item, dict):
            continue
        raw_stage_code = _normalize_raw_stage_code(
            str(item.get("stage_code") or item.get("stageCode") or item.get("raw_stage_code") or "").strip(),
        )
        raw_start_date = item.get("start_date") or item.get("startDate") or item.get("key_date") or item.get("keyDate")
        if raw_stage_code is None or raw_start_date is None:
            continue
        normalized_points.append(
            {
                "stage_code": raw_stage_code,
                "start_date": _parse_required_iso_date(raw_start_date, f"{raw_stage_code}.start_date"),
                "source": str(item.get("source") or "predicted"),
            },
        )
    normalized_points.sort(
        key=lambda item: (item["start_date"], _RAW_STAGE_ORDER_INDEX.get(item["stage_code"], 999)),
    )
    return normalized_points


def _resolve_accumulated_on_or_before(accumulated_by_date: dict[date, Decimal], target_date: date) -> Decimal | None:
    candidate_dates = [row_date for row_date in accumulated_by_date if row_date <= target_date]
    if not candidate_dates:
        return None
    latest_date = max(candidate_dates)
    return accumulated_by_date[latest_date]


def _resolve_snapshot_as_of_date(snapshot: StagePredictionSnapshot | None) -> date | None:
    if snapshot is None:
        return None
    calculation_context = snapshot.input_payload.get("calculation_context")
    if not isinstance(calculation_context, dict):
        return None
    raw_as_of_date = calculation_context.get("as_of_date")
    if raw_as_of_date is None:
        return None
    return _parse_required_iso_date(raw_as_of_date, "calculation_context.as_of_date")


def _normalize_optional_float(raw_value: Any) -> float:
    return float(Decimal(str(raw_value)))


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
