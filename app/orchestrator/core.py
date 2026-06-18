from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from typing import Any, Protocol
from uuid import uuid4

from app.core.constants import (
    CALENDAR_STATUS_GENERATED,
    EVENT_PROCESSING_STATUS_FAILED,
    EVENT_PROCESSING_STATUS_PROCESSED,
    EVENT_PROCESSING_STATUS_PROCESSING,
    EVENT_PROCESSING_STATUS_RECEIVED,
    EVENT_TYPE_ACTUAL_STAGE_RECORDED,
    EVENT_TYPE_CALENDAR_ITEM_REFRESH_FAILED,
    EVENT_TYPE_EXECUTION_COMPLETED,
    EVENT_TYPE_FARMING_TASK_CREATED,
    EVENT_TYPE_PLAN_CREATED,
    EVENT_TYPE_PLAN_KEY_INFO_CHANGED,
    EVENT_TYPE_OPERATION_PLAN_CREATED,
    EVENT_TYPE_REVIEW_REQUEST_CREATED,
    EVENT_TYPE_REVIEW_REQUEST_RESOLVED,
    EVENT_TYPE_STAGE_CHANGED,
    EVENT_TYPE_SURVEY_RESULT_RECORDED,
    EVENT_TYPE_TASK_DUE_CHECK_TRIGGERED,
    EVENT_TYPE_TASK_INTENT_CREATED,
    EVENT_TYPE_WEATHER_UPDATED,
    EXECUTION_MODE_MANUAL,
    FARMING_TASK_STATUS_PENDING,
    OPERATION_PLAN_STATUS_ACTIVE,
    REVIEW_REQUEST_STATUS_OPEN,
    TASK_INTENT_STATUS_REJECTED,
    TASK_INTENT_STATUS_CONVERTED,
    TASK_INTENT_STATUS_PENDING_MORE_INFO,
    SURVEY_DATE_RECOMMENDATION_JOB,
    TASK_CATEGORY_PLANT_PROTECTION,
    TASK_DUE_CHECK_JOB,
    TASK_SUBTYPE_DISEASE_PEST_CONTROL,
    TASK_INTENT_STATUS_NO_ACTION,
    TASK_INTENT_STATUS_PENDING,
    TASK_SUBTYPE_CONTROL_EFFECT_SURVEY,
    TASK_SUBTYPE_INJURY_MITIGATION,
    TASK_SUBTYPE_RICE_SAFETY_SURVEY,
    TASK_SUBTYPE_REGULAR_DISEASE_PEST_SURVEY,
    TASK_SUBTYPE_SERVICE_EFFECT_EVALUATION,
    TASK_SUBTYPE_SERVICE_EFFECT_SURVEY,
    TASK_SUBTYPE_SOIL_SEALING_WEED_CONTROL,
    TASK_SUBTYPE_STEM_LEAF_WEED_CONTROL,
    TASK_SUBTYPE_STEM_LEAF_WEED_PRE_SURVEY,
    TASK_SUBTYPE_STEM_LEAF_WEED_RECONTROL_PRE_SURVEY,
    TASK_SUBTYPE_SUDDEN_DISEASE_PEST_SURVEY,
)
from app.core.logging import summarize_for_log
from app.models import (
    CalendarItem,
    CropStageState,
    CropThermalTimeState,
    EventRecord,
    FarmingTask,
    OperationPlan,
    ReviewRequest,
    StagePredictionSnapshot,
    TaskIntent,
)
from app.repositories import (
    CalendarItemRepository,
    EventRecordRepository,
    FarmingTaskRepository,
    OperationPlanRepository,
    PlantingPlanRepository,
    ReviewRequestRepository,
    TaskIntentRepository,
)
from app.services.calendar_tasks import (
    SoilTreatmentDiagnosisResult,
    PlantProtectionPlanContextResolver,
    SurveyDateRecommendationService,
    WeatherProvider,
    WeedDiagnosisClient,
)
from app.services.pest_disease_control import PestDiseaseControlPlanningService
from app.services.stage_management import StageManagementService

logger = logging.getLogger(__name__)
_WEATHER_WINDOW = timedelta(days=45)


@dataclass(slots=True)
class OrchestratorResult:
    calendar_items: list[CalendarItem] = field(default_factory=list)
    farming_tasks: list[FarmingTask] = field(default_factory=list)
    task_intents: list[TaskIntent] = field(default_factory=list)
    review_requests: list[ReviewRequest] = field(default_factory=list)
    operation_plans: list[OperationPlan] = field(default_factory=list)
    crop_stage_states: list[CropStageState] = field(default_factory=list)
    crop_thermal_time_states: list[CropThermalTimeState] = field(default_factory=list)
    stage_prediction_snapshots: list[StagePredictionSnapshot] = field(default_factory=list)


class EventHandler(Protocol):
    def handle(self, event_record: EventRecord) -> OrchestratorResult: ...


class PlanOrchestrator:
    def __init__(self, handlers: dict[str, EventHandler]) -> None:
        self.handlers = handlers

    def handle(self, event_record: EventRecord) -> OrchestratorResult:
        handler = self.handlers.get(event_record.event_type)
        if handler is None:
            logger.info(
                "No orchestrator handler registered event_id=%s event_type=%s planting_plan_id=%s",
                event_record.id,
                event_record.event_type,
                event_record.planting_plan_id,
            )
            event_record.processing_status = EVENT_PROCESSING_STATUS_PROCESSED
            event_record.processed_at = _utcnow()
            return OrchestratorResult()

        event_record.processing_status = EVENT_PROCESSING_STATUS_PROCESSING
        logger.info(
            "Handling orchestrator event event_id=%s event_type=%s planting_plan_id=%s handler=%s payload=%s",
            event_record.id,
            event_record.event_type,
            event_record.planting_plan_id,
            handler.__class__.__name__,
            summarize_for_log(event_record.payload),
        )
        try:
            result = handler.handle(event_record)
        except Exception as exc:
            event_record.processing_status = EVENT_PROCESSING_STATUS_FAILED
            event_record.processed_at = _utcnow()
            event_record.error_message = str(exc)
            logger.exception(
                "Orchestrator event failed event_id=%s event_type=%s planting_plan_id=%s handler=%s",
                event_record.id,
                event_record.event_type,
                event_record.planting_plan_id,
                handler.__class__.__name__,
            )
            raise

        event_record.processing_status = EVENT_PROCESSING_STATUS_PROCESSED
        event_record.processed_at = _utcnow()
        event_record.error_message = None
        logger.info(
            "Orchestrator event handled event_id=%s event_type=%s planting_plan_id=%s handler=%s results=%s",
            event_record.id,
            event_record.event_type,
            event_record.planting_plan_id,
            handler.__class__.__name__,
            summarize_for_log(_summarize_orchestrator_result(result)),
        )
        return result


