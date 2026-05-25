from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib import error, request

from sqlalchemy import select

from app.api.deps import build_cropflow_plan_orchestrator
from app.core.constants import TASK_SUBTYPE_STEM_LEAF_WEED_PRE_SURVEY
from app.core.config import get_settings
from app.db.session import get_session_factory
from app.models import CalendarItem, EventRecord, FarmingTask, OperationPlan, ReviewRequest, TaskIntent
from app.repositories import EventRecordRepository, PlantingPlanRepository
from app.services import TaskGenerationService

REPO_ROOT = Path(__file__).resolve().parents[1]
TRACE_DIR = REPO_ROOT / "project-context" / "session-log" / "e2e-traces"


@dataclass(slots=True)
class StepTrace:
    name: str
    started_at: str
    finished_at: str
    ok: bool
    detail: dict[str, Any]


class TraceRecorder:
    def __init__(self) -> None:
        self.started_at = _utcnow().isoformat()
        self.steps: list[StepTrace] = []

    def record(self, name: str, started_at: datetime, ok: bool, detail: dict[str, Any]) -> None:
        self.steps.append(
            StepTrace(
                name=name,
                started_at=started_at.isoformat(),
                finished_at=_utcnow().isoformat(),
                ok=ok,
                detail=detail,
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "started_at": self.started_at,
            "finished_at": _utcnow().isoformat(),
            "steps": [asdict(step) for step in self.steps],
        }


def main() -> None:
    recorder = TraceRecorder()
    base_url = os.environ.get("CROPFLOW_E2E_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    trace_path = TRACE_DIR / f"{datetime.now(UTC).strftime('%Y-%m-%dT%H-%M-%SZ')}-local-api-e2e-trace.json"
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    planting_plan_id: int | None = None

    try:
        health = _http_json("GET", f"{base_url}/api/health")
        recorder.record("health_check", _utcnow(), True, health)

        unique_suffix = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        plan_payload = {
            "plan_code": f"E2E-TRACE-{unique_suffix}",
            "plan_name": f"E2E Trace {unique_suffix}",
            "farm_id": 1,
            "field_ids": [10, 11],
            "culti_type_code": 5,
            "planting_method_code": 1,
            "crop_name": "水稻",
            "variety_id": 1,
            "sowing_date": "2026-04-10",
            "status": "active",
            "task_generation_window_days": 14,
            "metadata": {
                "province": "湖南省",
                "trace": True,
            },
        }
        plan_created = _http_json("POST", f"{base_url}/api/planting-plans", plan_payload)
        planting_plan_id = int(plan_created["id"])
        recorder.record("create_plan", _utcnow(), True, {"request": plan_payload, "response": plan_created})

        calendar_items = _http_json("GET", f"{base_url}/api/planting-plans/{planting_plan_id}/calendar-items")
        recorder.record("list_calendar_items_initial", _utcnow(), True, {"response": calendar_items})
        if not calendar_items:
            raise RuntimeError("No initial calendar items were generated for the planting plan.")
        pre_survey_item = next(
            (item for item in calendar_items if item["task_subtype"] == TASK_SUBTYPE_STEM_LEAF_WEED_PRE_SURVEY),
            None,
        )
        if pre_survey_item is None:
            raise RuntimeError("The planting plan did not generate a pre-treatment survey calendar item.")
        pre_survey_date = pre_survey_item["suggested_start_date"]

        generated_tasks = _run_due_task_generation(planting_plan_id, pre_survey_date)
        recorder.record("generate_due_tasks_pre_survey", _utcnow(), True, {"response": generated_tasks})

        tasks = _http_json("GET", f"{base_url}/api/planting-plans/{planting_plan_id}/tasks")
        pre_survey_task = next(item for item in tasks if item["task_subtype"] == "plant_protection.stem_leaf_weed_pre_survey")
        recorder.record("list_tasks_pre_survey", _utcnow(), True, {"response": tasks})

        pre_survey_payload = {
            "result_payload": {
                "province": "湖南省",
                "survey_date": "20260418",
                "rice_leaf_age": 4.5,
                "BaiCao": {"leaf_age": 2, "mass": 100},
                "QianJinZi": {"leaf_age": 0, "mass": 0},
                "KuoYeCao": {"mass": 0},
                "SuoCao": {"mass": 0},
            },
        }
        pre_survey_result = _http_json(
            "POST",
            f"{base_url}/api/tasks/{pre_survey_task['id']}/survey-results",
            pre_survey_payload,
        )
        recorder.record(
            "record_pre_survey_result",
            _utcnow(),
            True,
            {"request": pre_survey_payload, "response": pre_survey_result},
        )

        task_intents = _http_json("GET", f"{base_url}/api/planting-plans/{planting_plan_id}/task-intents")
        review_requests = _http_json("GET", f"{base_url}/api/planting-plans/{planting_plan_id}/review-requests")
        recorder.record("list_task_intents", _utcnow(), True, {"response": task_intents})
        recorder.record("list_review_requests", _utcnow(), True, {"response": review_requests})

        weed_control_review = next(
            (item for item in review_requests if item["review_type"] == "weed_control_recommendation"),
            None,
        )
        if weed_control_review is None:
            raise RuntimeError("The planting plan did not generate a weed-control review request.")
        review_request_id = int(weed_control_review["id"])
        approve_payload = {
            "decision": "approve",
            "decision_payload": {},
            "decision_note": "Approved in run_e2e_trace.py",
            "resolved_by": "reviewer-demo",
        }
        approve_result = _http_json(
            "POST",
            f"{base_url}/api/review-requests/{review_request_id}/resolve",
            approve_payload,
        )
        control_task_id = int(approve_result["farming_task_ids"][0])
        recorder.record(
            "resolve_review_request",
            _utcnow(),
            True,
            {"request": approve_payload, "response": approve_result},
        )

        control_intent = next(item for item in task_intents if item["id"] == weed_control_review["source_entity_id"])
        control_date = control_intent["rule_result"]["proposedTask"]["recommendedControlDate"][0]
        execution_payload = {
            "result_payload": {
                "province": "湖南省",
                "note": "E2E execution completion",
            },
            "operation_date": f"{control_date}T09:00:00",
            "actual_start_at": f"{control_date}T09:00:00",
            "actual_end_at": f"{control_date}T10:00:00",
            "actual_area": 1.25,
            "actual_amount": 1.0,
            "amount_unit": "亩",
        }
        execution_result = _http_json(
            "POST",
            f"{base_url}/api/tasks/{control_task_id}/execution-completions",
            execution_payload,
        )
        recorder.record(
            "complete_control_task",
            _utcnow(),
            True,
            {"request": execution_payload, "response": execution_result},
        )

        calendar_items_after_execution = _http_json("GET", f"{base_url}/api/planting-plans/{planting_plan_id}/calendar-items")
        recorder.record(
            "list_calendar_items_after_execution",
            _utcnow(),
            True,
            {"response": calendar_items_after_execution},
        )
        latest_survey_date = max(item["suggested_start_date"] for item in calendar_items_after_execution)
        generated_post_tasks = _run_due_task_generation(planting_plan_id, latest_survey_date)
        recorder.record("generate_due_tasks_post_treatment", _utcnow(), True, {"response": generated_post_tasks})

        tasks_after_execution = _http_json("GET", f"{base_url}/api/planting-plans/{planting_plan_id}/tasks")
        recorder.record("list_tasks_after_execution", _utcnow(), True, {"response": tasks_after_execution})
        rice_safety_task = next(item for item in tasks_after_execution if item["task_subtype"] == "plant_protection.rice_safety_survey")
        control_effect_task = next(
            item for item in tasks_after_execution if item["task_subtype"] == "plant_protection.control_effect_survey"
        )

        rice_safety_payload = {
            "result_payload": {
                "survey_date": "20260422",
                "rice_injury_level": "无",
            },
        }
        rice_safety_result = _http_json(
            "POST",
            f"{base_url}/api/tasks/{rice_safety_task['id']}/survey-results",
            rice_safety_payload,
        )
        recorder.record(
            "record_rice_safety_survey",
            _utcnow(),
            True,
            {"request": rice_safety_payload, "response": rice_safety_result},
        )

        control_effect_payload = {
            "result_payload": {
                "province": "湖南省",
                "control_date": control_date.replace("-", ""),
                "previous_injury_level": "无",
                "survey_date": "20260426",
                "rice_leaf_age": 4.5,
                "rice_injury_level": "无",
                "BaiCao": {"control_effect": 0.95, "leaf_age": 2, "mass": 5},
                "QianJinZi": {"control_effect": 1, "leaf_age": 0, "mass": 0},
                "KuoYeCao": {"control_effect": 1, "mass": 0},
                "SuoCao": {"control_effect": 1, "mass": 0},
                "survey_data_before_treatment": pre_survey_payload["result_payload"],
            },
        }
        control_effect_result = _http_json(
            "POST",
            f"{base_url}/api/tasks/{control_effect_task['id']}/survey-results",
            control_effect_payload,
        )
        recorder.record(
            "record_control_effect_survey",
            _utcnow(),
            True,
            {"request": control_effect_payload, "response": control_effect_result},
        )

        final_snapshot = _snapshot_plan_state(planting_plan_id)
        recorder.record("final_snapshot", _utcnow(), True, final_snapshot)
    except Exception as exc:
        failure_detail: dict[str, Any] = {
            "error_type": type(exc).__name__,
            "message": str(exc),
        }
        if planting_plan_id is not None:
            failure_detail["planting_plan_id"] = planting_plan_id
            failure_detail["plan_snapshot"] = _snapshot_plan_state(planting_plan_id)
        recorder.record(
            "failure",
            _utcnow(),
            False,
            failure_detail,
        )
        raise
    finally:
        trace_path.write_text(json.dumps(recorder.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        print(trace_path)


def _http_json(method: str, url: str, payload: dict[str, Any] | None = None) -> dict[str, Any] | list[dict[str, Any]]:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    http_request = request.Request(url, data=body, headers=headers, method=method)
    try:
        with request.urlopen(http_request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        raw_response = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            json.dumps(
                {
                    "url": url,
                    "status": exc.code,
                    "response": raw_response,
                    "request": payload,
                },
                ensure_ascii=False,
            ),
        ) from exc


def _run_due_task_generation(planting_plan_id: int, check_date_iso: str) -> list[dict[str, Any]]:
    session = get_session_factory()()
    try:
        orchestrator = build_cropflow_plan_orchestrator(session, get_settings())
        service = TaskGenerationService(
            planting_plan_repository=PlantingPlanRepository(session),
            event_record_repository=EventRecordRepository(session),
            plan_orchestrator=orchestrator,
        )
        generated_tasks = service.generate_due_tasks(
            planting_plan_id,
            check_date=date.fromisoformat(check_date_iso),
        )
        session.commit()
        return [
            {
                "id": task.id,
                "task_subtype": task.task_subtype,
                "calendar_item_id": task.calendar_item_id,
            }
            for task in generated_tasks
        ]
    finally:
        session.close()


def _snapshot_plan_state(planting_plan_id: int) -> dict[str, Any]:
    session = get_session_factory()()
    try:
        calendar_items = list(
            session.scalars(
                select(CalendarItem).where(CalendarItem.planting_plan_id == planting_plan_id).order_by(CalendarItem.id.asc()),
            ),
        )
        tasks = list(
            session.scalars(
                select(FarmingTask).where(FarmingTask.planting_plan_id == planting_plan_id).order_by(FarmingTask.id.asc()),
            ),
        )
        task_intents = list(
            session.scalars(
                select(TaskIntent).where(TaskIntent.planting_plan_id == planting_plan_id).order_by(TaskIntent.id.asc()),
            ),
        )
        review_requests = list(
            session.scalars(
                select(ReviewRequest).where(ReviewRequest.planting_plan_id == planting_plan_id).order_by(ReviewRequest.id.asc()),
            ),
        )
        operation_plans = list(
            session.scalars(
                select(OperationPlan).where(OperationPlan.planting_plan_id == planting_plan_id).order_by(OperationPlan.id.asc()),
            ),
        )
        events = list(
            session.scalars(
                select(EventRecord).where(EventRecord.planting_plan_id == planting_plan_id).order_by(EventRecord.id.asc()),
            ),
        )
        return {
            "calendar_items": [_serialize_model(item) for item in calendar_items],
            "tasks": [_serialize_model(item) for item in tasks],
            "task_intents": [_serialize_model(item) for item in task_intents],
            "review_requests": [_serialize_model(item) for item in review_requests],
            "operation_plans": [_serialize_model(item) for item in operation_plans],
            "events": [_serialize_model(item) for item in events],
        }
    finally:
        session.close()


def _serialize_model(model: Any) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for column in model.__table__.columns:
        value = getattr(model, column.name)
        if isinstance(value, datetime):
            data[column.name] = value.isoformat()
        elif isinstance(value, date):
            data[column.name] = value.isoformat()
        elif isinstance(value, Decimal):
            data[column.name] = str(value)
        else:
            data[column.name] = value
    return data


def _utcnow() -> datetime:
    return datetime.now(UTC)


if __name__ == "__main__":
    main()
