from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Callable
from uuid import uuid4
from typing import Any

from app.core.constants import (
    EVENT_PROCESSING_STATUS_RECEIVED,
    EVENT_TYPE_ACTUAL_STAGE_RECORDED,
    EVENT_TYPE_PLAN_CREATED,
    EVENT_TYPE_PLAN_KEY_INFO_CHANGED,
    EVENT_TYPE_PLAN_UPDATED,
    EVENT_TYPE_TASK_DUE_CHECK_TRIGGERED,
    TASK_DUE_CHECK_JOB,
)
from app.models import EventRecord, Field, PlantingPlan, RiceVariety
from app.repositories import (
    EventRecordRepository,
    FarmFieldRelationRepository,
    FarmRepository,
    FieldRepository,
    PlantingPlanFieldRelationRepository,
    PlantingPlanRepository,
    RiceVarietyRepository,
)
from app.services.stage_management import (
    get_raw_stage_order_index,
    is_raw_stage_code,
    validate_manual_raw_stage_dates,
)


class PlanEventDispatcher:
    def handle(self, event_record: EventRecord):
        raise NotImplementedError

PLANTING_PLAN_ALLOWED_STATUSES = {"draft", "active", "completed", "cancelled"}


@dataclass(slots=True)
class PlantingPlanDetails:
    planting_plan: PlantingPlan
    field_ids: list[int]
    farm_name: str | None = None


@dataclass(slots=True)
class PlantingPlanCreateInput:
    plan_name: str
    farm_id: int
    field_ids: list[int]
    culti_type_code: int
    planting_method_code: int
    crop_name: str
    variety_id: int
    sowing_date: date
    plan_code: str | None = None
    year: int | None = None
    transplant_date: date | None = None
    harvest_date: date | None = None
    transplant_leaf_age: Decimal | None = None
    previous_harvest_date: date | None = None
    ratoon_first_season_harvest_date: date | None = None
    expected_harvest_date: date | None = None
    status: str = "draft"
    task_generation_window_days: int = 14
    metadata_payload: dict[str, Any] | None = None


@dataclass(slots=True)
class PlantingPlanUpdateInput:
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
    metadata_payload: dict[str, Any] | None = None


@dataclass(slots=True)
class ActualStageRecordedInput:
    stage_dates: dict[str, date]
    source_record_id: str | None = None
    operator_id: str | None = None
    note: str | None = None
    metadata_payload: dict[str, Any] | None = None