class PlanCalendarRefreshHandler:
    def __init__(
        self,
        survey_date_recommendation_service: SurveyDateRecommendationService,
        event_record_repository: EventRecordRepository,
        task_intent_repository: TaskIntentRepository,
        review_request_repository: ReviewRequestRepository,
        task_due_check_handler: TaskDueCheckTriggeredHandler | None = None,
    ) -> None:
        self.survey_date_recommendation_service = survey_date_recommendation_service
        self.event_record_repository = event_record_repository
        self.task_intent_repository = task_intent_repository
        self.review_request_repository = review_request_repository
        self.task_due_check_handler = task_due_check_handler

    def handle(self, event_record: EventRecord) -> OrchestratorResult:
        if event_record.planting_plan_id is None:
            return OrchestratorResult()
        if (
            event_record.event_type == EVENT_TYPE_WEATHER_UPDATED
            and _get_payload_value(event_record.payload, "sourceType", "source_type", required=False) == "forecast"
        ):
            return OrchestratorResult()

        calendar_items: list[CalendarItem] = []
        farming_tasks: list[FarmingTask] = []
        task_intents: list[TaskIntent] = []
        review_requests: list[ReviewRequest] = []

        try:
            soil_diagnosis = self.survey_date_recommendation_service.diagnose_soil_treatment(
                event_record.planting_plan_id,
            )
            task_intent, review_request = self._upsert_soil_treatment_review(
                event_record=event_record,
                diagnosis=soil_diagnosis,
            )
            task_intents.append(task_intent)
            if review_request is not None:
                review_requests.append(review_request)
        except Exception as exc:
            self._record_calendar_refresh_failure(
                event_record.planting_plan_id,
                TASK_SUBTYPE_SOIL_SEALING_WEED_CONTROL,
                exc,
            )
            logger.warning(
                "Failed to refresh soil-treatment recommendation for planting plan %s.",
                event_record.planting_plan_id,
                exc_info=True,
            )

        try:
            calendar_items.append(
                self.survey_date_recommendation_service.recommend_pre_treatment_survey(
                    event_record.planting_plan_id,
                ),
            )
        except Exception as exc:
            self._record_calendar_refresh_failure(
                event_record.planting_plan_id,
                TASK_SUBTYPE_STEM_LEAF_WEED_PRE_SURVEY,
                exc,
            )
            logger.warning(
                "Failed to refresh pre-treatment survey recommendation for planting plan %s.",
                event_record.planting_plan_id,
                exc_info=True,
            )
        try:
            calendar_items.extend(
                self.survey_date_recommendation_service.recommend_regular_disease_pest_surveys(
                    event_record.planting_plan_id,
                ),
            )
        except Exception as exc:
            self._record_calendar_refresh_failure(
                event_record.planting_plan_id,
                TASK_SUBTYPE_REGULAR_DISEASE_PEST_SURVEY,
                exc,
            )
            logger.warning(
                "Failed to refresh regular pest disease survey recommendations for planting plan %s.",
                event_record.planting_plan_id,
                exc_info=True,
            )
        try:
            daily_update_items = self.survey_date_recommendation_service.recommend_pest_disease_daily_update_surveys(
                event_record.planting_plan_id,
                as_of_date=(
                    _parse_payload_date(event_record.payload, "weatherDate")
                    if event_record.event_type == EVENT_TYPE_WEATHER_UPDATED
                    else None
                ),
            )
            calendar_items.extend(daily_update_items)
        except Exception as exc:
            self._record_calendar_refresh_failure(
                event_record.planting_plan_id,
                TASK_SUBTYPE_SUDDEN_DISEASE_PEST_SURVEY,
                exc,
            )
            logger.warning(
                "Failed to refresh pest disease daily update survey recommendations for planting plan %s.",
                event_record.planting_plan_id,
                exc_info=True,
            )
        if event_record.event_type == EVENT_TYPE_STAGE_CHANGED:
            try:
                farming_tasks.extend(self._run_immediate_due_task_check(event_record))
            except Exception:
                logger.warning(
                    "Failed to run immediate due-task check after stage change for planting plan %s.",
                    event_record.planting_plan_id,
                    exc_info=True,
                )
        return OrchestratorResult(
            calendar_items=calendar_items,
            farming_tasks=farming_tasks,
            task_intents=task_intents,
            review_requests=review_requests,
        )

    def _run_immediate_due_task_check(self, event_record: EventRecord) -> list[FarmingTask]:
        if event_record.planting_plan_id is None or self.task_due_check_handler is None:
            return []
        planting_plan = self.survey_date_recommendation_service.planting_plan_repository.get(
            event_record.planting_plan_id,
        )
        if planting_plan is None or planting_plan.status != "active":
            return []
        check_date = event_record.occurred_at.date() if event_record.occurred_at is not None else _utcnow().date()
        due_check_event = self._record_immediate_due_check_event(
            planting_plan_id=event_record.planting_plan_id,
            source_event=event_record,
            check_date=check_date,
        )
        due_check_event.processing_status = EVENT_PROCESSING_STATUS_PROCESSING
        try:
            result = self.task_due_check_handler.handle(due_check_event)
        except Exception as exc:
            due_check_event.processing_status = EVENT_PROCESSING_STATUS_FAILED
            due_check_event.processed_at = _utcnow()
            due_check_event.error_message = str(exc)
            raise
        due_check_event.processing_status = EVENT_PROCESSING_STATUS_PROCESSED
        due_check_event.processed_at = _utcnow()
        due_check_event.error_message = None
        return list(result.farming_tasks)

    def _record_immediate_due_check_event(
        self,
        *,
        planting_plan_id: int,
        source_event: EventRecord,
        check_date: date,
    ) -> EventRecord:
        idempotency_key = (
            f"{TASK_DUE_CHECK_JOB}:{planting_plan_id}:{check_date.isoformat()}:"
            f"source-event:{source_event.id}"
        )
        payload = {
            "jobKey": TASK_DUE_CHECK_JOB,
            "checkDate": check_date.isoformat(),
            "sourceEventId": source_event.id,
            "sourceEventType": source_event.event_type,
            "triggerMode": "stage_change_immediate",
        }
        existing_event = None
        if hasattr(self.event_record_repository, "get_by_idempotency_key"):
            existing_event = self.event_record_repository.get_by_idempotency_key(idempotency_key)
        if existing_event is not None:
            existing_event.payload = payload
            existing_event.processing_status = EVENT_PROCESSING_STATUS_RECEIVED
            existing_event.processed_at = None
            existing_event.error_message = None
            return existing_event

        due_check_event = EventRecord(
            planting_plan_id=planting_plan_id,
            event_type=EVENT_TYPE_TASK_DUE_CHECK_TRIGGERED,
            event_category="job",
            event_source="orchestrator",
            source_system="cropflow",
            payload=payload,
            occurred_at=_utcnow(),
            processing_status=EVENT_PROCESSING_STATUS_RECEIVED,
            idempotency_key=idempotency_key,
            created_by_type="system",
            created_by_id="PlanCalendarRefreshHandler",
        )
        self.event_record_repository.add(due_check_event)
        return due_check_event

    def _upsert_soil_treatment_review(
        self,
        *,
        event_record: EventRecord,
        diagnosis: SoilTreatmentDiagnosisResult,
    ) -> tuple[TaskIntent, ReviewRequest | None]:
        planting_plan_id = int(event_record.planting_plan_id)
        idempotency_key = (
            f"task-intent:soil-treatment:{planting_plan_id}:"
            f"{diagnosis.recommended_date[0].isoformat()}:{diagnosis.recommended_date[1].isoformat()}"
        )
        existing_task_intent = None
        if hasattr(self.task_intent_repository, "get_by_idempotency_key"):
            existing_task_intent = self.task_intent_repository.get_by_idempotency_key(idempotency_key)
        if existing_task_intent is None:
            existing_task_intent = next(
                (
                    item
                    for item in self.task_intent_repository.list_current_by_plan(planting_plan_id)
                    if item.task_subtype == TASK_SUBTYPE_SOIL_SEALING_WEED_CONTROL
                ),
                None,
            )
        trigger_summary = "soil_treatment_diagnosis recommended a soil-sealing treatment window."
        rule_result = {
            "algorithmCode": "soil_treatment_diagnosis",
            "branchType": "soil_treatment",
            "proposedTask": {
                "title": "土壤封闭除草",
                "recommendedControlDate": _format_date_range(diagnosis.recommended_date),
                "operationAction": diagnosis.farming_operation,
            },
            "proposedPlan": {
                "controlPlan": diagnosis.control_plan,
                "operationAction": diagnosis.farming_operation,
            },
            "parentTaskId": None,
            "sourceExecutionId": None,
            "sourceExecutionRecordId": None,
            "inputExecutionRecordIds": [],
            "rawResponse": diagnosis.raw_response,
        }
        if existing_task_intent is not None and existing_task_intent.status == TASK_INTENT_STATUS_CONVERTED:
            return existing_task_intent, None
        if existing_task_intent is None:
            task_intent = TaskIntent(
                planting_plan_id=planting_plan_id,
                task_category=TASK_CATEGORY_PLANT_PROTECTION,
                task_subtype=TASK_SUBTYPE_SOIL_SEALING_WEED_CONTROL,
                status=TASK_INTENT_STATUS_PENDING,
                trigger_type=event_record.event_type,
                trigger_summary=trigger_summary,
                rule_result=rule_result,
                suggested_action="建议执行土壤封闭除草",
                source_event_id=event_record.id,
                idempotency_key=idempotency_key,
                created_by_type="system",
                created_by_id="PlanCalendarRefreshHandler",
            )
            self.task_intent_repository.add(task_intent)
            self.task_intent_repository.flush()
            self._record_soil_followup_event(EVENT_TYPE_TASK_INTENT_CREATED, task_intent, event_record)
        else:
            task_intent = existing_task_intent
            task_intent.trigger_type = event_record.event_type
            task_intent.trigger_summary = trigger_summary
            task_intent.rule_result = rule_result
            task_intent.suggested_action = "建议执行土壤封闭除草"
            task_intent.source_event_id = event_record.id
            task_intent.idempotency_key = idempotency_key

        existing_review_request = next(
            (
                item
                for item in self.review_request_repository.list_current_by_plan(planting_plan_id)
                if item.source_entity_type in {"task_intent", "cf_task_intent"}
                and item.source_entity_id == task_intent.id
            ),
            None,
        )
        review_idempotency_key = f"review-request:task-intent:{task_intent.id}:soil_treatment_recommendation"
        if existing_review_request is None:
            review_request = ReviewRequest(
                planting_plan_id=planting_plan_id,
                review_type="soil_treatment_recommendation",
                status=REVIEW_REQUEST_STATUS_OPEN,
                source_entity_type="task_intent",
                source_entity_id=task_intent.id,
                title="土壤封闭建议待审核",
                description="计划初始化后生成了土壤封闭建议，需审核后再生成正式任务。",
                decision_payload={
                    "contextRefs": {
                        "taskIntentId": task_intent.id,
                        "parentTaskId": None,
                        "sourceExecutionId": None,
                        "sourceExecutionRecordId": None,
                    },
                },
                idempotency_key=review_idempotency_key,
                created_by_type="system",
                created_by_id="PlanCalendarRefreshHandler",
            )
            self.review_request_repository.add(review_request)
            self.review_request_repository.flush()
            self._record_soil_followup_event(EVENT_TYPE_REVIEW_REQUEST_CREATED, review_request, event_record)
        else:
            review_request = existing_review_request
            review_request.review_type = "soil_treatment_recommendation"
            review_request.status = REVIEW_REQUEST_STATUS_OPEN
            review_request.source_entity_type = "task_intent"
            review_request.source_entity_id = task_intent.id
            review_request.title = "土壤封闭建议待审核"
            review_request.description = "计划初始化后生成了土壤封闭建议，需审核后再生成正式任务。"
            review_request.decision = None
            review_request.resolved_by = None
            review_request.resolved_at = None
            review_request.decision_payload = {
                "contextRefs": {
                    "taskIntentId": task_intent.id,
                    "parentTaskId": None,
                    "sourceExecutionId": None,
                    "sourceExecutionRecordId": None,
                },
            }
            review_request.idempotency_key = review_idempotency_key

        self._close_stale_soil_reviews(planting_plan_id, task_intent.id, review_request.id)
        return task_intent, review_request

    def _close_stale_soil_reviews(
        self,
        planting_plan_id: int,
        active_task_intent_id: int,
        active_review_request_id: int,
    ) -> None:
        for item in self.task_intent_repository.list_current_by_plan(planting_plan_id):
            if item.id == active_task_intent_id or item.task_subtype != TASK_SUBTYPE_SOIL_SEALING_WEED_CONTROL:
                continue
            item.status = TASK_INTENT_STATUS_REJECTED
            item.no_action_reason = "Superseded by a newer soil treatment recommendation."
        for item in self.review_request_repository.list_current_by_plan(planting_plan_id):
            if item.id == active_review_request_id:
                continue
            if item.review_type != "soil_treatment_recommendation":
                continue
            item.status = "cancelled"
            item.decision = None

    def _record_soil_followup_event(
        self,
        event_type: str,
        entity: TaskIntent | ReviewRequest,
        event_record: EventRecord,
    ) -> None:
        self.event_record_repository.add(
            EventRecord(
                planting_plan_id=event_record.planting_plan_id,
                event_type=event_type,
                event_category="plan",
                event_source="orchestrator",
                source_system="cropflow",
                source_record_id=str(entity.id),
                payload={
                    "branchType": "soil_treatment",
                    "entityType": entity.__tablename__,
                    "entityId": entity.id,
                    "sourceEventId": event_record.id,
                },
                occurred_at=_utcnow(),
                processing_status=EVENT_PROCESSING_STATUS_PROCESSED,
                processed_at=_utcnow(),
                idempotency_key=f"{event_type}:{entity.__tablename__}:{entity.id}",
                created_by_type="system",
                created_by_id="PlanCalendarRefreshHandler",
            ),
        )

    def _record_calendar_refresh_failure(
        self,
        planting_plan_id: int,
        task_subtype: str,
        exc: Exception,
    ) -> EventRecord:
        now = _utcnow()
        event_record = EventRecord(
            planting_plan_id=planting_plan_id,
            event_type=EVENT_TYPE_CALENDAR_ITEM_REFRESH_FAILED,
            event_category="job",
            event_source="orchestrator",
            source_system="cropflow",
            payload={
                "jobKey": SURVEY_DATE_RECOMMENDATION_JOB,
                "calendarItemSubtype": task_subtype,
                "error": str(exc),
            },
            occurred_at=now,
            processing_status=EVENT_PROCESSING_STATUS_FAILED,
            processed_at=now,
            idempotency_key=(
                f"{SURVEY_DATE_RECOMMENDATION_JOB}:{planting_plan_id}:{task_subtype}:failed:{uuid4()}"
            ),
            error_message=str(exc),
            created_by_type="system",
            created_by_id=SURVEY_DATE_RECOMMENDATION_JOB,
        )
        self.event_record_repository.add(event_record)
        return event_record


