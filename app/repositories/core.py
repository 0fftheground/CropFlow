from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models import (
    AdministrativeDivision,
    CalendarItem,
    CodeDict,
    CropStageDict,
    CropStageState,
    CropThermalTimeState,
    EventRecord,
    Execution,
    ExecutionRecord,
    Farm,
    Field,
    FarmFieldRelation,
    FarmingTask,
    OperationPlan,
    PlantingPlan,
    PlantingPlanFieldRelation,
    RiceControlWindowLevel1,
    RiceVariety,
    ReviewRequest,
    StagePredictionSnapshot,
    TaskIntent,
    WeatherSnapshot,
)


class Repository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, entity: Any) -> Any:
        self.session.add(entity)
        return entity

    def flush(self) -> None:
        self.session.flush()

    def add_all(self, entities: list[Any]) -> None:
        self.session.add_all(entities)

    def delete(self, entity: Any) -> None:
        self.session.delete(entity)


class PlantingPlanRepository(Repository):
    def get(self, planting_plan_id: int) -> PlantingPlan | None:
        return self.session.get(PlantingPlan, planting_plan_id)

    def get_by_plan_code(self, plan_code: str) -> PlantingPlan | None:
        stmt = select(PlantingPlan).where(PlantingPlan.plan_code == plan_code)
        return self.session.scalar(stmt)

    def list_by_statuses(self, statuses: list[str] | None = None) -> list[PlantingPlan]:
        stmt = select(PlantingPlan)
        if statuses:
            stmt = stmt.where(PlantingPlan.status.in_(statuses))
        stmt = stmt.order_by(PlantingPlan.created_at.desc(), PlantingPlan.id.desc())
        return list(self.session.scalars(stmt))

    def exists_by_farm_id(self, farm_id: int) -> bool:
        stmt = select(PlantingPlan.id).where(PlantingPlan.farm_id == farm_id).limit(1)
        return self.session.scalar(stmt) is not None


class FarmRepository(Repository):
    def get(self, farm_id: int) -> Farm | None:
        return self.session.get(Farm, farm_id)

    def get_by_external_farm_id(self, external_farm_id: str) -> Farm | None:
        stmt = select(Farm).where(Farm.external_farm_id == external_farm_id)
        return self.session.scalar(stmt)

    def list_all(self) -> list[Farm]:
        stmt = select(Farm).order_by(Farm.created_at.desc(), Farm.id.desc())
        return list(self.session.scalars(stmt))


class CodeDictRepository(Repository):
    def get_by_code(self, code: int) -> CodeDict | None:
        stmt = select(CodeDict).where(CodeDict.code == code)
        return self.session.scalar(stmt)

    def list_active_by_category(self, category: str) -> list[CodeDict]:
        stmt = (
            select(CodeDict)
            .where(CodeDict.category == category)
            .where(CodeDict.is_active.is_(True))
            .order_by(CodeDict.code.asc())
        )
        return list(self.session.scalars(stmt))


class AdministrativeDivisionRepository(Repository):
    def get_by_code_and_level(self, code: str, level: int) -> AdministrativeDivision | None:
        stmt = (
            select(AdministrativeDivision)
            .where(AdministrativeDivision.code == code)
            .where(AdministrativeDivision.level == level)
            .limit(1)
        )
        return self.session.scalar(stmt)

    def list_roots(self) -> list[AdministrativeDivision]:
        stmt = (
            select(AdministrativeDivision)
            .where(AdministrativeDivision.parent_code.is_(None))
            .order_by(AdministrativeDivision.sort_order.asc(), AdministrativeDivision.id.asc())
        )
        return list(self.session.scalars(stmt))

    def list_by_parent_code(self, parent_code: str) -> list[AdministrativeDivision]:
        stmt = (
            select(AdministrativeDivision)
            .where(AdministrativeDivision.parent_code == parent_code)
            .order_by(AdministrativeDivision.sort_order.asc(), AdministrativeDivision.id.asc())
        )
        return list(self.session.scalars(stmt))

    def has_children(self, code: str) -> bool:
        stmt = select(AdministrativeDivision.id).where(AdministrativeDivision.parent_code == code).limit(1)
        return self.session.scalar(stmt) is not None


