from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from app.agent_runtime.contracts import ActionRejected, RuntimeActor, RuntimeScope
from app.agent_runtime.ontology import ActionContract, CropFlowOntology
from app.agent_runtime.projection import _json_value, serialize_farming_task, serialize_review_request
from app.services import (
    FarmingTaskQueryService,
    ReviewRequestQueryService,
    ReviewRequestResolveInput,
    ReviewRequestService,
    TaskExecutionCompleteInput,
    TaskExecutionService,
)


class AvailableActionResolver:
    def __init__(self, ontology: CropFlowOntology) -> None:
        self.ontology = ontology

    def resolve(self, actor: RuntimeActor, scope: RuntimeScope) -> tuple[ActionContract, ...]:
        return self.ontology.resolve_actions(actor, scope)


@dataclass(frozen=True, slots=True)
class ActionInvocation:
    run_id: str
    call_id: str
    action_name: str
    arguments: dict[str, Any]
    actor: RuntimeActor
    scope: RuntimeScope


class CropFlowActionExecutor:
    def __init__(
        self,
        *,
        ontology: CropFlowOntology,
        farming_task_query_service: FarmingTaskQueryService,
        review_request_query_service: ReviewRequestQueryService,
        task_execution_service: TaskExecutionService | None,
        review_request_service: ReviewRequestService | None,
        plan_context_loader,
    ) -> None:
        self.ontology = ontology
        self.farming_task_query_service = farming_task_query_service
        self.review_request_query_service = review_request_query_service
        self.task_execution_service = task_execution_service
        self.review_request_service = review_request_service
        self.plan_context_loader = plan_context_loader

    def validate(self, invocation: ActionInvocation) -> ActionContract:
        contract = self.ontology.get_action(invocation.action_name)
        if contract is None:
            raise ActionRejected(f"Unknown action: {invocation.action_name}.", code="unknown_action")
        available = {item.name for item in self.ontology.resolve_actions(invocation.actor, invocation.scope)}
        if invocation.action_name not in available:
            raise ActionRejected(
                "Action is not available for the current role, PlantingPlan state, and workflow context.",
                code="action_not_available",
            )
        _validate_schema(contract.input_schema, invocation.arguments)
        self._validate_object_scope(invocation)
        return contract

    def execute(self, invocation: ActionInvocation) -> dict[str, Any]:
        self.validate(invocation)
        if invocation.action_name == "view_plan_context":
            return self.plan_context_loader(invocation.scope.planting_plan_id).object_view
        if invocation.action_name == "get_task_detail":
            return self._get_task_detail(int(invocation.arguments["task_id"]))
        if invocation.action_name == "get_review_request_detail":
            return self._get_review_detail(int(invocation.arguments["review_request_id"]))
        if invocation.action_name == "complete_farming_task":
            if self.task_execution_service is None:
                raise ActionRejected(
                    "Task execution service is unavailable in this executor.",
                    code="action_not_implemented",
                )
            result = self.task_execution_service.complete_task(
                int(invocation.arguments["task_id"]),
                TaskExecutionCompleteInput(
                    operation_date=date.fromisoformat(str(invocation.arguments["operation_date"])),
                    result_payload=dict(invocation.arguments["result_payload"]),
                ),
            )
            return {
                "execution_id": result.execution.id,
                "execution_record_id": result.execution_record.id,
                "event_record_id": result.event_record.id,
                "calendar_item_ids": [item.id for item in result.calendar_items],
                "task_status": "completed",
            }
        if invocation.action_name == "resolve_review_request":
            if self.review_request_service is None:
                raise ActionRejected(
                    "Review request service is unavailable in this executor.",
                    code="action_not_implemented",
                )
            result = self.review_request_service.resolve(
                int(invocation.arguments["review_request_id"]),
                ReviewRequestResolveInput(
                    decision=str(invocation.arguments["decision"]),
                    decision_payload=dict(invocation.arguments["decision_payload"]),
                    decision_note=str(invocation.arguments["decision_note"]).strip() or None,
                    resolved_by=invocation.actor.user_id,
                ),
            )
            return {
                "review_request_id": result.review_request.id,
                "status": result.review_request.status,
                "decision": result.review_request.decision,
                "event_record_id": result.event_record.id,
                "task_intent_ids": [item.id for item in result.task_intents],
                "farming_task_ids": [item.id for item in result.farming_tasks],
                "operation_plan_ids": [item.id for item in result.operation_plans],
            }
        raise ActionRejected(
            f"Action is declared but not implemented: {invocation.action_name}.",
            code="action_not_implemented",
        )

    def approval_summary(self, invocation: ActionInvocation) -> str:
        if invocation.action_name == "complete_farming_task":
            return (
                f"确认完成 FarmingTask {invocation.arguments['task_id']}，"
                f"作业日期 {invocation.arguments['operation_date']}，并写入执行结果。"
            )
        if invocation.action_name == "resolve_review_request":
            return (
                f"确认以 {invocation.arguments['decision']} 处理 ReviewRequest "
                f"{invocation.arguments['review_request_id']}。"
            )
        return f"确认执行 {invocation.action_name}。"

    def _validate_object_scope(self, invocation: ActionInvocation) -> None:
        if "task_id" in invocation.arguments:
            detail = self.farming_task_query_service.get_detail(int(invocation.arguments["task_id"]))
            task = detail.farming_task
            if task.planting_plan_id != invocation.scope.planting_plan_id:
                raise ActionRejected(
                    "FarmingTask does not belong to the active PlantingPlan.",
                    code="object_scope_mismatch",
                )
            if invocation.action_name == "complete_farming_task" and task.status not in {"pending", "confirmed", "in_progress"}:
                raise ActionRejected(
                    f"FarmingTask {task.id} cannot be completed from status {task.status}.",
                    code="business_state_mismatch",
                )
        if "review_request_id" in invocation.arguments:
            detail = self.review_request_query_service.get_detail(int(invocation.arguments["review_request_id"]))
            review = detail.review_request
            if review.planting_plan_id != invocation.scope.planting_plan_id:
                raise ActionRejected(
                    "ReviewRequest does not belong to the active PlantingPlan.",
                    code="object_scope_mismatch",
                )
            if invocation.action_name == "resolve_review_request" and review.status != "open":
                raise ActionRejected(
                    f"ReviewRequest {review.id} is not open.",
                    code="business_state_mismatch",
                )

    def _get_task_detail(self, task_id: int) -> dict[str, Any]:
        detail = self.farming_task_query_service.get_detail(task_id)
        return {
            "farming_task": serialize_farming_task(detail.farming_task),
            "operation_plans": [
                {
                    "operation_plan_id": item.id,
                    "status": item.status,
                    "version": item.version,
                    "execution_mode": item.execution_mode,
                    "operation_window_start": _json_value(item.operation_window_start),
                    "operation_window_end": _json_value(item.operation_window_end),
                    "parameters": _json_value(item.parameters or {}),
                    "basis": item.basis,
                }
                for item in detail.operation_plans
            ],
            "executions": [
                {
                    "execution_id": item.id,
                    "status": item.status,
                    "execution_mode": item.execution_mode,
                    "started_at": _json_value(item.started_at),
                    "completed_at": _json_value(item.completed_at),
                    "failure_reason": item.failure_reason,
                }
                for item in detail.executions
            ],
            "execution_records": [
                {
                    "execution_record_id": item.id,
                    "record_type": item.record_type,
                    "record_time": _json_value(item.record_time),
                    "result_payload": _json_value(item.result_payload or {}),
                }
                for item in detail.execution_records
            ],
            "review_request": serialize_review_request(detail.review_request) if detail.review_request else None,
        }

    def _get_review_detail(self, review_request_id: int) -> dict[str, Any]:
        detail = self.review_request_query_service.get_detail(review_request_id)
        return {
            "review_request": {
                **serialize_review_request(detail.review_request),
                "decision_payload": _json_value(detail.review_request.decision_payload or {}),
            },
            "source_task_intent": (
                {
                    "task_intent_id": detail.source_task_intent.id,
                    "status": detail.source_task_intent.status,
                    "trigger_summary": detail.source_task_intent.trigger_summary,
                    "rule_result": _json_value(detail.source_task_intent.rule_result or {}),
                    "suggested_action": detail.source_task_intent.suggested_action,
                }
                if detail.source_task_intent
                else None
            ),
            "linked_farming_task": (
                serialize_farming_task(detail.linked_farming_task) if detail.linked_farming_task else None
            ),
            "operation_plan_ids": [item.id for item in detail.operation_plans],
            "source_execution_record": (
                {
                    "execution_record_id": detail.source_execution_record.id,
                    "record_type": detail.source_execution_record.record_type,
                    "result_payload": _json_value(detail.source_execution_record.result_payload or {}),
                }
                if detail.source_execution_record
                else None
            ),
        }