class StageRefreshHandler:
    def __init__(
        self,
        stage_management_service: StageManagementService,
        event_record_repository: EventRecordRepository,
    ) -> None:
        self.stage_management_service = stage_management_service
        self.event_record_repository = event_record_repository

    def handle(self, event_record: EventRecord) -> OrchestratorResult:
        if event_record.planting_plan_id is None:
            return OrchestratorResult()

        if event_record.event_type == EVENT_TYPE_PLAN_CREATED:
            prediction_source = "initial"
            refresh_result = self.stage_management_service.refresh_prediction(
                event_record.planting_plan_id,
                prediction_source=prediction_source,
                source_event_id=event_record.id,
            )
        elif event_record.event_type == EVENT_TYPE_PLAN_KEY_INFO_CHANGED:
            prediction_source = "plan_change"
            refresh_result = self.stage_management_service.refresh_prediction(
                event_record.planting_plan_id,
                prediction_source=prediction_source,
                source_event_id=event_record.id,
            )
        elif event_record.event_type == EVENT_TYPE_WEATHER_UPDATED:
            refresh_result = self.stage_management_service.refresh_for_weather_update(
                event_record.planting_plan_id,
                source_event_id=event_record.id,
                as_of_date=_parse_payload_date(event_record.payload, "weatherDate"),
                source_event_payload=dict(event_record.payload or {}),
            )
        elif event_record.event_type == EVENT_TYPE_ACTUAL_STAGE_RECORDED:
            raw_stage_dates = _parse_stage_dates_payload(event_record.payload)
            if raw_stage_dates:
                actual_result = self.stage_management_service.apply_actual_stage_records(
                    event_record.planting_plan_id,
                    stage_dates=raw_stage_dates,
                    source_event_id=event_record.id,
                )
            else:
                actual_result = self.stage_management_service.apply_actual_stage_recorded(
                    event_record.planting_plan_id,
                    stage_code=str(_get_payload_value(event_record.payload, "stageCode", "stage_code")),
                    stage_name=_get_payload_value(event_record.payload, "stageName", "stage_name", required=False),
                    effective_date=_parse_payload_date(event_record.payload, "effectiveDate"),
                    source_event_id=event_record.id,
                )
            self._record_stage_changed_event(
                event_record=event_record,
                previous_stage_code=actual_result.previous_stage_code,
                current_stage_code=actual_result.crop_stage_state.current_stage_code,
                effective_date=actual_result.crop_stage_state.effective_date,
                stage_changed=actual_result.stage_changed,
                source_snapshot_id=actual_result.snapshot.id,
            )
            return OrchestratorResult(
                crop_stage_states=[actual_result.crop_stage_state],
                crop_thermal_time_states=[actual_result.crop_thermal_time_state],
                stage_prediction_snapshots=[actual_result.snapshot],
            )
        else:
            refresh_result = self.stage_management_service.refresh_prediction(
                event_record.planting_plan_id,
                prediction_source="runtime_refresh",
                source_event_id=event_record.id,
            )
        self._record_stage_changed_event(
            event_record=event_record,
            previous_stage_code=refresh_result.previous_stage_code,
            current_stage_code=refresh_result.crop_stage_state.current_stage_code,
            effective_date=refresh_result.crop_stage_state.effective_date,
            stage_changed=(
                refresh_result.stage_changed
                and (
                    event_record.event_type != EVENT_TYPE_WEATHER_UPDATED
                    or _get_payload_value(event_record.payload, "sourceType", "source_type", required=False) != "forecast"
                )
            ),
            source_snapshot_id=refresh_result.snapshot.id,
        )
        return OrchestratorResult(
            crop_stage_states=[refresh_result.crop_stage_state],
            crop_thermal_time_states=[refresh_result.crop_thermal_time_state],
            stage_prediction_snapshots=[refresh_result.snapshot],
        )

    def _record_stage_changed_event(
        self,
        *,
        event_record: EventRecord,
        previous_stage_code: str | None,
        current_stage_code: str,
        effective_date: date,
        stage_changed: bool,
        source_snapshot_id: int | None = None,
    ) -> EventRecord | None:
        if not stage_changed or event_record.planting_plan_id is None:
            return None
        idempotency_key = (
            f"{EVENT_TYPE_STAGE_CHANGED}:{event_record.planting_plan_id}:"
            f"{previous_stage_code}:{current_stage_code}:{effective_date.isoformat()}:source:{event_record.id}"
        )
        existing_event = self.event_record_repository.get_by_idempotency_key(idempotency_key)
        if existing_event is not None:
            return existing_event
        stage_changed_event = EventRecord(
            planting_plan_id=event_record.planting_plan_id,
            event_type=EVENT_TYPE_STAGE_CHANGED,
            event_category="stage",
            event_source="orchestrator",
            source_system="cropflow",
            source_record_id=str(source_snapshot_id or event_record.id),
            payload={
                "previousStageCode": previous_stage_code,
                "currentStageCode": current_stage_code,
                "effectiveDate": effective_date.isoformat(),
                "sourceEventId": event_record.id,
                "sourceEventType": event_record.event_type,
                "sourceSnapshotId": source_snapshot_id,
            },
            occurred_at=_utcnow(),
            processing_status=EVENT_PROCESSING_STATUS_PROCESSED,
            processed_at=_utcnow(),
            idempotency_key=idempotency_key,
            created_by_type="system",
            created_by_id="StageRefreshHandler",
        )
        self.event_record_repository.add(stage_changed_event)
        return stage_changed_event


class CompositeHandler:
    def __init__(self, *handlers: EventHandler) -> None:
        self.handlers = handlers

    def handle(self, event_record: EventRecord) -> OrchestratorResult:
        result = OrchestratorResult()
        for handler in self.handlers:
            result = _merge_orchestrator_results(result, handler.handle(event_record))
        return result


class TaskDueCheckTriggeredHandler:
    def __init__(
        self,
        planting_plan_repository: PlantingPlanRepository,
        calendar_item_repository: CalendarItemRepository,
        farming_task_repository: FarmingTaskRepository,
        event_record_repository: EventRecordRepository,
    ) -> None:
        self.planting_plan_repository = planting_plan_repository
        self.calendar_item_repository = calendar_item_repository
        self.farming_task_repository = farming_task_repository
        self.event_record_repository = event_record_repository

    def handle(self, event_record: EventRecord) -> OrchestratorResult:
        if event_record.planting_plan_id is None:
            return OrchestratorResult()
        check_date = _parse_payload_date(event_record.payload, "checkDate")
        planting_plan = self.planting_plan_repository.get(event_record.planting_plan_id)
        if planting_plan is None:
            raise ValueError(f"Planting plan {event_record.planting_plan_id} does not exist.")

        due_items = self.calendar_item_repository.list_due_for_generation(
            event_record.planting_plan_id,
            check_date=check_date,
            window_days=planting_plan.task_generation_window_days,
        )
        generated_tasks: list[FarmingTask] = []
        for calendar_item in due_items:
            task = FarmingTask(
                planting_plan_id=event_record.planting_plan_id,
                calendar_item_id=calendar_item.id,
                task_category=calendar_item.task_category,
                task_subtype=calendar_item.task_subtype,
                title=calendar_item.title,
                description=calendar_item.description,
                target_stage_code=calendar_item.stage_code,
                planned_start_at=datetime.combine(calendar_item.suggested_start_date, time.min),
                planned_end_at=datetime.combine(calendar_item.suggested_end_date, time.max),
                status=FARMING_TASK_STATUS_PENDING,
                execution_mode=EXECUTION_MODE_MANUAL,
                generation_reason=f"calendar_item:{calendar_item.id}:window_reached",
                parent_task_id=calendar_item.parent_task_id,
                source_execution_id=calendar_item.source_execution_id,
                source_execution_record_id=calendar_item.source_execution_record_id,
                idempotency_key=f"farming-task:calendar-item:{calendar_item.id}",
                created_by_type="system",
                created_by_id="TaskDueCheckTriggeredHandler",
            )
            self.farming_task_repository.add(task)
            self.farming_task_repository.flush()

            calendar_item.generated_task_id = task.id
            calendar_item.status = CALENDAR_STATUS_GENERATED
            calendar_item.last_generation_checked_at = _utcnow()

            self._record_event(
                planting_plan_id=event_record.planting_plan_id,
                event_type=EVENT_TYPE_FARMING_TASK_CREATED,
                payload={
                    "jobKey": TASK_DUE_CHECK_JOB,
                    "calendarItemId": calendar_item.id,
                    "taskSubtype": calendar_item.task_subtype,
                    "farmingTaskId": task.id,
                    "sourceEventId": event_record.id,
                },
                idempotency_key=f"{TASK_DUE_CHECK_JOB}:{event_record.planting_plan_id}:calendar-item:{calendar_item.id}",
            )
            generated_tasks.append(task)

        return OrchestratorResult(farming_tasks=generated_tasks)

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
            event_source="orchestrator",
            source_system="cropflow",
            payload=payload,
            occurred_at=_utcnow(),
            processing_status=EVENT_PROCESSING_STATUS_PROCESSED,
            processed_at=_utcnow(),
            idempotency_key=idempotency_key,
            created_by_type="system",
            created_by_id=payload.get("jobKey"),
        )
        self.event_record_repository.add(event_record)
        return event_record