class CropStageDictRepository(Repository):
    def get_by_stage_code(self, stage_code: str) -> CropStageDict | None:
        stmt = select(CropStageDict).where(CropStageDict.stage_code == stage_code)
        return self.session.scalar(stmt)

    def list_active(self) -> list[CropStageDict]:
        stmt = (
            select(CropStageDict)
            .where(CropStageDict.is_active.is_(True))
            .order_by(CropStageDict.display_order.asc(), CropStageDict.id.asc())
        )
        return list(self.session.scalars(stmt))


class RiceVarietyRepository(Repository):
    def get(self, rice_variety_id: int) -> RiceVariety | None:
        return self.session.get(RiceVariety, rice_variety_id)

    def search_by_name(self, query: str | None, *, limit: int) -> list[RiceVariety]:
        stmt = select(RiceVariety)
        if query and query.strip():
            stmt = stmt.where(RiceVariety.name.ilike(f"%{query.strip()}%"))
        stmt = stmt.order_by(RiceVariety.name.asc()).limit(limit)
        return list(self.session.scalars(stmt))


class RiceControlWindowLevel1Repository(Repository):
    def get_by_region_and_year(
        self,
        *,
        province: str,
        city: str,
        county: str,
        data_year: int,
    ) -> RiceControlWindowLevel1 | None:
        stmt = (
            select(RiceControlWindowLevel1)
            .where(RiceControlWindowLevel1.province == province)
            .where(RiceControlWindowLevel1.city == city)
            .where(RiceControlWindowLevel1.county == county)
            .where(RiceControlWindowLevel1.data_year == data_year)
            .order_by(RiceControlWindowLevel1.updated_at.desc(), RiceControlWindowLevel1.id.desc())
            .limit(1)
        )
        return self.session.scalar(stmt)


class FieldRepository(Repository):
    def get(self, field_id: int) -> Field | None:
        return self.session.get(Field, field_id)

    def list_existing_ids(self, field_ids: list[int]) -> list[int]:
        if not field_ids:
            return []
        stmt = select(Field.id).where(Field.id.in_(field_ids)).order_by(Field.id.asc())
        return list(self.session.scalars(stmt))

    def get_by_external_field_id(self, external_field_id: str) -> Field | None:
        stmt = select(Field).where(Field.external_field_id == external_field_id)
        return self.session.scalar(stmt)

    def list_by_ids(self, field_ids: list[int]) -> list[Field]:
        if not field_ids:
            return []
        stmt = select(Field).where(Field.id.in_(field_ids)).order_by(Field.id.asc())
        return list(self.session.scalars(stmt))


class FarmFieldRelationRepository(Repository):
    def get_by_farm_field(self, farm_id: int, field_id: int) -> FarmFieldRelation | None:
        stmt = (
            select(FarmFieldRelation)
            .where(FarmFieldRelation.farm_id == farm_id)
            .where(FarmFieldRelation.field_id == field_id)
        )
        return self.session.scalar(stmt)

    def list_field_ids_by_farm(self, farm_id: int) -> list[int]:
        stmt = (
            select(FarmFieldRelation.field_id)
            .where(FarmFieldRelation.farm_id == farm_id)
            .order_by(FarmFieldRelation.field_id.asc())
        )
        return list(self.session.scalars(stmt))

    def count_by_field(self, field_id: int) -> int:
        stmt = select(FarmFieldRelation).where(FarmFieldRelation.field_id == field_id)
        return len(list(self.session.scalars(stmt)))

    def create(self, farm_id: int, field_id: int) -> FarmFieldRelation:
        relation = FarmFieldRelation(
            farm_id=farm_id,
            field_id=field_id,
            created_by_type="user",
            created_by_id="api",
        )
        self.add(relation)
        return relation

    def delete_by_farm(self, farm_id: int) -> None:
        stmt = select(FarmFieldRelation).where(FarmFieldRelation.farm_id == farm_id)
        for relation in self.session.scalars(stmt):
            self.delete(relation)


