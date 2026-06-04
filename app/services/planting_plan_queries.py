from __future__ import annotations

from dataclasses import dataclass

from app.models import (
    CalendarItem,
    CropStageState,
    CropThermalTimeState,
    EventRecord,
    FarmingTask,
    OperationPlan,
    PlantingPlan,
    ReviewRequest,
    StagePredictionSnapshot,
    TaskIntent,
)
from app.repositories import (
    CalendarItemRepository,
    CropStageStateRepository,
    CropThermalTimeStateRepository,
    EventRecordRepository,
    FarmingTaskRepository,
    OperationPlanRepository,
    PlantingPlanRepository,
    PlantingPlanFieldRelationRepository,
    ReviewRequestRepository,
    StagePredictionSnapshotRepository,
    TaskIntentRepository,
)


@dataclass(slots=True)
class PlantingPlanM2Snapshot:
    planting_plan: PlantingPlan
    calendar_items: list[CalendarItem]
    farming_tasks: list[FarmingTask]
    task_intents: list[TaskIntent]
    review_requests: list[ReviewRequest]
    event_records: list[EventRecord]
    crop_stage_state: CropStageState | None = None
    crop_thermal_time_state: CropThermalTimeState | None = None
    latest_stage_prediction_snapshot: StagePredictionSnapshot | None = None


@dataclass(slots=True)
class PlantingPlanDebugSnapshot:
    planting_plan: PlantingPlan
    field_ids: list[int]
    calendar_items: list[CalendarItem]
    farming_tasks: list[FarmingTask]
    task_intents: list[TaskIntent]
    review_requests: list[ReviewRequest]
    operation_plans: list[OperationPlan]
    event_records: list[EventRecord]
    stage_prediction_snapshots: list[StagePredictionSnapshot]
    crop_stage_state: CropStageState | None = None
    crop_thermal_time_state: CropThermalTimeState | None = None


class PlantingPlanQueryService:
    def __init__(
        self,
        planting_plan_repository: PlantingPlanRepository,
        planting_plan_field_relation_repository: PlantingPlanFieldRelationRepository,
        calendar_item_repository: CalendarItemRepository,
        farming_task_repository: FarmingTaskRepository,
        task_intent_repository: TaskIntentRepository,
        review_request_repository: ReviewRequestRepository,
        operation_plan_repository: OperationPlanRepository,
        event_record_repository: EventRecordRepository,
        crop_stage_state_repository: CropStageStateRepository,
        crop_thermal_time_state_repository: CropThermalTimeStateRepository,
        stage_prediction_snapshot_repository: StagePredictionSnapshotRepository,
    ) -> None:
        self.planting_plan_repository = planting_plan_repository
        self.planting_plan_field_relation_repository = planting_plan_field_relation_repository
        self.calendar_item_repository = calendar_item_repository
        self.farming_task_repository = farming_task_repository
        self.task_intent_repository = task_intent_repository
        self.review_request_repository = review_request_repository
        self.operation_plan_repository = operation_plan_repository
        self.event_record_repository = event_record_repository
        self.crop_stage_state_repository = crop_stage_state_repository
        self.crop_thermal_time_state_repository = crop_thermal_time_state_repository
        self.stage_prediction_snapshot_repository = stage_prediction_snapshot_repository

    def list_calendar_items(self, planting_plan_id: int) -> list[CalendarItem]:
        self._get_plan(planting_plan_id)
        return self.calendar_item_repository.list_current_by_plan(planting_plan_id)

    def list_farming_tasks(self, planting_plan_id: int) -> list[FarmingTask]:
        self._get_plan(planting_plan_id)
        return self.farming_task_repository.list_by_plan(planting_plan_id)

    def list_task_intents(self, planting_plan_id: int) -> list[TaskIntent]:
        self._get_plan(planting_plan_id)
        return self.task_intent_repository.list_current_by_plan(planting_plan_id)

    def list_review_requests(self, planting_plan_id: int) -> list[ReviewRequest]:
        self._get_plan(planting_plan_id)
        return self.review_request_repository.list_current_by_plan(planting_plan_id)

    def list_event_records(self, planting_plan_id: int) -> list[EventRecord]:
        self._get_plan(planting_plan_id)
        return self.event_record_repository.list_by_plan(planting_plan_id)

    def get_crop_stage_state(self, planting_plan_id: int) -> CropStageState | None:
        self._get_plan(planting_plan_id)
        return self.crop_stage_state_repository.get_by_plan(planting_plan_id)

    def get_crop_thermal_time_state(self, planting_plan_id: int) -> CropThermalTimeState | None:
        self._get_plan(planting_plan_id)
        return self.crop_thermal_time_state_repository.get_by_plan(planting_plan_id)

    def get_latest_stage_prediction_snapshot(self, planting_plan_id: int) -> StagePredictionSnapshot | None:
        self._get_plan(planting_plan_id)
        return self.stage_prediction_snapshot_repository.get_latest_by_plan(planting_plan_id)

    def get_m2_snapshot(self, planting_plan_id: int) -> PlantingPlanM2Snapshot:
        planting_plan = self._get_plan(planting_plan_id)
        return PlantingPlanM2Snapshot(
            planting_plan=planting_plan,
            calendar_items=self.calendar_item_repository.list_current_by_plan(planting_plan_id),
            farming_tasks=self.farming_task_repository.list_by_plan(planting_plan_id),
            task_intents=self.task_intent_repository.list_current_by_plan(planting_plan_id),
            review_requests=self.review_request_repository.list_current_by_plan(planting_plan_id),
            event_records=self.event_record_repository.list_by_plan(planting_plan_id),
            crop_stage_state=self.crop_stage_state_repository.get_by_plan(planting_plan_id),
            crop_thermal_time_state=self.crop_thermal_time_state_repository.get_by_plan(planting_plan_id),
            latest_stage_prediction_snapshot=self.stage_prediction_snapshot_repository.get_latest_by_plan(planting_plan_id),
        )

    def get_debug_snapshot(self, planting_plan_id: int) -> PlantingPlanDebugSnapshot:
        planting_plan = self._get_plan(planting_plan_id)
        return PlantingPlanDebugSnapshot(
            planting_plan=planting_plan,
            field_ids=self.planting_plan_field_relation_repository.list_field_ids_by_plan(planting_plan_id),
            calendar_items=self.calendar_item_repository.list_current_by_plan(planting_plan_id),
            farming_tasks=self.farming_task_repository.list_by_plan(planting_plan_id),
            task_intents=self.task_intent_repository.list_current_by_plan(planting_plan_id),
            review_requests=self.review_request_repository.list_current_by_plan(planting_plan_id),
            operation_plans=self.operation_plan_repository.list_by_plan(planting_plan_id),
            event_records=self.event_record_repository.list_by_plan(planting_plan_id),
            stage_prediction_snapshots=self.stage_prediction_snapshot_repository.list_by_plan(planting_plan_id),
            crop_stage_state=self.crop_stage_state_repository.get_by_plan(planting_plan_id),
            crop_thermal_time_state=self.crop_thermal_time_state_repository.get_by_plan(planting_plan_id),
        )

    def _get_plan(self, planting_plan_id: int) -> PlantingPlan:
        planting_plan = self.planting_plan_repository.get(planting_plan_id)
        if planting_plan is None:
            raise LookupError(f"Planting plan {planting_plan_id} does not exist.")
        return planting_plan