class SurveyResultRecordedHandler:
    def __init__(
        self,
        planting_plan_repository: PlantingPlanRepository,
        farming_task_repository: FarmingTaskRepository,
        event_record_repository: EventRecordRepository,
        task_intent_repository: TaskIntentRepository,
        review_request_repository: ReviewRequestRepository,
        survey_date_recommendation_service: SurveyDateRecommendationService,
        weather_provider: WeatherProvider,
        diagnosis_client: WeedDiagnosisClient,
        context_resolver: PlantProtectionPlanContextResolver,
        pest_disease_control_planning_service: PestDiseaseControlPlanningService,
    ) -> None:
        self.planting_plan_repository = planting_plan_repository
        self.farming_task_repository = farming_task_repository
        self.event_record_repository = event_record_repository
        self.task_intent_repository = task_intent_repository
        self.review_request_repository = review_request_repository
        self.survey_date_recommendation_service = survey_date_recommendation_service
        self.weather_provider = weather_provider
        self.diagnosis_client = diagnosis_client
        self.context_resolver = context_resolver
        self.pest_disease_control_planning_service = pest_disease_control_planning_service

    def handle(self, event_record: EventRecord) -> OrchestratorResult:
        event = _SurveyResultRecorded.from_event_record(event_record)
        farming_task = self.farming_task_repository.get(event.task_id)
        if farming_task is None:
            raise LookupError(f"Farming task {event.task_id} does not exist.")

        if event.task_subtype in {TASK_SUBTYPE_STEM_LEAF_WEED_PRE_SURVEY, TASK_SUBTYPE_STEM_LEAF_WEED_RECONTROL_PRE_SURVEY}:
            return self._handle_pre_treatment_survey(event, farming_task, event_record)
        if event.task_subtype == TASK_SUBTYPE_RICE_SAFETY_SURVEY:
            return self._handle_rice_safety_survey(event, event_record)
        if event.task_subtype == TASK_SUBTYPE_CONTROL_EFFECT_SURVEY:
            return self._handle_control_effect_survey(event, farming_task, event_record)
        if event.task_subtype == TASK_SUBTYPE_SERVICE_EFFECT_EVALUATION:
            return self._handle_service_effect_evaluation(event, farming_task, event_record)
        if event.task_subtype in {TASK_SUBTYPE_REGULAR_DISEASE_PEST_SURVEY, TASK_SUBTYPE_SUDDEN_DISEASE_PEST_SURVEY}:
            return self._handle_pest_disease_survey(event, farming_task, event_record)
        return OrchestratorResult()

    def _handle_pest_disease_survey(
        self,
        event: "_SurveyResultRecorded",
        farming_task: FarmingTask,
        event_record: EventRecord,
    ) -> OrchestratorResult:
        planning_result = self.pest_disease_control_planning_service.generate_theory_plan_for_survey(
            farming_task=farming_task,
            survey_data=event.result_payload,
        )
        theory_result = planning_result.theory_result
        adjusted_result = planning_result.adjusted_result
        if not theory_result.rounds:
            task_intent = self._create_no_action_intent(
                event=event,
                event_record=event_record,
                task_subtype=TASK_SUBTYPE_DISEASE_PEST_CONTROL,
                algorithm_code="pest_disease.generate_theory_control_plan",
                branch_type=f"{planning_result.branch_type}_no_action",
                reason="病虫调查后理论防治结果为无需防治。",
                raw_response=theory_result.raw_response,
            )
            return OrchestratorResult(task_intents=[task_intent])
        merge_candidate = self._find_pest_disease_merge_candidate(
            event.planting_plan_id,
            current_control_type=planning_result.control_type,
        )
        if merge_candidate is not None:
            merge_result = self._build_pest_disease_merge_result(
                current_planning_result=planning_result,
                merge_candidate=merge_candidate,
                planting_plan_id=event.planting_plan_id,
            )
            stale_farming_tasks, stale_task_intents, stale_review_requests = self._close_existing_pest_disease_control_artifacts(
                event.planting_plan_id,
            )
            if not merge_result.merged_result.events:
                task_intent = self._create_no_action_intent(
                    event=event,
                    event_record=event_record,
                    task_subtype=TASK_SUBTYPE_DISEASE_PEST_CONTROL,
                    algorithm_code="pest_disease.merge_control_plan",
                    branch_type="disease_pest_merged_control_no_action",
                    reason="病虫调查后常规与突发合并结果为无可执行防治日期。",
                    raw_response={
                        "regularTheory": merge_result.regular_theory,
                        "emergencyTheory": merge_result.emergency_theory,
                        "mergeRange": merge_result.merge_range_result.raw_response,
                        "merge": merge_result.merged_result.raw_response,
                    },
                )
                return OrchestratorResult(
                    farming_tasks=stale_farming_tasks,
                    task_intents=[*stale_task_intents, task_intent],
                    review_requests=stale_review_requests,
                )

            operation_window = _format_date_range(_resolve_merged_control_operation_window(merge_result.merged_result))
            proposed_plan = {
                "planType": "plant_protection_control",
                "controlType": "merged" if merge_result.merged_result.merged else "regular_and_emergency",
                "operationWindow": operation_window,
                "targets": _merge_merged_event_targets(merge_result.merged_result),
                "events": [_serialize_merged_event_payload(item) for item in merge_result.merged_result.events],
                "regularTheoryPlan": dict(merge_result.regular_theory),
                "emergencyTheoryPlan": dict(merge_result.emergency_theory),
                "mergeRequiredRange": _format_date_range(
                    merge_result.merge_range_result.spray_suitability_required_range,
                ),
                "spraySuitabilityData": [dict(item) for item in merge_result.spray_suitability_data],
                "mergedPlan": dict(merge_result.merged_result.raw_data),
                "controlPlan": {
                    "regularTheory": dict(merge_result.regular_theory),
                    "emergencyTheory": dict(merge_result.emergency_theory),
                    "events": [_serialize_merged_event_payload(item) for item in merge_result.merged_result.events],
                },
                "basis": (
                    f"{event.task_subtype} survey result triggered merged disease pest control planning "
                    "with existing opposite control recommendation."
                ),
            }
            task_intent = self._create_task_intent(
                event=event,
                event_record=event_record,
                task_subtype=TASK_SUBTYPE_DISEASE_PEST_CONTROL,
                algorithm_code="pest_disease.merge_control_plan",
                branch_type="disease_pest_merged_control",
                proposed_task={
                    "title": merge_result.title,
                    "recommendedControlDate": operation_window,
                },
                proposed_plan=proposed_plan,
                suggested_action=merge_result.suggested_action,
                raw_response={
                    "regularTheory": merge_result.regular_theory,
                    "emergencyTheory": merge_result.emergency_theory,
                    "mergeRange": merge_result.merge_range_result.raw_response,
                    "merge": merge_result.merged_result.raw_response,
                },
            )
            review_request = self._create_review_request(
                task_intent,
                review_type=merge_result.review_type,
                title=merge_result.review_title,
                description=merge_result.review_description,
            )
            return OrchestratorResult(
                farming_tasks=stale_farming_tasks,
                task_intents=[*stale_task_intents, task_intent],
                review_requests=[*stale_review_requests, review_request],
            )
        if not adjusted_result.rounds:
            task_intent = self._create_no_action_intent(
                event=event,
                event_record=event_record,
                task_subtype=TASK_SUBTYPE_DISEASE_PEST_CONTROL,
                algorithm_code="pest_disease.adjust_control_window",
                branch_type=f"{planning_result.branch_type}_weather_no_action",
                reason="病虫调查后气象调整结果为无可执行防治日期。",
                raw_response=adjusted_result.raw_response,
            )
            return OrchestratorResult(task_intents=[task_intent])

        operation_window = _format_date_range(_resolve_adjusted_control_operation_window(adjusted_result))
        proposed_plan = {
            "planType": "plant_protection_control",
            "controlType": planning_result.control_type,
            "controlMode": adjusted_result.control_mode,
            "status": adjusted_result.status,
            "operationWindow": operation_window,
            "targets": _merge_adjusted_round_targets(adjusted_result),
            "rounds": [_serialize_adjusted_round_payload(item) for item in adjusted_result.rounds],
            "theoryPlan": dict(theory_result.raw_data),
            "adjustedPlan": dict(adjusted_result.raw_data),
            "spraySuitabilityRequiredRange": (
                _format_date_range(theory_result.spray_suitability_required_range)
                if theory_result.spray_suitability_required_range
                else []
            ),
            "spraySuitabilityData": [dict(item) for item in planning_result.spray_suitability_data],
            "weatherAdjust": dict(adjusted_result.weather_adjust),
            "controlPlan": {
                "rounds": [
                    {
                        "round": item.round,
                        "targets": dict(theory_item.targets),
                        "prescription": dict(theory_item.prescription),
                    }
                    for item, theory_item in zip(adjusted_result.rounds, theory_result.rounds, strict=False)
                ],
            },
            "requestPayload": planning_result.request_payload,
            "basis": f"{event.task_subtype} survey result triggered {planning_result.control_type} theory control planning.",
        }
        task_intent = self._create_task_intent(
            event=event,
            event_record=event_record,
            task_subtype=planning_result.task_subtype,
            algorithm_code="pest_disease.generate_theory_control_plan",
            branch_type=planning_result.branch_type,
            proposed_task={
                "title": planning_result.title,
                "recommendedControlDate": operation_window,
            },
            proposed_plan=proposed_plan,
            suggested_action=planning_result.suggested_action,
            raw_response={
                "theory": theory_result.raw_response,
                "adjust": adjusted_result.raw_response,
            },
        )
        review_request = self._create_review_request(
            task_intent,
            review_type=planning_result.review_type,
            title=planning_result.review_title,
            description=planning_result.review_description,
        )
        return OrchestratorResult(task_intents=[task_intent], review_requests=[review_request])

    def _handle_pre_treatment_survey(
        self,
        event: "_SurveyResultRecorded",
        farming_task: FarmingTask,
        event_record: EventRecord,
    ) -> OrchestratorResult:
        planting_plan = self._get_plan(event.planting_plan_id)
        context = self.context_resolver.resolve(planting_plan)
        survey_date = _parse_payload_date(event.result_payload, "survey_date")
        weather_data = self.weather_provider.get_daily_weather(planting_plan, survey_date, survey_date + _WEATHER_WINDOW)
        diagnosis = self.diagnosis_client.diagnose_weed_treatment(
            province=str(event.result_payload.get("province", "湖南省")),
            weather_data=weather_data,
            rice_type=context.rice_type,
            cultivation_system=context.cultivation_system,
            cultivation_pattern=context.cultivation_pattern,
            cultivation_date=context.cultivation_date,
            survey_data_before_treatment=event.result_payload,
            last_survey_date=None,
        )
        if diagnosis.next_survey_date:
            calendar_item = self.survey_date_recommendation_service.schedule_followup_pre_survey(
                event.planting_plan_id,
                suggested_date=diagnosis.next_survey_date,
                parent_task_id=farming_task.id,
                source_execution_id=event.execution_id,
                source_execution_record_id=event.execution_record_id,
            )
            return OrchestratorResult(calendar_items=[calendar_item])

        task_intent = self._create_task_intent(
            event=event,
            event_record=event_record,
            task_subtype=TASK_SUBTYPE_STEM_LEAF_WEED_CONTROL,
            algorithm_code="weed_treatment_diagnosis",
            branch_type="weed_control",
            proposed_task={
                "title": "茎叶除草",
                "recommendedControlDate": _format_date_range(diagnosis.recommended_control_date),
            },
            proposed_plan={
                "controlTarget": diagnosis.control_target,
                "controlPlan": diagnosis.control_plan,
            },
            suggested_action="建议执行茎叶除草",
            raw_response=diagnosis.raw_response,
        )
        review_request = self._create_review_request(
            task_intent,
            review_type="weed_control_recommendation",
            title="茎叶除草建议待审核",
            description="药前调查结果达到防治条件，需审核后生成正式防治任务。",
        )
        return OrchestratorResult(task_intents=[task_intent], review_requests=[review_request])

    def _find_pest_disease_merge_candidate(
        self,
        planting_plan_id: int,
        *,
        current_control_type: str,
    ) -> TaskIntent | None:
        opposite_control_type = "emergency" if current_control_type == "regular" else "regular"
        for item in self.task_intent_repository.list_current_by_plan(planting_plan_id):
            if self._is_pest_disease_merge_candidate(item, expected_control_type=opposite_control_type):
                return item
        for item in self.farming_task_repository.list_current_by_plan(planting_plan_id):
            if item.task_subtype != TASK_SUBTYPE_DISEASE_PEST_CONTROL:
                continue
            if item.status != FARMING_TASK_STATUS_PENDING:
                continue
            if item.task_intent_id is None:
                continue
            source_task_intent = self.task_intent_repository.get(item.task_intent_id)
            if source_task_intent is None or source_task_intent.status != TASK_INTENT_STATUS_CONVERTED:
                continue
            if self._is_pest_disease_merge_candidate(source_task_intent, expected_control_type=opposite_control_type):
                return source_task_intent
        return None

    def _is_pest_disease_merge_candidate(
        self,
        task_intent: TaskIntent,
        *,
        expected_control_type: str,
    ) -> bool:
        if task_intent.task_subtype != TASK_SUBTYPE_DISEASE_PEST_CONTROL:
            return False
        proposed_plan = dict(task_intent.rule_result.get("proposedPlan") or {})
        if proposed_plan.get("controlType") != expected_control_type:
            return False
        return isinstance(proposed_plan.get("theoryPlan"), dict)

    def _build_pest_disease_merge_result(
        self,
        *,
        current_planning_result,
        merge_candidate: TaskIntent,
        planting_plan_id: int,
    ):
        current_theory = dict(current_planning_result.theory_result.raw_data)
        candidate_plan = dict(merge_candidate.rule_result.get("proposedPlan") or {})
        candidate_theory = dict(candidate_plan.get("theoryPlan") or {})
        if current_planning_result.control_type == "regular":
            regular_theory = current_theory
            emergency_theory = candidate_theory
        else:
            regular_theory = candidate_theory
            emergency_theory = current_theory
        return self.pest_disease_control_planning_service.merge_theory_plans(
            planting_plan_id=planting_plan_id,
            regular_theory=regular_theory,
            emergency_theory=emergency_theory,
        )

    def _close_existing_pest_disease_control_artifacts(
        self,
        planting_plan_id: int,
    ) -> tuple[list[FarmingTask], list[TaskIntent], list[ReviewRequest]]:
        stale_farming_tasks: list[FarmingTask] = []
        closed_task_intents: list[TaskIntent] = []
        closed_review_requests: list[ReviewRequest] = []
        closed_task_intent_ids: set[int] = set()
        stale_reason = "Superseded by merged disease pest control recommendation."
        active_task_intents = [
            item
            for item in self.task_intent_repository.list_current_by_plan(planting_plan_id)
            if item.task_subtype == TASK_SUBTYPE_DISEASE_PEST_CONTROL
        ]
        for item in active_task_intents:
            item.status = TASK_INTENT_STATUS_REJECTED
            item.no_action_reason = stale_reason
            closed_task_intents.append(item)
            if item.id is not None:
                closed_task_intent_ids.add(int(item.id))
        active_task_intent_ids = {int(item.id) for item in active_task_intents if item.id is not None}
        for item in self.review_request_repository.list_current_by_plan(planting_plan_id):
            if item.source_entity_type not in {"task_intent", "cf_task_intent"}:
                continue
            if item.source_entity_id not in active_task_intent_ids:
                continue
            item.status = "cancelled"
            item.decision = None
            closed_review_requests.append(item)
        for item in self.farming_task_repository.list_current_by_plan(planting_plan_id):
            if item.task_subtype != TASK_SUBTYPE_DISEASE_PEST_CONTROL:
                continue
            item.status = "cancelled"
            stale_farming_tasks.append(item)
            if item.task_intent_id is None:
                continue
            source_task_intent = self.task_intent_repository.get(item.task_intent_id)
            if source_task_intent is None or source_task_intent.task_subtype != TASK_SUBTYPE_DISEASE_PEST_CONTROL:
                continue
            source_task_intent.no_action_reason = stale_reason
            if source_task_intent.id is None or int(source_task_intent.id) in closed_task_intent_ids:
                continue
            closed_task_intents.append(source_task_intent)
            closed_task_intent_ids.add(int(source_task_intent.id))
        return (stale_farming_tasks, closed_task_intents, closed_review_requests)

    def _handle_rice_safety_survey(
        self,
        event: "_SurveyResultRecorded",
        event_record: EventRecord,
    ) -> OrchestratorResult:
        diagnosis = self.diagnosis_client.diagnose_injury_mitigation(
            survey_date=_parse_payload_date(event.result_payload, "survey_date"),
            rice_injury_level=str(event.result_payload["rice_injury_level"]),
        )
        if not diagnosis.need_mitigation:
            task_intent = self._create_no_action_intent(
                event=event,
                event_record=event_record,
                task_subtype=TASK_SUBTYPE_INJURY_MITIGATION,
                algorithm_code="injury_mitigation_diagnosis",
                branch_type="injury_no_action",
                reason="安全性调查后诊断无需药害缓解。",
                raw_response=diagnosis.raw_response,
            )
            return OrchestratorResult(task_intents=[task_intent])

        task_intent = self._create_task_intent(
            event=event,
            event_record=event_record,
            task_subtype=TASK_SUBTYPE_INJURY_MITIGATION,
            algorithm_code="injury_mitigation_diagnosis",
            branch_type="injury_mitigation",
            proposed_task={
                "title": "药害缓解",
                "recommendedMitigationDate": _format_date_range(diagnosis.recommended_mitigation_date),
            },
            proposed_plan={"measures": diagnosis.measures},
            suggested_action="建议执行药害缓解措施",
            raw_response=diagnosis.raw_response,
        )
        review_request = self._create_review_request(
            task_intent,
            review_type="herbicide_damage_mitigation",
            title="药害缓解建议待审核",
            description="安全性调查后诊断需要药害缓解，需审核后生成正式任务。",
        )
        return OrchestratorResult(task_intents=[task_intent], review_requests=[review_request])

    def _handle_control_effect_survey(
        self,
        event: "_SurveyResultRecorded",
        farming_task: FarmingTask,
        event_record: EventRecord,
    ) -> OrchestratorResult:
        planting_plan = self._get_plan(event.planting_plan_id)
        context = self.context_resolver.resolve(planting_plan)
        diagnosis = self.diagnosis_client.diagnose_additional_treatment(
            province=str(event.result_payload.get("province", "湖南省")),
            cultivation_system=context.cultivation_system,
            cultivation_pattern=context.cultivation_pattern,
            cultivation_date=context.cultivation_date,
            control_date=_parse_payload_date(event.result_payload, "control_date"),
            previous_injury_level=str(event.result_payload.get("previous_injury_level", "无")),
            survey_data_before_treatment=dict(event.result_payload.get("survey_data_before_treatment") or {}),
            survey_data_after_treatment=event.result_payload,
        )
        result = OrchestratorResult()

        if diagnosis.additional_survey_date:
            result.calendar_items.append(
                self.survey_date_recommendation_service.schedule_recontrol_pre_survey(
                    event.planting_plan_id,
                    suggested_date=diagnosis.additional_survey_date,
                    parent_task_id=farming_task.id,
                    source_execution_id=event.execution_id,
                    source_execution_record_id=event.execution_record_id,
                ),
            )

        if diagnosis.service_effect_evaluation_date:
            result.calendar_items.append(
                self.survey_date_recommendation_service.schedule_service_effect_evaluation(
                    event.planting_plan_id,
                    suggested_date=diagnosis.service_effect_evaluation_date,
                    parent_task_id=farming_task.id,
                    source_execution_id=event.execution_id,
                    source_execution_record_id=event.execution_record_id,
                ),
            )
            result.task_intents.append(
                self._create_no_action_intent(
                    event=event,
                    event_record=event_record,
                    task_subtype=TASK_SUBTYPE_STEM_LEAF_WEED_CONTROL,
                    algorithm_code="additional_treatment_diagnosis",
                    branch_type="additional_no_action",
                    reason="防效兼安全性调查后诊断无需补防。",
                    raw_response=diagnosis.raw_response,
                ),
            )

        if diagnosis.recommended_recontrol_date and diagnosis.control_plan:
            task_intent = self._create_task_intent(
                event=event,
                event_record=event_record,
                task_subtype=TASK_SUBTYPE_STEM_LEAF_WEED_CONTROL,
                algorithm_code="additional_treatment_diagnosis",
                branch_type="additional_recontrol",
                proposed_task={
                    "title": "茎叶除草补防",
                    "recommendedRecontrolDate": _format_date_range(diagnosis.recommended_recontrol_date),
                },
                proposed_plan={
                    "recontrolTarget": diagnosis.recontrol_target,
                    "controlPlan": diagnosis.control_plan,
                },
                suggested_action="建议执行茎叶除草补防",
                raw_response=diagnosis.raw_response,
            )
            result.task_intents.append(task_intent)
            result.review_requests.append(
                self._create_review_request(
                    task_intent,
                    review_type="additional_control_immediate",
                    title="立即补防建议待审核",
                    description="防效兼安全性调查后诊断需要补防，需审核后生成正式任务。",
                ),
            )

        if diagnosis.injury_mitigation and diagnosis.injury_mitigation.get("need_mitigation"):
            task_intent = self._create_task_intent(
                event=event,
                event_record=event_record,
                task_subtype=TASK_SUBTYPE_INJURY_MITIGATION,
                algorithm_code="additional_treatment_diagnosis",
                branch_type="additional_injury_mitigation",
                proposed_task={
                    "title": "药害缓解",
                    "recommendedMitigationDate": diagnosis.injury_mitigation.get("recommended_mitigation_date"),
                },
                proposed_plan={"measures": diagnosis.injury_mitigation.get("measures")},
                suggested_action="建议执行药害缓解措施",
                raw_response=diagnosis.raw_response,
            )
            result.task_intents.append(task_intent)
            result.review_requests.append(
                self._create_review_request(
                    task_intent,
                    review_type="herbicide_damage_mitigation",
                    title="药害缓解建议待审核",
                    description="防效兼安全性调查后诊断需要药害缓解，需审核后生成正式任务。",
                ),
            )

        return result

    def _handle_service_effect_evaluation(
        self,
        event: "_SurveyResultRecorded",
        farming_task: FarmingTask,
        event_record: EventRecord,
    ) -> OrchestratorResult:
        is_satisfied = _parse_required_payload_bool(event.result_payload, "is_satisfied", "isSatisfied")
        if is_satisfied:
            return OrchestratorResult()

        followup_task = FarmingTask(
            planting_plan_id=event.planting_plan_id,
            task_category=TASK_CATEGORY_PLANT_PROTECTION,
            task_subtype=TASK_SUBTYPE_SERVICE_EFFECT_SURVEY,
            title="服务人员现场确认",
            description="服务效果评估结果为不满意，需安排服务人员现场确认并补充记录。",
            planned_start_at=_parse_optional_payload_datetime(
                event.result_payload,
                "evaluated_at",
                "evaluatedAt",
            )
            or event_record.occurred_at,
            planned_end_at=_parse_optional_payload_datetime(
                event.result_payload,
                "evaluated_at",
                "evaluatedAt",
            )
            or event_record.occurred_at,
            status=FARMING_TASK_STATUS_PENDING,
            execution_mode=farming_task.execution_mode or EXECUTION_MODE_MANUAL,
            generation_reason=f"survey_result:{event.execution_record_id}:service_evaluation_unsatisfied",
            parent_task_id=farming_task.id,
            source_execution_id=event.execution_id,
            source_execution_record_id=event.execution_record_id,
            idempotency_key=(
                f"farming-task:service-effect-evaluation:{event.execution_record_id}:{TASK_SUBTYPE_SERVICE_EFFECT_SURVEY}"
            ),
            created_by_type="system",
            created_by_id="SurveyResultRecordedHandler",
        )
        self.farming_task_repository.add(followup_task)
        self.farming_task_repository.flush()
        self._record_followup_farming_task_event(
            followup_task,
            event=event,
            event_record=event_record,
            branch_type="service_effect_survey",
        )
        return OrchestratorResult(farming_tasks=[followup_task])

    def _create_task_intent(
        self,
        *,
        event: "_SurveyResultRecorded",
        event_record: EventRecord,
        task_subtype: str,
        algorithm_code: str,
        branch_type: str,
        proposed_task: dict[str, Any],
        proposed_plan: dict[str, Any],
        suggested_action: str,
        raw_response: dict[str, Any] | None = None,
    ) -> TaskIntent:
        task_intent = TaskIntent(
            planting_plan_id=event.planting_plan_id,
            task_category=TASK_CATEGORY_PLANT_PROTECTION,
            task_subtype=task_subtype,
            status=TASK_INTENT_STATUS_PENDING,
            trigger_type=EVENT_TYPE_SURVEY_RESULT_RECORDED,
            trigger_summary=f"{event.task_subtype} survey result triggered {branch_type}.",
            rule_result={
                "algorithmCode": algorithm_code,
                "branchType": branch_type,
                "proposedTask": proposed_task,
                "proposedPlan": proposed_plan,
                "parentTaskId": event.task_id,
                "sourceExecutionId": event.execution_id,
                "sourceExecutionRecordId": event.execution_record_id,
                "inputExecutionRecordIds": [event.execution_record_id],
                "rawResponse": raw_response,
            },
            suggested_action=suggested_action,
            parent_task_id=event.task_id,
            source_execution_id=event.execution_id,
            source_execution_record_id=event.execution_record_id,
            source_event_id=event_record.id,
            idempotency_key=f"task-intent:{event.execution_record_id}:{branch_type}:{task_subtype}",
            created_by_type="system",
            created_by_id="SurveyResultRecordedHandler",
        )
        self.task_intent_repository.add(task_intent)
        self.task_intent_repository.flush()
        self._record_followup_event(EVENT_TYPE_TASK_INTENT_CREATED, task_intent, event, branch_type)
        return task_intent

    def _create_no_action_intent(
        self,
        *,
        event: "_SurveyResultRecorded",
        event_record: EventRecord,
        task_subtype: str,
        algorithm_code: str,
        branch_type: str,
        reason: str,
        raw_response: dict[str, Any],
    ) -> TaskIntent:
        task_intent = TaskIntent(
            planting_plan_id=event.planting_plan_id,
            task_category=TASK_CATEGORY_PLANT_PROTECTION,
            task_subtype=task_subtype,
            status=TASK_INTENT_STATUS_NO_ACTION,
            trigger_type=EVENT_TYPE_SURVEY_RESULT_RECORDED,
            trigger_summary=reason,
            rule_result={
                "algorithmCode": algorithm_code,
                "branchType": branch_type,
                "parentTaskId": event.task_id,
                "sourceExecutionId": event.execution_id,
                "sourceExecutionRecordId": event.execution_record_id,
                "inputExecutionRecordIds": [event.execution_record_id],
                "rawResponse": raw_response,
            },
            no_action_reason=reason,
            parent_task_id=event.task_id,
            source_execution_id=event.execution_id,
            source_execution_record_id=event.execution_record_id,
            source_event_id=event_record.id,
            idempotency_key=f"task-intent:{event.execution_record_id}:{branch_type}:{task_subtype}",
            created_by_type="system",
            created_by_id="SurveyResultRecordedHandler",
        )
        self.task_intent_repository.add(task_intent)
        self.task_intent_repository.flush()
        self._record_followup_event(EVENT_TYPE_TASK_INTENT_CREATED, task_intent, event, branch_type)
        return task_intent

    def _create_review_request(
        self,
        task_intent: TaskIntent,
        *,
        review_type: str,
        title: str,
        description: str,
    ) -> ReviewRequest:
        review_request = ReviewRequest(
            planting_plan_id=task_intent.planting_plan_id,
            review_type=review_type,
            status=REVIEW_REQUEST_STATUS_OPEN,
            source_entity_type="task_intent",
            source_entity_id=task_intent.id,
            title=title,
            description=description,
            decision_payload={
                "contextRefs": {
                    "taskIntentId": task_intent.id,
                    "parentTaskId": task_intent.parent_task_id,
                    "sourceExecutionId": task_intent.source_execution_id,
                    "sourceExecutionRecordId": task_intent.source_execution_record_id,
                },
            },
            idempotency_key=f"review-request:task-intent:{task_intent.id}:{review_type}",
            created_by_type="system",
            created_by_id="SurveyResultRecordedHandler",
        )
        self.review_request_repository.add(review_request)
        self.review_request_repository.flush()
        self._record_followup_event(
            EVENT_TYPE_REVIEW_REQUEST_CREATED,
            review_request,
            _SurveyResultRecorded(
                planting_plan_id=task_intent.planting_plan_id,
                task_id=task_intent.parent_task_id or 0,
                task_subtype=task_intent.task_subtype,
                execution_id=task_intent.source_execution_id or 0,
                execution_record_id=task_intent.source_execution_record_id or 0,
                result_payload={},
            ),
            review_type,
        )
        return review_request

    def _record_followup_event(
        self,
        event_type: str,
        entity: TaskIntent | ReviewRequest,
        event: "_SurveyResultRecorded",
        branch_type: str,
    ) -> None:
        self.event_record_repository.add(
            EventRecord(
                planting_plan_id=event.planting_plan_id,
                event_type=event_type,
                event_category="runtime",
                event_source="orchestrator",
                source_system="cropflow",
                source_record_id=str(entity.id),
                payload={
                    "branchType": branch_type,
                    "sourceExecutionRecordId": event.execution_record_id,
                    "entityType": entity.__tablename__,
                    "entityId": entity.id,
                },
                occurred_at=_utcnow(),
                processing_status=EVENT_PROCESSING_STATUS_PROCESSED,
                processed_at=_utcnow(),
                idempotency_key=f"{event_type}:{entity.__tablename__}:{entity.id}",
                created_by_type="system",
                created_by_id="SurveyResultRecordedHandler",
            ),
        )

    def _record_followup_farming_task_event(
        self,
        farming_task: FarmingTask,
        *,
        event: "_SurveyResultRecorded",
        event_record: EventRecord,
        branch_type: str,
    ) -> None:
        self.event_record_repository.add(
            EventRecord(
                planting_plan_id=event.planting_plan_id,
                event_type=EVENT_TYPE_FARMING_TASK_CREATED,
                event_category="runtime",
                event_source="orchestrator",
                source_system="cropflow",
                source_record_id=str(farming_task.id),
                payload={
                    "branchType": branch_type,
                    "sourceEventId": event_record.id,
                    "sourceExecutionRecordId": event.execution_record_id,
                    "farmingTaskId": farming_task.id,
                    "parentTaskId": farming_task.parent_task_id,
                },
                occurred_at=_utcnow(),
                processing_status=EVENT_PROCESSING_STATUS_PROCESSED,
                processed_at=_utcnow(),
                idempotency_key=f"{EVENT_TYPE_FARMING_TASK_CREATED}:farming-task:{farming_task.id}",
                created_by_type="system",
                created_by_id="SurveyResultRecordedHandler",
            ),
        )

    def _get_plan(self, planting_plan_id: int):
        planting_plan = self.planting_plan_repository.get(planting_plan_id)
        if planting_plan is None:
            raise LookupError(f"Planting plan {planting_plan_id} does not exist.")
        return planting_plan


