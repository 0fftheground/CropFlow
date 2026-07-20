from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.agent_runtime.contracts import AgentRole, RuntimeActor, RuntimeScope


@dataclass(frozen=True, slots=True)
class ActionContract:
    name: str
    description: str
    allowed_roles: tuple[AgentRole, ...]
    input_schema: dict[str, Any]
    side_effect: bool = False
    approval_required: bool = False
    parallel_safe: bool = False
    risk_level: str = "low"
    requires_pending_task: bool = False
    requires_open_review: bool = False

    def model_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "side_effect": self.side_effect,
            "approval_required": self.approval_required,
            "parallel_safe": self.parallel_safe,
            "risk_level": self.risk_level,
        }


class CropFlowOntology:
    version = "cropflow-agent-runtime-v1"

    def __init__(self) -> None:
        empty_schema = {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        }
        self.actions = {
            item.name: item
            for item in (
                ActionContract(
                    name="view_plan_context",
                    description="读取当前 PlantingPlan 的运行态、当前生育期、任务和待复核摘要。",
                    allowed_roles=(AgentRole.OBSERVER, AgentRole.OPERATOR, AgentRole.REVIEWER),
                    input_schema=empty_schema,
                    parallel_safe=True,
                ),
                ActionContract(
                    name="get_task_detail",
                    description="读取当前 PlantingPlan 内指定 FarmingTask 的方案、执行和上下游详情。",
                    allowed_roles=(AgentRole.OBSERVER, AgentRole.OPERATOR, AgentRole.REVIEWER),
                    input_schema={
                        "type": "object",
                        "properties": {"task_id": {"type": "integer", "minimum": 1}},
                        "required": ["task_id"],
                        "additionalProperties": False,
                    },
                    parallel_safe=True,
                ),
                ActionContract(
                    name="get_review_request_detail",
                    description="读取当前 PlantingPlan 内指定 ReviewRequest 的证据和待决内容。",
                    allowed_roles=(AgentRole.OBSERVER, AgentRole.OPERATOR, AgentRole.REVIEWER),
                    input_schema={
                        "type": "object",
                        "properties": {"review_request_id": {"type": "integer", "minimum": 1}},
                        "required": ["review_request_id"],
                        "additionalProperties": False,
                    },
                    parallel_safe=True,
                ),
                ActionContract(
                    name="complete_farming_task",
                    description=(
                        "为当前 PlantingPlan 内的 pending/in_progress FarmingTask 记录人工执行结果。"
                        "该动作会改变任务与执行状态，必须先获得当前用户明确批准。"
                    ),
                    allowed_roles=(AgentRole.OPERATOR,),
                    input_schema={
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "integer", "minimum": 1},
                            "operation_date": {"type": "string", "format": "date"},
                            "result_payload": {"type": "object"},
                        },
                        "required": ["task_id", "operation_date", "result_payload"],
                        "additionalProperties": False,
                    },
                    side_effect=True,
                    approval_required=True,
                    risk_level="high",
                    requires_pending_task=True,
                ),
                ActionContract(
                    name="resolve_review_request",
                    description=(
                        "处理当前 PlantingPlan 内仍为 open 的 ReviewRequest，并把结果交回 PlanOrchestrator。"
                        "该动作必须先获得当前审核用户明确批准。"
                    ),
                    allowed_roles=(AgentRole.REVIEWER,),
                    input_schema={
                        "type": "object",
                        "properties": {
                            "review_request_id": {"type": "integer", "minimum": 1},
                            "decision": {
                                "type": "string",
                                "enum": ["approve", "reject", "adjust", "no_action", "need_more_info"],
                            },
                            "decision_payload": {
                                "type": "object",
                                "description": "结构化调整内容；没有额外结构化内容时传空对象 {}。",
                            },
                            "decision_note": {"type": "string"},
                        },
                        "required": ["review_request_id", "decision", "decision_payload", "decision_note"],
                        "additionalProperties": False,
                    },
                    side_effect=True,
                    approval_required=True,
                    risk_level="high",
                    requires_open_review=True,
                ),
            )
        }

    def get_action(self, name: str) -> ActionContract | None:
        return self.actions.get(name)

    def resolve_actions(self, actor: RuntimeActor, scope: RuntimeScope) -> tuple[ActionContract, ...]:
        if scope.plan_status in {"completed", "archived", "cancelled"}:
            read_only = True
        else:
            read_only = False

        resolved: list[ActionContract] = []
        for action in self.actions.values():
            if actor.role not in action.allowed_roles:
                continue
            if read_only and action.side_effect:
                continue
            if action.requires_pending_task and scope.pending_task_count == 0:
                continue
            if action.requires_open_review and scope.open_review_count == 0:
                continue
            resolved.append(action)
        return tuple(resolved)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "object_types": {
                "PlantingPlan": {
                    "authority": "cf_planting_plan and related CropFlow domain tables",
                    "links": [
                        "CropStageState",
                        "CalendarItem",
                        "FarmingTask",
                        "OperationPlan",
                        "Execution",
                        "Feedback",
                        "ReviewRequest",
                    ],
                }
            },
            "roles": [item.value for item in AgentRole],
            "actions": {
                name: {
                    **asdict(action),
                    "allowed_roles": [role.value for role in action.allowed_roles],
                }
                for name, action in self.actions.items()
            },
        }