class PlantingPlanFieldRelationRepository(Repository):
    def list_field_ids_by_plan(self, planting_plan_id: int) -> list[int]:
        stmt = (
            select(PlantingPlanFieldRelation.field_id)
            .where(PlantingPlanFieldRelation.planting_plan_id == planting_plan_id)
            .order_by(PlantingPlanFieldRelation.field_id.asc())
        )
        return list(self.session.scalars(stmt))

    def list_field_ids_by_plan_ids(self, planting_plan_ids: list[int]) -> dict[int, list[int]]:
        if not planting_plan_ids:
            return {}

        stmt = (
            select(PlantingPlanFieldRelation.planting_plan_id, PlantingPlanFieldRelation.field_id)
            .where(PlantingPlanFieldRelation.planting_plan_id.in_(planting_plan_ids))
            .order_by(
                PlantingPlanFieldRelation.planting_plan_id.asc(),
                PlantingPlanFieldRelation.field_id.asc(),
            )
        )
        mapping: dict[int, list[int]] = {}
        for planting_plan_id, field_id in self.session.execute(stmt):
            mapping.setdefault(planting_plan_id, []).append(field_id)
        return mapping

    def list_linked_field_ids(self, field_ids: list[int]) -> list[int]:
        if not field_ids:
            return []
        stmt = (
            select(PlantingPlanFieldRelation.field_id)
            .where(PlantingPlanFieldRelation.field_id.in_(field_ids))
            .distinct()
            .order_by(PlantingPlanFieldRelation.field_id.asc())
        )
        return list(self.session.scalars(stmt))

    def replace_for_plan(self, planting_plan_id: int, field_ids: list[int]) -> None:
        existing_stmt = select(PlantingPlanFieldRelation).where(
            PlantingPlanFieldRelation.planting_plan_id == planting_plan_id,
        )
        existing_relations = list(self.session.scalars(existing_stmt))
        for relation in existing_relations:
            self.session.delete(relation)

        self.session.add_all(
            [
                PlantingPlanFieldRelation(
                    planting_plan_id=planting_plan_id,
                    field_id=field_id,
                    created_by_type="user",
                    created_by_id="api",
                )
                for field_id in field_ids
            ],
        )


class EventRecordRepository(Repository):
    def get(self, event_record_id: int) -> EventRecord | None:
        return self.session.get(EventRecord, event_record_id)

    def get_by_idempotency_key(self, idempotency_key: str) -> EventRecord | None:
        stmt = select(EventRecord).where(EventRecord.idempotency_key == idempotency_key)
        return self.session.scalar(stmt)

    def list_by_plan(self, planting_plan_id: int) -> list[EventRecord]:
        stmt = (
            select(EventRecord)
            .where(EventRecord.planting_plan_id == planting_plan_id)
            .order_by(EventRecord.occurred_at.desc(), EventRecord.id.desc())
        )
        return list(self.session.scalars(stmt))

    def list_by_source_record_id(self, source_record_id: str) -> list[EventRecord]:
        stmt = (
            select(EventRecord)
            .where(EventRecord.source_record_id == source_record_id)
            .order_by(EventRecord.occurred_at.desc(), EventRecord.id.desc())
        )
        return list(self.session.scalars(stmt))


class StagePredictionSnapshotRepository(Repository):
    def get(self, snapshot_id: int) -> StagePredictionSnapshot | None:
        return self.session.get(StagePredictionSnapshot, snapshot_id)

    def list_by_plan(self, planting_plan_id: int) -> list[StagePredictionSnapshot]:
        stmt = (
            select(StagePredictionSnapshot)
            .where(StagePredictionSnapshot.planting_plan_id == planting_plan_id)
            .order_by(StagePredictionSnapshot.prediction_version.desc(), StagePredictionSnapshot.id.desc())
        )
        return list(self.session.scalars(stmt))

    def get_latest_by_plan(self, planting_plan_id: int) -> StagePredictionSnapshot | None:
        stmt = (
            select(StagePredictionSnapshot)
            .where(StagePredictionSnapshot.planting_plan_id == planting_plan_id)
            .order_by(StagePredictionSnapshot.prediction_version.desc(), StagePredictionSnapshot.id.desc())
            .limit(1)
        )
        return self.session.scalar(stmt)