class ReviewRequestResolvedHandler:
    APPROVE_DECISIONS = {"approve", "adjust"}

    def __init__(
        self,
        task_intent_repository: TaskIntentRepository,
        review_request_repository: ReviewRequestRepository,
        farming_task_repository: FarmingTaskRepository,
        operation_plan_repository: OperationPlanRepository,
        event_record_repository: EventRecordRepository,
        pest_disease_control_planning_service: PestDiseaseControlPlanningService | None = None,
    ) -> None:
        self.task_intent_repository = task_intent_repository
        self.review_request_repository = review_request_repository
        self.farming_task_repository = farming_task_repository
        self.operation_plan_repository = operation_plan_repository
        self.event_record_repository = event_record_repository
        self.pest_disease_control_planning_service = pest_disease_control_planning_service

    def handle(self, event_record: EventRecord) -> OrchestratorResult:
        review_request_id = int(event_record.payload["reviewRequestId"])
        review_request = self.review_request_repository.get(review_request_id)
        if review_request is None:
            raise LookupError(f"Review request {review_request_id} does not exist.")
        if review_request.source_entity_type not in {"task_intent", "cf_task_intent"}:
            raise ValueError("Only task_intent sourced review requests are supported in M4.")

        task_intent = self.task_intent_repository.get(review_request.source_entity_id)
        if task_intent is None:
            raise LookupError(f"Task intent {review_request.source_entity_id} does not exist.")

        decision = str(event_record.payload["decision"])
        if decision in self.APPROVE_DECISIONS:
            return self._approve(event_record, review_request, task_intent)
        if decision == "reject":
            task_intent.status = "rejected"
            return OrchestratorResult(task_intents=[task_intent], review_requests=[review_request])
        if decision == "no_action":
            task_intent.status = TASK_INTENT_STATUS_NO_ACTION
            task_intent.no_action_reason = str(event_record.payload.get("decisionNote") or "复核结论为无需处理。")
            return OrchestratorResult(task_intents=[task_intent], review_requests=[review_request])
        if decision == "need_more_info":
            task_intent.status = TASK_INTENT_STATUS_PENDING_MORE_INFO
            task_intent.need_more_info_fields = dict(event_record.payload.get("decisionPayload") or {})
            return OrchestratorResult(task_intents=[task_intent], review_requests=[review_request])
        raise ValueError(f"Unsupported review decision: {decision}.")

    def _approve(
        self,
        event_record: EventRecord,
        review_request: ReviewRequest,
        task_intent: TaskIntent,
    ) -> OrchestratorResult:
        proposed_task = dict(task_intent.rule_result.get("proposedTask") or {})
        proposed_plan = dict(task_intent.rule_result.get("proposedPlan") or {})
        overrides = dict(event_record.payload.get("decisionPayload") or {})
        proposed_task = _merge_review_override(proposed_task, dict(overrides.get("proposedTask") or {}))
        proposed_plan = _merge_review_override(proposed_plan, dict(overrides.get("proposedPlan") or {}))
        if _has_disease_pest_theory_window_override(overrides):
            self._refresh_disease_pest_adjusted_plan(task_intent, proposed_task, proposed_plan)

        farming_task = FarmingTask(
            planting_plan_id=task_intent.planting_plan_id,
            task_intent_id=task_intent.id,
            review_request_id=review_request.id,
            task_category=task_intent.task_category,
            task_subtype=task_intent.task_subtype,
            title=str(proposed_task.get("title") or task_intent.suggested_action or review_request.title),
            description=str(proposed_task.get("description") or task_intent.trigger_summary or review_request.description or ""),
            planned_start_at=_parse_optional_datetime_or_date_range_start(
                proposed_task.get("plannedStartAt")
                or proposed_task.get("recommendedControlDate")
                or proposed_task.get("recommendedRecontrolDate")
                or proposed_task.get("recommendedMitigationDate"),
            ),
            planned_end_at=_parse_optional_datetime_or_date_range_end(
                proposed_task.get("plannedEndAt")
                or proposed_task.get("recommendedControlDate")
                or proposed_task.get("recommendedRecontrolDate")
                or proposed_task.get("recommendedMitigationDate"),
            ),
            status=FARMING_TASK_STATUS_PENDING,
            execution_mode=str(proposed_task.get("executionMode") or EXECUTION_MODE_MANUAL),
            generation_reason=f"review_request:{review_request.id}:approved",
            parent_task_id=task_intent.parent_task_id,
            source_execution_id=task_intent.source_execution_id,
            source_execution_record_id=task_intent.source_execution_record_id,
            idempotency_key=f"farming-task:review-request:{review_request.id}:task-intent:{task_intent.id}",
            created_by_type="system",
            created_by_id="ReviewRequestResolvedHandler",
        )
        self.farming_task_repository.add(farming_task)
        self.farming_task_repository.flush()

        task_intent.status = TASK_INTENT_STATUS_CONVERTED
        task_intent.converted_task_id = farming_task.id

        self._record_event(
            planting_plan_id=task_intent.planting_plan_id,
            event_type=EVENT_TYPE_FARMING_TASK_CREATED,
            source_record_id=str(farming_task.id),
            payload={
                "reviewRequestId": review_request.id,
                "taskIntentId": task_intent.id,
                "farmingTaskId": farming_task.id,
                "sourceEventId": event_record.id,
            },
            idempotency_key=f"FarmingTaskCreated:review-request:{review_request.id}",
        )
        operation_plan = self._create_operation_plan_if_needed(
            event_record,
            farming_task,
            task_intent,
            proposed_plan,
        )
        operation_plans = [operation_plan] if operation_plan else []
        return OrchestratorResult(
            farming_tasks=[farming_task],
            task_intents=[task_intent],
            review_requests=[review_request],
            operation_plans=operation_plans,
        )

    def _refresh_disease_pest_adjusted_plan(
        self,
        task_intent: TaskIntent,
        proposed_task: dict[str, Any],
        proposed_plan: dict[str, Any],
    ) -> None:
        if task_intent.task_subtype != TASK_SUBTYPE_DISEASE_PEST_CONTROL:
            return
        if self.pest_disease_control_planning_service is None:
            raise ValueError("Pest disease control planning service is required to adjust theory window.")
        theory_plan = dict(proposed_plan.get("theoryPlan") or {})
        control_type = str(proposed_plan.get("controlType") or theory_plan.get("control_type") or "").strip()
        if not control_type:
            raise ValueError("Pest disease control type is required to adjust theory window.")

        review_adjustment = self.pest_disease_control_planning_service.adjust_theory_plan_for_review(
            planting_plan_id=task_intent.planting_plan_id,
            control_type=control_type,
            theory_plan=theory_plan,
        )
        adjusted_result = review_adjustment.adjusted_result
        operation_window = _format_date_range(_resolve_adjusted_control_operation_window(adjusted_result))

        proposed_task["recommendedControlDate"] = operation_window
        proposed_plan["operationWindow"] = operation_window
        proposed_plan["controlMode"] = adjusted_result.control_mode
        proposed_plan["status"] = adjusted_result.status
        proposed_plan["rounds"] = [_serialize_adjusted_round_payload(item) for item in adjusted_result.rounds]
        proposed_plan["targets"] = _merge_adjusted_round_targets(adjusted_result)
        proposed_plan["adjustedPlan"] = dict(adjusted_result.raw_data)
        proposed_plan["spraySuitabilityRequiredRange"] = _format_date_range(
            review_adjustment.spray_suitability_required_range,
        )
        proposed_plan["spraySuitabilityData"] = [dict(item) for item in review_adjustment.spray_suitability_data]
        proposed_plan["weatherAdjust"] = dict(adjusted_result.weather_adjust)

    def _create_operation_plan_if_needed(
        self,
        event_record: EventRecord,
        farming_task: FarmingTask,
        task_intent: TaskIntent,
        proposed_plan: dict[str, Any],
    ) -> OperationPlan | None:
        if not proposed_plan:
            return None

        operation_window_start = _parse_optional_datetime_or_date_range_start(
            proposed_plan.get("operationWindow")
            or proposed_plan.get("recommendedControlDate")
            or proposed_plan.get("recommendedRecontrolDate")
            or proposed_plan.get("recommendedMitigationDate"),
        )
        operation_window_end = _parse_optional_datetime_or_date_range_end(
            proposed_plan.get("operationWindow")
            or proposed_plan.get("recommendedControlDate")
            or proposed_plan.get("recommendedRecontrolDate")
            or proposed_plan.get("recommendedMitigationDate"),
        )
        operation_plan = OperationPlan(
            planting_plan_id=task_intent.planting_plan_id,
            farming_task_id=farming_task.id,
            plan_type=str(proposed_plan.get("planType") or task_intent.task_subtype),
            status=OPERATION_PLAN_STATUS_ACTIVE,
            algorithm_code=task_intent.rule_result.get("algorithmCode"),
            operation_area=dict(proposed_plan.get("operationArea") or {}),
            operation_window_start=operation_window_start,
            operation_window_end=operation_window_end,
            execution_mode=farming_task.execution_mode,
            parameters=proposed_plan,
            prescription_map=dict(proposed_plan.get("prescriptionMap") or proposed_plan.get("controlPlan") or {}),
            acceptance_criteria=dict(proposed_plan.get("acceptanceCriteria") or {}),
            basis=str(proposed_plan.get("basis") or task_intent.trigger_summary or ""),
            source_event_id=event_record.id,
            idempotency_key=f"operation-plan:farming-task:{farming_task.id}",
            created_by_type="system",
            created_by_id="ReviewRequestResolvedHandler",
        )
        self.operation_plan_repository.add(operation_plan)
        self.operation_plan_repository.flush()
        self._record_event(
            planting_plan_id=task_intent.planting_plan_id,
            event_type=EVENT_TYPE_OPERATION_PLAN_CREATED,
            source_record_id=str(operation_plan.id),
            payload={
                "reviewRequestId": farming_task.review_request_id,
                "taskIntentId": task_intent.id,
                "farmingTaskId": farming_task.id,
                "operationPlanId": operation_plan.id,
                "sourceEventId": event_record.id,
            },
            idempotency_key=f"OperationPlanCreated:farming-task:{farming_task.id}",
        )
        return operation_plan

    def _record_event(
        self,
        *,
        planting_plan_id: int,
        event_type: str,
        source_record_id: str,
        payload: dict[str, Any],
        idempotency_key: str,
    ) -> EventRecord:
        event_record = EventRecord(
            planting_plan_id=planting_plan_id,
            event_type=event_type,
            event_category="runtime",
            event_source="orchestrator",
            source_system="cropflow",
            source_record_id=source_record_id,
            payload=payload,
            occurred_at=_utcnow(),
            processing_status=EVENT_PROCESSING_STATUS_PROCESSED,
            processed_at=_utcnow(),
            idempotency_key=idempotency_key,
            created_by_type="system",
            created_by_id="ReviewRequestResolvedHandler",
        )
        self.event_record_repository.add(event_record)
        return event_record


