from __future__ import annotations

import calendar
import hashlib
import json
import logging
import socket
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any, Protocol
from urllib import error, request
from urllib.parse import urlencode, urlsplit

from app.core.logging import LogTimer, summarize_for_log
from app.core.constants import (
    CALENDAR_STATUS_ACTIVE,
    CALENDAR_STATUS_GENERATED,
    CALENDAR_STATUS_INVALIDATED,
    DAILY_WEATHER_CHECK_JOB,
    EVENT_TYPE_CALENDAR_ITEM_UPDATED,
    EVENT_PROCESSING_STATUS_RECEIVED,
    EVENT_TYPE_TASK_DUE_CHECK_TRIGGERED,
    EVENT_TYPE_WEATHER_UPDATED,
    SURVEY_DATE_RECOMMENDATION_JOB,
    TASK_CATEGORY_PLANT_PROTECTION,
    TASK_DUE_CHECK_JOB,
    TASK_SUBTYPE_CONTROL_EFFECT_SURVEY,
    TASK_SUBTYPE_RICE_SAFETY_SURVEY,
    TASK_SUBTYPE_REGULAR_DISEASE_PEST_SURVEY,
    TASK_SUBTYPE_SERVICE_EFFECT_EVALUATION,
    TASK_SUBTYPE_SUDDEN_DISEASE_PEST_SURVEY,
    TASK_SUBTYPE_STEM_LEAF_WEED_PRE_SURVEY,
    TASK_SUBTYPE_STEM_LEAF_WEED_RECONTROL_PRE_SURVEY,
)
from app.models import (
    CalendarItem,
    EventRecord,
    Farm,
    FarmingTask,
    PlantingPlan,
    RiceControlWindowLevel1,
    RiceVariety,
    WeatherSnapshot,
)
from app.repositories import (
    CalendarItemRepository,
    CodeDictRepository,
    EventRecordRepository,
    FarmRepository,
    PlantingPlanRepository,
    RiceControlWindowLevel1Repository,
    RiceVarietyRepository,
    StagePredictionSnapshotRepository,
    WeatherSnapshotRepository,
)
from app.services.stage_management import extract_pest_disease_growth_stage

logger = logging.getLogger(__name__)


class WeatherProvider(Protocol):
    def get_daily_weather(
        self,
        planting_plan: PlantingPlan,
        start_date: date,
        end_date: date,
        *,
        as_of_date: date | None = None,
    ) -> list[dict[str, Any]]: ...

    def get_spray_suitability_weather(
        self,
        planting_plan: PlantingPlan,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]: ...


class EventDispatcher(Protocol):
    def handle(self, event_record: EventRecord) -> Any: ...


class WeedDiagnosisClient(Protocol):
    def diagnose_soil_treatment(
        self,
        *,
        province: str,
        cultivation_system: str,
        cultivation_pattern: str,
        cultivation_date: date,
    ) -> "SoilTreatmentDiagnosisResult": ...

    def recommend_pre_treatment_survey_date(
        self,
        *,
        weather_data: list[dict[str, Any]],
        rice_type: str,
        cultivation_system: str,
        cultivation_pattern: str,
        cultivation_date: date,
    ) -> "PreTreatmentSurveyRecommendation": ...

    def recommend_post_treatment_survey_dates(
        self,
        *,
        operation_date: date,
    ) -> "PostTreatmentSurveyRecommendation": ...

    def diagnose_weed_treatment(
        self,
        *,
        province: str,
        weather_data: list[dict[str, Any]],
        rice_type: str,
        cultivation_system: str,
        cultivation_pattern: str,
        cultivation_date: date,
        survey_data_before_treatment: dict[str, Any],
        last_survey_date: date | None,
    ) -> WeedTreatmentDiagnosisResult: ...

    def diagnose_injury_mitigation(
        self,
        *,
        survey_date: date,
        rice_injury_level: str,
    ) -> InjuryMitigationDiagnosisResult: ...

    def diagnose_additional_treatment(
        self,
        *,
        province: str,
        cultivation_system: str,
        cultivation_pattern: str,
        cultivation_date: date,
        control_date: date,
        previous_injury_level: str,
        survey_data_before_treatment: dict[str, Any],
        survey_data_after_treatment: dict[str, Any],
    ) -> AdditionalTreatmentDiagnosisResult: ...


class PestDiseaseSurveyWindowClient(Protocol):
    def init_regular_surveys(
        self,
        *,
        cultivation_type: str,
        growth_stage: dict[str, str],
        level1_of_year: dict[str, list[str]],
    ) -> "PestDiseaseRegularSurveyInitResult": ...

    def daily_update_surveys(
        self,
        *,
        cultivation_type: str | None = None,
        growth_stage: dict[str, str],
        regular_plans: list[dict[str, Any]],
        weather_data: list[dict[str, Any]],
        typhoon_data: dict[str, Any],
        actual_control_date: date | None = None,
    ) -> "PestDiseaseDailyUpdateResult": ...


@dataclass(slots=True)
class PreTreatmentSurveyRecommendation:
    recommendation_date: date
    raw_response: dict[str, Any]


@dataclass(slots=True)
class PostTreatmentSurveyRecommendation:
    rice_safety_survey_date: date
    control_effect_survey_date: date
    raw_response: dict[str, Any]


@dataclass(slots=True)
class WeedTreatmentDiagnosisResult:
    branch_type: str
    control_target: list[str] | None
    recommended_control_date: tuple[date, date] | None
    control_plan: dict[str, Any] | None
    next_survey_date: date | None
    raw_response: dict[str, Any]


@dataclass(slots=True)
class InjuryMitigationDiagnosisResult:
    need_mitigation: bool
    measures: list[str]
    recommended_mitigation_date: tuple[date, date] | None
    raw_response: dict[str, Any]


@dataclass(slots=True)
class AdditionalTreatmentDiagnosisResult:
    need_recontrol: bool
    recontrol_target: list[str] | None
    recommended_recontrol_date: tuple[date, date] | None
    control_plan: dict[str, Any] | None
    additional_survey_date: date | None
    injury_mitigation: dict[str, Any] | None
    service_effect_evaluation_date: date | None
    raw_response: dict[str, Any]


@dataclass(slots=True)
class SoilTreatmentDiagnosisResult:
    recommended_date: tuple[date, date]
    farming_operation: str
    control_plan: dict[str, Any]
    raw_response: dict[str, Any]


@dataclass(slots=True)
class PestDiseaseRegularSurveyPlan:
    survey_window: tuple[date, date]
    targets: list[str]
    exclude_reasons: dict[str, Any]
    status: str
    message: str
    spray_stage: str | None
    survey_method: str | None
    adjusted: bool
    raw_plan: dict[str, Any]


@dataclass(slots=True)
class PestDiseaseRegularSurveyInitResult:
    regular_plans: list[PestDiseaseRegularSurveyPlan]
    raw_response: dict[str, Any]


@dataclass(slots=True)
class PestDiseaseDailyUpdateResult:
    status: str
    message: str
    survey_window: tuple[date, date] | None
    spray_stage: str | None
    targets: list[str]
    exclude_reasons: dict[str, Any]
    source: str | None
    raw_result: dict[str, Any]
    raw_response: dict[str, Any]


@dataclass(slots=True)
class PlantProtectionPlanContext:
    rice_type: str
    cultivation_system: str
    cultivation_pattern: str
    cultivation_date: date


@dataclass(slots=True)
class WeatherSnapshotRecordResult:
    snapshot: WeatherSnapshot
    previous_snapshot: WeatherSnapshot | None
    change_type: str