class CropStageStateRepository(Repository):
    def get_by_plan(self, planting_plan_id: int) -> CropStageState | None:
        stmt = select(CropStageState).where(CropStageState.planting_plan_id == planting_plan_id)
        return self.session.scalar(stmt)


class CropThermalTimeStateRepository(Repository):
    def get_by_plan(self, planting_plan_id: int) -> CropThermalTimeState | None:
        stmt = select(CropThermalTimeState).where(CropThermalTimeState.planting_plan_id == planting_plan_id)
        return self.session.scalar(stmt)


class WeatherSnapshotRepository(Repository):
    def get_by_identity(
        self,
        *,
        farm_id: int,
        weather_year: int,
        weather_date: date,
        source_type: str,
        data_version: str,
        data_hash: str,
    ) -> WeatherSnapshot | None:
        stmt = (
            select(WeatherSnapshot)
            .where(WeatherSnapshot.farm_id == farm_id)
            .where(WeatherSnapshot.weather_year == weather_year)
            .where(WeatherSnapshot.weather_date == weather_date)
            .where(WeatherSnapshot.source_type == source_type)
            .where(WeatherSnapshot.data_version == data_version)
            .where(WeatherSnapshot.data_hash == data_hash)
        )
        return self.session.scalar(stmt)

    def list_by_farm_and_date(
        self,
        farm_id: int,
        *,
        weather_date: date,
    ) -> list[WeatherSnapshot]:
        stmt = (
            select(WeatherSnapshot)
            .where(WeatherSnapshot.farm_id == farm_id)
            .where(WeatherSnapshot.weather_date == weather_date)
            .order_by(WeatherSnapshot.created_at.desc(), WeatherSnapshot.id.desc())
        )
        return list(self.session.scalars(stmt))

    def get_active_by_farm_date_source(
        self,
        *,
        farm_id: int,
        weather_year: int,
        weather_date: date,
        source_type: str,
    ) -> WeatherSnapshot | None:
        stmt = (
            select(WeatherSnapshot)
            .where(WeatherSnapshot.farm_id == farm_id)
            .where(WeatherSnapshot.weather_year == weather_year)
            .where(WeatherSnapshot.weather_date == weather_date)
            .where(WeatherSnapshot.source_type == source_type)
            .where(WeatherSnapshot.is_active.is_(True))
            .order_by(WeatherSnapshot.created_at.desc(), WeatherSnapshot.id.desc())
            .limit(1)
        )
        return self.session.scalar(stmt)

    def supersede_active_for_farm_date_source(
        self,
        *,
        farm_id: int,
        weather_year: int,
        weather_date: date,
        source_type: str,
        superseded_by_snapshot_id: int,
    ) -> None:
        stmt = (
            select(WeatherSnapshot)
            .where(WeatherSnapshot.farm_id == farm_id)
            .where(WeatherSnapshot.weather_year == weather_year)
            .where(WeatherSnapshot.weather_date == weather_date)
            .where(WeatherSnapshot.source_type == source_type)
            .where(WeatherSnapshot.is_active.is_(True))
            .where(WeatherSnapshot.id != superseded_by_snapshot_id)
        )
        now = datetime.now(UTC).replace(tzinfo=None)
        for snapshot in self.session.scalars(stmt):
            snapshot.is_active = False
            snapshot.superseded_at = now
            snapshot.superseded_by_snapshot_id = superseded_by_snapshot_id


