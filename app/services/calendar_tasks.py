from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any, Protocol
from urllib import request

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
class PlantProtectionPlanContext:
    rice_type: str
    cultivation_system: str
    cultivation_pattern: str
    cultivation_date: date


class HttpWeedDiagnosisClient:
    def __init__(self, base_url: str, timeout_seconds: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

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
        recommendation_date = _parse_api_date(response["data"]["pre_stem_leaf_herbicide_survey_date"])
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
        data = response["data"]
        return PostTreatmentSurveyRecommendation(
            rice_safety_survey_date=_parse_api_date(data["rice_safety_survey_date"]),
            control_effect_survey_date=_parse_api_date(data["control_effect_survey_date"]),
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
        data = response["data"]
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
        data = response["data"]
        return InjuryMitigationDiagnosisResult(
            need_mitigation=bool(data["need_mitigation"]),
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
        data = response["data"]
        additional_survey_date = data.get("additional_survey_date")
        service_effect_evaluation_date = data.get("service_effect_evaluation_date")
        return AdditionalTreatmentDiagnosisResult(
            need_recontrol=bool(data["need_recontrol"]),
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
        http_request = request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))


class MockWeedDiagnosisClient:
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
        start_date = context.cultivation_date
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
            suggested_date=recommendation.recommendation_date,
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
            suggested_date=recommendation.rice_safety_survey_date,
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
            suggested_date=recommendation.control_effect_survey_date,
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
            suggested_date=suggested_date,
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
            suggested_date=suggested_date,
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
            suggested_date=suggested_date,
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
        suggested_date: date,
        generation_condition: dict[str, Any],
        idempotency_scope: str,
        parent_task_id: int | None = None,
        source_execution_id: int | None = None,
        source_execution_record_id: int | None = None,
    ) -> CalendarItem:
        existing_items = self.calendar_item_repository.list_active_by_plan_and_subtype(
            planting_plan.id,
            task_subtype,
            parent_task_id=parent_task_id,
            source_execution_record_id=source_execution_record_id,
        )
        matched_item = None
        for item in existing_items:
            if item.suggested_start_date == suggested_date and item.suggested_end_date == suggested_date:
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
                suggested_start_date=suggested_date,
                suggested_end_date=suggested_date,
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