class ExecutionCompletedHandler:
    def __init__(
        self,
        farming_task_repository: FarmingTaskRepository,
        survey_date_recommendation_service: SurveyDateRecommendationService,
    ) -> None:
        self.farming_task_repository = farming_task_repository
        self.survey_date_recommendation_service = survey_date_recommendation_service

    def handle(self, event_record: EventRecord) -> OrchestratorResult:
        task_id = int(event_record.payload["taskId"])
        farming_task = self.farming_task_repository.get(task_id)
        if farming_task is None:
            raise LookupError(f"Farming task {task_id} does not exist.")

        if farming_task.task_subtype != TASK_SUBTYPE_STEM_LEAF_WEED_CONTROL:
            return OrchestratorResult()

        operation_date = _parse_payload_date(event_record.payload, "operationDate")
        safety_item, effect_item = self.survey_date_recommendation_service.recommend_post_treatment_surveys(
            farming_task.planting_plan_id,
            operation_date=operation_date,
            parent_task_id=farming_task.id,
            source_execution_id=int(event_record.payload["executionId"]),
            source_execution_record_id=int(event_record.payload["executionRecordId"]),
        )
        return OrchestratorResult(calendar_items=[safety_item, effect_item])


@dataclass(slots=True)
class _SurveyResultRecorded:
    planting_plan_id: int
    task_id: int
    task_subtype: str
    execution_id: int
    execution_record_id: int
    result_payload: dict[str, Any]

    @classmethod
    def from_event_record(cls, event_record: EventRecord) -> "_SurveyResultRecorded":
        return cls(
            planting_plan_id=int(event_record.planting_plan_id),
            task_id=int(event_record.payload["taskId"]),
            task_subtype=str(event_record.payload["taskSubtype"]),
            execution_id=int(event_record.payload["executionId"]),
            execution_record_id=int(event_record.payload["executionRecordId"]),
            result_payload=dict(event_record.payload.get("resultPayload") or {}),
        )