class HttpWeedDiagnosisClient:
    def __init__(self, base_url: str, timeout_seconds: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def diagnose_soil_treatment(
        self,
        *,
        province: str,
        cultivation_system: str,
        cultivation_pattern: str,
        cultivation_date: date,
    ) -> SoilTreatmentDiagnosisResult:
        response = self._post_json(
            "/api/soil_treatment_diagnosis",
            {
                "province": province,
                "cultivation_system": cultivation_system,
                "cultivation_pattern": cultivation_pattern,
                "cultivation_date": cultivation_date.strftime("%Y%m%d"),
            },
        )
        data = self._get_response_data(response, "soil_treatment_diagnosis")
        recommended_date = _parse_api_date_range(data["soil_treatment_recommended_date"])
        if recommended_date is None:
            raise ValueError("soil_treatment_diagnosis did not return soil_treatment_recommended_date.")
        return SoilTreatmentDiagnosisResult(
            recommended_date=recommended_date,
            farming_operation=str(data.get("farming_operation") or "苗后封闭"),
            control_plan=dict(data.get("control_plan") or {}),
            raw_response=response,
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
        payload = {
            "weather_data": self._normalize_weather_data(weather_data),
            "rice_type": rice_type,
            "cultivation_system": cultivation_system,
            "cultivation_pattern": cultivation_pattern,
            "cultivation_date": cultivation_date.strftime("%Y%m%d"),
        }
        response = self._post_json("/api/weed_survey_date_diagnosis", payload)
        data = self._get_response_data(response, "weed_survey_date_diagnosis")
        recommendation_date = _parse_api_date(
            self._require_data_field(data, "pre_stem_leaf_herbicide_survey_date", "weed_survey_date_diagnosis"),
        )
        return PreTreatmentSurveyRecommendation(
            recommendation_date=recommendation_date,
            raw_response=response,
        )

    def recommend_post_treatment_survey_dates(
        self,
        *,
        operation_date: date,
    ) -> PostTreatmentSurveyRecommendation:
        payload = {"operation_date": operation_date.strftime("%Y%m%d")}
        response = self._post_json("/api/after_treatment_survey_date_diagnosis", payload)
        data = self._get_response_data(response, "after_treatment_survey_date_diagnosis")
        return PostTreatmentSurveyRecommendation(
            rice_safety_survey_date=_parse_api_date(
                self._require_data_field(data, "rice_safety_survey_date", "after_treatment_survey_date_diagnosis"),
            ),
            control_effect_survey_date=_parse_api_date(
                self._require_data_field(data, "control_effect_survey_date", "after_treatment_survey_date_diagnosis"),
            ),
            raw_response=response,
        )

    def diagnose_weed_treatment(
        self,
        *,
        province: str,
        weather_data: list[dict[str, Any]],
        rice_type: str,
        cultivation_system: str,
        cultivation_pattern: str,
        cultivation_date: date,
        survey_data_before_treatment: dict[str, Any],
        last_survey_date: date | None,
    ) -> WeedTreatmentDiagnosisResult:
        response = self._post_json(
            "/api/weed_treatment_diagnosis",
            {
                "province": province,
                "weather_data": self._normalize_weather_data(weather_data),
                "rice_type": rice_type,
                "cultivation_system": cultivation_system,
                "cultivation_pattern": cultivation_pattern,
                "cultivation_date": cultivation_date.strftime("%Y%m%d"),
                "survey_data_before_treatment": survey_data_before_treatment,
                "last_survey_date": last_survey_date.strftime("%Y%m%d") if last_survey_date else None,
            },
        )
        data = self._get_response_data(response, "weed_treatment_diagnosis")
        next_survey_date = data.get("pre_stem_leaf_herbicide_survey_date")
        return WeedTreatmentDiagnosisResult(
            branch_type="resurvey" if next_survey_date else "control",
            control_target=data.get("control_target"),
            recommended_control_date=_parse_api_date_range(data.get("recommended_control_date")),
            control_plan=data.get("control_plan"),
            next_survey_date=_parse_api_date(next_survey_date) if next_survey_date else None,
            raw_response=response,
        )

    def _normalize_weather_data(self, weather_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for row in weather_data:
            if "DATE" in row and "TEMP" in row:
                normalized.append(dict(row))
                continue
            raw_date = row.get("date")
            raw_temp = row.get("avg_temp")
            if raw_date is None or raw_temp is None:
                normalized.append(dict(row))
                continue
            if isinstance(raw_date, date):
                normalized_date = raw_date.strftime("%Y%m%d")
            else:
                normalized_date = str(raw_date).strip()
                if "-" in normalized_date:
                    normalized_date = date.fromisoformat(normalized_date).strftime("%Y%m%d")
            normalized.append(
                {
                    "DATE": normalized_date,
                    "TEMP": float(raw_temp),
                },
            )
        return normalized

    def diagnose_injury_mitigation(
        self,
        *,
        survey_date: date,
        rice_injury_level: str,
    ) -> InjuryMitigationDiagnosisResult:
        response = self._post_json(
            "/api/injury_mitigation_diagnosis",
            {
                "survey_date": survey_date.strftime("%Y%m%d"),
                "rice_injury_level": rice_injury_level,
            },
        )
        data = self._get_response_data(response, "injury_mitigation_diagnosis")
        return InjuryMitigationDiagnosisResult(
            need_mitigation=bool(self._require_data_field(data, "need_mitigation", "injury_mitigation_diagnosis")),
            measures=list(data.get("measures") or []),
            recommended_mitigation_date=_parse_api_date_range(data.get("recommended_mitigation_date")),
            raw_response=response,
        )

    def diagnose_additional_treatment(
        self,
        *,
        province: str,
        cultivation_system: str,
        cultivation_pattern: str,
        cultivation_date: date,
        control_date: date,
        previous_injury_level: str,
        survey_data_before_treatment: dict[str, Any],
        survey_data_after_treatment: dict[str, Any],
    ) -> AdditionalTreatmentDiagnosisResult:
        response = self._post_json(
            "/api/additional_treatment_diagnosis",
            {
                "province": province,
                "cultivation_system": cultivation_system,
                "cultivation_pattern": cultivation_pattern,
                "cultivation_date": cultivation_date.strftime("%Y%m%d"),
                "control_date": control_date.strftime("%Y%m%d"),
                "previous_injury_level": previous_injury_level,
                "survey_data_before_treatment": survey_data_before_treatment,
                "survey_data_after_treatment": survey_data_after_treatment,
            },
        )
        data = self._get_response_data(response, "additional_treatment_diagnosis")
        additional_survey_date = data.get("additional_survey_date")
        service_effect_evaluation_date = data.get("service_effect_evaluation_date")
        return AdditionalTreatmentDiagnosisResult(
            need_recontrol=bool(self._require_data_field(data, "need_recontrol", "additional_treatment_diagnosis")),
            recontrol_target=data.get("recontrol_target"),
            recommended_recontrol_date=_parse_api_date_range(data.get("recommended_recontrol_date")),
            control_plan=data.get("control_plan"),
            additional_survey_date=_parse_api_date(additional_survey_date) if additional_survey_date else None,
            injury_mitigation=data.get("injury_mitigation"),
            service_effect_evaluation_date=(
                _parse_api_date(service_effect_evaluation_date) if service_effect_evaluation_date else None
            ),
            raw_response=response,
        )

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        url = f"{self.base_url}{path}"
        http_request = request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        timer = LogTimer()
        logger.info(
            "Calling weed diagnosis API path=%s host=%s payload=%s",
            path,
            urlsplit(url).netloc,
            summarize_for_log(payload),
        )
        try:
            with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
                logger.info(
                    "Weed diagnosis API succeeded path=%s status=%s duration_ms=%.2f response=%s",
                    path,
                    getattr(response, "status", 200),
                    timer.elapsed_ms,
                    summarize_for_log(response_payload),
                )
                return response_payload
        except error.HTTPError as exc:
            raw_response = exc.read().decode("utf-8", errors="replace")
            logger.warning(
                "Weed diagnosis API returned HTTP error path=%s status=%s duration_ms=%.2f payload=%s response=%s",
                path,
                exc.code,
                timer.elapsed_ms,
                summarize_for_log(payload),
                summarize_for_log(raw_response),
            )
            message = f"Weed diagnosis API {path} returned HTTP {exc.code}"
            if raw_response:
                message = f"{message}: {raw_response}"
            raise ValueError(message) from exc
        except error.URLError as exc:
            logger.error(
                "Weed diagnosis API is unreachable path=%s duration_ms=%.2f payload=%s reason=%s",
                path,
                timer.elapsed_ms,
                summarize_for_log(payload),
                exc.reason,
            )
            raise RuntimeError(f"Weed diagnosis API {path} is unreachable: {exc.reason}") from exc
        except (TimeoutError, socket.timeout) as exc:
            logger.error(
                "Weed diagnosis API timed out path=%s duration_ms=%.2f payload=%s",
                path,
                timer.elapsed_ms,
                summarize_for_log(payload),
            )
            raise RuntimeError(f"Weed diagnosis API {path} timed out.") from exc

    def _get_response_data(self, response: dict[str, Any], api_name: str) -> dict[str, Any]:
        data = response.get("data")
        if not isinstance(data, dict):
            raise ValueError(f"{api_name} did not return a valid data object.")
        return data

    def _require_data_field(self, data: dict[str, Any], field: str, api_name: str) -> Any:
        if field not in data:
            raise ValueError(f"{api_name} did not return {field}.")
        return data[field]


class HttpPestDiseaseSurveyWindowClient:
    def __init__(self, base_url: str, timeout_seconds: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def init_regular_surveys(
        self,
        *,
        cultivation_type: str,
        growth_stage: dict[str, str],
        level1_of_year: dict[str, list[str]],
    ) -> PestDiseaseRegularSurveyInitResult:
        response = self._post_json(
            "/pestDisease/survey/init-regular-survey",
            {
                "cultivation_type": cultivation_type,
                "growth_stage": growth_stage,
                "level1_of_year": level1_of_year,
            },
        )
        data = self._get_response_data(response, "init-regular-survey")
        raw_plans = data.get("regular_plans")
        if not isinstance(raw_plans, list):
            raise ValueError("init-regular-survey did not return regular_plans.")
        return PestDiseaseRegularSurveyInitResult(
            regular_plans=[_parse_pest_disease_regular_plan(item) for item in raw_plans],
            raw_response=response,
        )

    def daily_update_surveys(
        self,
        *,
        cultivation_type: str | None = None,
        growth_stage: dict[str, str],
        regular_plans: list[dict[str, Any]],
        weather_data: list[dict[str, Any]],
        typhoon_data: dict[str, Any],
        actual_control_date: date | None = None,
    ) -> PestDiseaseDailyUpdateResult:
        payload: dict[str, Any] = {
            "growth_stage": growth_stage,
            "regular_plans": regular_plans,
            "weather_data": weather_data,
            "typhoon_data": typhoon_data,
        }
        if cultivation_type is not None:
            payload["cultivation_type"] = cultivation_type
        if actual_control_date is not None:
            payload["actual_control_date"] = actual_control_date.strftime("%Y%m%d")
        response = self._post_json("/pestDisease/survey/daily-update-survey", payload)
        data = self._get_response_data(response, "daily-update-survey")
        return _parse_pest_disease_daily_update_result(data, response)

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
            "Calling pest disease survey API path=%s host=%s payload=%s",
            path,
            urlsplit(url).netloc,
            summarize_for_log(payload),
        )
        try:
            with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
                logger.info(
                    "Pest disease survey API succeeded path=%s status=%s duration_ms=%.2f response=%s",
                    path,
                    getattr(response, "status", 200),
                    timer.elapsed_ms,
                    summarize_for_log(response_payload),
                )
                return response_payload
        except error.HTTPError as exc:
            raw_response = exc.read().decode("utf-8", errors="replace")
            logger.warning(
                "Pest disease survey API returned HTTP error path=%s status=%s duration_ms=%.2f payload=%s response=%s",
                path,
                exc.code,
                timer.elapsed_ms,
                summarize_for_log(payload),
                summarize_for_log(raw_response),
            )
            message = f"Pest disease survey API {path} returned HTTP {exc.code}"
            if raw_response:
                message = f"{message}: {raw_response}"
            raise ValueError(message) from exc
        except error.URLError as exc:
            logger.error(
                "Pest disease survey API is unreachable path=%s duration_ms=%.2f payload=%s reason=%s",
                path,
                timer.elapsed_ms,
                summarize_for_log(payload),
                exc.reason,
            )
            raise RuntimeError(f"Pest disease survey API {path} is unreachable: {exc.reason}") from exc
        except (TimeoutError, socket.timeout) as exc:
            logger.error(
                "Pest disease survey API timed out path=%s duration_ms=%.2f payload=%s",
                path,
                timer.elapsed_ms,
                summarize_for_log(payload),
            )
            raise RuntimeError(f"Pest disease survey API {path} timed out.") from exc

    def _get_response_data(self, response: dict[str, Any], api_name: str) -> dict[str, Any]:
        data = response.get("data")
        if not isinstance(data, dict):
            raise ValueError(f"{api_name} did not return a valid data object.")
        return data


class MockPestDiseaseSurveyWindowClient:
    def init_regular_surveys(
        self,
        *,
        cultivation_type: str,
        growth_stage: dict[str, str],
        level1_of_year: dict[str, list[str]],
    ) -> PestDiseaseRegularSurveyInitResult:
        year = date.fromisoformat(growth_stage["tillering_date"]).year
        plans: list[PestDiseaseRegularSurveyPlan] = []
        raw_plans: list[dict[str, Any]] = []
        excluded_brown_planthopper = cultivation_type == "早稻"
        for sequence, window in sorted(level1_of_year.items(), key=lambda item: int(item[0])):
            start_date = _parse_month_day(year, window[0])
            end_date = _parse_month_day(year, window[1])
            targets = ["二化螟", "稻纵卷叶螟", "稻飞虱", "稻瘟病", "纹枯病"]
            exclude_reasons: dict[str, Any] = {}
            if excluded_brown_planthopper:
                targets.remove("稻飞虱")
                exclude_reasons["稻飞虱"] = "早稻不调查稻飞虱"
            raw_plan = {
                "status": "need_survey",
                "survey_window": [start_date.strftime("%Y%m%d"), end_date.strftime("%Y%m%d")],
                "spray_stage": "常规病虫预防",
                "survey_method": "一级理论防治日期",
                "targets": targets,
                "exclude_reasons": exclude_reasons,
                "msg": f"Mock regular pest disease survey plan {sequence}",
                "adjusted": False,
            }
            raw_plans.append(raw_plan)
            plans.append(_parse_pest_disease_regular_plan(raw_plan))
        return PestDiseaseRegularSurveyInitResult(
            regular_plans=plans,
            raw_response={
                "mock": True,
                "code": 200,
                "msg": f"已生成{len(plans)}个常规调查任务",
                "data": {"count": len(plans), "regular_plans": raw_plans},
            },
        )

    def daily_update_surveys(
        self,
        *,
        cultivation_type: str | None = None,
        growth_stage: dict[str, str],
        regular_plans: list[dict[str, Any]],
        weather_data: list[dict[str, Any]],
        typhoon_data: dict[str, Any],
        actual_control_date: date | None = None,
    ) -> PestDiseaseDailyUpdateResult:
        has_typhoon_alert = bool(typhoon_data.get("alerts"))
        targets = ["稻飞虱", "纹枯病"]
        exclude_reasons: dict[str, Any] = {}
        if cultivation_type == "早稻":
            targets = ["纹枯病"]
            exclude_reasons["稻飞虱"] = "早稻不调查稻飞虱"
        if has_typhoon_alert:
            data = {
                "status": "new_emergency",
                "msg": "已识别到临时调查触发条件，建议开展临时调查",
                "survey_window": ["20260703", "20260704"],
                "spray_stage": "突发病虫防治",
                "targets": targets,
                "exclude_reasons": exclude_reasons,
                "source": "emergency",
                "raw_result": {
                    "cultivation_type": cultivation_type,
                    "growth_stage": growth_stage,
                    "regular_plans": regular_plans,
                    "weather_data": weather_data,
                    "typhoon_data": typhoon_data,
                    "actual_control_date": actual_control_date.strftime("%Y%m%d") if actual_control_date else None,
                },
            }
        else:
            data = {
                "status": "no_new_event",
                "msg": "当天无新增调查事件",
                "survey_window": [],
                "spray_stage": None,
                "targets": [],
                "exclude_reasons": {},
                "source": "none",
                "raw_result": {
                    "cultivation_type": cultivation_type,
                    "growth_stage": growth_stage,
                    "regular_plans": regular_plans,
                    "weather_data": weather_data,
                    "typhoon_data": typhoon_data,
                    "actual_control_date": actual_control_date.strftime("%Y%m%d") if actual_control_date else None,
                },
            }
        response = {"mock": True, "code": 200, "msg": data["msg"], "data": data}
        return _parse_pest_disease_daily_update_result(data, response)


class MockWeedDiagnosisClient:
    def diagnose_soil_treatment(
        self,
        *,
        province: str,
        cultivation_system: str,
        cultivation_pattern: str,
        cultivation_date: date,
    ) -> SoilTreatmentDiagnosisResult:
        recommended_start = cultivation_date + timedelta(days=8)
        recommended_end = cultivation_date + timedelta(days=11)
        control_plan = {
            "prescriptions": [
                {
                    "pesticide": "60%苄·丁",
                    "formulation": "OD",
                    "manufacturer": "示例厂商",
                    "recommended_dosage": "100 g/亩",
                },
            ],
            "water_volume": "3 L/亩",
        }
        return SoilTreatmentDiagnosisResult(
            recommended_date=(recommended_start, recommended_end),
            farming_operation="苗后封闭",
            control_plan=control_plan,
            raw_response={
                "mock": True,
                "data": {
                    "soil_treatment_recommended_date": [
                        recommended_start.strftime("%Y%m%d"),
                        recommended_end.strftime("%Y%m%d"),
                    ],
                    "farming_operation": "苗后封闭",
                    "control_plan": control_plan,
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
        recommendation_date = cultivation_date + timedelta(days=8)
        return PreTreatmentSurveyRecommendation(
            recommendation_date=recommendation_date,
            raw_response={
                "mock": True,
                "data": {
                    "pre_stem_leaf_herbicide_survey_date": recommendation_date.strftime("%Y%m%d"),
                },
            },
        )

    def recommend_post_treatment_survey_dates(
        self,
        *,
        operation_date: date,
    ) -> PostTreatmentSurveyRecommendation:
        rice_safety_survey_date = operation_date + timedelta(days=3)
        control_effect_survey_date = operation_date + timedelta(days=7)
        return PostTreatmentSurveyRecommendation(
            rice_safety_survey_date=rice_safety_survey_date,
            control_effect_survey_date=control_effect_survey_date,
            raw_response={
                "mock": True,
                "data": {
                    "rice_safety_survey_date": rice_safety_survey_date.strftime("%Y%m%d"),
                    "control_effect_survey_date": control_effect_survey_date.strftime("%Y%m%d"),
                },
            },
        )

    def diagnose_weed_treatment(
        self,
        *,
        province: str,
        weather_data: list[dict[str, Any]],
        rice_type: str,
        cultivation_system: str,
        cultivation_pattern: str,
        cultivation_date: date,
        survey_data_before_treatment: dict[str, Any],
        last_survey_date: date | None,
    ) -> WeedTreatmentDiagnosisResult:
        survey_date = _parse_api_date(str(survey_data_before_treatment["survey_date"]))
        if survey_data_before_treatment.get("mock_branch") == "resurvey":
            next_survey_date = survey_date + timedelta(days=5)
            return WeedTreatmentDiagnosisResult(
                branch_type="resurvey",
                control_target=None,
                recommended_control_date=None,
                control_plan=None,
                next_survey_date=next_survey_date,
                raw_response={
                    "mock": True,
                    "msg": "5d后重新调查",
                    "data": {
                        "pre_stem_leaf_herbicide_survey_date": next_survey_date.strftime("%Y%m%d"),
                    },
                },
            )

        recommended_date = survey_date + timedelta(days=2)
        control_plan = _mock_control_plan()
        return WeedTreatmentDiagnosisResult(
            branch_type="control",
            control_target=["BaiCao"],
            recommended_control_date=(recommended_date, recommended_date),
            control_plan=control_plan,
            next_survey_date=None,
            raw_response={
                "mock": True,
                "msg": "已推荐除草日期",
                "data": {
                    "control_target": ["BaiCao"],
                    "recommended_control_date": [
                        recommended_date.strftime("%Y%m%d"),
                        recommended_date.strftime("%Y%m%d"),
                    ],
                    "control_plan": control_plan,
                },
            },
        )

    def diagnose_injury_mitigation(
        self,
        *,
        survey_date: date,
        rice_injury_level: str,
    ) -> InjuryMitigationDiagnosisResult:
        need_mitigation = rice_injury_level not in {"无", "轻"}
        recommended_date = (survey_date, survey_date + timedelta(days=2)) if need_mitigation else None
        measures = ["尿素3～5公斤/亩"] if need_mitigation else ["自然恢复"]
        return InjuryMitigationDiagnosisResult(
            need_mitigation=need_mitigation,
            measures=measures,
            recommended_mitigation_date=recommended_date,
            raw_response={
                "mock": True,
                "data": {
                    "need_mitigation": need_mitigation,
                    "measures": measures,
                    "recommended_mitigation_date": (
                        [item.strftime("%Y%m%d") for item in recommended_date] if recommended_date else None
                    ),
                },
            },
        )

    def diagnose_additional_treatment(
        self,
        *,
        province: str,
        cultivation_system: str,
        cultivation_pattern: str,
        cultivation_date: date,
        control_date: date,
        previous_injury_level: str,
        survey_data_before_treatment: dict[str, Any],
        survey_data_after_treatment: dict[str, Any],
    ) -> AdditionalTreatmentDiagnosisResult:
        branch = survey_data_after_treatment.get("mock_branch", "service_evaluation")
        survey_date = _parse_api_date(str(survey_data_after_treatment["survey_date"]))
        if branch == "immediate_recontrol":
            recommended_date = (survey_date, survey_date + timedelta(days=1))
            control_plan = _mock_control_plan()
            return AdditionalTreatmentDiagnosisResult(
                need_recontrol=True,
                recontrol_target=["BaiCao"],
                recommended_recontrol_date=recommended_date,
                control_plan=control_plan,
                additional_survey_date=None,
                injury_mitigation=None,
                service_effect_evaluation_date=None,
                raw_response={"mock": True, "data": {"branch": branch}},
            )

        if branch == "mitigation":
            additional_survey_date = survey_date + timedelta(days=3)
            return AdditionalTreatmentDiagnosisResult(
                need_recontrol=False,
                recontrol_target=None,
                recommended_recontrol_date=None,
                control_plan=None,
                additional_survey_date=additional_survey_date,
                injury_mitigation={
                    "need_mitigation": True,
                    "measures": ["尿素3～5公斤/亩"],
                    "injury_trend": "持平",
                    "recommended_mitigation_date": [
                        survey_date.strftime("%Y%m%d"),
                        (survey_date + timedelta(days=2)).strftime("%Y%m%d"),
                    ],
                },
                service_effect_evaluation_date=None,
                raw_response={"mock": True, "data": {"branch": branch}},
            )

        return AdditionalTreatmentDiagnosisResult(
            need_recontrol=False,
            recontrol_target=None,
            recommended_recontrol_date=None,
            control_plan=None,
            additional_survey_date=None,
            injury_mitigation=None,
            service_effect_evaluation_date=survey_date + timedelta(days=5),
            raw_response={"mock": True, "data": {"branch": branch}},
        )


class HttpWeatherProvider:
    FORECAST_HOURLY_PATH = "/algBaseDataApi/v1/getForecast10DaysBeforeAndAfter"
    FORECAST_DAILY_PATH = "/weather/v1/getForecast10DaysBeforeAnd15DaysAfter"
    AVERAGE_TEMP_PRECIPITATION_PATH = "/weather/v1/getAvgTemAndPre"
    FARM_ID_PAYLOAD_CANDIDATES = ("farmId", "farmID")
    FORECAST_DAILY_LOOKAHEAD_DAYS = 14
    DEFAULT_SUITABILITY_WINDS = 2.0
    DEFAULT_SUITABILITY_RH = 70.0
    TYPHOON_ALERTS_PATH = "/Zoomlion/alert"
    TYPHOON_EVENT_KEYWORDS = ("台风", "热带风暴", "强热带风暴", "超强台风", "热带低压", "台风外围", "外围环流")
    TYPHOON_ALERT_PROVINCE_PREFIXES = {
        "湖南省": ("43", "44", "45"),
        "安徽省": ("34", "33", "35", "31", "32"),
    }

    def __init__(
        self,
        farm_repository: FarmRepository,
        base_url: str,
        auth_token: str,
        alert_base_url: str | None = None,
        alert_auth_token: str | None = None,
        timeout_seconds: float = 10.0,
        climatology_reference_years: int = 3,
    ) -> None:
        self.farm_repository = farm_repository
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
        self.alert_base_url = alert_base_url.rstrip("/") if alert_base_url else None
        self.alert_auth_token = alert_auth_token
        self.timeout_seconds = timeout_seconds
        self.climatology_reference_years = climatology_reference_years

    def get_daily_weather(
        self,
        planting_plan: PlantingPlan,
        start_date: date,
        end_date: date,
        *,
        as_of_date: date | None = None,
    ) -> list[dict[str, Any]]:
        if start_date > end_date:
            return []

        effective_as_of_date = as_of_date or date.today()
        farm = self._get_farm(planting_plan.farm_id)
        external_farm_id = self._resolve_external_farm_id(farm)
        weather_data: list[dict[str, Any]] = []

        observed_end_date = min(end_date, effective_as_of_date - timedelta(days=1))
        if start_date <= observed_end_date:
            weather_data.extend(
                self._load_observed_daily_weather(
                    external_farm_id,
                    start_date=start_date,
                    end_date=observed_end_date,
                ),
            )

        forecast_start_date = max(start_date, effective_as_of_date)
        # The upstream API returns current day plus the next 14 calendar days.
        forecast_end_date = min(end_date, effective_as_of_date + timedelta(days=self.FORECAST_DAILY_LOOKAHEAD_DAYS))
        if forecast_start_date <= forecast_end_date:
            weather_data.extend(
                self._load_forecast_daily_weather(
                    external_farm_id,
                    start_date=forecast_start_date,
                    end_date=forecast_end_date,
                ),
            )

        climatology_start_date = max(
            start_date,
            effective_as_of_date + timedelta(days=self.FORECAST_DAILY_LOOKAHEAD_DAYS + 1),
        )
        if climatology_start_date <= end_date:
            weather_data.extend(
                self._load_climatology_daily_weather(
                    external_farm_id,
                    start_date=climatology_start_date,
                    end_date=end_date,
                ),
            )

        weather_data.sort(key=lambda item: str(item["date"]))
        return weather_data

    def get_pest_disease_daily_weather(
        self,
        planting_plan: PlantingPlan,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        if start_date > end_date:
            return []

        farm = self._get_farm(planting_plan.farm_id)
        external_farm_id = self._resolve_external_farm_id(farm)
        response_data = self._load_forecast_daily_response_data(external_farm_id)
        weather_data: list[dict[str, Any]] = []
        for row in response_data:
            row_date = date.fromisoformat(str(row.get("datatime")))
            if row_date < start_date or row_date > end_date:
                continue
            weather_data.append(
                {
                    "DATE": row_date.strftime("%Y%m%d"),
                    "TMAX": _normalize_required_float(row.get("tMax"), "tMax", self.FORECAST_DAILY_PATH),
                    "RAIN": _normalize_required_float(row.get("pre"), "pre", self.FORECAST_DAILY_PATH),
                    "SUN": _normalize_required_float(row.get("ssh"), "ssh", self.FORECAST_DAILY_PATH),
                },
            )
        expected_dates = {item.strftime("%Y%m%d") for item in _build_closed_date_range(start_date, end_date)}
        returned_dates = {str(item["DATE"]) for item in weather_data}
        missing_dates = sorted(expected_dates - returned_dates)
        if missing_dates:
            raise ValueError(f"Pest disease daily weather is missing rows for dates: {missing_dates}.")
        weather_data.sort(key=lambda item: str(item["DATE"]))
        return weather_data

    def get_spray_suitability_weather(
        self,
        planting_plan: PlantingPlan,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        if start_date > end_date:
            return []

        farm = self._get_farm(planting_plan.farm_id)
        external_farm_id = self._resolve_external_farm_id(farm)
        effective_as_of_date = date.today()
        weather_rows_by_date: dict[str, dict[str, Any]] = {}

        observed_end_date = min(end_date, effective_as_of_date - timedelta(days=1))
        if start_date <= observed_end_date:
            for row in self._load_observed_daily_weather(
                external_farm_id,
                start_date=start_date,
                end_date=observed_end_date,
            ):
                weather_rows_by_date[str(row["date"])] = self._build_suitability_row_from_daily_weather(row)

        for row in self._load_forecast_daily_response_data(external_farm_id):
            row_date = date.fromisoformat(str(row.get("datatime")))
            if row_date < start_date or row_date > end_date:
                continue
            weather_rows_by_date[row_date.isoformat()] = {
                "date": row_date.strftime("%Y%m%d"),
                "wins": _normalize_required_float(row.get("wins"), "wins", self.FORECAST_DAILY_PATH),
                "pre": _normalize_required_float(row.get("pre"), "pre", self.FORECAST_DAILY_PATH),
                "rh": _normalize_required_float(row.get("rh"), "rh", self.FORECAST_DAILY_PATH),
                "tAvg": _normalize_required_float(row.get("tAvg"), "tAvg", self.FORECAST_DAILY_PATH),
            }

        climatology_start_date = max(
            start_date,
            effective_as_of_date + timedelta(days=self.FORECAST_DAILY_LOOKAHEAD_DAYS + 1),
        )
        if climatology_start_date <= end_date:
            for row in self._load_climatology_daily_weather(
                external_farm_id,
                start_date=climatology_start_date,
                end_date=end_date,
            ):
                weather_rows_by_date[str(row["date"])] = self._build_suitability_row_from_daily_weather(row)

        weather_data = [
            weather_rows_by_date[item.isoformat()]
            for item in _build_closed_date_range(start_date, end_date)
            if item.isoformat() in weather_rows_by_date
        ]
        expected_dates = {item.strftime("%Y%m%d") for item in _build_closed_date_range(start_date, end_date)}
        returned_dates = {str(item["date"]) for item in weather_data}
        missing_dates = sorted(expected_dates - returned_dates)
        if missing_dates:
            raise ValueError(f"Spray suitability weather is missing rows for dates: {missing_dates}.")
        weather_data.sort(key=lambda item: str(item["date"]))
        return weather_data

    def get_hourly_weather_72h(
        self,
        planting_plan: PlantingPlan,
        *,
        as_of_datetime: datetime | None = None,
    ) -> list[dict[str, Any]]:
        farm = self._get_farm(planting_plan.farm_id)
        external_farm_id = self._resolve_external_farm_id(farm)
        effective_as_of = _floor_to_hour(as_of_datetime or _utcnow())
        try:
            response_data = self._post_weather_json_with_farm_id_compatibility(
                self.FORECAST_HOURLY_PATH,
                {"farmId": external_farm_id},
                preferred_farm_id_keys=("farmId", "farmID"),
            )
            return self._build_hourly_weather_from_hourly_rows(response_data, effective_as_of=effective_as_of)
        except (RuntimeError, ValueError):
            return self._build_hourly_weather_from_daily_forecast(
                external_farm_id,
                effective_as_of=effective_as_of,
            )

    def get_typhoon_alerts(self, planting_plan: PlantingPlan) -> list[dict[str, Any]]:
        if not self.alert_base_url:
            return []

        farm = self._get_farm(planting_plan.farm_id)
        province = str(farm.province or "").strip()
        if not province:
            raise ValueError("Typhoon alert lookup requires Farm.province.")

        relevant_prefixes = self.TYPHOON_ALERT_PROVINCE_PREFIXES.get(province)
        if relevant_prefixes is None:
            adcode = str(farm.adcode or "").strip()
            if len(adcode) < 2:
                return []
            relevant_prefixes = (adcode[:2],)

        rows = self._get_json(self.alert_base_url, self.TYPHOON_ALERTS_PATH, token=self.alert_auth_token)
        alerts: list[dict[str, Any]] = []
        for row in rows:
            msg_type = str(row.get("msgType") or "").strip()
            msg_type_code = str(row.get("msgTypeCode") or "").strip()
            event_type = str(row.get("eventType") or "").strip()
            if msg_type == "解除" or msg_type_code == "Cancel":
                continue
            if not any(keyword in event_type for keyword in self.TYPHOON_EVENT_KEYWORDS):
                continue
            affected_codes = _split_affected_area_codes(row.get("affectedArea"))
            if not affected_codes:
                fallback_code = str(row.get("geoCode") or row.get("areaCode") or "").strip()
                if fallback_code:
                    affected_codes = [fallback_code]
            if not any(any(code.startswith(prefix) for prefix in relevant_prefixes) for code in affected_codes):
                continue
            effective = str(row.get("effective") or "").strip()
            if not effective:
                continue
            alerts.append({"eventType": event_type, "effective": effective})
        alerts.sort(key=lambda item: (str(item["effective"]), str(item["eventType"])))
        return alerts

    def _get_farm(self, farm_id: int) -> Farm:
        farm = self.farm_repository.get(farm_id)
        if farm is None:
            raise ValueError(f"Farm {farm_id} does not exist.")
        return farm

    def _resolve_external_farm_id(self, farm: Farm) -> str:
        external_farm_id = farm.external_farm_id or str(farm.id)
        normalized = external_farm_id.strip()
        if not normalized:
            raise ValueError("Weather provider requires Farm.external_farm_id or a non-empty Farm.id.")
        return normalized

    def _load_observed_daily_weather(
        self,
        external_farm_id: str,
        *,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        weather_data: list[dict[str, Any]] = []
        chunk_start = start_date
        while chunk_start <= end_date:
            chunk_end = min(end_date, chunk_start + timedelta(days=364))
            response_data = self._post_weather_json_with_farm_id_compatibility(
                self.AVERAGE_TEMP_PRECIPITATION_PATH,
                {
                    "farmId": external_farm_id,
                    "startDate": chunk_start.isoformat(),
                    "endDate": chunk_end.isoformat(),
                },
                preferred_farm_id_keys=("farmId", "farmID"),
            )
            expected_dates = _build_closed_date_range(chunk_start, chunk_end)
            if len(response_data) != len(expected_dates):
                raise ValueError(
                    "Weather average API did not return the expected number of observed daily rows "
                    f"for {chunk_start} to {chunk_end}.",
                )
            data_version = f"weather-observed:{chunk_start.isoformat()}:{chunk_end.isoformat()}"
            for index, (expected_date, row) in enumerate(zip(expected_dates, response_data, strict=True)):
                weather_data.append(
                    {
                        "date": expected_date.isoformat(),
                        "avg_temp": _resolve_observed_avg_temp(
                            response_data,
                            index=index,
                            expected_date=expected_date,
                        ),
                        "precipitation": _normalize_optional_float(row.get("preAvg")),
                        "source_type": "observed",
                        "data_version": data_version,
                    },
                )
            chunk_start = chunk_end + timedelta(days=1)
        return weather_data

    def _load_forecast_daily_weather(
        self,
        external_farm_id: str,
        *,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        response_data = self._load_forecast_daily_response_data(external_farm_id)
        data_version = f"weather-forecast:{date.today().isoformat()}"
        weather_data: list[dict[str, Any]] = []
        for row in response_data:
            row_date = date.fromisoformat(str(row.get("datatime")))
            if row_date < start_date or row_date > end_date:
                continue
            weather_data.append(
                {
                    "date": row_date.isoformat(),
                    "avg_temp": _normalize_optional_float(row.get("tAvg")),
                    "min_temp": _normalize_optional_float(row.get("tMin")),
                    "max_temp": _normalize_optional_float(row.get("tMax")),
                    "precipitation": _normalize_optional_float(row.get("pre")),
                    "source_type": "forecast",
                    "data_version": data_version,
                },
            )
        expected_dates = {item.isoformat() for item in _build_closed_date_range(start_date, end_date)}
        returned_dates = {str(item["date"]) for item in weather_data}
        missing_dates = sorted(expected_dates - returned_dates)
        if missing_dates:
            raise ValueError(f"Weather forecast API is missing daily rows for dates: {missing_dates}.")
        return weather_data

    def _load_forecast_daily_response_data(self, external_farm_id: str) -> list[dict[str, Any]]:
        return self._post_weather_json_with_farm_id_compatibility(
            self.FORECAST_DAILY_PATH,
            {
                "farmID": external_farm_id,
            },
            preferred_farm_id_keys=("farmID", "farmId"),
        )

    def _load_climatology_daily_weather(
        self,
        external_farm_id: str,
        *,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        request_start_date = _shift_years(start_date, -self.climatology_reference_years)
        request_end_date = _shift_years(end_date, -1)
        response_data = self._post_weather_json_with_farm_id_compatibility(
            self.AVERAGE_TEMP_PRECIPITATION_PATH,
            {
                "farmId": external_farm_id,
                "startDate": request_start_date.isoformat(),
                "endDate": request_end_date.isoformat(),
            },
            preferred_farm_id_keys=("farmId", "farmID"),
        )
        row_by_month_day: dict[str, dict[str, Any]] = {}
        for row in response_data:
            month_day = str(row.get("dt") or "").strip()
            if not month_day:
                raise ValueError("Weather climatology API returned a row without dt.")
            row_by_month_day[month_day] = row

        data_version = f"weather-climatology:{request_start_date.isoformat()}:{request_end_date.isoformat()}"
        weather_data: list[dict[str, Any]] = []
        for target_date in _build_closed_date_range(start_date, end_date):
            month_day = target_date.strftime("%m-%d")
            row = row_by_month_day.get(month_day)
            if row is None:
                raise ValueError(f"Weather climatology API is missing dt={month_day}.")
            weather_data.append(
                {
                    "date": target_date.isoformat(),
                    "avg_temp": _normalize_optional_float(row.get("temAvg")),
                    "precipitation": _normalize_optional_float(row.get("preAvg")),
                    "source_type": "climatology",
                    "data_version": data_version,
                },
            )
        return weather_data

    def _build_suitability_row_from_daily_weather(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "date": date.fromisoformat(str(row["date"])).strftime("%Y%m%d"),
            "wins": self.DEFAULT_SUITABILITY_WINDS,
            "pre": float(row.get("precipitation") or 0.0),
            "rh": self.DEFAULT_SUITABILITY_RH,
            "tAvg": float(row["avg_temp"]),
        }

    def _build_hourly_weather_from_hourly_rows(
        self,
        response_data: list[dict[str, Any]],
        *,
        effective_as_of: datetime,
    ) -> list[dict[str, Any]]:
        end_datetime = effective_as_of + timedelta(hours=72)
        weather_data: list[dict[str, Any]] = []
        for row in response_data:
            raw_datetime = str(row.get("datatime") or "").strip()
            if not raw_datetime:
                continue
            row_datetime = datetime.fromisoformat(raw_datetime)
            if row_datetime < effective_as_of or row_datetime >= end_datetime:
                continue
            weather_data.append(
                {
                    "datetime": row_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                    "pre": _normalize_required_float(row.get("pre"), "pre", self.FORECAST_HOURLY_PATH),
                    "wins": _normalize_required_float(row.get("wins"), "wins", self.FORECAST_HOURLY_PATH),
                    "gust": _normalize_optional_float(row.get("gust")),
                    "wp": str(row.get("wp") or "").strip() or None,
                },
            )
        weather_data.sort(key=lambda item: str(item["datetime"]))
        if len(weather_data) < 72:
            raise ValueError(
                "Hourly weather API did not return enough rows for the next 72 hours. "
                f"expected at least 72, got {len(weather_data)}."
            )
        return weather_data[:72]

    def _build_hourly_weather_from_daily_forecast(
        self,
        external_farm_id: str,
        *,
        effective_as_of: datetime,
    ) -> list[dict[str, Any]]:
        rows_by_date = {
            str(item.get("datatime")): item
            for item in self._load_forecast_daily_response_data(external_farm_id)
            if str(item.get("datatime") or "").strip()
        }
        weather_data: list[dict[str, Any]] = []
        for offset in range(72):
            current_datetime = effective_as_of + timedelta(hours=offset)
            current_date = current_datetime.date().isoformat()
            row = rows_by_date.get(current_date)
            if row is None:
                raise ValueError(
                    "Daily forecast API did not return enough rows to synthesize the next 72 hours. "
                    f"missing date {current_date}.",
                )
            daily_precipitation = _normalize_required_float(row.get("pre"), "pre", self.FORECAST_DAILY_PATH)
            weather_data.append(
                {
                    "datetime": current_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                    "pre": round(daily_precipitation / 24.0, 4),
                    "wins": _normalize_required_float(row.get("wins"), "wins", self.FORECAST_DAILY_PATH),
                    "gust": _normalize_optional_float(row.get("wmax")),
                    "wp": None,
                },
            )
        return weather_data

    def _post_json(self, path: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        url = f"{self.base_url}{path}"
        http_request = request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": self.auth_token,
            },
            method="POST",
        )
        timer = LogTimer()
        logger.info(
            "Calling weather API path=%s host=%s payload=%s",
            path,
            urlsplit(url).netloc,
            summarize_for_log(payload),
        )
        try:
            with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
                logger.info(
                    "Weather API succeeded path=%s status=%s duration_ms=%.2f response=%s",
                    path,
                    getattr(response, "status", 200),
                    timer.elapsed_ms,
                    summarize_for_log(response_payload),
                )
        except error.HTTPError as exc:
            raw_response = exc.read().decode("utf-8", errors="replace")
            logger.warning(
                "Weather API returned HTTP error path=%s status=%s duration_ms=%.2f payload=%s response=%s",
                path,
                exc.code,
                timer.elapsed_ms,
                summarize_for_log(payload),
                summarize_for_log(raw_response),
            )
            message = f"Weather API {path} returned HTTP {exc.code}"
            if raw_response:
                message = f"{message}: {raw_response}"
            raise ValueError(message) from exc
        except error.URLError as exc:
            logger.error(
                "Weather API is unreachable path=%s duration_ms=%.2f payload=%s reason=%s",
                path,
                timer.elapsed_ms,
                summarize_for_log(payload),
                exc.reason,
            )
            raise RuntimeError(f"Weather API {path} is unreachable: {exc.reason}") from exc
        except (TimeoutError, socket.timeout) as exc:
            logger.error(
                "Weather API timed out path=%s duration_ms=%.2f payload=%s",
                path,
                timer.elapsed_ms,
                summarize_for_log(payload),
            )
            raise RuntimeError(f"Weather API {path} timed out.") from exc

        if str(response_payload.get("code")) != "0":
            raise ValueError(f"Weather API {path} returned business code {response_payload.get('code')}.")
        data = response_payload.get("data")
        if not isinstance(data, list):
            raise ValueError(f"Weather API {path} did not return a valid data array.")
        normalized_data = [dict(item) for item in data if isinstance(item, dict)]
        if len(normalized_data) != len(data):
            raise ValueError(f"Weather API {path} returned invalid row objects.")
        return normalized_data

    def _post_weather_json_with_farm_id_compatibility(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        preferred_farm_id_keys: tuple[str, ...],
    ) -> list[dict[str, Any]]:
        farm_id_value = None
        remaining_payload = dict(payload)
        for candidate_key in self.FARM_ID_PAYLOAD_CANDIDATES:
            if candidate_key in remaining_payload:
                farm_id_value = remaining_payload.pop(candidate_key)
                break
        if farm_id_value is None:
            return self._post_json(path, payload)

        errors: list[ValueError] = []
        attempted_payloads: set[str] = set()
        candidate_keys = preferred_farm_id_keys + tuple(
            key for key in self.FARM_ID_PAYLOAD_CANDIDATES if key not in preferred_farm_id_keys
        )
        for farm_id_key in candidate_keys:
            candidate_payload = {farm_id_key: farm_id_value, **remaining_payload}
            candidate_signature = json.dumps(
                candidate_payload,
                sort_keys=True,
                ensure_ascii=False,
                default=str,
                separators=(",", ":"),
            )
            if candidate_signature in attempted_payloads:
                continue
            attempted_payloads.add(candidate_signature)
            try:
                return self._post_json(path, candidate_payload)
            except ValueError as exc:
                errors.append(exc)

        raise errors[-1]

    def _get_json(
        self,
        base_url: str,
        path: str,
        *,
        query_params: dict[str, str] | None = None,
        token: str | None = None,
    ) -> list[dict[str, Any]]:
        query = f"?{urlencode(query_params)}" if query_params else ""
        url = f"{base_url}{path}{query}"
        headers = {"Authorization": token} if token else {}
        http_request = request.Request(url, headers=headers, method="GET")
        timer = LogTimer()
        logger.info(
            "Calling weather GET API path=%s host=%s query=%s",
            path,
            urlsplit(url).netloc,
            summarize_for_log(query_params or {}),
        )
        try:
            with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
                logger.info(
                    "Weather GET API succeeded path=%s status=%s duration_ms=%.2f response=%s",
                    path,
                    getattr(response, "status", 200),
                    timer.elapsed_ms,
                    summarize_for_log(response_payload),
                )
        except error.HTTPError as exc:
            raw_response = exc.read().decode("utf-8", errors="replace")
            logger.warning(
                "Weather GET API returned HTTP error path=%s status=%s duration_ms=%.2f response=%s",
                path,
                exc.code,
                timer.elapsed_ms,
                summarize_for_log(raw_response),
            )
            raise ValueError(f"Weather GET API {path} returned HTTP {exc.code}: {raw_response}") from exc
        except error.URLError as exc:
            logger.error(
                "Weather GET API is unreachable path=%s duration_ms=%.2f reason=%s",
                path,
                timer.elapsed_ms,
                exc.reason,
            )
            raise RuntimeError(f"Weather GET API {path} is unreachable: {exc.reason}") from exc
        except (TimeoutError, socket.timeout) as exc:
            logger.error(
                "Weather GET API timed out path=%s duration_ms=%.2f",
                path,
                timer.elapsed_ms,
            )
            raise RuntimeError(f"Weather GET API {path} timed out.") from exc

        status = response_payload.get("status")
        if status is not None and int(status) != 200:
            raise ValueError(f"Weather GET API {path} returned status {status}.")
        data = response_payload.get("data")
        if not isinstance(data, list):
            raise ValueError(f"Weather GET API {path} did not return a valid data array.")
        normalized_data = [dict(item) for item in data if isinstance(item, dict)]
        if len(normalized_data) != len(data):
            raise ValueError(f"Weather GET API {path} returned invalid row objects.")
        return normalized_data


class MockWeatherProvider:
    def get_daily_weather(
        self,
        planting_plan: PlantingPlan,
        start_date: date,
        end_date: date,
        *,
        as_of_date: date | None = None,
    ) -> list[dict[str, Any]]:
        weather_data: list[dict[str, Any]] = []
        current_date = start_date
        while current_date <= end_date:
            weather_data.append(
                {
                    "DATE": current_date.strftime("%Y%m%d"),
                    "TEMP": 26,
                },
            )
            current_date += timedelta(days=1)

        return weather_data

    def get_pest_disease_daily_weather(
        self,
        planting_plan: PlantingPlan,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        weather_data: list[dict[str, Any]] = []
        current_date = start_date
        while current_date <= end_date:
            weather_data.append(
                {
                    "DATE": current_date.strftime("%Y%m%d"),
                    "TMAX": 30.0,
                    "RAIN": 0.0,
                    "SUN": 6.0,
                },
            )
            current_date += timedelta(days=1)
        return weather_data

    def get_spray_suitability_weather(
        self,
        planting_plan: PlantingPlan,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        weather_data: list[dict[str, Any]] = []
        current_date = start_date
        while current_date <= end_date:
            weather_data.append(
                {
                    "date": current_date.strftime("%Y%m%d"),
                    "wins": 2.0,
                    "pre": 0.0,
                    "rh": 70.0,
                    "tAvg": 24.0,
                },
            )
            current_date += timedelta(days=1)
        return weather_data

    def get_hourly_weather_72h(
        self,
        planting_plan: PlantingPlan,
        *,
        as_of_datetime: datetime | None = None,
    ) -> list[dict[str, Any]]:
        start_datetime = _floor_to_hour(as_of_datetime or _utcnow())
        weather_data: list[dict[str, Any]] = []
        for offset in range(72):
            current_datetime = start_datetime + timedelta(hours=offset)
            weather_data.append(
                {
                    "datetime": current_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                    "pre": 0.0,
                    "wins": 2.0,
                    "gust": 3.0,
                    "wp": "多云",
                },
            )
        return weather_data

    def get_typhoon_alerts(self, planting_plan: PlantingPlan) -> list[dict[str, Any]]:
        return []


class PlantProtectionPlanContextResolver:
    CULTIVATION_SYSTEM_NORMALIZATION = {
        "双季晚稻": "晚稻",
        "一季晚稻": "晚稻",
    }
    RICE_TYPE_NORMALIZATION = {
        "籼": "籼稻",
        "粳": "粳稻",
    }

    def __init__(
        self,
        code_dict_repository: CodeDictRepository,
        rice_variety_repository: RiceVarietyRepository,
    ) -> None:
        self.code_dict_repository = code_dict_repository
        self.rice_variety_repository = rice_variety_repository

    def resolve(self, planting_plan: PlantingPlan) -> PlantProtectionPlanContext:
        cultivation_system = self._get_code_name(planting_plan.culti_type_code)
        cultivation_pattern = self._get_code_name(planting_plan.planting_method_code)

        rice_variety = self.rice_variety_repository.get(planting_plan.variety_id)
        if rice_variety is None or rice_variety.sub_type_code is None:
            raise ValueError(f"Rice variety {planting_plan.variety_id} is missing subtype code.")

        rice_type = self._get_code_name(rice_variety.sub_type_code)
        cultivation_date = planting_plan.transplant_date or planting_plan.sowing_date
        if cultivation_date is None:
            raise ValueError(f"Planting plan {planting_plan.id} is missing cultivation date.")

        return PlantProtectionPlanContext(
            rice_type=self.RICE_TYPE_NORMALIZATION.get(rice_type, rice_type),
            cultivation_system=self.CULTIVATION_SYSTEM_NORMALIZATION.get(cultivation_system, cultivation_system),
            cultivation_pattern=cultivation_pattern,
            cultivation_date=cultivation_date,
        )

    def _get_code_name(self, code: int) -> str:
        code_dict = self.code_dict_repository.get_by_code(code)
        if code_dict is None:
            raise ValueError(f"Code dict {code} is missing.")
        return code_dict.code_name


class SurveyDateRecommendationService:
    def __init__(
        self,
        planting_plan_repository: PlantingPlanRepository,
        farm_repository: FarmRepository | None,
        rice_variety_repository: RiceVarietyRepository,
        code_dict_repository: CodeDictRepository,
        rice_control_window_level1_repository: RiceControlWindowLevel1Repository | None,
        calendar_item_repository: CalendarItemRepository,
        event_record_repository: EventRecordRepository,
        weather_provider: WeatherProvider,
        diagnosis_client: WeedDiagnosisClient,
        pest_disease_client: PestDiseaseSurveyWindowClient | None = None,
        stage_prediction_snapshot_repository: StagePredictionSnapshotRepository | None = None,
    ) -> None:
        self.planting_plan_repository = planting_plan_repository
        self.farm_repository = farm_repository
        self.rice_variety_repository = rice_variety_repository
        self.code_dict_repository = code_dict_repository
        self.rice_control_window_level1_repository = rice_control_window_level1_repository
        self.calendar_item_repository = calendar_item_repository
        self.event_record_repository = event_record_repository
        self.weather_provider = weather_provider
        self.diagnosis_client = diagnosis_client
        self.pest_disease_client = pest_disease_client or MockPestDiseaseSurveyWindowClient()
        self.stage_prediction_snapshot_repository = stage_prediction_snapshot_repository
        self.context_resolver = PlantProtectionPlanContextResolver(
            code_dict_repository=code_dict_repository,
            rice_variety_repository=rice_variety_repository,
        )

    def recommend_pre_treatment_survey(
        self,
        planting_plan_id: int,
        *,
        check_date: date | None = None,
    ) -> CalendarItem:
        planting_plan = self._get_plan(planting_plan_id)
        context = self.context_resolver.resolve(planting_plan)
        start_date = self._resolve_pre_treatment_weather_start_date(context)
        end_date = start_date + timedelta(days=45)
        weather_data = self.weather_provider.get_daily_weather(planting_plan, start_date, end_date)
        recommendation = self.diagnosis_client.recommend_pre_treatment_survey_date(
            weather_data=weather_data,
            rice_type=context.rice_type,
            cultivation_system=context.cultivation_system,
            cultivation_pattern=context.cultivation_pattern,
            cultivation_date=context.cultivation_date,
        )
        calendar_item = self._upsert_calendar_item(
            planting_plan=planting_plan,
            task_subtype=TASK_SUBTYPE_STEM_LEAF_WEED_PRE_SURVEY,
            title="茎叶除草药前调查",
            description="由 weed_survey_date_diagnosis 推荐的茎叶除草药前调查日期。",
            suggested_start_date=recommendation.recommendation_date,
            generation_condition={
                "algorithmCode": "weed_survey_date_diagnosis",
                "jobKey": SURVEY_DATE_RECOMMENDATION_JOB,
                "checkDate": (check_date or recommendation.recommendation_date).isoformat(),
                "rawResponse": recommendation.raw_response,
            },
            idempotency_scope=f"{TASK_SUBTYPE_STEM_LEAF_WEED_PRE_SURVEY}:{recommendation.recommendation_date.isoformat()}",
        )
        self._record_event(
            planting_plan_id=planting_plan.id,
            event_type=EVENT_TYPE_CALENDAR_ITEM_UPDATED,
            payload={
                "jobKey": SURVEY_DATE_RECOMMENDATION_JOB,
                "calendarItemSubtype": TASK_SUBTYPE_STEM_LEAF_WEED_PRE_SURVEY,
                "calendarItemDate": recommendation.recommendation_date.isoformat(),
                "calendarItemId": calendar_item.id,
            },
            idempotency_key=f"{SURVEY_DATE_RECOMMENDATION_JOB}:{planting_plan.id}:{TASK_SUBTYPE_STEM_LEAF_WEED_PRE_SURVEY}:{recommendation.recommendation_date.isoformat()}",
        )
        return calendar_item

    def diagnose_soil_treatment(
        self,
        planting_plan_id: int,
    ) -> SoilTreatmentDiagnosisResult:
        planting_plan = self._get_plan(planting_plan_id)
        context = self.context_resolver.resolve(planting_plan)
        metadata_payload = planting_plan.metadata_payload or {}
        province = str(metadata_payload.get("province") or "湖南省")
        return self.diagnosis_client.diagnose_soil_treatment(
            province=province,
            cultivation_system=context.cultivation_system,
            cultivation_pattern=context.cultivation_pattern,
            cultivation_date=context.cultivation_date,
        )

    def _resolve_pre_treatment_weather_start_date(self, context: PlantProtectionPlanContext) -> date:
        if context.cultivation_pattern in {"直播", "插秧", "抛秧"}:
            # The upstream weed survey API expects the cultivation date and the previous calendar day.
            return context.cultivation_date - timedelta(days=1)
        return context.cultivation_date

    def recommend_regular_disease_pest_surveys(
        self,
        planting_plan_id: int,
    ) -> list[CalendarItem]:
        planting_plan = self._get_plan(planting_plan_id)
        request_payload = self._resolve_pest_disease_regular_survey_payload(planting_plan)
        if request_payload is None:
            return []

        context = self.context_resolver.resolve(planting_plan)
        recommendation = self.pest_disease_client.init_regular_surveys(
            cultivation_type=context.cultivation_system,
            growth_stage=request_payload["growth_stage"],
            level1_of_year=request_payload["level1_of_year"],
        )
        calendar_items: list[CalendarItem] = []
        active_idempotency_keys: set[str] = set()
        for plan in recommendation.regular_plans:
            idempotency_scope = self._build_regular_disease_pest_survey_idempotency_scope(plan)
            matched_item = self._find_existing_regular_disease_pest_survey_item(
                planting_plan_id=planting_plan.id,
                plan=plan,
            )
            calendar_item = self._upsert_calendar_item(
                planting_plan=planting_plan,
                task_subtype=TASK_SUBTYPE_REGULAR_DISEASE_PEST_SURVEY,
                title="病虫害常规调查",
                description=_build_regular_disease_pest_survey_description(plan),
                suggested_start_date=plan.survey_window[0],
                suggested_end_date=plan.survey_window[1],
                generation_condition={
                    "algorithmCode": "pestDisease.init_regular_survey",
                    "jobKey": SURVEY_DATE_RECOMMENDATION_JOB,
                    "surveyType": "regular_disease_pest",
                    "targets": plan.targets,
                    "excludeReasons": plan.exclude_reasons,
                    "status": plan.status,
                    "message": plan.message,
                    "sprayStage": plan.spray_stage,
                    "surveyMethod": plan.survey_method,
                    "adjusted": plan.adjusted,
                    "rawPlan": plan.raw_plan,
                    "rawResponse": recommendation.raw_response,
                },
                idempotency_scope=idempotency_scope,
                matched_item=matched_item,
                allow_multiple_active=True,
            )
            calendar_items.append(calendar_item)
            active_idempotency_keys.add(calendar_item.idempotency_key)

        self._invalidate_stale_regular_disease_pest_surveys(
            planting_plan.id,
            active_idempotency_keys=active_idempotency_keys,
        )
        self._record_event(
            planting_plan_id=planting_plan.id,
            event_type=EVENT_TYPE_CALENDAR_ITEM_UPDATED,
            payload={
                "jobKey": SURVEY_DATE_RECOMMENDATION_JOB,
                "calendarItems": [
                    {
                        "taskSubtype": item.task_subtype,
                        "suggestedStartDate": item.suggested_start_date.isoformat(),
                        "suggestedEndDate": item.suggested_end_date.isoformat(),
                        "calendarItemId": item.id,
                    }
                    for item in calendar_items
                ],
                "algorithmCode": "pestDisease.init_regular_survey",
            },
            idempotency_key=f"{SURVEY_DATE_RECOMMENDATION_JOB}:{planting_plan.id}:{TASK_SUBTYPE_REGULAR_DISEASE_PEST_SURVEY}:regular-init",
        )
        return calendar_items

    def recommend_post_treatment_surveys(
        self,
        planting_plan_id: int,
        *,
        operation_date: date,
        parent_task_id: int,
        source_execution_id: int,
        source_execution_record_id: int,
    ) -> tuple[CalendarItem, CalendarItem]:
        planting_plan = self._get_plan(planting_plan_id)
        recommendation = self.diagnosis_client.recommend_post_treatment_survey_dates(operation_date=operation_date)
        safety_item = self._upsert_calendar_item(
            planting_plan=planting_plan,
            task_subtype=TASK_SUBTYPE_RICE_SAFETY_SURVEY,
            title="茎叶除草安全性调查",
            description="由 after_treatment_survey_date_diagnosis 推荐的药后安全性调查日期。",
            suggested_start_date=recommendation.rice_safety_survey_date,
            generation_condition={
                "algorithmCode": "after_treatment_survey_date_diagnosis",
                "jobKey": SURVEY_DATE_RECOMMENDATION_JOB,
                "operationDate": operation_date.isoformat(),
                "rawResponse": recommendation.raw_response,
            },
            idempotency_scope=f"{TASK_SUBTYPE_RICE_SAFETY_SURVEY}:{source_execution_record_id}:{recommendation.rice_safety_survey_date.isoformat()}",
            parent_task_id=parent_task_id,
            source_execution_id=source_execution_id,
            source_execution_record_id=source_execution_record_id,
        )
        effect_item = self._upsert_calendar_item(
            planting_plan=planting_plan,
            task_subtype=TASK_SUBTYPE_CONTROL_EFFECT_SURVEY,
            title="茎叶除草防效兼安全性调查",
            description="由 after_treatment_survey_date_diagnosis 推荐的药后防效兼安全性调查日期。",
            suggested_start_date=recommendation.control_effect_survey_date,
            generation_condition={
                "algorithmCode": "after_treatment_survey_date_diagnosis",
                "jobKey": SURVEY_DATE_RECOMMENDATION_JOB,
                "operationDate": operation_date.isoformat(),
                "rawResponse": recommendation.raw_response,
            },
            idempotency_scope=f"{TASK_SUBTYPE_CONTROL_EFFECT_SURVEY}:{source_execution_record_id}:{recommendation.control_effect_survey_date.isoformat()}",
            parent_task_id=parent_task_id,
            source_execution_id=source_execution_id,
            source_execution_record_id=source_execution_record_id,
        )
        self._record_event(
            planting_plan_id=planting_plan.id,
            event_type=EVENT_TYPE_CALENDAR_ITEM_UPDATED,
            payload={
                "jobKey": SURVEY_DATE_RECOMMENDATION_JOB,
                "calendarItems": [
                    {
                        "taskSubtype": TASK_SUBTYPE_RICE_SAFETY_SURVEY,
                        "suggestedDate": recommendation.rice_safety_survey_date.isoformat(),
                    },
                    {
                        "taskSubtype": TASK_SUBTYPE_CONTROL_EFFECT_SURVEY,
                        "suggestedDate": recommendation.control_effect_survey_date.isoformat(),
                    },
                ],
                "sourceExecutionRecordId": source_execution_record_id,
            },
            idempotency_key=f"{SURVEY_DATE_RECOMMENDATION_JOB}:{planting_plan.id}:post-treatment:{source_execution_record_id}",
        )
        return safety_item, effect_item

    def build_pest_disease_daily_update_payload(
        self,
        planting_plan_id: int,
        *,
        as_of_date: date | None = None,
        actual_control_date: date | None = None,
    ) -> dict[str, Any] | None:
        planting_plan = self._get_plan(planting_plan_id)
        request_payload = self._resolve_pest_disease_regular_survey_payload(planting_plan)
        if request_payload is None:
            return None

        effective_as_of_date = as_of_date or date.today()
        regular_plans = self._resolve_pest_disease_daily_update_regular_plans(planting_plan, request_payload)
        if not regular_plans:
            return None

        weather_provider = self._require_pest_disease_weather_provider()
        payload: dict[str, Any] = {
            "cultivation_type": self.context_resolver.resolve(planting_plan).cultivation_system,
            "growth_stage": request_payload["growth_stage"],
            "regular_plans": regular_plans,
            "weather_data": weather_provider.get_pest_disease_daily_weather(
                planting_plan,
                effective_as_of_date - timedelta(days=8),
                effective_as_of_date + timedelta(days=7),
            ),
            "typhoon_data": {
                "alerts": weather_provider.get_typhoon_alerts(planting_plan),
                "hourly_weather_72h": weather_provider.get_hourly_weather_72h(
                    planting_plan,
                    as_of_datetime=datetime.combine(effective_as_of_date, time.min),
                ),
            },
        }
        if actual_control_date is not None:
            payload["actual_control_date"] = actual_control_date.strftime("%Y%m%d")
        return payload

    def run_pest_disease_daily_update(
        self,
        planting_plan_id: int,
        *,
        as_of_date: date | None = None,
        actual_control_date: date | None = None,
    ) -> PestDiseaseDailyUpdateResult | None:
        payload = self.build_pest_disease_daily_update_payload(
            planting_plan_id,
            as_of_date=as_of_date,
            actual_control_date=actual_control_date,
        )
        if payload is None:
            return None
        return self.pest_disease_client.daily_update_surveys(
            cultivation_type=str(payload.get("cultivation_type")) if payload.get("cultivation_type") is not None else None,
            growth_stage=dict(payload["growth_stage"]),
            regular_plans=[dict(item) for item in payload["regular_plans"]],
            weather_data=[dict(item) for item in payload["weather_data"]],
            typhoon_data=dict(payload["typhoon_data"]),
            actual_control_date=actual_control_date,
        )

    def recommend_pest_disease_daily_update_surveys(
        self,
        planting_plan_id: int,
        *,
        as_of_date: date | None = None,
        actual_control_date: date | None = None,
    ) -> list[CalendarItem]:
        planting_plan = self._get_plan(planting_plan_id)
        effective_as_of_date = as_of_date or date.today()
        result = self.run_pest_disease_daily_update(
            planting_plan_id,
            as_of_date=effective_as_of_date,
            actual_control_date=actual_control_date,
        )
        if result is None:
            return []

        if result.status == "new_emergency":
            calendar_item = self._upsert_sudden_disease_pest_survey(
                planting_plan=planting_plan,
                result=result,
                as_of_date=effective_as_of_date,
            )
            self._invalidate_stale_sudden_disease_pest_surveys(
                planting_plan.id,
                active_idempotency_keys={calendar_item.idempotency_key},
            )
            self._record_pest_disease_daily_update_event(
                planting_plan_id=planting_plan.id,
                result=result,
                as_of_date=effective_as_of_date,
                calendar_items=[calendar_item],
            )
            return [calendar_item]

        self._invalidate_stale_sudden_disease_pest_surveys(planting_plan.id, active_idempotency_keys=set())
        if result.status == "merged_into_regular":
            regular_item = self._upsert_merged_regular_disease_pest_survey(
                planting_plan=planting_plan,
                result=result,
                as_of_date=effective_as_of_date,
            )
            calendar_items = [regular_item] if regular_item is not None else []
            self._record_pest_disease_daily_update_event(
                planting_plan_id=planting_plan.id,
                result=result,
                as_of_date=effective_as_of_date,
                calendar_items=calendar_items,
            )
            return calendar_items

        if result.status == "no_new_event":
            self._record_pest_disease_daily_update_event(
                planting_plan_id=planting_plan.id,
                result=result,
                as_of_date=effective_as_of_date,
                calendar_items=[],
            )
            return []

        raise ValueError(f"Unsupported pest disease daily update status: {result.status}.")

    def schedule_recontrol_pre_survey(
        self,
        planting_plan_id: int,
        *,
        suggested_date: date,
        parent_task_id: int,
        source_execution_id: int,
        source_execution_record_id: int,
    ) -> CalendarItem:
        planting_plan = self._get_plan(planting_plan_id)
        return self._upsert_calendar_item(
            planting_plan=planting_plan,
            task_subtype=TASK_SUBTYPE_STEM_LEAF_WEED_RECONTROL_PRE_SURVEY,
            title="补防回流药前调查",
            description="由运行期补防分支回流的药前调查日期。",
            suggested_start_date=suggested_date,
            generation_condition={
                "triggerType": "additional_treatment_diagnosis",
                "jobKey": SURVEY_DATE_RECOMMENDATION_JOB,
            },
            idempotency_scope=f"{TASK_SUBTYPE_STEM_LEAF_WEED_RECONTROL_PRE_SURVEY}:{source_execution_record_id}:{suggested_date.isoformat()}",
            parent_task_id=parent_task_id,
            source_execution_id=source_execution_id,
            source_execution_record_id=source_execution_record_id,
        )

    def schedule_followup_pre_survey(
        self,
        planting_plan_id: int,
        *,
        suggested_date: date,
        parent_task_id: int,
        source_execution_id: int,
        source_execution_record_id: int,
    ) -> CalendarItem:
        planting_plan = self._get_plan(planting_plan_id)
        return self._upsert_calendar_item(
            planting_plan=planting_plan,
            task_subtype=TASK_SUBTYPE_STEM_LEAF_WEED_PRE_SURVEY,
            title="茎叶除草药前复查",
            description="由 weed_treatment_diagnosis 返回的下一次药前调查日期。",
            suggested_start_date=suggested_date,
            generation_condition={
                "triggerType": "weed_treatment_diagnosis",
                "jobKey": SURVEY_DATE_RECOMMENDATION_JOB,
            },
            idempotency_scope=f"{TASK_SUBTYPE_STEM_LEAF_WEED_PRE_SURVEY}:{source_execution_record_id}:{suggested_date.isoformat()}",
            parent_task_id=parent_task_id,
            source_execution_id=source_execution_id,
            source_execution_record_id=source_execution_record_id,
        )

    def schedule_service_effect_evaluation(
        self,
        planting_plan_id: int,
        *,
        suggested_date: date,
        parent_task_id: int,
        source_execution_id: int,
        source_execution_record_id: int,
    ) -> CalendarItem:
        planting_plan = self._get_plan(planting_plan_id)
        return self._upsert_calendar_item(
            planting_plan=planting_plan,
            task_subtype=TASK_SUBTYPE_SERVICE_EFFECT_EVALUATION,
            title="杂草防治服务效果评估",
            description="由补防诊断分支返回的服务效果评估日期。",
            suggested_start_date=suggested_date,
            generation_condition={
                "triggerType": "additional_treatment_diagnosis",
                "jobKey": SURVEY_DATE_RECOMMENDATION_JOB,
            },
            idempotency_scope=f"{TASK_SUBTYPE_SERVICE_EFFECT_EVALUATION}:{source_execution_record_id}:{suggested_date.isoformat()}",
            parent_task_id=parent_task_id,
            source_execution_id=source_execution_id,
            source_execution_record_id=source_execution_record_id,
        )

    def _resolve_pest_disease_regular_survey_payload(
        self,
        planting_plan: PlantingPlan,
    ) -> dict[str, Any] | None:
        metadata_payload = planting_plan.metadata_payload or {}
        pest_disease_payload = (
            metadata_payload.get("pestDisease")
            or metadata_payload.get("pest_disease")
            or metadata_payload.get("pest_disease_survey")
            or {}
        )
        if not isinstance(pest_disease_payload, dict):
            raise ValueError("Planting plan pest disease metadata must be an object.")

        growth_stage = pest_disease_payload.get("growth_stage") or metadata_payload.get("growth_stage")
        if growth_stage is None and self.stage_prediction_snapshot_repository is not None:
            latest_snapshot = self.stage_prediction_snapshot_repository.get_latest_by_plan(planting_plan.id)
            if latest_snapshot is not None:
                growth_stage = extract_pest_disease_growth_stage(latest_snapshot.stage_timeline)
        if growth_stage is None:
            return None
        if not isinstance(growth_stage, dict):
            raise ValueError("Pest disease regular survey metadata requires growth_stage object.")

        required_stage_fields = {"tillering_date", "pokou_date", "heading_date", "maturity_date"}
        missing_stage_fields = sorted(required_stage_fields - set(growth_stage))
        if missing_stage_fields:
            raise ValueError(f"Pest disease growth_stage is missing fields: {missing_stage_fields}.")

        normalized_growth_stage = {
            key: _normalize_iso_date_string(growth_stage[key], key)
            for key in sorted(required_stage_fields)
        }

        return {
            "growth_stage": normalized_growth_stage,
            "level1_of_year": self._resolve_pest_disease_level1_of_year(planting_plan),
        }

    def _resolve_pest_disease_level1_of_year(self, planting_plan: PlantingPlan) -> dict[str, list[str]]:
        if self.farm_repository is None:
            raise RuntimeError("SurveyDateRecommendationService requires FarmRepository for pest disease control window lookup.")
        if self.rice_control_window_level1_repository is None:
            raise RuntimeError(
                "SurveyDateRecommendationService requires RiceControlWindowLevel1Repository for pest disease control window lookup.",
            )
        farm = self.farm_repository.get(planting_plan.farm_id)
        if farm is None:
            raise ValueError(f"Farm {planting_plan.farm_id} does not exist.")

        province = str(farm.province or "").strip()
        city = str(farm.city or "").strip()
        county = str(farm.district_county or "").strip()
        missing_fields = [
            field_name
            for field_name, value in (("province", province), ("city", city), ("district_county", county))
            if not value
        ]
        if missing_fields:
            raise ValueError(
                "Pest disease control window lookup requires Farm region fields: " + ", ".join(missing_fields) + ".",
            )
        data_year = int(planting_plan.year or planting_plan.sowing_date.year)
        control_window = self.rice_control_window_level1_repository.get_by_region_and_year(
            province=province,
            city=city,
            county=county,
            data_year=data_year,
        )
        if control_window is None:
            raise ValueError(
                "Pest disease control window level1 is missing for "
                f"{province}/{city}/{county}/{data_year}.",
            )
        return _normalize_pest_disease_level1_of_year_detail(control_window)

    def _resolve_pest_disease_daily_update_regular_plans(
        self,
        planting_plan: PlantingPlan,
        request_payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        active_items = self.calendar_item_repository.list_active_by_plan_and_subtype(
            planting_plan.id,
            TASK_SUBTYPE_REGULAR_DISEASE_PEST_SURVEY,
        )
        active_items = sorted(
            active_items,
            key=lambda item: (item.suggested_start_date, item.suggested_end_date, int(item.id or 0)),
        )
        raw_plans: list[dict[str, Any]] = []
        for item in active_items:
            generation_condition = dict(item.generation_condition or {})
            raw_plan = generation_condition.get("rawPlan")
            if isinstance(raw_plan, dict):
                raw_plans.append(_normalize_pest_disease_regular_plan(raw_plan))
                continue
            raw_plans.append(
                {
                    "status": str(generation_condition.get("status") or "need_survey"),
                    "survey_window": [
                        item.suggested_start_date.strftime("%Y%m%d"),
                        item.suggested_end_date.strftime("%Y%m%d"),
                    ],
                    "spray_stage": generation_condition.get("sprayStage"),
                    "survey_method": generation_condition.get("surveyMethod"),
                    "targets": list(generation_condition.get("targets") or []),
                    "exclude_reasons": dict(generation_condition.get("excludeReasons") or {}),
                    "msg": str(generation_condition.get("message") or ""),
                },
            )
        if raw_plans:
            return raw_plans

        context = self.context_resolver.resolve(planting_plan)
        init_result = self.pest_disease_client.init_regular_surveys(
            cultivation_type=context.cultivation_system,
            growth_stage=request_payload["growth_stage"],
            level1_of_year=request_payload["level1_of_year"],
        )
        return [_normalize_pest_disease_regular_plan(plan.raw_plan) for plan in init_result.regular_plans]

    def _require_pest_disease_weather_provider(self) -> Any:
        missing_methods = [
            method_name
            for method_name in ("get_pest_disease_daily_weather", "get_hourly_weather_72h", "get_typhoon_alerts")
            if not hasattr(self.weather_provider, method_name)
        ]
        if missing_methods:
            raise RuntimeError(
                "Weather provider is missing pest disease weather methods: " + ", ".join(sorted(missing_methods))
            )
        return self.weather_provider

    def _invalidate_stale_regular_disease_pest_surveys(
        self,
        planting_plan_id: int,
        *,
        active_idempotency_keys: set[str],
    ) -> None:
        active_items = self.calendar_item_repository.list_active_by_plan_and_subtype(
            planting_plan_id,
            TASK_SUBTYPE_REGULAR_DISEASE_PEST_SURVEY,
        )
        for item in active_items:
            if item.idempotency_key in active_idempotency_keys:
                continue
            item.status = CALENDAR_STATUS_INVALIDATED
            item.invalidated_reason = "regular_disease_pest_survey_window_changed"
            item.last_generation_checked_at = _utcnow()

    def _build_regular_disease_pest_survey_idempotency_scope(
        self,
        plan: PestDiseaseRegularSurveyPlan,
    ) -> str:
        identity = _build_regular_disease_pest_survey_identity(
            suggested_start_date=plan.survey_window[0],
            suggested_end_date=plan.survey_window[1],
            spray_stage=plan.spray_stage,
        )
        identity_payload = {
            "suggestedStartDate": identity[1],
            "suggestedEndDate": identity[2],
            "sprayStage": identity[0] or "",
        }
        identity_digest = hashlib.sha1(
            json.dumps(identity_payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
        ).hexdigest()[:12]
        return (
            f"{TASK_SUBTYPE_REGULAR_DISEASE_PEST_SURVEY}:regular:"
            f"{identity[1]}:{identity[2]}:{identity_digest}"
        )

    def _find_existing_regular_disease_pest_survey_item(
        self,
        *,
        planting_plan_id: int,
        plan: PestDiseaseRegularSurveyPlan,
    ) -> CalendarItem | None:
        expected_identity = _build_regular_disease_pest_survey_identity(
            suggested_start_date=plan.survey_window[0],
            suggested_end_date=plan.survey_window[1],
            spray_stage=plan.spray_stage,
        )
        candidates = self.calendar_item_repository.list_by_plan_and_subtype(
            planting_plan_id,
            TASK_SUBTYPE_REGULAR_DISEASE_PEST_SURVEY,
        )
        matched_items = [
            item
            for item in candidates
            if _build_regular_disease_pest_survey_identity(
                suggested_start_date=item.suggested_start_date,
                suggested_end_date=item.suggested_end_date,
                spray_stage=_get_calendar_item_regular_disease_pest_spray_stage(item),
            )
            == expected_identity
        ]
        if not matched_items:
            return None
        matched_items.sort(key=_regular_disease_pest_calendar_item_reuse_priority)
        return matched_items[0]

    def _invalidate_stale_sudden_disease_pest_surveys(
        self,
        planting_plan_id: int,
        *,
        active_idempotency_keys: set[str],
    ) -> None:
        active_items = self.calendar_item_repository.list_active_by_plan_and_subtype(
            planting_plan_id,
            TASK_SUBTYPE_SUDDEN_DISEASE_PEST_SURVEY,
        )
        for item in active_items:
            if item.idempotency_key in active_idempotency_keys:
                continue
            item.status = CALENDAR_STATUS_INVALIDATED
            item.invalidated_reason = "pest_disease_daily_update_resolved"
            item.last_generation_checked_at = _utcnow()

    def _upsert_sudden_disease_pest_survey(
        self,
        *,
        planting_plan: PlantingPlan,
        result: PestDiseaseDailyUpdateResult,
        as_of_date: date,
    ) -> CalendarItem:
        if result.survey_window is None:
            raise ValueError("new_emergency result must provide survey_window.")
        return self._upsert_calendar_item(
            planting_plan=planting_plan,
            task_subtype=TASK_SUBTYPE_SUDDEN_DISEASE_PEST_SURVEY,
            title="突发病虫调查",
            description=_build_sudden_disease_pest_survey_description(result),
            suggested_start_date=result.survey_window[0],
            suggested_end_date=result.survey_window[1],
            generation_condition={
                "algorithmCode": "pestDisease.daily_update_survey",
                "jobKey": SURVEY_DATE_RECOMMENDATION_JOB,
                "surveyType": "sudden_disease_pest",
                "status": result.status,
                "message": result.message,
                "source": result.source,
                "targets": list(result.targets),
                "excludeReasons": dict(result.exclude_reasons),
                "sprayStage": result.spray_stage,
                "checkDate": as_of_date.isoformat(),
                "rawResult": dict(result.raw_result),
                "rawResponse": result.raw_response,
            },
            idempotency_scope=(
                f"{TASK_SUBTYPE_SUDDEN_DISEASE_PEST_SURVEY}:"
                f"{result.survey_window[0].isoformat()}:{result.survey_window[1].isoformat()}"
            ),
            allow_multiple_active=True,
        )

    def _upsert_merged_regular_disease_pest_survey(
        self,
        *,
        planting_plan: PlantingPlan,
        result: PestDiseaseDailyUpdateResult,
        as_of_date: date,
    ) -> CalendarItem | None:
        if result.survey_window is None:
            return None
        matched_item = self._find_active_calendar_item_by_window(
            planting_plan_id=planting_plan.id,
            task_subtype=TASK_SUBTYPE_REGULAR_DISEASE_PEST_SURVEY,
            suggested_start_date=result.survey_window[0],
            suggested_end_date=result.survey_window[1],
        )
        if matched_item is None:
            matched_item = self._upsert_calendar_item(
                planting_plan=planting_plan,
                task_subtype=TASK_SUBTYPE_REGULAR_DISEASE_PEST_SURVEY,
                title="病虫害常规调查",
                description=_build_merged_regular_disease_pest_survey_description(result),
                suggested_start_date=result.survey_window[0],
                suggested_end_date=result.survey_window[1],
                generation_condition={
                    "algorithmCode": "pestDisease.daily_update_survey",
                    "jobKey": SURVEY_DATE_RECOMMENDATION_JOB,
                    "surveyType": "regular_disease_pest",
                    "status": result.status,
                    "message": result.message,
                    "source": result.source,
                    "targets": list(result.targets),
                    "excludeReasons": dict(result.exclude_reasons),
                    "sprayStage": result.spray_stage,
                    "checkDate": as_of_date.isoformat(),
                    "rawResult": dict(result.raw_result),
                    "rawResponse": result.raw_response,
                },
                idempotency_scope=(
                    f"{TASK_SUBTYPE_REGULAR_DISEASE_PEST_SURVEY}:merged:"
                    f"{result.survey_window[0].isoformat()}:{result.survey_window[1].isoformat()}"
                ),
                allow_multiple_active=True,
            )
            return matched_item

        generation_condition = dict(matched_item.generation_condition or {})
        generation_condition.update(
            {
                "dailyUpdateStatus": result.status,
                "dailyUpdateMessage": result.message,
                "dailyUpdateSource": result.source,
                "dailyUpdateCheckDate": as_of_date.isoformat(),
                "dailyUpdateTargets": list(result.targets),
                "dailyUpdateExcludeReasons": dict(result.exclude_reasons),
                "dailyUpdateRawResult": dict(result.raw_result),
                "dailyUpdateRawResponse": result.raw_response,
            },
        )
        matched_item.generation_condition = generation_condition
        matched_item.description = _build_merged_regular_disease_pest_survey_description(result)
        matched_item.status = CALENDAR_STATUS_ACTIVE
        matched_item.invalidated_reason = None
        matched_item.last_generation_checked_at = _utcnow()
        return matched_item

    def _find_active_calendar_item_by_window(
        self,
        *,
        planting_plan_id: int,
        task_subtype: str,
        suggested_start_date: date,
        suggested_end_date: date,
    ) -> CalendarItem | None:
        active_items = self.calendar_item_repository.list_active_by_plan_and_subtype(
            planting_plan_id,
            task_subtype,
        )
        return next(
            (
                item
                for item in active_items
                if item.suggested_start_date == suggested_start_date and item.suggested_end_date == suggested_end_date
            ),
            None,
        )

    def _record_pest_disease_daily_update_event(
        self,
        *,
        planting_plan_id: int,
        result: PestDiseaseDailyUpdateResult,
        as_of_date: date,
        calendar_items: list[CalendarItem],
    ) -> EventRecord:
        return self._record_event(
            planting_plan_id=planting_plan_id,
            event_type=EVENT_TYPE_CALENDAR_ITEM_UPDATED,
            payload={
                "jobKey": SURVEY_DATE_RECOMMENDATION_JOB,
                "algorithmCode": "pestDisease.daily_update_survey",
                "checkDate": as_of_date.isoformat(),
                "status": result.status,
                "message": result.message,
                "source": result.source,
                "calendarItems": [
                    {
                        "taskSubtype": item.task_subtype,
                        "suggestedStartDate": item.suggested_start_date.isoformat(),
                        "suggestedEndDate": item.suggested_end_date.isoformat(),
                        "calendarItemId": item.id,
                    }
                    for item in calendar_items
                ],
            },
            idempotency_key=(
                f"{SURVEY_DATE_RECOMMENDATION_JOB}:{planting_plan_id}:pest-disease-daily-update:"
                f"{as_of_date.isoformat()}:{result.status}"
            ),
        )

    def _get_plan(self, planting_plan_id: int) -> PlantingPlan:
        planting_plan = self.planting_plan_repository.get(planting_plan_id)
        if planting_plan is None:
            raise ValueError(f"Planting plan {planting_plan_id} does not exist.")
        return planting_plan

    def _upsert_calendar_item(
        self,
        *,
        planting_plan: PlantingPlan,
        task_subtype: str,
        title: str,
        description: str,
        suggested_start_date: date,
        suggested_end_date: date | None = None,
        generation_condition: dict[str, Any],
        idempotency_scope: str,
        matched_item: CalendarItem | None = None,
        parent_task_id: int | None = None,
        source_execution_id: int | None = None,
        source_execution_record_id: int | None = None,
        allow_multiple_active: bool = False,
    ) -> CalendarItem:
        suggested_end_date = suggested_end_date or suggested_start_date
        idempotency_key = f"calendar-item:{planting_plan.id}:{idempotency_scope}"
        matched_by_key = self.calendar_item_repository.get_by_idempotency_key(idempotency_key)
        if matched_by_key is not None:
            matched_item = matched_by_key
        existing_items = self.calendar_item_repository.list_active_by_plan_and_subtype(
            planting_plan.id,
            task_subtype,
            parent_task_id=parent_task_id,
            source_execution_record_id=source_execution_record_id,
        )
        for item in existing_items:
            if matched_item is not None and item.id == matched_item.id:
                continue
            if allow_multiple_active and item.idempotency_key == idempotency_key:
                matched_item = item
            elif not allow_multiple_active and (
                item.suggested_start_date == suggested_start_date
                and item.suggested_end_date == suggested_end_date
            ):
                matched_item = item
            elif not allow_multiple_active:
                item.status = CALENDAR_STATUS_INVALIDATED
                item.invalidated_reason = "recommendation_date_changed"
                item.last_generation_checked_at = _utcnow()

        if matched_item is None:
            matched_item = CalendarItem(
                planting_plan_id=planting_plan.id,
                task_category=TASK_CATEGORY_PLANT_PROTECTION,
                task_subtype=task_subtype,
                title=title,
                description=description,
                suggested_start_date=suggested_start_date,
                suggested_end_date=suggested_end_date,
                status=CALENDAR_STATUS_ACTIVE,
                generation_condition=generation_condition,
                idempotency_key=idempotency_key,
                created_by_type="system",
                created_by_id=SURVEY_DATE_RECOMMENDATION_JOB,
                parent_task_id=parent_task_id,
                source_execution_id=source_execution_id,
                source_execution_record_id=source_execution_record_id,
            )
            self.calendar_item_repository.add(matched_item)
        else:
            matched_item.title = title
            matched_item.description = description
            matched_item.suggested_start_date = suggested_start_date
            matched_item.suggested_end_date = suggested_end_date
            matched_item.generation_condition = generation_condition
            matched_item.idempotency_key = idempotency_key
            matched_item.parent_task_id = parent_task_id
            matched_item.source_execution_id = source_execution_id
            matched_item.source_execution_record_id = source_execution_record_id
            if matched_item.status != CALENDAR_STATUS_GENERATED:
                matched_item.status = CALENDAR_STATUS_ACTIVE
                matched_item.invalidated_reason = None

        return matched_item

    def _record_event(
        self,
        *,
        planting_plan_id: int,
        event_type: str,
        payload: dict[str, Any],
        idempotency_key: str,
    ) -> EventRecord:
        existing_event = None
        if hasattr(self.event_record_repository, "get_by_idempotency_key"):
            existing_event = self.event_record_repository.get_by_idempotency_key(idempotency_key)
        if existing_event is not None:
            existing_event.payload = payload
            existing_event.event_type = event_type
            existing_event.processing_status = "processed"
            existing_event.processed_at = _utcnow()
            existing_event.error_message = None
            return existing_event

        event_record = EventRecord(
            planting_plan_id=planting_plan_id,
            event_type=event_type,
            event_category="job",
            event_source="background_job",
            source_system="cropflow",
            payload=payload,
            occurred_at=_utcnow(),
            processing_status="processed",
            processed_at=_utcnow(),
            idempotency_key=idempotency_key,
            created_by_type="system",
            created_by_id=payload.get("jobKey"),
        )
        self.event_record_repository.add(event_record)
        return event_record


class TaskGenerationService:
    def __init__(
        self,
        planting_plan_repository: PlantingPlanRepository,
        event_record_repository: EventRecordRepository,
        plan_orchestrator: EventDispatcher | None = None,
    ) -> None:
        self.planting_plan_repository = planting_plan_repository
        self.event_record_repository = event_record_repository
        self.plan_orchestrator = plan_orchestrator

    def generate_due_tasks(
        self,
        planting_plan_id: int,
        *,
        check_date: date,
    ) -> list[FarmingTask]:
        planting_plan = self.planting_plan_repository.get(planting_plan_id)
        if planting_plan is None:
            raise ValueError(f"Planting plan {planting_plan_id} does not exist.")

        if self.plan_orchestrator is None:
            raise RuntimeError("TaskGenerationService requires PlanOrchestrator to generate due tasks.")

        event_record = self._record_event(
            planting_plan_id=planting_plan_id,
            event_type=EVENT_TYPE_TASK_DUE_CHECK_TRIGGERED,
            payload={
                "jobKey": TASK_DUE_CHECK_JOB,
                "checkDate": check_date.isoformat(),
            },
            idempotency_key=f"{TASK_DUE_CHECK_JOB}:{planting_plan_id}:{check_date.isoformat()}",
        )
        return list(self.plan_orchestrator.handle(event_record).farming_tasks)

    def _record_event(
        self,
        *,
        planting_plan_id: int,
        event_type: str,
        payload: dict[str, Any],
        idempotency_key: str,
    ) -> EventRecord:
        existing_event = None
        if hasattr(self.event_record_repository, "get_by_idempotency_key"):
            existing_event = self.event_record_repository.get_by_idempotency_key(idempotency_key)
        if existing_event is not None:
            return existing_event

        event_record = EventRecord(
            planting_plan_id=planting_plan_id,
            event_type=event_type,
            event_category="job",
            event_source="background_job",
            source_system="cropflow",
            payload=payload,
            occurred_at=_utcnow(),
            processing_status=EVENT_PROCESSING_STATUS_RECEIVED,
            idempotency_key=idempotency_key,
            created_by_type="system",
            created_by_id=payload.get("jobKey"),
        )
        self.event_record_repository.add(event_record)
        if hasattr(self.event_record_repository, "flush"):
            self.event_record_repository.flush()
        return event_record


class WeatherUpdateService:
    def __init__(
        self,
        planting_plan_repository: PlantingPlanRepository,
        event_record_repository: EventRecordRepository,
        weather_provider: WeatherProvider,
        plan_orchestrator: EventDispatcher | None = None,
        weather_snapshot_repository: WeatherSnapshotRepository | None = None,
    ) -> None:
        self.planting_plan_repository = planting_plan_repository
        self.event_record_repository = event_record_repository
        self.weather_provider = weather_provider
        self.plan_orchestrator = plan_orchestrator
        self.weather_snapshot_repository = weather_snapshot_repository

    def generate_weather_updates(
        self,
        planting_plan_id: int,
        *,
        check_date: date,
    ) -> list[EventRecord]:
        planting_plan = self.planting_plan_repository.get(planting_plan_id)
        if planting_plan is None:
            raise ValueError(f"Planting plan {planting_plan_id} does not exist.")

        if self.plan_orchestrator is None:
            raise RuntimeError("WeatherUpdateService requires PlanOrchestrator to generate weather updates.")

        weather_rows = self.weather_provider.get_daily_weather(
            planting_plan,
            check_date,
            check_date,
            as_of_date=check_date,
        )
        created_events: list[EventRecord] = []
        for row in weather_rows:
            weather_date = str(row.get("date") or "").strip()
            data_version = str(row.get("data_version") or "").strip()
            source_type = str(row.get("source_type") or "unknown").strip()
            data_hash = _hash_payload(row)
            if not weather_date:
                raise ValueError("Weather row must include date when generating WeatherUpdated.")
            if not data_version:
                raise ValueError("Weather row must include data_version when generating WeatherUpdated.")
            parsed_weather_date = _parse_stage_or_iso_date(weather_date)
            snapshot_result = self._record_weather_snapshot(
                farm_id=planting_plan.farm_id,
                weather_date=parsed_weather_date,
                source_type=source_type,
                data_version=data_version,
                data_hash=data_hash,
                row=dict(row),
            )
            snapshot = snapshot_result.snapshot if snapshot_result is not None else None
            previous_snapshot = snapshot_result.previous_snapshot if snapshot_result is not None else None
            change_type = snapshot_result.change_type if snapshot_result is not None else "event_only"

            existing_event = self.event_record_repository.get_by_idempotency_key(
                f"{DAILY_WEATHER_CHECK_JOB}:{planting_plan_id}:{weather_date}:{data_version}:{data_hash}",
            )
            if existing_event is not None:
                created_events.append(existing_event)
                continue

            event_record = EventRecord(
                planting_plan_id=planting_plan_id,
                event_type=EVENT_TYPE_WEATHER_UPDATED,
                event_category="job",
                event_source="background_job",
                source_system="cropflow",
                source_record_id=weather_date,
                payload={
                    "jobKey": DAILY_WEATHER_CHECK_JOB,
                    "checkDate": check_date.isoformat(),
                    "weatherDate": weather_date,
                    "dataVersion": data_version,
                    "dataHash": data_hash,
                    "sourceType": source_type,
                    "weatherSnapshotId": snapshot.id if snapshot is not None else None,
                    "previousWeatherSnapshotId": previous_snapshot.id if previous_snapshot is not None else None,
                    "weatherChangeType": change_type,
                    "weather": dict(row),
                },
                occurred_at=_utcnow(),
                processing_status=EVENT_PROCESSING_STATUS_RECEIVED,
                idempotency_key=f"{DAILY_WEATHER_CHECK_JOB}:{planting_plan_id}:{weather_date}:{data_version}:{data_hash}",
                created_by_type="system",
                created_by_id=DAILY_WEATHER_CHECK_JOB,
            )
            self.event_record_repository.add(event_record)
            if hasattr(self.event_record_repository, "flush"):
                self.event_record_repository.flush()
            if snapshot is not None and snapshot.source_event_id is None:
                snapshot.source_event_id = event_record.id
            self.plan_orchestrator.handle(event_record)
            created_events.append(event_record)
        return created_events

    def _record_weather_snapshot(
        self,
        *,
        farm_id: int,
        weather_date: date,
        source_type: str,
        data_version: str,
        data_hash: str,
        row: dict[str, Any],
    ) -> WeatherSnapshotRecordResult | None:
        if self.weather_snapshot_repository is None:
            return None
        active_snapshot = self.weather_snapshot_repository.get_active_by_farm_date_source(
            farm_id=farm_id,
            weather_year=weather_date.year,
            weather_date=weather_date,
            source_type=source_type,
        )
        existing_snapshot = self.weather_snapshot_repository.get_by_identity(
            farm_id=farm_id,
            weather_year=weather_date.year,
            weather_date=weather_date,
            source_type=source_type,
            data_version=data_version,
            data_hash=data_hash,
        )
        if existing_snapshot is not None:
            previous_snapshot = active_snapshot if active_snapshot is not None and active_snapshot.id != existing_snapshot.id else None
            if previous_snapshot is not None:
                existing_snapshot.is_active = True
                existing_snapshot.superseded_at = None
                existing_snapshot.superseded_by_snapshot_id = None
                self.weather_snapshot_repository.flush()
                self.weather_snapshot_repository.supersede_active_for_farm_date_source(
                    farm_id=farm_id,
                    weather_year=weather_date.year,
                    weather_date=weather_date,
                    source_type=source_type,
                    superseded_by_snapshot_id=int(existing_snapshot.id),
                )
                return WeatherSnapshotRecordResult(
                    snapshot=existing_snapshot,
                    previous_snapshot=previous_snapshot,
                    change_type="restored_snapshot",
                )
            return WeatherSnapshotRecordResult(
                snapshot=existing_snapshot,
                previous_snapshot=None,
                change_type="reused_snapshot",
            )
        snapshot = WeatherSnapshot(
            farm_id=farm_id,
            weather_year=weather_date.year,
            weather_date=weather_date,
            source_type=source_type,
            data_version=data_version,
            data_hash=data_hash,
            payload=row,
            is_active=True,
            created_by_type="system",
            created_by_id=DAILY_WEATHER_CHECK_JOB,
        )
        self.weather_snapshot_repository.add(snapshot)
        if hasattr(self.weather_snapshot_repository, "flush"):
            self.weather_snapshot_repository.flush()
        if active_snapshot is not None:
            self.weather_snapshot_repository.supersede_active_for_farm_date_source(
                farm_id=farm_id,
                weather_year=weather_date.year,
                weather_date=weather_date,
                source_type=source_type,
                superseded_by_snapshot_id=int(snapshot.id),
            )
        return WeatherSnapshotRecordResult(
            snapshot=snapshot,
            previous_snapshot=active_snapshot,
            change_type="changed_snapshot" if active_snapshot is not None else "new_snapshot",
        )


def _parse_api_date(raw_value: str) -> date:
    return datetime.strptime(raw_value, "%Y%m%d").date()


def _parse_stage_or_iso_date(raw_value: str) -> date:
    if len(raw_value) == 8 and raw_value.isdigit():
        return datetime.strptime(raw_value, "%Y%m%d").date()
    return date.fromisoformat(raw_value)


def _hash_payload(payload: dict[str, Any]) -> str:
    normalized_payload = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":"))
    return hashlib.sha256(normalized_payload.encode("utf-8")).hexdigest()


def _parse_api_date_range(raw_value: list[str] | None) -> tuple[date, date] | None:
    if not raw_value:
        return None
    return _parse_api_date(raw_value[0]), _parse_api_date(raw_value[1])


def _normalize_pest_disease_regular_plan(raw_plan: dict[str, Any]) -> dict[str, Any]:
    normalized_plan = dict(raw_plan)
    raw_window = normalized_plan.get("survey_window", normalized_plan.get("调查日期"))
    raw_targets = normalized_plan.get("targets", normalized_plan.get("调查对象"))
    raw_exclude_reasons = normalized_plan.get("exclude_reasons", normalized_plan.get("排除原因"))

    if isinstance(raw_window, list):
        normalized_plan["survey_window"] = [str(item) for item in raw_window]
    elif raw_window is not None:
        normalized_plan["survey_window"] = raw_window

    if isinstance(raw_targets, list):
        normalized_plan["targets"] = [str(item) for item in raw_targets]
    elif raw_targets is not None:
        normalized_plan["targets"] = raw_targets

    if isinstance(raw_exclude_reasons, dict):
        normalized_plan["exclude_reasons"] = dict(raw_exclude_reasons)
    elif raw_exclude_reasons is not None:
        normalized_plan["exclude_reasons"] = raw_exclude_reasons

    normalized_plan.pop("调查日期", None)
    normalized_plan.pop("调查对象", None)
    normalized_plan.pop("排除原因", None)
    return normalized_plan


def _parse_pest_disease_regular_plan(raw_plan: dict[str, Any]) -> PestDiseaseRegularSurveyPlan:
    normalized_plan = _normalize_pest_disease_regular_plan(raw_plan)
    raw_window = normalized_plan.get("survey_window")
    if not isinstance(raw_window, list) or len(raw_window) != 2:
        raise ValueError("regular plan did not return a valid survey_window.")
    raw_targets = normalized_plan.get("targets") or []
    if not isinstance(raw_targets, list):
        raise ValueError("regular plan targets must be a list.")
    raw_exclude_reasons = normalized_plan.get("exclude_reasons") or {}
    if not isinstance(raw_exclude_reasons, dict):
        raise ValueError("regular plan exclude_reasons must be an object.")
    return PestDiseaseRegularSurveyPlan(
        survey_window=(_parse_api_date(str(raw_window[0])), _parse_api_date(str(raw_window[1]))),
        targets=[str(item) for item in raw_targets],
        exclude_reasons=raw_exclude_reasons,
        status=str(normalized_plan.get("status") or ""),
        message=str(normalized_plan.get("msg") or ""),
        spray_stage=str(normalized_plan["spray_stage"]) if normalized_plan.get("spray_stage") is not None else None,
        survey_method=str(normalized_plan["survey_method"]) if normalized_plan.get("survey_method") is not None else None,
        adjusted=bool(normalized_plan.get("adjusted")),
        raw_plan=normalized_plan,
    )


def _parse_pest_disease_daily_update_result(
    raw_result: dict[str, Any],
    raw_response: dict[str, Any],
) -> PestDiseaseDailyUpdateResult:
    raw_window = raw_result.get("survey_window")
    survey_window = _parse_api_date_range(raw_window) if isinstance(raw_window, list) and raw_window else None
    raw_targets = raw_result.get("targets") or []
    if not isinstance(raw_targets, list):
        raise ValueError("daily-update-survey targets must be a list.")
    raw_exclude_reasons = raw_result.get("exclude_reasons") or {}
    if not isinstance(raw_exclude_reasons, dict):
        raise ValueError("daily-update-survey exclude_reasons must be an object.")
    return PestDiseaseDailyUpdateResult(
        status=str(raw_result.get("status") or ""),
        message=str(raw_result.get("msg") or ""),
        survey_window=survey_window,
        spray_stage=str(raw_result["spray_stage"]) if raw_result.get("spray_stage") is not None else None,
        targets=[str(item) for item in raw_targets],
        exclude_reasons=raw_exclude_reasons,
        source=str(raw_result["source"]) if raw_result.get("source") is not None else None,
        raw_result=dict(raw_result.get("raw_result") or {}),
        raw_response=raw_response,
    )


def _build_regular_disease_pest_survey_description(plan: PestDiseaseRegularSurveyPlan) -> str:
    targets = "、".join(plan.targets) if plan.targets else "未返回调查对象"
    parts = [f"由 pestDisease init-regular-survey 推荐的病虫害常规调查窗口；调查对象：{targets}。"]
    if plan.spray_stage:
        parts.append(f"打药阶段：{plan.spray_stage}。")
    if plan.survey_method:
        parts.append(f"调查日期来源：{plan.survey_method}。")
    return "".join(parts)


def _build_regular_disease_pest_survey_identity(
    *,
    suggested_start_date: date,
    suggested_end_date: date,
    spray_stage: str | None,
) -> tuple[str | None, str, str]:
    normalized_stage = spray_stage.strip() if isinstance(spray_stage, str) else None
    return (
        normalized_stage or None,
        suggested_start_date.isoformat(),
        suggested_end_date.isoformat(),
    )


def _get_calendar_item_regular_disease_pest_spray_stage(item: CalendarItem) -> str | None:
    generation_condition = item.generation_condition or {}
    if not isinstance(generation_condition, dict):
        return None
    raw_value = generation_condition.get("sprayStage")
    if raw_value is None:
        return None
    return str(raw_value)


def _regular_disease_pest_calendar_item_reuse_priority(item: CalendarItem) -> tuple[int, int]:
    if item.status == CALENDAR_STATUS_GENERATED:
        priority = 0
    elif item.status == CALENDAR_STATUS_ACTIVE:
        priority = 1
    elif item.status == CALENDAR_STATUS_INVALIDATED:
        priority = 2
    else:
        priority = 3
    return priority, item.id or 0


def _build_sudden_disease_pest_survey_description(result: PestDiseaseDailyUpdateResult) -> str:
    targets = "、".join(result.targets) if result.targets else "未返回调查对象"
    parts = [f"由 pestDisease daily-update-survey 推荐的突发病虫调查；调查对象：{targets}。"]
    if result.spray_stage:
        parts.append(f"打药阶段：{result.spray_stage}。")
    if result.message:
        parts.append(f"结果说明：{result.message}。")
    return "".join(parts)


def _build_merged_regular_disease_pest_survey_description(result: PestDiseaseDailyUpdateResult) -> str:
    targets = "、".join(result.targets) if result.targets else "未返回调查对象"
    parts = [f"常规病虫害调查窗口已吸收 daily-update-survey 合并结果；调查对象：{targets}。"]
    if result.spray_stage:
        parts.append(f"打药阶段：{result.spray_stage}。")
    if result.message:
        parts.append(f"结果说明：{result.message}。")
    return "".join(parts)


def _normalize_pest_disease_level1_of_year_detail(
    control_window: RiceControlWindowLevel1,
) -> dict[str, list[str]]:
    raw_detail = control_window.detail or {}
    if not isinstance(raw_detail, dict) or not raw_detail:
        raise ValueError(
            "Pest disease control window level1 detail must be a non-empty object for "
            f"{control_window.province}/{control_window.city}/{control_window.county}/{control_window.data_year}.",
        )
    normalized_level1_of_year: dict[str, list[str]] = {}
    for sequence, window in raw_detail.items():
        if not isinstance(window, list) or len(window) != 2:
            raise ValueError(f"Pest disease level1_of_year[{sequence!r}] must be a two-item MMDD list.")
        normalized_level1_of_year[str(sequence)] = [
            _normalize_month_day_string(window[0], f"level1_of_year[{sequence!r}][0]"),
            _normalize_month_day_string(window[1], f"level1_of_year[{sequence!r}][1]"),
        ]
    return normalized_level1_of_year


def _normalize_iso_date_string(raw_value: Any, field_name: str) -> str:
    if isinstance(raw_value, date):
        return raw_value.isoformat()
    if not isinstance(raw_value, str):
        raise ValueError(f"{field_name} must be a date string.")
    return date.fromisoformat(raw_value).isoformat()


def _normalize_month_day_string(raw_value: Any, field_name: str) -> str:
    value = str(raw_value)
    if len(value) != 4 or not value.isdigit():
        raise ValueError(f"{field_name} must use MMDD format.")
    _parse_month_day(2000, value)
    return value


def _parse_month_day(year: int, raw_value: str) -> date:
    return datetime.strptime(f"{year}{raw_value}", "%Y%m%d").date()


def _build_closed_date_range(start_date: date, end_date: date) -> list[date]:
    dates: list[date] = []
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date)
        current_date += timedelta(days=1)
    return dates


def _shift_years(target_date: date, years: int) -> date:
    shifted_year = target_date.year + years
    max_day = calendar.monthrange(shifted_year, target_date.month)[1]
    return date(shifted_year, target_date.month, min(target_date.day, max_day))


def _normalize_optional_float(raw_value: Any) -> float | None:
    if raw_value is None:
        return None
    return float(raw_value)


def _normalize_required_float(raw_value: Any, field_name: str, api_name: str) -> float:
    normalized = _normalize_optional_float(raw_value)
    if normalized is None:
        raise ValueError(f"{api_name} did not return required numeric field {field_name}.")
    return normalized


def _resolve_observed_avg_temp(
    response_data: list[dict[str, Any]],
    *,
    index: int,
    expected_date: date,
) -> float:
    current_value = _normalize_optional_float(response_data[index].get("temAvg"))
    if current_value is not None:
        return current_value

    previous_value: float | None = None
    for previous_index in range(index - 1, -1, -1):
        previous_value = _normalize_optional_float(response_data[previous_index].get("temAvg"))
        if previous_value is not None:
            break

    next_value: float | None = None
    for next_index in range(index + 1, len(response_data)):
        next_value = _normalize_optional_float(response_data[next_index].get("temAvg"))
        if next_value is not None:
            break

    if previous_value is not None and next_value is not None:
        return round((previous_value + next_value) / 2, 2)
    if previous_value is not None:
        return previous_value
    if next_value is not None:
        return next_value
    raise ValueError(
        "Weather average API did not return a usable observed temAvg value "
        f"for {expected_date.isoformat()}.",
    )


def _split_affected_area_codes(raw_value: Any) -> list[str]:
    if raw_value is None:
        return []
    if isinstance(raw_value, str):
        return [item.strip() for item in raw_value.split(",") if item.strip()]
    return []


def _floor_to_hour(raw_value: datetime) -> datetime:
    return raw_value.replace(minute=0, second=0, microsecond=0)


def _mock_control_plan() -> dict[str, Any]:
    return {
        "prescriptions": [
            {
                "pesticide": "示例农药",
                "formulation": "SC",
                "manufacturer": "示例厂商",
                "recommended_dosage": "100 ~ 150 mL/亩",
            },
        ],
        "water_volume": "4 L/亩",
    }


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