class CalendarItemRepository(Repository):
    TERMINAL_STATUSES = ("generated", "invalidated")

    def get(self, calendar_item_id: int) -> CalendarItem | None:
        return self.session.get(CalendarItem, calendar_item_id)

    def get_by_idempotency_key(self, idempotency_key: str) -> CalendarItem | None:
        stmt = select(CalendarItem).where(CalendarItem.idempotency_key == idempotency_key)
        return self.session.scalar(stmt)

    def list_by_plan_and_subtype(
        self,
        planting_plan_id: int,
        task_subtype: str,
        *,
        parent_task_id: int | None = None,
        source_execution_record_id: int | None = None,
    ) -> list[CalendarItem]:
        stmt = (
            select(CalendarItem)
            .where(CalendarItem.planting_plan_id == planting_plan_id)
            .where(CalendarItem.task_subtype == task_subtype)
        )
        if parent_task_id is None:
            stmt = stmt.where(CalendarItem.parent_task_id.is_(None))
        else:
            stmt = stmt.where(CalendarItem.parent_task_id == parent_task_id)
        if source_execution_record_id is None:
            stmt = stmt.where(CalendarItem.source_execution_record_id.is_(None))
        else:
            stmt = stmt.where(CalendarItem.source_execution_record_id == source_execution_record_id)
        stmt = stmt.order_by(CalendarItem.id.asc())
        return list(self.session.scalars(stmt))

    def list_current_by_plan(self, planting_plan_id: int) -> list[CalendarItem]:
        stmt = (
            select(CalendarItem)
            .where(CalendarItem.planting_plan_id == planting_plan_id)
            .where(~CalendarItem.status.in_(self.TERMINAL_STATUSES))
            .order_by(CalendarItem.suggested_start_date.asc(), CalendarItem.id.asc())
        )
        return list(self.session.scalars(stmt))

    def list_by_parent_task(self, parent_task_id: int) -> list[CalendarItem]:
        stmt = select(CalendarItem).where(CalendarItem.parent_task_id == parent_task_id).order_by(CalendarItem.id.asc())
        return list(self.session.scalars(stmt))

    def list_by_source_execution_record(self, execution_record_id: int) -> list[CalendarItem]:
        stmt = (
            select(CalendarItem)
            .where(CalendarItem.source_execution_record_id == execution_record_id)
            .order_by(CalendarItem.id.asc())
        )
        return list(self.session.scalars(stmt))

    def list_active_by_plan_and_subtype(
        self,
        planting_plan_id: int,
        task_subtype: str,
        *,
        parent_task_id: int | None = None,
        source_execution_record_id: int | None = None,
    ) -> list[CalendarItem]:
        stmt = (
            select(CalendarItem)
            .where(CalendarItem.planting_plan_id == planting_plan_id)
            .where(CalendarItem.task_subtype == task_subtype)
            .where(CalendarItem.status == "active")
        )
        if parent_task_id is None:
            stmt = stmt.where(CalendarItem.parent_task_id.is_(None))
        else:
            stmt = stmt.where(CalendarItem.parent_task_id == parent_task_id)
        if source_execution_record_id is None:
            stmt = stmt.where(CalendarItem.source_execution_record_id.is_(None))
        else:
            stmt = stmt.where(CalendarItem.source_execution_record_id == source_execution_record_id)
        stmt = stmt.order_by(CalendarItem.id.asc())
        return list(self.session.scalars(stmt))

    def list_due_for_generation(
        self,
        planting_plan_id: int,
        *,
        check_date: date,
        window_days: int,
    ) -> list[CalendarItem]:
        latest_start_date = check_date + timedelta(days=window_days)
        stmt = (
            select(CalendarItem)
            .where(CalendarItem.planting_plan_id == planting_plan_id)
            .where(CalendarItem.status == "active")
            .where(CalendarItem.generated_task_id.is_(None))
            .where(CalendarItem.suggested_start_date <= latest_start_date)
            .order_by(CalendarItem.suggested_start_date.asc(), CalendarItem.id.asc())
        )
        return list(self.session.scalars(stmt))


