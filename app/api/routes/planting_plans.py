from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field as PydanticField
from sqlalchemy.orm import Session

from app.api.deps import get_planting_plan_query_service, get_planting_plan_service
from app.db.session import get_db
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
from app.services import (
    ActualStageRecordedInput,
    PlantingPlanCreateInput,
    PlantingPlanDetails,
    PlantingPlanQueryService,
    PlantingPlanService,
    PlantingPlanUpdateInput,
)

router = APIRouter(prefix="/planting-plans")


class PlantingPlanCreateRequest(BaseModel):
    plan_name: str
    farm_id: int
    field_ids: list[int] = PydanticField(default_factory=list)
    culti_type_code: int
    planting_method_code: int
    crop_name: str
    variety_id: int
    sowing_date: date
    year: int | None = None
    transplant_date: date | None = None
    harvest_date: date | None = None
    transplant_leaf_age: Decimal | None = None
    previous_harvest_date: date | None = None
    ratoon_first_season_harvest_date: date | None = None
    expected_harvest_date: date | None = None
    status: str = "draft"
    task_generation_window_days: int = 14
    metadata: dict[str, Any] = PydanticField(default_factory=dict)


class PlantingPlanUpdateRequest(BaseModel):
    plan_name: str | None = None
    farm_id: int | None = None
    field_ids: list[int] | None = None
    culti_type_code: int | None = None
    planting_method_code: int | None = None
    crop_name: str | None = None
    variety_id: int | None = None
    sowing_date: date | None = None
    year: int | None = None
    transplant_date: date | None = None
    harvest_date: date | None = None
    transplant_leaf_age: Decimal | None = None
    previous_harvest_date: date | None = None
    ratoon_first_season_harvest_date: date | None = None
    expected_harvest_date: date | None = None
    status: str | None = None
    task_generation_window_days: int | None = None
    metadata: dict[str, Any] | None = None


class ActualStageRecordedRequest(BaseModel):
    stages: dict[str, date] = PydanticField(..., min_length=1)
    source_record_id: str | None = None
    operator_id: str | None = None
    note: str | None = None
    metadata: dict[str, Any] = PydanticField(default_factory=dict)


class PlantingPlanResponse(BaseModel):
    id: int
    plan_code: str
    plan_name: str
    farm_id: int
    field_ids: list[int]
    year: int | None
    culti_type_code: int
    planting_method_code: int
    crop_name: str
    variety_id: int
    variety_name: str
    sowing_date: date
    transplant_date: date | None
    harvest_date: date | None
    transplant_leaf_age: Decimal | None
    previous_harvest_date: date | None
    ratoon_first_season_harvest_date: date | None
    expected_harvest_date: date | None
    status: str
    task_generation_window_days: int
    metadata: dict[str, Any]
    created_at: datetime | None
    updated_at: datetime | None


class CalendarItemResponse(BaseModel):
    id: int
    planting_plan_id: int
    stage_code: str | None
    task_category: str
    task_subtype: str
    title: str
    description: str | None
    suggested_start_date: date
    suggested_end_date: date
    status: str
    generation_condition: dict[str, Any]
    parent_task_id: int | None
    source_execution_id: int | None
    source_execution_record_id: int | None
    generated_task_id: int | None
    created_at: datetime | None
    updated_at: datetime | None


class FarmingTaskResponse(BaseModel):
    id: int
    planting_plan_id: int
    calendar_item_id: int | None
    task_intent_id: int | None
    review_request_id: int | None
    task_category: str
    task_subtype: str
    title: str
    description: str | None
    target_stage_code: str | None
    planned_start_at: datetime | None
    planned_end_at: datetime | None
    priority: str
    status: str
    execution_mode: str
    generation_reason: str | None
    parent_task_id: int | None
    source_execution_id: int | None
    source_execution_record_id: int | None
    created_at: datetime | None
    updated_at: datetime | None


class TaskIntentResponse(BaseModel):
    id: int
    planting_plan_id: int
    task_category: str
    task_subtype: str
    priority: str
    status: str
    trigger_type: str
    trigger_summary: str | None
    rule_result: dict[str, Any]
    suggested_action: str | None
    need_more_info_fields: dict[str, Any]
    no_action_reason: str | None
    parent_task_id: int | None
    source_execution_id: int | None
    source_execution_record_id: int | None
    converted_task_id: int | None
    source_event_id: int | None
    created_at: datetime | None
    updated_at: datetime | None