def build_plan_orchestrator(
    *,
    planting_plan_repository: PlantingPlanRepository,
    calendar_item_repository: CalendarItemRepository,
    farming_task_repository: FarmingTaskRepository,
    event_record_repository: EventRecordRepository,
    task_intent_repository: TaskIntentRepository,
    review_request_repository: ReviewRequestRepository,
    operation_plan_repository: OperationPlanRepository,
    stage_management_service: StageManagementService,
    survey_date_recommendation_service: SurveyDateRecommendationService,
    weather_provider: WeatherProvider,
    diagnosis_client: WeedDiagnosisClient,
    context_resolver: PlantProtectionPlanContextResolver,
    pest_disease_control_planning_service: PestDiseaseControlPlanningService,
) -> PlanOrchestrator:
    stage_refresh_handler = StageRefreshHandler(
        stage_management_service=stage_management_service,
        event_record_repository=event_record_repository,
    )
    task_due_check_handler = TaskDueCheckTriggeredHandler(
        planting_plan_repository=planting_plan_repository,
        calendar_item_repository=calendar_item_repository,
        farming_task_repository=farming_task_repository,
        event_record_repository=event_record_repository,
    )
    plan_refresh_handler = PlanCalendarRefreshHandler(
        survey_date_recommendation_service=survey_date_recommendation_service,
        event_record_repository=event_record_repository,
        task_intent_repository=task_intent_repository,
        review_request_repository=review_request_repository,
        task_due_check_handler=task_due_check_handler,
    )
    lifecycle_handler = CompositeHandler(stage_refresh_handler, plan_refresh_handler)
    return PlanOrchestrator(
        handlers={
            EVENT_TYPE_PLAN_CREATED: lifecycle_handler,
            EVENT_TYPE_PLAN_KEY_INFO_CHANGED: lifecycle_handler,
            EVENT_TYPE_WEATHER_UPDATED: lifecycle_handler,
            EVENT_TYPE_ACTUAL_STAGE_RECORDED: lifecycle_handler,
            EVENT_TYPE_STAGE_CHANGED: plan_refresh_handler,
            EVENT_TYPE_TASK_DUE_CHECK_TRIGGERED: task_due_check_handler,
            EVENT_TYPE_SURVEY_RESULT_RECORDED: SurveyResultRecordedHandler(
                planting_plan_repository=planting_plan_repository,
                farming_task_repository=farming_task_repository,
                event_record_repository=event_record_repository,
                task_intent_repository=task_intent_repository,
                review_request_repository=review_request_repository,
                survey_date_recommendation_service=survey_date_recommendation_service,
                weather_provider=weather_provider,
                diagnosis_client=diagnosis_client,
                context_resolver=context_resolver,
                pest_disease_control_planning_service=pest_disease_control_planning_service,
            ),
            EVENT_TYPE_REVIEW_REQUEST_RESOLVED: ReviewRequestResolvedHandler(
                task_intent_repository=task_intent_repository,
                review_request_repository=review_request_repository,
                farming_task_repository=farming_task_repository,
                operation_plan_repository=operation_plan_repository,
                event_record_repository=event_record_repository,
                pest_disease_control_planning_service=pest_disease_control_planning_service,
            ),
            EVENT_TYPE_EXECUTION_COMPLETED: ExecutionCompletedHandler(
                farming_task_repository=farming_task_repository,
                survey_date_recommendation_service=survey_date_recommendation_service,
            ),
        },
    )