class TaskIntentRepository(Repository):
    TERMINAL_STATUSES = ("converted", "rejected", "no_action")

    def get(self, task_intent_id: int) -> TaskIntent | None:
        return self.session.get(TaskIntent, task_intent_id)

    def get_by_idempotency_key(self, idempotency_key: str) -> TaskIntent | None:
        stmt = select(TaskIntent).where(TaskIntent.idempotency_key == idempotency_key)
        return self.session.scalar(stmt)

    def list_current_by_plan(self, planting_plan_id: int) -> list[TaskIntent]:
        stmt = (
            select(TaskIntent)
            .where(TaskIntent.planting_plan_id == planting_plan_id)
            .where(~TaskIntent.status.in_(self.TERMINAL_STATUSES))
            .order_by(TaskIntent.created_at.desc(), TaskIntent.id.desc())
        )
        return list(self.session.scalars(stmt))

    def list_by_parent_task(self, parent_task_id: int) -> list[TaskIntent]:
        stmt = select(TaskIntent).where(TaskIntent.parent_task_id == parent_task_id).order_by(TaskIntent.id.asc())
        return list(self.session.scalars(stmt))

    def list_by_source_execution_record(self, execution_record_id: int) -> list[TaskIntent]:
        stmt = (
            select(TaskIntent)
            .where(TaskIntent.source_execution_record_id == execution_record_id)
            .order_by(TaskIntent.id.asc())
        )
        return list(self.session.scalars(stmt))


class ReviewRequestRepository(Repository):
    TERMINAL_STATUSES = ("resolved", "cancelled")
    SOURCE_ENTITY_MODELS = {
        "calendar_item": CalendarItem,
        "cf_calendar_item": CalendarItem,
        "event_record": EventRecord,
        "cf_event_record": EventRecord,
        "execution": Execution,
        "cf_execution": Execution,
        "execution_record": ExecutionRecord,
        "cf_execution_record": ExecutionRecord,
        "farming_task": FarmingTask,
        "cf_farming_task": FarmingTask,
        "operation_plan": OperationPlan,
        "cf_operation_plan": OperationPlan,
        "planting_plan": PlantingPlan,
        "cf_planting_plan": PlantingPlan,
        "review_request": ReviewRequest,
        "cf_review_request": ReviewRequest,
        "task_intent": TaskIntent,
        "cf_task_intent": TaskIntent,
    }

    def get(self, review_request_id: int) -> ReviewRequest | None:
        return self.session.get(ReviewRequest, review_request_id)

    def list_current_by_plan(self, planting_plan_id: int) -> list[ReviewRequest]:
        stmt = (
            select(ReviewRequest)
            .where(ReviewRequest.planting_plan_id == planting_plan_id)
            .where(~ReviewRequest.status.in_(self.TERMINAL_STATUSES))
            .order_by(ReviewRequest.created_at.desc(), ReviewRequest.id.desc())
        )
        return list(self.session.scalars(stmt))

    def list_by_source_entity(
        self,
        source_entity_type: str,
        source_entity_id: int,
    ) -> list[ReviewRequest]:
        stmt = (
            select(ReviewRequest)
            .where(ReviewRequest.source_entity_type == source_entity_type)
            .where(ReviewRequest.source_entity_id == source_entity_id)
            .order_by(ReviewRequest.created_at.desc(), ReviewRequest.id.desc())
        )
        return list(self.session.scalars(stmt))

    def get_source_entity(self, review_request_or_id: ReviewRequest | int) -> Any | None:
        review_request = (
            review_request_or_id
            if isinstance(review_request_or_id, ReviewRequest)
            else self.get(review_request_or_id)
        )
        if review_request is None:
            return None

        model = self.SOURCE_ENTITY_MODELS.get(review_request.source_entity_type)
        if model is None:
            return None

        return self.session.get(model, review_request.source_entity_id)


