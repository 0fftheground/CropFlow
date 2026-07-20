from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.agent_runtime.contracts import AgentRole, ModelRequest, RuntimeActor, RuntimeRejected, RuntimeScope
from app.agent_runtime.ontology import CropFlowOntology
from app.models import FarmingTask, ReviewRequest, User
from app.repositories import (
    AgentRuntimeRepository,
    CropStageStateRepository,
    CropThermalTimeStateRepository,
    FarmRepository,
    FarmingTaskRepository,
    PlantingPlanFieldRelationRepository,
    PlantingPlanRepository,
    ReviewRequestRepository,
)


CURRENT_TASK_STATUSES = {"pending", "confirmed", "in_progress"}


@dataclass(frozen=True, slots=True)
class CropFlowRuntimeSnapshot:
    object_view: dict[str, Any]
    scope: RuntimeScope


class CropFlowContextBuilder:
    def __init__(
        self,
        *,
        runtime_repository: AgentRuntimeRepository,
        planting_plan_repository: PlantingPlanRepository,
        planting_plan_field_repository: PlantingPlanFieldRelationRepository,
        farm_repository: FarmRepository,
        crop_stage_repository: CropStageStateRepository,
        crop_thermal_repository: CropThermalTimeStateRepository,
        farming_task_repository: FarmingTaskRepository,
        review_request_repository: ReviewRequestRepository,
        ontology: CropFlowOntology,
        default_role: str = "observer",
        task_limit: int = 20,
        review_limit: int = 20,
    ) -> None:
        self.runtime_repository = runtime_repository
        self.planting_plan_repository = planting_plan_repository
        self.planting_plan_field_repository = planting_plan_field_repository
        self.farm_repository = farm_repository
        self.crop_stage_repository = crop_stage_repository
        self.crop_thermal_repository = crop_thermal_repository
        self.farming_task_repository = farming_task_repository
        self.review_request_repository = review_request_repository
        self.ontology = ontology
        self.default_role = default_role
        self.task_limit = task_limit
        self.review_limit = review_limit

    def resolve_actor(self, user_id: str, requested_role: str | None) -> RuntimeActor:
        user = self.runtime_repository.get_user(user_id)
        if user is None:
            raise RuntimeRejected(f"User {user_id} does not exist.", code="user_not_found")
        if user.status != "active":
            raise RuntimeRejected(f"User {user_id} is not active.", code="user_inactive")

        allowed_roles = self._resolve_user_roles(user)
        if requested_role is not None:
            try:
                selected_role = AgentRole(requested_role)
            except ValueError as exc:
                raise RuntimeRejected(f"Unsupported agent role: {requested_role}.", code="invalid_role") from exc
            if selected_role not in allowed_roles:
                raise RuntimeRejected(
                    f"User {user_id} is not assigned agent role {requested_role}.",
                    code="role_not_assigned",
                )
        else:
            selected_role = min(allowed_roles, key=_role_priority)

        return RuntimeActor(
            user_id=user.id,
            display_name=user.display_name or user.username,
            role=selected_role,
        )

    def load_snapshot(self, planting_plan_id: int) -> CropFlowRuntimeSnapshot:
        plan = self.planting_plan_repository.get(planting_plan_id)
        if plan is None:
            raise RuntimeRejected(
                f"Planting plan {planting_plan_id} does not exist.",
                code="planting_plan_not_found",
            )

        tasks = self.farming_task_repository.list_current_by_plan(planting_plan_id)
        reviews = self.review_request_repository.list_current_by_plan(planting_plan_id)
        stage = self.crop_stage_repository.get_by_plan(planting_plan_id)
        thermal = self.crop_thermal_repository.get_by_plan(planting_plan_id)
        farm = self.farm_repository.get(plan.farm_id)
        field_ids = self.planting_plan_field_repository.list_field_ids_by_plan(planting_plan_id)

        scope = RuntimeScope(
            planting_plan_id=planting_plan_id,
            plan_status=plan.status,
            pending_task_count=sum(item.status in CURRENT_TASK_STATUSES for item in tasks),
            open_review_count=sum(item.status == "open" for item in reviews),
        )
        object_view = {
            "object_type": "PlantingPlan",
            "object_id": plan.id,
            "plan_code": plan.plan_code,
            "plan_name": plan.plan_name,
            "status": plan.status,
            "crop_name": plan.crop_name,
            "variety_name": plan.variety_name,
            "farm": {
                "farm_id": plan.farm_id,
                "farm_name": farm.farm_name if farm is not None else None,
                "province": farm.province if farm is not None else None,
                "city": farm.city if farm is not None else None,
                "district_county": farm.district_county if farm is not None else None,
            },
            "field_ids": field_ids,
            "schedule": {
                "sowing_date": _json_value(plan.sowing_date),
                "transplant_date": _json_value(plan.transplant_date),
                "expected_harvest_date": _json_value(plan.expected_harvest_date),
            },
            "current_stage": (
                {
                    "stage_code": stage.current_stage_code,
                    "stage_name": stage.current_stage_name,
                    "source": stage.stage_source,
                    "effective_date": _json_value(stage.effective_date),
                    "version": stage.version,
                }
                if stage is not None
                else None
            ),
            "thermal_time": (
                {
                    "accumulated": _json_value(thermal.accumulated_thermal_time),
                    "unit": thermal.thermal_time_unit,
                    "last_calculated_date": _json_value(thermal.last_calculated_date),
                }
                if thermal is not None
                else None
            ),
            "current_tasks": [serialize_farming_task(item) for item in tasks[: self.task_limit]],
            "open_review_requests": [serialize_review_request(item) for item in reviews[: self.review_limit]],
            "context_limits": {
                "task_limit": self.task_limit,
                "review_limit": self.review_limit,
                "task_count_before_limit": len(tasks),
                "review_count_before_limit": len(reviews),
            },
            "authority": {
                "business_state": "CropFlow domain tables",
                "runtime_state": "cf_agent_* tables",
                "ontology_version": self.ontology.version,
            },
        }
        return CropFlowRuntimeSnapshot(object_view=object_view, scope=scope)

    def build_model_request(
        self,
        *,
        run_id: str,
        session_id: str,
        user_input: str,
        actor: RuntimeActor,
        provider_state: dict[str, Any],
    ) -> ModelRequest:
        session = self.runtime_repository.get_session(session_id)
        if session is None:
            raise RuntimeRejected(f"Agent session {session_id} does not exist.", code="session_not_found")
        snapshot = self.load_snapshot(session.planting_plan_id)
        actions = self.ontology.resolve_actions(actor, snapshot.scope)
        return ModelRequest(
            run_id=run_id,
            current_user_input=user_input,
            recent_messages=tuple(self.runtime_repository.list_recent_messages(session_id)),
            actor={
                "user_id": actor.user_id,
                "display_name": actor.display_name,
                "role": actor.role.value,
            },
            object_view=snapshot.object_view,
            available_actions=tuple(item.model_schema() for item in actions),
            tool_results=tuple(self.runtime_repository.list_tool_results(run_id)),
            provider_state=provider_state or {},
        )

    def _resolve_user_roles(self, user: User) -> set[AgentRole]:
        metadata = dict(user.metadata_payload or {})
        raw_roles = metadata.get("agent_roles", metadata.get("agentRoles"))
        if isinstance(raw_roles, str):
            values = [raw_roles]
        elif isinstance(raw_roles, list):
            values = [item for item in raw_roles if isinstance(item, str)]
        else:
            values = [self.default_role]

        roles: set[AgentRole] = set()
        for value in values:
            try:
                roles.add(AgentRole(value))
            except ValueError:
                continue
        if not roles:
            try:
                roles.add(AgentRole(self.default_role))
            except ValueError as exc:
                raise RuntimeRejected(
                    f"Invalid configured default agent role: {self.default_role}.",
                    code="invalid_default_role",
                ) from exc
        return roles


def serialize_farming_task(task: FarmingTask) -> dict[str, Any]:
    return {
        "task_id": task.id,
        "task_category": task.task_category,
        "task_subtype": task.task_subtype,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "execution_mode": task.execution_mode,
        "planned_start_at": _json_value(task.planned_start_at),
        "planned_end_at": _json_value(task.planned_end_at),
        "target_stage_code": task.target_stage_code,
        "generation_reason": task.generation_reason,
    }


def serialize_review_request(review: ReviewRequest) -> dict[str, Any]:
    return {
        "review_request_id": review.id,
        "review_type": review.review_type,
        "status": review.status,
        "priority": review.priority,
        "title": review.title,
        "description": review.description,
        "assigned_user_id": review.assigned_user_id,
        "source_entity_type": review.source_entity_type,
        "source_entity_id": review.source_entity_id,
    }


def _json_value(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def _role_priority(role: AgentRole) -> int:
    return {
        AgentRole.OBSERVER: 0,
        AgentRole.OPERATOR: 1,
        AgentRole.REVIEWER: 2,
    }[role]