def _validate_schema(schema: dict[str, Any], arguments: dict[str, Any]) -> None:
    required = set(schema.get("required", []))
    missing = sorted(required - arguments.keys())
    if missing:
        raise ActionRejected(
            f"Missing required action arguments: {', '.join(missing)}.",
            code="schema_validation_failed",
        )
    properties = dict(schema.get("properties", {}))
    if schema.get("additionalProperties") is False:
        extras = sorted(arguments.keys() - properties.keys())
        if extras:
            raise ActionRejected(
                f"Unexpected action arguments: {', '.join(extras)}.",
                code="schema_validation_failed",
            )
    for name, value in arguments.items():
        definition = properties.get(name, {})
        expected = definition.get("type")
        if expected == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
            raise ActionRejected(f"Action argument {name} must be an integer.", code="schema_validation_failed")
        if expected == "integer" and "minimum" in definition and value < definition["minimum"]:
            raise ActionRejected(
                f"Action argument {name} must be at least {definition['minimum']}.",
                code="schema_validation_failed",
            )
        if expected == "string" and not isinstance(value, str):
            raise ActionRejected(f"Action argument {name} must be a string.", code="schema_validation_failed")
        if expected == "object" and not isinstance(value, dict):
            raise ActionRejected(f"Action argument {name} must be an object.", code="schema_validation_failed")
        if "enum" in definition and value not in definition["enum"]:
            raise ActionRejected(f"Action argument {name} has an unsupported value.", code="schema_validation_failed")
        if definition.get("format") == "date" and isinstance(value, str):
            try:
                date.fromisoformat(value)
            except ValueError as exc:
                raise ActionRejected(
                    f"Action argument {name} must be an ISO date.",
                    code="schema_validation_failed",
                ) from exc
