from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import build_weather_provider
from app.core.config import Settings, get_settings
from app.core.constants import FARMING_TASK_STATUS_PENDING, TASK_INTENT_STATUS_CONVERTED, TASK_SUBTYPE_DISEASE_PEST_CONTROL
from app.db.session import get_session_factory
from app.models import EventRecord, FarmingTask, OperationPlan, TaskIntent
from app.orchestrator.core import (
    _format_date_range,
    _merge_merged_event_targets,
    _parse_optional_datetime_or_date_range_end,
    _parse_optional_datetime_or_date_range_start,
    _resolve_merged_control_operation_window,
    _serialize_merged_event_payload,
)
from app.repositories import (
    CalendarItemRepository,
    CodeDictRepository,
    FarmRepository,
    OperationPlanRepository,
    PlantingPlanRepository,
    RiceControlWindowLevel1Repository,
    RiceVarietyRepository,
    StagePredictionSnapshotRepository,
)
from app.services import HttpPestDiseaseControlClient, PestDiseaseControlPlanningService, PlantProtectionPlanContextResolver

REPAIR_ACTOR = "repair_merged_disease_pest_controls"
REPAIR_EVENT_TYPE = "system.repair_merged_disease_pest_control"
REPAIR_IDEMPOTENCY_PREFIX = "repair-merged-disease-pest-control"
REPAIR_TRIGGER_SUMMARY = "System repair merged existing regular and emergency disease pest control recommendations."
STALE_REASON = "Superseded by merged disease pest control recommendation."


@dataclass(slots=True)
class PendingControlBundle:
    task_intent_id: int
    farming_task_id: int
    operation_plan_id: int | None
    control_type: str
    task_created_at: datetime


