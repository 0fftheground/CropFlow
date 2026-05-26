from __future__ import annotations

import json
import logging
import socket
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any, Protocol
from urllib import error, request
from urllib.parse import urlsplit

from app.core.logging import LogTimer, summarize_for_log
from app.core.constants import (
    CALENDAR_STATUS_ACTIVE,
    CALENDAR_STATUS_INVALIDATED,
    EVENT_TYPE_CALENDAR_ITEM_UPDATED,
    EVENT_PROCESSING_STATUS_RECEIVED,
    EVENT_TYPE_TASK_DUE_CHECK_TRIGGERED,
    SURVEY_DATE_RECOMMENDATION_JOB,
    TASK_CATEGORY_PLANT_PROTECTION,
    TASK_DUE_CHECK_JOB,
    TASK_SUBTYPE_CONTROL_EFFECT_SURVEY,
    TASK_SUBTYPE_RICE_SAFETY_SURVEY,
    TASK_SUBTYPE_SERVICE_EFFECT_EVALUATION,
    TASK_SUBTYPE_STEM_LEAF_WEED_PRE_SURVEY,
    TASK_SUBTYPE_STEM_LEAF_WEED_RECONTROL_PRE_SURVEY,
)
from app.models import CalendarItem, EventRecord, FarmingTask, PlantingPlan, RiceVariety
from app.repositories import (
    CalendarItemRepository,
    CodeDictRepository,
    EventRecordRepository,
    PlantingPlanRepository,
    RiceVarietyRepository,
)

logger = logging.getLogger(__name__)


class WeatherProvider(Protocol):
    def get_daily_weather(
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
class PlantProtectionPlanContext:
    rice_type: str
    cultivation_system: str
    cultivation_pattern: str
    cultivation_date: date


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
            "weather_data": weather_data,
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
                "weather_data": weather_data,
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


class MockWeatherProvider:
    def get_daily_weather(
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
                    "TEMP": 26,
                },
            )
            current_date += timedelta(days=1)

        return weather_data


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
        rice_variety_repository: RiceVarietyRepository,
        code_dict_repository: CodeDictRepository,
        calendar_item_repository: CalendarItemRepository,
        event_record_repository: EventRecordRepository,
        weather_provider: WeatherProvider,
        diagnosis_client: WeedDiagnosisClient,
    ) -> None:
        self.planting_plan_repository = planting_plan_repository
        self.rice_variety_repository = rice_variety_repository
        self.code_dict_repository = code_dict_repository
        self.calendar_item_repository = calendar_item_repository
        self.event_record_repository = event_record_repository
        self.weather_provider = weather_provider
        self.diagnosis_client = diagnosis_client
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
        if context.cultivation_pattern == "直播":
            # The live algorithm expects direct-seeded plans to include the day before sowing.
            return context.cultivation_date - timedelta(days=1)
        return context.cultivation_date

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
        parent_task_id: int | None = None,
        source_execution_id: int | None = None,
        source_execution_record_id: int | None = None,
    ) -> CalendarItem:
        suggested_end_date = suggested_end_date or suggested_start_date
        existing_items = self.calendar_item_repository.list_active_by_plan_and_subtype(
            planting_plan.id,
            task_subtype,
            parent_task_id=parent_task_id,
            source_execution_record_id=source_execution_record_id,
        )
        matched_item = None
        for item in existing_items:
            if (
                item.suggested_start_date == suggested_start_date
                and item.suggested_end_date == suggested_end_date
            ):
                matched_item = item
            else:
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
                idempotency_key=f"calendar-item:{planting_plan.id}:{idempotency_scope}",
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
            matched_item.status = CALENDAR_STATUS_ACTIVE
            matched_item.parent_task_id = parent_task_id
            matched_item.source_execution_id = source_execution_id
            matched_item.source_execution_record_id = source_execution_record_id
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


def _parse_api_date(raw_value: str) -> date:
    return datetime.strptime(raw_value, "%Y%m%d").date()


def _parse_api_date_range(raw_value: list[str] | None) -> tuple[date, date] | None:
    if not raw_value:
        return None
    return _parse_api_date(raw_value[0]), _parse_api_date(raw_value[1])


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