class FarmingTaskRepository(Repository):
    TERMINAL_STATUSES = ("completed", "failed", "cancelled")

    def get(self, farming_task_id: int) -> FarmingTask | None:
        return self.session.get(FarmingTask, farming_task_id)

    def list_by_plan(self, planting_plan_id: int) -> list[FarmingTask]:
        stmt = (
            select(FarmingTask)
            .where(FarmingTask.planting_plan_id == planting_plan_id)
            .order_by(FarmingTask.created_at.desc(), FarmingTask.id.desc())
        )
        return list(self.session.scalars(stmt))

    def list_current_by_plan(self, planting_plan_id: int) -> list[FarmingTask]:
        stmt = (
            select(FarmingTask)
            .where(FarmingTask.planting_plan_id == planting_plan_id)
            .where(~FarmingTask.status.in_(self.TERMINAL_STATUSES))
            .order_by(FarmingTask.created_at.desc(), FarmingTask.id.desc())
        )
        return list(self.session.scalars(stmt))

    def list_by_parent_task(self, parent_task_id: int) -> list[FarmingTask]:
        stmt = select(FarmingTask).where(FarmingTask.parent_task_id == parent_task_id).order_by(FarmingTask.id.asc())
        return list(self.session.scalars(stmt))

    def list_by_source_execution_record(self, execution_record_id: int) -> list[FarmingTask]:
        stmt = (
            select(FarmingTask)
            .where(FarmingTask.source_execution_record_id == execution_record_id)
            .order_by(FarmingTask.id.asc())
        )
        return list(self.session.scalars(stmt))


class OperationPlanRepository(Repository):
    def get(self, operation_plan_id: int) -> OperationPlan | None:
        return self.session.get(OperationPlan, operation_plan_id)

    def list_by_plan(self, planting_plan_id: int) -> list[OperationPlan]:
        stmt = (
            select(OperationPlan)
            .where(OperationPlan.planting_plan_id == planting_plan_id)
            .order_by(OperationPlan.created_at.desc(), OperationPlan.id.desc())
        )
        return list(self.session.scalars(stmt))

    def list_by_task(self, farming_task_id: int) -> list[OperationPlan]:
        stmt = (
            select(OperationPlan)
            .where(OperationPlan.farming_task_id == farming_task_id)
            .order_by(OperationPlan.version.desc(), OperationPlan.id.desc())
        )
        return list(self.session.scalars(stmt))

    def get_active_by_task(self, farming_task_id: int) -> OperationPlan | None:
        stmt = select(OperationPlan).where(
            OperationPlan.farming_task_id == farming_task_id,
            OperationPlan.status == "active",
        )
        return self.session.scalar(stmt)


class ExecutionRepository(Repository):
    def get(self, execution_id: int) -> Execution | None:
        return self.session.get(Execution, execution_id)

    def list_by_task(self, farming_task_id: int) -> list[Execution]:
        stmt = select(Execution).where(Execution.farming_task_id == farming_task_id).order_by(Execution.id.desc())
        return list(self.session.scalars(stmt))


class ExecutionRecordRepository(Repository):
    def get(self, execution_record_id: int) -> ExecutionRecord | None:
        return self.session.get(ExecutionRecord, execution_record_id)

    def list_by_execution(self, execution_id: int) -> list[ExecutionRecord]:
        stmt = (
            select(ExecutionRecord)
            .where(ExecutionRecord.execution_id == execution_id)
            .order_by(ExecutionRecord.record_time.desc(), ExecutionRecord.id.desc())
        )
        return list(self.session.scalars(stmt))

    def list_by_task(self, farming_task_id: int) -> list[ExecutionRecord]:
        stmt: Select[tuple[ExecutionRecord]] = (
            select(ExecutionRecord)
            .join(Execution, Execution.id == ExecutionRecord.execution_id)
            .where(Execution.farming_task_id == farming_task_id)
            .order_by(ExecutionRecord.record_time.desc(), ExecutionRecord.id.desc())
        )
        return list(self.session.scalars(stmt))

    def get_latest_survey_record_for_task(self, farming_task_id: int) -> ExecutionRecord | None:
        stmt: Select[tuple[ExecutionRecord]] = (
            select(ExecutionRecord)
            .join(Execution, Execution.id == ExecutionRecord.execution_id)
            .where(Execution.farming_task_id == farming_task_id)
            .where(ExecutionRecord.record_type == "survey_result")
            .order_by(ExecutionRecord.record_time.desc(), ExecutionRecord.id.desc())
            .limit(1)
        )
        return self.session.scalar(stmt)