@dataclass(slots=True)
class RepairOutcome:
    planting_plan_id: int
    status: str
    message: str
    kept_task_intent_id: int | None = None
    kept_task_id: int | None = None
    cancelled_task_intent_id: int | None = None
    cancelled_task_id: int | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge existing pending regular/emergency disease pest control tasks into one task per planting plan.",
    )
    parser.add_argument("--plan-id", type=int, action="append", help="Only repair the specified planting plan id. Repeatable.")
    parser.add_argument("--apply", action="store_true", help="Persist changes. Without this flag, only print the detected actions.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()
    session_factory = get_session_factory()

    with session_factory() as session:
        plan_ids = discover_candidate_plan_ids(session, plan_ids=args.plan_id)

    outcomes: list[RepairOutcome] = []
    for plan_id in plan_ids:
        with session_factory() as session:
            try:
                outcome = repair_plan(session, settings, plan_id=plan_id, apply=args.apply)
            except Exception as exc:  # pragma: no cover - exercised through manual repair
                session.rollback()
                outcome = RepairOutcome(
                    planting_plan_id=plan_id,
                    status="error",
                    message=str(exc),
                )
            else:
                if args.apply and outcome.status == "repaired":
                    session.commit()
                else:
                    session.rollback()
            outcomes.append(outcome)

    summary = {
        "apply": bool(args.apply),
        "candidate_plan_ids": plan_ids,
        "outcomes": [asdict(item) for item in outcomes],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def discover_candidate_plan_ids(session: Session, *, plan_ids: list[int] | None) -> list[int]:
    stmt = (
        select(FarmingTask.planting_plan_id)
        .join(TaskIntent, TaskIntent.id == FarmingTask.task_intent_id)
        .where(FarmingTask.task_subtype == TASK_SUBTYPE_DISEASE_PEST_CONTROL)
        .where(FarmingTask.status == FARMING_TASK_STATUS_PENDING)
        .where(TaskIntent.status == TASK_INTENT_STATUS_CONVERTED)
        .order_by(FarmingTask.planting_plan_id.asc())
    )
    if plan_ids:
        stmt = stmt.where(FarmingTask.planting_plan_id.in_(plan_ids))

    discovered: set[int] = set()
    for planting_plan_id in session.scalars(stmt):
        if planting_plan_id is not None:
            discovered.add(int(planting_plan_id))
    return [plan_id for plan_id in sorted(discovered) if load_candidate(session, plan_id) is not None]


def repair_plan(session: Session, settings: Settings, *, plan_id: int, apply: bool) -> RepairOutcome:
    candidate = load_candidate(session, plan_id)
    if candidate is None:
        return RepairOutcome(
            planting_plan_id=plan_id,
            status="skipped",
            message="No pending regular+emergency disease pest control pair found.",
        )

    service = build_repair_service(session, settings)
    regular_intent = session.get(TaskIntent, candidate["regular"].task_intent_id)
    emergency_intent = session.get(TaskIntent, candidate["emergency"].task_intent_id)
    if regular_intent is None or emergency_intent is None:
        raise LookupError(f"Missing task intent while repairing planting plan {plan_id}.")

    regular_theory = dict((regular_intent.rule_result.get("proposedPlan") or {}).get("theoryPlan") or {})
    emergency_theory = dict((emergency_intent.rule_result.get("proposedPlan") or {}).get("theoryPlan") or {})
    if not regular_theory or not emergency_theory:
        return RepairOutcome(
            planting_plan_id=plan_id,
            status="skipped",
            message="Regular or emergency theory plan is missing.",
        )

    merge_result = service.merge_theory_plans(
        planting_plan_id=plan_id,
        regular_theory=regular_theory,
        emergency_theory=emergency_theory,
    )
    if not merge_result.merged_result.events:
        return RepairOutcome(
            planting_plan_id=plan_id,
            status="skipped",
            message="Merge result does not contain executable events.",
        )

    survivor = choose_survivor(candidate["regular"], candidate["emergency"])
    stale = candidate["emergency"] if survivor.control_type == "regular" else candidate["regular"]

    survivor_task_intent = session.get(TaskIntent, survivor.task_intent_id)
    stale_task_intent = session.get(TaskIntent, stale.task_intent_id)
    survivor_task = session.get(FarmingTask, survivor.farming_task_id)
    stale_task = session.get(FarmingTask, stale.farming_task_id)
    if survivor_task_intent is None or stale_task_intent is None or survivor_task is None or stale_task is None:
        raise LookupError(f"Missing task/task_intent while repairing planting plan {plan_id}.")

    survivor_operation_plan = (
        session.get(OperationPlan, survivor.operation_plan_id) if survivor.operation_plan_id is not None else None
    )
    if survivor_operation_plan is None:
        return RepairOutcome(
            planting_plan_id=plan_id,
            status="skipped",
            message="Survivor task is missing an active operation plan.",
        )
    stale_operation_plan = session.get(OperationPlan, stale.operation_plan_id) if stale.operation_plan_id is not None else None

    proposed_task, proposed_plan, raw_response = build_merged_payload(
        merge_result=merge_result,
        survivor_task_intent=survivor_task_intent,
        stale_task_intent=stale_task_intent,
    )
    merged_rule_result = build_merged_rule_result(
        survivor_task_intent=survivor_task_intent,
        stale_task_intent=stale_task_intent,
        proposed_task=proposed_task,
        proposed_plan=proposed_plan,
        raw_response=raw_response,
    )

    if apply:
        survivor_task_intent.rule_result = merged_rule_result
        survivor_task_intent.trigger_summary = REPAIR_TRIGGER_SUMMARY
        survivor_task_intent.suggested_action = merge_result.suggested_action
        survivor_task_intent.no_action_reason = None

        stale_task_intent.no_action_reason = STALE_REASON

        survivor_task.title = str(proposed_task["title"])
        survivor_task.description = REPAIR_TRIGGER_SUMMARY
        survivor_task.planned_start_at = _parse_optional_datetime_or_date_range_start(
            proposed_task["recommendedControlDate"],
        )
        survivor_task.planned_end_at = _parse_optional_datetime_or_date_range_end(
            proposed_task["recommendedControlDate"],
        )

        stale_task.status = "cancelled"

        survivor_operation_plan.algorithm_code = "pest_disease.merge_control_plan"
        survivor_operation_plan.operation_window_start = _parse_optional_datetime_or_date_range_start(
            proposed_plan["operationWindow"],
        )
        survivor_operation_plan.operation_window_end = _parse_optional_datetime_or_date_range_end(
            proposed_plan["operationWindow"],
        )
        survivor_operation_plan.parameters = proposed_plan
        survivor_operation_plan.prescription_map = dict(
            proposed_plan.get("prescriptionMap") or proposed_plan.get("controlPlan") or {},
        )
        survivor_operation_plan.basis = str(proposed_plan.get("basis") or "")

        if stale_operation_plan is not None:
            stale_operation_plan.status = "cancelled"

        session.add(
            EventRecord(
                planting_plan_id=plan_id,
                event_type=REPAIR_EVENT_TYPE,
                event_category="runtime",
                event_source="orchestrator",
                source_system="cropflow",
                source_record_id=str(survivor_task.id),
                payload={
                    "keptTaskIntentId": survivor_task_intent.id,
                    "keptTaskId": survivor_task.id,
                    "cancelledTaskIntentId": stale_task_intent.id,
                    "cancelledTaskId": stale_task.id,
                    "mergedTitle": proposed_task["title"],
                    "mergedOperationWindow": proposed_plan["operationWindow"],
                    "controlType": proposed_plan["controlType"],
                    "merged": merge_result.merged_result.merged,
                },
                occurred_at=_utcnow(),
                processing_status="processed",
                processed_at=_utcnow(),
                idempotency_key=f"{REPAIR_IDEMPOTENCY_PREFIX}:{plan_id}",
                created_by_type="system",
                created_by_id=REPAIR_ACTOR,
            ),
        )

    return RepairOutcome(
        planting_plan_id=plan_id,
        status="repaired" if apply else "would_repair",
        message=(
            f"Keep task {survivor_task.id} ({survivor.control_type}) and cancel task {stale_task.id} "
            f"({stale.control_type})."
        ),
        kept_task_intent_id=int(survivor_task_intent.id),
        kept_task_id=int(survivor_task.id),
        cancelled_task_intent_id=int(stale_task_intent.id),
        cancelled_task_id=int(stale_task.id),
    )


def load_candidate(session: Session, plan_id: int) -> dict[str, PendingControlBundle] | None:
    operation_plan_repository = OperationPlanRepository(session)
    stmt = (
        select(FarmingTask, TaskIntent)
        .join(TaskIntent, TaskIntent.id == FarmingTask.task_intent_id)
        .where(FarmingTask.planting_plan_id == plan_id)
        .where(FarmingTask.task_subtype == TASK_SUBTYPE_DISEASE_PEST_CONTROL)
        .where(FarmingTask.status == FARMING_TASK_STATUS_PENDING)
        .where(TaskIntent.status == TASK_INTENT_STATUS_CONVERTED)
        .order_by(FarmingTask.created_at.asc(), FarmingTask.id.asc())
    )

    regular: list[PendingControlBundle] = []
    emergency: list[PendingControlBundle] = []
    for farming_task, task_intent in session.execute(stmt):
        proposed_plan = dict(task_intent.rule_result.get("proposedPlan") or {})
        control_type = str(proposed_plan.get("controlType") or "")
        if control_type not in {"regular", "emergency"}:
            continue
        operation_plan = operation_plan_repository.get_active_by_task(int(farming_task.id))
        bundle = PendingControlBundle(
            task_intent_id=int(task_intent.id),
            farming_task_id=int(farming_task.id),
            operation_plan_id=int(operation_plan.id) if operation_plan is not None else None,
            control_type=control_type,
            task_created_at=farming_task.created_at,
        )
        if control_type == "regular":
            regular.append(bundle)
        else:
            emergency.append(bundle)

    if len(regular) != 1 or len(emergency) != 1:
        return None
    return {"regular": regular[0], "emergency": emergency[0]}


def choose_survivor(regular: PendingControlBundle, emergency: PendingControlBundle) -> PendingControlBundle:
    return max((regular, emergency), key=lambda item: (item.task_created_at, item.farming_task_id))


def build_repair_service(session: Session, settings: Settings) -> PestDiseaseControlPlanningService:
    return PestDiseaseControlPlanningService(
        planting_plan_repository=PlantingPlanRepository(session),
        farm_repository=FarmRepository(session),
        rice_control_window_level1_repository=RiceControlWindowLevel1Repository(session),
        stage_prediction_snapshot_repository=StagePredictionSnapshotRepository(session),
        calendar_item_repository=CalendarItemRepository(session),
        operation_plan_repository=OperationPlanRepository(session),
        context_resolver=PlantProtectionPlanContextResolver(
            code_dict_repository=CodeDictRepository(session),
            rice_variety_repository=RiceVarietyRepository(session),
        ),
        weather_provider=build_weather_provider(session, settings),
        control_client=HttpPestDiseaseControlClient(settings.pest_disease_survey_base_url),
    )


def build_merged_payload(
    *,
    merge_result,
    survivor_task_intent: TaskIntent,
    stale_task_intent: TaskIntent,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    operation_window = _format_date_range(_resolve_merged_control_operation_window(merge_result.merged_result))
    proposed_task = {
        "title": merge_result.title,
        "recommendedControlDate": operation_window,
    }
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
            "Repair merged existing regular and emergency disease pest control recommendations "
            f"from task intents {survivor_task_intent.id} and {stale_task_intent.id}."
        ),
    }
    raw_response = {
        "regularTheory": dict(merge_result.regular_theory),
        "emergencyTheory": dict(merge_result.emergency_theory),
        "mergeRange": merge_result.merge_range_result.raw_response,
        "merge": merge_result.merged_result.raw_response,
    }
    return proposed_task, proposed_plan, raw_response


def build_merged_rule_result(
    *,
    survivor_task_intent: TaskIntent,
    stale_task_intent: TaskIntent,
    proposed_task: dict[str, Any],
    proposed_plan: dict[str, Any],
    raw_response: dict[str, Any],
) -> dict[str, Any]:
    merged_rule_result = dict(survivor_task_intent.rule_result or {})
    merged_rule_result["algorithmCode"] = "pest_disease.merge_control_plan"
    merged_rule_result["branchType"] = "repair_merged_disease_pest_control"
    merged_rule_result["proposedTask"] = proposed_task
    merged_rule_result["proposedPlan"] = proposed_plan
    merged_rule_result["inputExecutionRecordIds"] = merge_input_execution_record_ids(
        survivor_task_intent.rule_result,
        stale_task_intent.rule_result,
    )
    merged_rule_result["rawResponse"] = raw_response
    return merged_rule_result


def merge_input_execution_record_ids(*rule_results: dict[str, Any]) -> list[int]:
    seen: set[int] = set()
    merged_ids: list[int] = []
    for rule_result in rule_results:
        raw_ids = rule_result.get("inputExecutionRecordIds") or []
        for raw_value in raw_ids:
            value = int(raw_value)
            if value in seen:
                continue
            seen.add(value)
            merged_ids.append(value)
    return merged_ids


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


if __name__ == "__main__":
    main()