class ReviewRequestResponse(BaseModel):
    id: int
    planting_plan_id: int
    review_type: str
    status: str
    priority: str
    assigned_user_id: str | None
    source_entity_type: str
    source_entity_id: int
    title: str
    description: str | None
    decision: str | None
    decision_payload: dict[str, Any]
    resolved_by: str | None
    resolved_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None


class EventRecordResponse(BaseModel):
    id: int
    planting_plan_id: int | None
    event_type: str
    event_category: str
    event_source: str
    source_system: str | None
    source_record_id: str | None
    payload: dict[str, Any]
    occurred_at: datetime
    received_at: datetime | None
    processed_at: datetime | None
    processing_status: str
    error_message: str | None
    created_at: datetime | None
    updated_at: datetime | None


class CropStageStateResponse(BaseModel):
    id: int
    planting_plan_id: int
    current_stage_code: str
    current_stage_name: str
    stage_source: str
    effective_date: date
    source_snapshot_id: int | None
    last_updated_at: datetime | None
    version: int
    created_at: datetime | None
    updated_at: datetime | None


class CropThermalTimeStateResponse(BaseModel):
    id: int
    planting_plan_id: int
    accumulated_thermal_time: Decimal
    thermal_time_unit: str
    base_temperature: Decimal | None
    start_date: date | None
    last_calculated_date: date | None
    threshold_snapshot_id: int | None
    data_version: str | None
    created_at: datetime | None
    updated_at: datetime | None


class StagePredictionSnapshotResponse(BaseModel):
    id: int
    planting_plan_id: int
    prediction_version: int
    prediction_source: str
    algorithm_code: str
    algorithm_version: str | None
    generated_at: datetime | None
    input_payload: dict[str, Any]
    stage_timeline: dict[str, Any]
    thermal_thresholds: dict[str, Any]
    source_event_id: int | None
    created_at: datetime | None
    updated_at: datetime | None


class PlantingPlanDebugOperationPlanResponse(BaseModel):
    id: int
    farming_task_id: int
    plan_type: str
    status: str
    version: int
    algorithm_code: str | None
    algorithm_version: str | None
    operation_window_start: datetime | None
    operation_window_end: datetime | None
    execution_mode: str
    parameters: dict[str, Any]
    prescription_map: dict[str, Any]
    basis: str | None
    source_event_id: int | None
    created_at: datetime | None
    updated_at: datetime | None


class PlantingPlanDebugSnapshotResponse(BaseModel):
    planting_plan: PlantingPlanResponse
    calendar_items: list[CalendarItemResponse]
    farming_tasks: list[FarmingTaskResponse]
    task_intents: list[TaskIntentResponse]
    review_requests: list[ReviewRequestResponse]
    operation_plans: list[PlantingPlanDebugOperationPlanResponse]
    event_records: list[EventRecordResponse]
    crop_stage_state: CropStageStateResponse | None
    crop_thermal_time_state: CropThermalTimeStateResponse | None
    stage_prediction_snapshots: list[StagePredictionSnapshotResponse]