def _parse_payload_date(payload: dict[str, Any], key: str) -> date:
    raw_value = payload[key]
    if isinstance(raw_value, date):
        return raw_value
    if isinstance(raw_value, str) and "-" in raw_value:
        return date.fromisoformat(raw_value)
    return datetime.strptime(str(raw_value), "%Y%m%d").date()


def _parse_stage_dates_payload(payload: dict[str, Any]) -> dict[str, date]:
    raw_stage_dates = payload.get("stageDates") or payload.get("stage_dates")
    if not isinstance(raw_stage_dates, dict):
        return {}
    parsed_stage_dates: dict[str, date] = {}
    for stage_code, raw_date in raw_stage_dates.items():
        normalized_stage_code = str(stage_code).strip()
        if not normalized_stage_code:
            continue
        parsed_stage_dates[normalized_stage_code] = (
            raw_date
            if isinstance(raw_date, date)
            else (date.fromisoformat(raw_date) if isinstance(raw_date, str) and "-" in raw_date else datetime.strptime(str(raw_date), "%Y%m%d").date())
        )
    return parsed_stage_dates


def _resolve_theory_control_operation_window(theory_result) -> tuple[date, date]:
    first_start = min(item.theory_window[0] for item in theory_result.rounds)
    last_end = max(item.theory_window[1] for item in theory_result.rounds)
    return (first_start, last_end)


def _serialize_theory_round_payload(round_item) -> dict[str, Any]:
    return {
        "round": round_item.round,
        "theoryWindow": _format_date_range(round_item.theory_window),
        "targets": dict(round_item.targets),
        "prescription": dict(round_item.prescription),
    }


def _merge_theory_round_targets(theory_result) -> dict[str, Any]:
    merged_targets: dict[str, Any] = {}
    for round_item in theory_result.rounds:
        merged_targets.update(dict(round_item.targets))
    return merged_targets


def _resolve_adjusted_control_operation_window(adjusted_result) -> tuple[date, date]:
    windows = [item.final_window for item in adjusted_result.rounds if item.final_window is not None]
    if not windows:
        raise ValueError("Adjusted control result does not contain final_window.")
    first_start = min(item[0] for item in windows)
    last_end = max(item[1] for item in windows)
    return (first_start, last_end)


def _serialize_adjusted_round_payload(round_item) -> dict[str, Any]:
    payload = {
        "round": round_item.round,
        "theoryWindow": _format_date_range(round_item.theory_window),
        "targets": dict(round_item.targets),
        "suitabilityDates": dict(round_item.suitability_dates),
        "weatherAdjustReason": round_item.weather_adjust_reason,
    }
    if round_item.final_window is not None:
        payload["finalWindow"] = _format_date_range(round_item.final_window)
    else:
        payload["finalWindow"] = []
    return payload


def _merge_adjusted_round_targets(adjusted_result) -> dict[str, Any]:
    merged_targets: dict[str, Any] = {}
    for round_item in adjusted_result.rounds:
        merged_targets.update(dict(round_item.targets))
    return merged_targets


def _resolve_merged_control_operation_window(merged_result) -> tuple[date, date]:
    windows = [item.final_window for item in merged_result.events if item.final_window is not None]
    if not windows:
        raise ValueError("Merged control result does not contain final_window.")
    first_start = min(item[0] for item in windows)
    last_end = max(item[1] for item in windows)
    return (first_start, last_end)


def _serialize_merged_event_payload(event_item) -> dict[str, Any]:
    payload = {
        "type": event_item.event_type,
        "round": event_item.round,
        "theoryWindow": _format_date_range(event_item.theory_window),
        "targets": dict(event_item.targets),
        "suitabilityDates": dict(event_item.suitability_dates),
    }
    if event_item.final_window is not None:
        payload["finalWindow"] = _format_date_range(event_item.final_window)
    else:
        payload["finalWindow"] = []
    return payload


def _merge_merged_event_targets(merged_result) -> dict[str, Any]:
    merged_targets: dict[str, Any] = {}
    for event_item in merged_result.events:
        merged_targets.update(dict(event_item.targets))
    return merged_targets


def _parse_required_payload_bool(payload: dict[str, Any], *keys: str) -> bool:
    raw_value = _get_payload_value(payload, *keys)
    if isinstance(raw_value, bool):
        return raw_value
    if isinstance(raw_value, int) and raw_value in {0, 1}:
        return bool(raw_value)
    if isinstance(raw_value, str):
        normalized = raw_value.strip().lower()
        if normalized in {"true", "1", "yes", "y"}:
            return True
        if normalized in {"false", "0", "no", "n"}:
            return False
    raise ValueError(f"Expected boolean payload field in keys {keys!r}.")


def _parse_optional_payload_datetime(payload: dict[str, Any], *keys: str) -> datetime | None:
    raw_value = _get_payload_value(payload, *keys, required=False)
    if raw_value is None:
        return None
    return _parse_datetime_or_date(raw_value, time.min)


def _get_payload_value(payload: dict[str, Any], *keys: str, required: bool = True) -> Any:
    for key in keys:
        if key in payload:
            return payload[key]
    if required:
        raise ValueError(f"Missing required payload field. expected one of {keys!r}.")
    return None


def _format_date_range(raw_value: tuple[date, date] | None) -> list[str] | None:
    if raw_value is None:
        return None
    return [raw_value[0].isoformat(), raw_value[1].isoformat()]


def _merge_review_override(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        existing_value = merged.get(key)
        if isinstance(existing_value, dict) and isinstance(value, dict):
            merged[key] = _merge_review_override(existing_value, value)
        elif key == "rounds" and isinstance(existing_value, list) and isinstance(value, list):
            merged[key] = _merge_round_overrides(existing_value, value)
        else:
            merged[key] = value
    return merged


def _merge_round_overrides(base_rounds: list[Any], override_rounds: list[Any]) -> list[Any]:
    merged_rounds = list(base_rounds)
    round_index_by_number = {
        item.get("round"): index
        for index, item in enumerate(merged_rounds)
        if isinstance(item, dict) and item.get("round") is not None
    }
    for override_index, override_round in enumerate(override_rounds):
        if not isinstance(override_round, dict):
            if override_index >= len(merged_rounds):
                raise ValueError(f"Cannot adjust round index {override_index}; existing round does not exist.")
            merged_rounds[override_index] = override_round
            continue

        target_index = None
        if override_round.get("round") is not None:
            target_index = round_index_by_number.get(override_round.get("round"))
        elif override_index < len(merged_rounds):
            target_index = override_index
        if target_index is None:
            raise ValueError(f"Cannot adjust round {override_round.get('round')!r}; existing round does not exist.")

        existing_round = merged_rounds[target_index]
        if isinstance(existing_round, dict):
            merged_rounds[target_index] = _merge_review_override(existing_round, override_round)
        else:
            merged_rounds[target_index] = override_round
    return merged_rounds


def _has_disease_pest_theory_window_override(overrides: dict[str, Any]) -> bool:
    proposed_plan = overrides.get("proposedPlan")
    if not isinstance(proposed_plan, dict):
        return False
    theory_plan = proposed_plan.get("theoryPlan")
    if not isinstance(theory_plan, dict):
        return False
    rounds = theory_plan.get("rounds")
    if not isinstance(rounds, list):
        return False
    return any(isinstance(item, dict) and "theory_window" in item for item in rounds)


def _parse_optional_datetime_or_date_range_start(raw_value: Any) -> datetime | None:
    if raw_value is None:
        return None
    if isinstance(raw_value, list | tuple):
        return _parse_optional_datetime_or_date_range_start(raw_value[0]) if raw_value else None
    return _parse_datetime_or_date(raw_value, time.min)


def _parse_optional_datetime_or_date_range_end(raw_value: Any) -> datetime | None:
    if raw_value is None:
        return None
    if isinstance(raw_value, list | tuple):
        return _parse_optional_datetime_or_date_range_end(raw_value[-1]) if raw_value else None
    return _parse_datetime_or_date(raw_value, time.max)


def _parse_datetime_or_date(raw_value: Any, default_time: time) -> datetime:
    if isinstance(raw_value, datetime):
        return raw_value.replace(tzinfo=None)
    if isinstance(raw_value, date):
        return datetime.combine(raw_value, default_time)
    if isinstance(raw_value, str) and "T" in raw_value:
        return datetime.fromisoformat(raw_value).replace(tzinfo=None)
    if isinstance(raw_value, str):
        return datetime.combine(date.fromisoformat(raw_value), default_time)
    raise ValueError(f"Unsupported datetime value: {raw_value!r}.")


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _merge_orchestrator_results(left: OrchestratorResult, right: OrchestratorResult) -> OrchestratorResult:
    return OrchestratorResult(
        calendar_items=[*left.calendar_items, *right.calendar_items],
        farming_tasks=[*left.farming_tasks, *right.farming_tasks],
        task_intents=[*left.task_intents, *right.task_intents],
        review_requests=[*left.review_requests, *right.review_requests],
        operation_plans=[*left.operation_plans, *right.operation_plans],
        crop_stage_states=[*left.crop_stage_states, *right.crop_stage_states],
        crop_thermal_time_states=[*left.crop_thermal_time_states, *right.crop_thermal_time_states],
        stage_prediction_snapshots=[*left.stage_prediction_snapshots, *right.stage_prediction_snapshots],
    )


def _summarize_orchestrator_result(result: OrchestratorResult) -> dict[str, int]:
    return {
        "calendar_items": len(result.calendar_items),
        "farming_tasks": len(result.farming_tasks),
        "task_intents": len(result.task_intents),
        "review_requests": len(result.review_requests),
        "operation_plans": len(result.operation_plans),
        "crop_stage_states": len(result.crop_stage_states),
        "crop_thermal_time_states": len(result.crop_thermal_time_states),
        "stage_prediction_snapshots": len(result.stage_prediction_snapshots),
    }