class PlantingPlanService:
    def __init__(
        self,
        planting_plan_repository: PlantingPlanRepository,
        field_repository: FieldRepository,
        planting_plan_field_relation_repository: PlantingPlanFieldRelationRepository,
        rice_variety_repository: RiceVarietyRepository,
        farm_field_relation_repository: FarmFieldRelationRepository | None = None,
        farm_repository: FarmRepository | None = None,
        event_record_repository: EventRecordRepository | None = None,
        plan_orchestrator: PlanEventDispatcher | None = None,
        plan_code_factory: Callable[[], str] | None = None,
    ) -> None:
        self.planting_plan_repository = planting_plan_repository
        self.field_repository = field_repository
        self.farm_field_relation_repository = farm_field_relation_repository
        self.planting_plan_field_relation_repository = planting_plan_field_relation_repository
        self.rice_variety_repository = rice_variety_repository
        self.farm_repository = farm_repository
        self.event_record_repository = event_record_repository
        self.plan_orchestrator = plan_orchestrator
        self.plan_code_factory = plan_code_factory

    def create(self, payload: PlantingPlanCreateInput) -> PlantingPlanDetails:
        self._validate_status(payload.status)
        plan_code = payload.plan_code or self._generate_plan_code()
        if self.planting_plan_repository.get_by_plan_code(plan_code) is not None:
            raise ValueError(f"Planting plan code {plan_code} already exists.")

        variety = self._get_variety(payload.variety_id)
        self._ensure_farm_exists(payload.farm_id)
        self._ensure_fields_exist(payload.field_ids)
        self._ensure_fields_belong_to_farm(payload.farm_id, payload.field_ids)

        planting_plan = PlantingPlan(
            plan_code=plan_code,
            plan_name=payload.plan_name,
            farm_id=payload.farm_id,
            year=payload.year,
            culti_type_code=payload.culti_type_code,
            planting_method_code=payload.planting_method_code,
            crop_name=payload.crop_name,
            variety_id=payload.variety_id,
            variety_name=variety.name,
            sowing_date=payload.sowing_date,
            transplant_date=payload.transplant_date,
            harvest_date=payload.harvest_date,
            transplant_leaf_age=payload.transplant_leaf_age,
            previous_harvest_date=payload.previous_harvest_date,
            ratoon_first_season_harvest_date=payload.ratoon_first_season_harvest_date,
            expected_harvest_date=payload.expected_harvest_date,
            status=payload.status,
            task_generation_window_days=payload.task_generation_window_days,
            metadata_payload=payload.metadata_payload or {},
            created_by_type="user",
            created_by_id="api",
        )
        self.planting_plan_repository.add(planting_plan)
        self.planting_plan_repository.flush()
        self.planting_plan_field_relation_repository.replace_for_plan(planting_plan.id, payload.field_ids)
        self._record_and_dispatch_plan_event(
            planting_plan.id,
            event_type=EVENT_TYPE_PLAN_CREATED,
            payload={"planCode": planting_plan.plan_code},
            idempotency_key=f"plan-created:{planting_plan.id}",
        )
        return self.get_details(planting_plan.id)

    def _generate_plan_code(self) -> str:
        for _ in range(10):
            candidate = self.plan_code_factory() if self.plan_code_factory is not None else _default_plan_code()
            if self.planting_plan_repository.get_by_plan_code(candidate) is None:
                return candidate
        raise ValueError("Unable to generate unique planting plan code.")

    def _get_farm_name(self, farm_id: int) -> str | None:
        if self.farm_repository is None:
            return None
        farm = self.farm_repository.get(farm_id)
        return farm.farm_name if farm is not None else None

    def get_details(self, planting_plan_id: int) -> PlantingPlanDetails:
        planting_plan = self.planting_plan_repository.get(planting_plan_id)
        if planting_plan is None:
            raise LookupError(f"Planting plan {planting_plan_id} does not exist.")

        field_ids = self.planting_plan_field_relation_repository.list_field_ids_by_plan(planting_plan_id)
        return PlantingPlanDetails(
            planting_plan=planting_plan,
            field_ids=field_ids,
            farm_name=self._get_farm_name(planting_plan.farm_id),
        )

    def list_by_statuses(self, statuses: list[str] | None = None) -> list[PlantingPlanDetails]:
        if statuses:
            for status in statuses:
                self._validate_status(status)
        planting_plans = self.planting_plan_repository.list_by_statuses(statuses)
        if not planting_plans:
            return []

        plan_ids = [plan.id for plan in planting_plans]
        field_ids_map = self.planting_plan_field_relation_repository.list_field_ids_by_plan_ids(plan_ids)
        return [
            PlantingPlanDetails(
                planting_plan=plan,
                field_ids=field_ids_map.get(plan.id, []),
                farm_name=self._get_farm_name(plan.farm_id),
            )
            for plan in planting_plans
        ]

    def update(self, planting_plan_id: int, payload: PlantingPlanUpdateInput) -> PlantingPlanDetails:
        planting_plan = self.planting_plan_repository.get(planting_plan_id)
        if planting_plan is None:
            raise LookupError(f"Planting plan {planting_plan_id} does not exist.")

        before_field_ids = self.planting_plan_field_relation_repository.list_field_ids_by_plan(planting_plan_id)
        before_snapshot = self._build_plan_audit_snapshot(planting_plan, before_field_ids)
        previous_status = planting_plan.status
        refresh_calendar = False

        if payload.plan_name is not None:
            planting_plan.plan_name = payload.plan_name
        if payload.farm_id is not None:
            self._ensure_farm_exists(payload.farm_id)
            planting_plan.farm_id = payload.farm_id
        if payload.year is not None:
            planting_plan.year = payload.year
        if payload.culti_type_code is not None:
            planting_plan.culti_type_code = payload.culti_type_code
            refresh_calendar = True
        if payload.planting_method_code is not None:
            planting_plan.planting_method_code = payload.planting_method_code
            refresh_calendar = True
        if payload.crop_name is not None:
            planting_plan.crop_name = payload.crop_name
        if payload.variety_id is not None and payload.variety_id != planting_plan.variety_id:
            variety = self._get_variety(payload.variety_id)
            planting_plan.variety_id = payload.variety_id
            planting_plan.variety_name = variety.name
            refresh_calendar = True
        if payload.sowing_date is not None:
            planting_plan.sowing_date = payload.sowing_date
            refresh_calendar = True
        if payload.transplant_date is not None:
            planting_plan.transplant_date = payload.transplant_date
            refresh_calendar = True
        if payload.harvest_date is not None:
            planting_plan.harvest_date = payload.harvest_date
        if payload.transplant_leaf_age is not None:
            planting_plan.transplant_leaf_age = payload.transplant_leaf_age
        if payload.previous_harvest_date is not None:
            planting_plan.previous_harvest_date = payload.previous_harvest_date
        if payload.ratoon_first_season_harvest_date is not None:
            planting_plan.ratoon_first_season_harvest_date = payload.ratoon_first_season_harvest_date
        if payload.expected_harvest_date is not None:
            planting_plan.expected_harvest_date = payload.expected_harvest_date
        if payload.status is not None:
            self._validate_status(payload.status)
            planting_plan.status = payload.status
        if payload.task_generation_window_days is not None:
            planting_plan.task_generation_window_days = payload.task_generation_window_days
        if payload.metadata_payload is not None:
            planting_plan.metadata_payload = payload.metadata_payload
        if payload.field_ids is not None:
            self._validate_field_ids(payload.field_ids)
            self._ensure_fields_exist(payload.field_ids)
            self._ensure_fields_belong_to_farm(planting_plan.farm_id, payload.field_ids)
            self.planting_plan_field_relation_repository.replace_for_plan(planting_plan_id, payload.field_ids)
        elif payload.farm_id is not None:
            self._ensure_fields_belong_to_farm(payload.farm_id, before_field_ids)

        planting_plan.updated_at = _utcnow()
        self.planting_plan_repository.flush()

        after_field_ids = (
            sorted(payload.field_ids)
            if payload.field_ids is not None
            else before_field_ids
        )
        after_snapshot = self._build_plan_audit_snapshot(planting_plan, after_field_ids)
        changed_fields = [
            field_name
            for field_name in after_snapshot
            if before_snapshot[field_name] != after_snapshot[field_name]
        ]
        if changed_fields:
            self._record_and_dispatch_plan_event(
                planting_plan.id,
                event_type=EVENT_TYPE_PLAN_UPDATED,
                payload={
                    "changedFields": changed_fields,
                    "before": {field_name: before_snapshot[field_name] for field_name in changed_fields},
                    "after": {field_name: after_snapshot[field_name] for field_name in changed_fields},
                },
                idempotency_key=f"plan-updated:{planting_plan.id}:{_utcnow().isoformat()}",
            )

        if refresh_calendar and planting_plan.status in {"draft", "active"}:
            self._record_and_dispatch_plan_event(
                planting_plan.id,
                event_type=EVENT_TYPE_PLAN_KEY_INFO_CHANGED,
                payload={"refreshCalendar": True},
                idempotency_key=f"plan-key-info-changed:{planting_plan.id}:{_utcnow().isoformat()}",
            )
        if previous_status != "active" and planting_plan.status == "active":
            self._record_and_dispatch_task_due_check_event(planting_plan.id)

        return self.get_details(planting_plan.id)

    def record_actual_stages(self, planting_plan_id: int, payload: ActualStageRecordedInput) -> list[EventRecord]:
        if self.event_record_repository is None or self.plan_orchestrator is None:
            raise RuntimeError(
                "PlantingPlanService requires EventRecordRepository and PlanOrchestrator to record actual stages.",
            )

        planting_plan = self.planting_plan_repository.get(planting_plan_id)
        if planting_plan is None:
            raise LookupError(f"Planting plan {planting_plan_id} does not exist.")
        if not payload.stage_dates:
            raise ValueError("At least one actual stage record is required.")

        ordered_stage_dates = sorted(
            enumerate(payload.stage_dates.items()),
            key=lambda item: (item[1][1], item[0]),
        )
        normalized_stage_dates: dict[str, date] = {}
        for _, (raw_stage_code, effective_date) in ordered_stage_dates:
            stage_code = str(raw_stage_code).strip()
            if not stage_code:
                raise ValueError("Actual stage code cannot be empty.")
            if not is_raw_stage_code(stage_code):
                raise ValueError(f"Actual stage code must be a raw stage code, got: {stage_code}.")
            normalized_stage_dates[stage_code] = effective_date
        validate_manual_raw_stage_dates(normalized_stage_dates)
        latest_stage_code, latest_effective_date = max(
            normalized_stage_dates.items(),
            key=lambda item: (item[1], get_raw_stage_order_index(item[0]) or -1),
        )
        stage_dates_payload = {
            stage_code: effective_date.isoformat()
            for stage_code, effective_date in sorted(
                normalized_stage_dates.items(),
                key=lambda item: (item[1], get_raw_stage_order_index(item[0]) or -1),
            )
        }

        source_record_id = (
            payload.source_record_id or f"{planting_plan_id}:{latest_stage_code}:{latest_effective_date.isoformat()}"
        )
        canonical_stage_dates = ",".join(f"{stage_code}:{stage_date}" for stage_code, stage_date in stage_dates_payload.items())
        idempotency_key = (
            f"actual-stage-recorded:{planting_plan_id}:{source_record_id}:{canonical_stage_dates}"
        )
        existing_event = self.event_record_repository.get_by_idempotency_key(idempotency_key)
        if existing_event is not None:
            return [existing_event]

        event_record = EventRecord(
            planting_plan_id=planting_plan_id,
            event_type=EVENT_TYPE_ACTUAL_STAGE_RECORDED,
            event_category="runtime",
            event_source="api",
            source_system="cropflow",
            source_record_id=source_record_id,
            payload={
                "stageCode": latest_stage_code,
                "effectiveDate": latest_effective_date.isoformat(),
                "stageDates": stage_dates_payload,
                "sourceRecordId": source_record_id,
                "operatorId": payload.operator_id,
                "note": payload.note,
                "metadata": payload.metadata_payload or {},
            },
            occurred_at=_utcnow(),
            processing_status=EVENT_PROCESSING_STATUS_RECEIVED,
            idempotency_key=idempotency_key,
            created_by_type="user",
            created_by_id=payload.operator_id or "api",
        )
        self.event_record_repository.add(event_record)
        if hasattr(self.event_record_repository, "flush"):
            self.event_record_repository.flush()
        self.plan_orchestrator.handle(event_record)

        return [event_record]

    def _record_and_dispatch_plan_event(
        self,
        planting_plan_id: int,
        *,
        event_type: str,
        payload: dict[str, Any],
        idempotency_key: str,
    ) -> EventRecord | None:
        if self.event_record_repository is None:
            return None

        event_record = EventRecord(
            planting_plan_id=planting_plan_id,
            event_type=event_type,
            event_category="plan",
            event_source="api",
            source_system="cropflow",
            payload=payload,
            occurred_at=_utcnow(),
            processing_status=EVENT_PROCESSING_STATUS_RECEIVED,
            idempotency_key=idempotency_key,
            created_by_type="user",
            created_by_id="api",
        )
        self.event_record_repository.add(event_record)
        if hasattr(self.event_record_repository, "flush"):
            self.event_record_repository.flush()
        if self.plan_orchestrator is not None:
            self.plan_orchestrator.handle(event_record)
        return event_record

    def _record_and_dispatch_task_due_check_event(self, planting_plan_id: int) -> EventRecord | None:
        if self.event_record_repository is None:
            return None

        check_date = _utcnow().date()
        idempotency_key = f"{TASK_DUE_CHECK_JOB}:{planting_plan_id}:{check_date.isoformat()}"
        existing_event = None
        if hasattr(self.event_record_repository, "get_by_idempotency_key"):
            existing_event = self.event_record_repository.get_by_idempotency_key(idempotency_key)
        if existing_event is not None:
            if self.plan_orchestrator is not None:
                self.plan_orchestrator.handle(existing_event)
            return existing_event

        event_record = EventRecord(
            planting_plan_id=planting_plan_id,
            event_type=EVENT_TYPE_TASK_DUE_CHECK_TRIGGERED,
            event_category="job",
            event_source="api",
            source_system="cropflow",
            payload={
                "jobKey": TASK_DUE_CHECK_JOB,
                "checkDate": check_date.isoformat(),
            },
            occurred_at=_utcnow(),
            processing_status=EVENT_PROCESSING_STATUS_RECEIVED,
            idempotency_key=idempotency_key,
            created_by_type="system",
            created_by_id=TASK_DUE_CHECK_JOB,
        )
        self.event_record_repository.add(event_record)
        if hasattr(self.event_record_repository, "flush"):
            self.event_record_repository.flush()
        if self.plan_orchestrator is not None:
            self.plan_orchestrator.handle(event_record)
        return event_record

    def _build_plan_audit_snapshot(self, planting_plan: PlantingPlan, field_ids: list[int]) -> dict[str, Any]:
        return {
            "plan_name": planting_plan.plan_name,
            "farm_id": planting_plan.farm_id,
            "field_ids": sorted(field_ids),
            "year": planting_plan.year,
            "culti_type_code": planting_plan.culti_type_code,
            "planting_method_code": planting_plan.planting_method_code,
            "crop_name": planting_plan.crop_name,
            "variety_id": planting_plan.variety_id,
            "variety_name": planting_plan.variety_name,
            "sowing_date": _serialize_event_value(planting_plan.sowing_date),
            "transplant_date": _serialize_event_value(planting_plan.transplant_date),
            "harvest_date": _serialize_event_value(planting_plan.harvest_date),
            "transplant_leaf_age": _serialize_event_value(planting_plan.transplant_leaf_age),
            "previous_harvest_date": _serialize_event_value(planting_plan.previous_harvest_date),
            "ratoon_first_season_harvest_date": _serialize_event_value(planting_plan.ratoon_first_season_harvest_date),
            "expected_harvest_date": _serialize_event_value(planting_plan.expected_harvest_date),
            "status": planting_plan.status,
            "task_generation_window_days": planting_plan.task_generation_window_days,
            "metadata": deepcopy(planting_plan.metadata_payload or {}),
        }

    def _get_variety(self, variety_id: int) -> RiceVariety:
        variety = self.rice_variety_repository.get(variety_id)
        if variety is None:
            raise ValueError(f"Rice variety {variety_id} does not exist.")
        return variety

    def _ensure_fields_exist(self, field_ids: list[int]) -> list[int]:
        if hasattr(self.field_repository, "list_existing_ids"):
            existing_ids = set(self.field_repository.list_existing_ids(field_ids))
        else:
            existing_ids = {field.id for field in self.field_repository.list_by_ids(field_ids)}
        if len(existing_ids) != len(set(field_ids)):
            missing_ids = sorted(set(field_ids) - existing_ids)
            raise ValueError(f"Fields {missing_ids} do not exist.")
        return sorted(existing_ids)

    def _ensure_farm_exists(self, farm_id: int) -> None:
        if self.farm_repository is None:
            raise RuntimeError("PlantingPlanService requires FarmRepository to validate farm_id.")
        farm = self.farm_repository.get(farm_id)
        if farm is None:
            raise ValueError(f"Farm {farm_id} does not exist.")

    def _ensure_fields_belong_to_farm(self, farm_id: int, field_ids: list[int]) -> None:
        if not field_ids:
            return
        if self.farm_field_relation_repository is None:
            raise RuntimeError(
                "PlantingPlanService requires FarmFieldRelationRepository to validate field ownership.",
            )
        farm_field_ids = set(self.farm_field_relation_repository.list_field_ids_by_farm(farm_id))
        invalid_field_ids = sorted(set(field_ids) - farm_field_ids)
        if invalid_field_ids:
            raise ValueError(f"Fields {invalid_field_ids} do not belong to farm {farm_id}.")

    def _validate_field_ids(self, field_ids: list[int]) -> None:
        return None

    def _validate_status(self, status: str) -> None:
        if status not in PLANTING_PLAN_ALLOWED_STATUSES:
            raise ValueError(
                f"Unsupported planting plan status: {status}. Allowed values: {sorted(PLANTING_PLAN_ALLOWED_STATUSES)}.",
            )


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _serialize_event_value(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _default_plan_code() -> str:
    return f"PLAN-{datetime.now(UTC).strftime('%Y%m%d')}-{uuid4().hex[:6].upper()}"