@router.post("", response_model=PlantingPlanResponse, status_code=status.HTTP_201_CREATED)
def create_planting_plan(
    payload: PlantingPlanCreateRequest,
    service: PlantingPlanService = Depends(get_planting_plan_service),
    db: Session = Depends(get_db),
) -> PlantingPlanResponse:
    try:
        result = service.create(
            PlantingPlanCreateInput(
                plan_name=payload.plan_name,
                farm_id=payload.farm_id,
                field_ids=payload.field_ids,
                culti_type_code=payload.culti_type_code,
                planting_method_code=payload.planting_method_code,
                crop_name=payload.crop_name,
                variety_id=payload.variety_id,
                sowing_date=payload.sowing_date,
                year=payload.year,
                transplant_date=payload.transplant_date,
                harvest_date=payload.harvest_date,
                transplant_leaf_age=payload.transplant_leaf_age,
                previous_harvest_date=payload.previous_harvest_date,
                ratoon_first_season_harvest_date=payload.ratoon_first_season_harvest_date,
                expected_harvest_date=payload.expected_harvest_date,
                status=payload.status,
                task_generation_window_days=payload.task_generation_window_days,
                metadata_payload=payload.metadata,
            ),
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    return _serialize_planting_plan(result)


@router.get("/{planting_plan_id}/calendar-items", response_model=list[CalendarItemResponse])
def list_planting_plan_calendar_items(
    planting_plan_id: int,
    service: PlantingPlanQueryService = Depends(get_planting_plan_query_service),
) -> list[CalendarItemResponse]:
    try:
        result = service.list_calendar_items(planting_plan_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [_serialize_calendar_item(item) for item in result]


@router.get("/{planting_plan_id}/tasks", response_model=list[FarmingTaskResponse])
def list_planting_plan_tasks(
    planting_plan_id: int,
    service: PlantingPlanQueryService = Depends(get_planting_plan_query_service),
) -> list[FarmingTaskResponse]:
    try:
        result = service.list_farming_tasks(planting_plan_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [_serialize_farming_task(item) for item in result]


@router.get("/{planting_plan_id}/task-intents", response_model=list[TaskIntentResponse])
def list_planting_plan_task_intents(
    planting_plan_id: int,
    service: PlantingPlanQueryService = Depends(get_planting_plan_query_service),
) -> list[TaskIntentResponse]:
    try:
        result = service.list_task_intents(planting_plan_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [_serialize_task_intent(item) for item in result]


@router.get("/{planting_plan_id}/review-requests", response_model=list[ReviewRequestResponse])
def list_planting_plan_review_requests(
    planting_plan_id: int,
    service: PlantingPlanQueryService = Depends(get_planting_plan_query_service),
) -> list[ReviewRequestResponse]:
    try:
        result = service.list_review_requests(planting_plan_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [_serialize_review_request(item) for item in result]


@router.get("/{planting_plan_id}/event-records", response_model=list[EventRecordResponse])
def list_planting_plan_event_records(
    planting_plan_id: int,
    service: PlantingPlanQueryService = Depends(get_planting_plan_query_service),
) -> list[EventRecordResponse]:
    try:
        result = service.list_event_records(planting_plan_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [_serialize_event_record(item) for item in result]


@router.get("/{planting_plan_id}/stage-state", response_model=CropStageStateResponse | None)
def get_planting_plan_stage_state(
    planting_plan_id: int,
    service: PlantingPlanQueryService = Depends(get_planting_plan_query_service),
) -> CropStageStateResponse | None:
    try:
        result = service.get_crop_stage_state(planting_plan_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _serialize_crop_stage_state(result) if result is not None else None


@router.get("/{planting_plan_id}/thermal-time-state", response_model=CropThermalTimeStateResponse | None)
def get_planting_plan_thermal_time_state(
    planting_plan_id: int,
    service: PlantingPlanQueryService = Depends(get_planting_plan_query_service),
) -> CropThermalTimeStateResponse | None:
    try:
        result = service.get_crop_thermal_time_state(planting_plan_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _serialize_crop_thermal_time_state(result) if result is not None else None


@router.get("/{planting_plan_id}/stage-predictions/latest", response_model=StagePredictionSnapshotResponse | None)
def get_latest_stage_prediction_snapshot(
    planting_plan_id: int,
    service: PlantingPlanQueryService = Depends(get_planting_plan_query_service),
) -> StagePredictionSnapshotResponse | None:
    try:
        result = service.get_latest_stage_prediction_snapshot(planting_plan_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _serialize_stage_prediction_snapshot(result) if result is not None else None


@router.get("/{planting_plan_id}/debug-snapshot", response_model=PlantingPlanDebugSnapshotResponse)
def get_planting_plan_debug_snapshot(
    planting_plan_id: int,
    service: PlantingPlanQueryService = Depends(get_planting_plan_query_service),
) -> PlantingPlanDebugSnapshotResponse:
    try:
        result = service.get_debug_snapshot(planting_plan_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return PlantingPlanDebugSnapshotResponse(
        planting_plan=_serialize_planting_plan(
            PlantingPlanDetails(planting_plan=result.planting_plan, field_ids=result.field_ids),
        ),
        calendar_items=[_serialize_calendar_item(item) for item in result.calendar_items],
        farming_tasks=[_serialize_farming_task(item) for item in result.farming_tasks],
        task_intents=[_serialize_task_intent(item) for item in result.task_intents],
        review_requests=[_serialize_review_request(item) for item in result.review_requests],
        operation_plans=[_serialize_debug_operation_plan(item) for item in result.operation_plans],
        event_records=[_serialize_event_record(item) for item in result.event_records],
        crop_stage_state=(
            _serialize_crop_stage_state(result.crop_stage_state) if result.crop_stage_state is not None else None
        ),
        crop_thermal_time_state=(
            _serialize_crop_thermal_time_state(result.crop_thermal_time_state)
            if result.crop_thermal_time_state is not None
            else None
        ),
        stage_prediction_snapshots=[
            _serialize_stage_prediction_snapshot(item)
            for item in result.stage_prediction_snapshots
        ],
    )


@router.post(
    "/{planting_plan_id}/actual-stages",
    response_model=list[EventRecordResponse],
    status_code=status.HTTP_201_CREATED,
)
def record_actual_stages(
    planting_plan_id: int,
    payload: ActualStageRecordedRequest,
    service: PlantingPlanService = Depends(get_planting_plan_service),
    db: Session = Depends(get_db),
) -> list[EventRecordResponse]:
    try:
        result = service.record_actual_stages(
            planting_plan_id,
            ActualStageRecordedInput(
                stage_dates=payload.stages,
                source_record_id=payload.source_record_id,
                operator_id=payload.operator_id,
                note=payload.note,
                metadata_payload=payload.metadata,
            ),
        )
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    return [_serialize_event_record(item) for item in result]


@router.get("/{planting_plan_id}", response_model=PlantingPlanResponse)
def get_planting_plan(
    planting_plan_id: int,
    service: PlantingPlanService = Depends(get_planting_plan_service),
) -> PlantingPlanResponse:
    try:
        result = service.get_details(planting_plan_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _serialize_planting_plan(result)


@router.get("", response_model=list[PlantingPlanResponse])
def list_planting_plans(
    statuses: list[str] | None = Query(default=None),
    service: PlantingPlanService = Depends(get_planting_plan_service),
) -> list[PlantingPlanResponse]:
    try:
        result = service.list_by_statuses(statuses)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return [_serialize_planting_plan(item) for item in result]


@router.patch("/{planting_plan_id}", response_model=PlantingPlanResponse)
def update_planting_plan(
    planting_plan_id: int,
    payload: PlantingPlanUpdateRequest,
    service: PlantingPlanService = Depends(get_planting_plan_service),
    db: Session = Depends(get_db),
) -> PlantingPlanResponse:
    try:
        result = service.update(
            planting_plan_id,
            PlantingPlanUpdateInput(
                plan_name=payload.plan_name,
                farm_id=payload.farm_id,
                field_ids=payload.field_ids,
                culti_type_code=payload.culti_type_code,
                planting_method_code=payload.planting_method_code,
                crop_name=payload.crop_name,
                variety_id=payload.variety_id,
                sowing_date=payload.sowing_date,
                year=payload.year,
                transplant_date=payload.transplant_date,
                harvest_date=payload.harvest_date,
                transplant_leaf_age=payload.transplant_leaf_age,
                previous_harvest_date=payload.previous_harvest_date,
                ratoon_first_season_harvest_date=payload.ratoon_first_season_harvest_date,
                expected_harvest_date=payload.expected_harvest_date,
                status=payload.status,
                task_generation_window_days=payload.task_generation_window_days,
                metadata_payload=payload.metadata,
            ),
        )
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    return _serialize_planting_plan(result)


def _serialize_planting_plan(details: PlantingPlanDetails) -> PlantingPlanResponse:
    planting_plan = details.planting_plan
    return PlantingPlanResponse(
        id=planting_plan.id,
        plan_code=planting_plan.plan_code,
        plan_name=planting_plan.plan_name,
        farm_id=planting_plan.farm_id,
        field_ids=details.field_ids,
        year=planting_plan.year,
        culti_type_code=planting_plan.culti_type_code,
        planting_method_code=planting_plan.planting_method_code,
        crop_name=planting_plan.crop_name,
        variety_id=planting_plan.variety_id,
        variety_name=planting_plan.variety_name,
        sowing_date=planting_plan.sowing_date,
        transplant_date=planting_plan.transplant_date,
        harvest_date=planting_plan.harvest_date,
        transplant_leaf_age=planting_plan.transplant_leaf_age,
        previous_harvest_date=planting_plan.previous_harvest_date,
        ratoon_first_season_harvest_date=planting_plan.ratoon_first_season_harvest_date,
        expected_harvest_date=planting_plan.expected_harvest_date,
        status=planting_plan.status,
        task_generation_window_days=planting_plan.task_generation_window_days,
        metadata=planting_plan.metadata_payload,
        created_at=planting_plan.created_at,
        updated_at=planting_plan.updated_at,
    )


def _serialize_calendar_item(calendar_item: CalendarItem) -> CalendarItemResponse:
    return CalendarItemResponse(
        id=calendar_item.id,
        planting_plan_id=calendar_item.planting_plan_id,
        stage_code=calendar_item.stage_code,
        task_category=calendar_item.task_category,
        task_subtype=calendar_item.task_subtype,
        title=calendar_item.title,
        description=calendar_item.description,
        suggested_start_date=calendar_item.suggested_start_date,
        suggested_end_date=calendar_item.suggested_end_date,
        status=calendar_item.status,
        generation_condition=calendar_item.generation_condition,
        parent_task_id=calendar_item.parent_task_id,
        source_execution_id=calendar_item.source_execution_id,
        source_execution_record_id=calendar_item.source_execution_record_id,
        generated_task_id=calendar_item.generated_task_id,
        created_at=calendar_item.created_at,
        updated_at=calendar_item.updated_at,
    )


def _serialize_farming_task(farming_task: FarmingTask) -> FarmingTaskResponse:
    return FarmingTaskResponse(
        id=farming_task.id,
        planting_plan_id=farming_task.planting_plan_id,
        calendar_item_id=farming_task.calendar_item_id,
        task_intent_id=farming_task.task_intent_id,
        review_request_id=farming_task.review_request_id,
        task_category=farming_task.task_category,
        task_subtype=farming_task.task_subtype,
        title=farming_task.title,
        description=farming_task.description,
        target_stage_code=farming_task.target_stage_code,
        planned_start_at=farming_task.planned_start_at,
        planned_end_at=farming_task.planned_end_at,
        priority=farming_task.priority,
        status=farming_task.status,
        execution_mode=farming_task.execution_mode,
        generation_reason=farming_task.generation_reason,
        parent_task_id=farming_task.parent_task_id,
        source_execution_id=farming_task.source_execution_id,
        source_execution_record_id=farming_task.source_execution_record_id,
        created_at=farming_task.created_at,
        updated_at=farming_task.updated_at,
    )


def _serialize_task_intent(task_intent: TaskIntent) -> TaskIntentResponse:
    return TaskIntentResponse(
        id=task_intent.id,
        planting_plan_id=task_intent.planting_plan_id,
        task_category=task_intent.task_category,
        task_subtype=task_intent.task_subtype,
        priority=task_intent.priority,
        status=task_intent.status,
        trigger_type=task_intent.trigger_type,
        trigger_summary=task_intent.trigger_summary,
        rule_result=task_intent.rule_result,
        suggested_action=task_intent.suggested_action,
        need_more_info_fields=task_intent.need_more_info_fields,
        no_action_reason=task_intent.no_action_reason,
        parent_task_id=task_intent.parent_task_id,
        source_execution_id=task_intent.source_execution_id,
        source_execution_record_id=task_intent.source_execution_record_id,
        converted_task_id=task_intent.converted_task_id,
        source_event_id=task_intent.source_event_id,
        created_at=task_intent.created_at,
        updated_at=task_intent.updated_at,
    )


def _serialize_review_request(review_request: ReviewRequest) -> ReviewRequestResponse:
    return ReviewRequestResponse(
        id=review_request.id,
        planting_plan_id=review_request.planting_plan_id,
        review_type=review_request.review_type,
        status=review_request.status,
        priority=review_request.priority,
        assigned_user_id=review_request.assigned_user_id,
        source_entity_type=review_request.source_entity_type,
        source_entity_id=review_request.source_entity_id,
        title=review_request.title,
        description=review_request.description,
        decision=review_request.decision,
        decision_payload=review_request.decision_payload,
        resolved_by=review_request.resolved_by,
        resolved_at=review_request.resolved_at,
        created_at=review_request.created_at,
        updated_at=review_request.updated_at,
    )


def _serialize_event_record(event_record: EventRecord) -> EventRecordResponse:
    return EventRecordResponse(
        id=event_record.id,
        planting_plan_id=event_record.planting_plan_id,
        event_type=event_record.event_type,
        event_category=event_record.event_category,
        event_source=event_record.event_source,
        source_system=event_record.source_system,
        source_record_id=event_record.source_record_id,
        payload=event_record.payload,
        occurred_at=event_record.occurred_at,
        received_at=event_record.received_at,
        processed_at=event_record.processed_at,
        processing_status=event_record.processing_status,
        error_message=event_record.error_message,
        created_at=event_record.created_at,
        updated_at=event_record.updated_at,
    )


def _serialize_crop_stage_state(crop_stage_state: CropStageState) -> CropStageStateResponse:
    return CropStageStateResponse(
        id=crop_stage_state.id,
        planting_plan_id=crop_stage_state.planting_plan_id,
        current_stage_code=crop_stage_state.current_stage_code,
        current_stage_name=crop_stage_state.current_stage_name,
        stage_source=crop_stage_state.stage_source,
        effective_date=crop_stage_state.effective_date,
        source_snapshot_id=crop_stage_state.source_snapshot_id,
        last_updated_at=crop_stage_state.last_updated_at,
        version=crop_stage_state.version,
        created_at=crop_stage_state.created_at,
        updated_at=crop_stage_state.updated_at,
    )


def _serialize_crop_thermal_time_state(
    crop_thermal_time_state: CropThermalTimeState,
) -> CropThermalTimeStateResponse:
    return CropThermalTimeStateResponse(
        id=crop_thermal_time_state.id,
        planting_plan_id=crop_thermal_time_state.planting_plan_id,
        accumulated_thermal_time=crop_thermal_time_state.accumulated_thermal_time,
        thermal_time_unit=crop_thermal_time_state.thermal_time_unit,
        base_temperature=crop_thermal_time_state.base_temperature,
        start_date=crop_thermal_time_state.start_date,
        last_calculated_date=crop_thermal_time_state.last_calculated_date,
        threshold_snapshot_id=crop_thermal_time_state.threshold_snapshot_id,
        data_version=crop_thermal_time_state.data_version,
        created_at=crop_thermal_time_state.created_at,
        updated_at=crop_thermal_time_state.updated_at,
    )


def _serialize_stage_prediction_snapshot(
    stage_prediction_snapshot: StagePredictionSnapshot,
) -> StagePredictionSnapshotResponse:
    return StagePredictionSnapshotResponse(
        id=stage_prediction_snapshot.id,
        planting_plan_id=stage_prediction_snapshot.planting_plan_id,
        prediction_version=stage_prediction_snapshot.prediction_version,
        prediction_source=stage_prediction_snapshot.prediction_source,
        algorithm_code=stage_prediction_snapshot.algorithm_code,
        algorithm_version=stage_prediction_snapshot.algorithm_version,
        generated_at=stage_prediction_snapshot.generated_at,
        input_payload=stage_prediction_snapshot.input_payload,
        stage_timeline=stage_prediction_snapshot.stage_timeline,
        thermal_thresholds=stage_prediction_snapshot.thermal_thresholds,
        source_event_id=stage_prediction_snapshot.source_event_id,
        created_at=stage_prediction_snapshot.created_at,
        updated_at=stage_prediction_snapshot.updated_at,
    )


def _serialize_debug_operation_plan(
    operation_plan: OperationPlan,
) -> PlantingPlanDebugOperationPlanResponse:
    return PlantingPlanDebugOperationPlanResponse(
        id=operation_plan.id,
        farming_task_id=operation_plan.farming_task_id,
        plan_type=operation_plan.plan_type,
        status=operation_plan.status,
        version=operation_plan.version,
        algorithm_code=operation_plan.algorithm_code,
        algorithm_version=operation_plan.algorithm_version,
        operation_window_start=operation_plan.operation_window_start,
        operation_window_end=operation_plan.operation_window_end,
        execution_mode=operation_plan.execution_mode,
        parameters=operation_plan.parameters,
        prescription_map=operation_plan.prescription_map,
        basis=operation_plan.basis,
        source_event_id=operation_plan.source_event_id,
        created_at=operation_plan.created_at,
        updated_at=operation_plan.updated_at,
    )
