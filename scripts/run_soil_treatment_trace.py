from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib import error, request

from sqlalchemy import select

from app.db.session import get_session_factory
from app.models import EventRecord, FarmingTask, OperationPlan, ReviewRequest, TaskIntent

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
    trace_path = TRACE_DIR / f"{datetime.now(UTC).strftime('%Y-%m-%dT%H-%M-%SZ')}-soil-treatment-trace.json"
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    planting_plan_id: int | None = None

    try:
        health = _http_json("GET", f"{base_url}/api/health")
        recorder.record("health_check", _utcnow(), True, health)

        unique_suffix = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        plan_payload = {
            "plan_code": f"SOIL-TRACE-{unique_suffix}",
            "plan_name": f"Soil Trace {unique_suffix}",
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

        task_intents = _http_json("GET", f"{base_url}/api/planting-plans/{planting_plan_id}/task-intents")
        review_requests = _http_json("GET", f"{base_url}/api/planting-plans/{planting_plan_id}/review-requests")
        calendar_items = _http_json("GET", f"{base_url}/api/planting-plans/{planting_plan_id}/calendar-items")
        recorder.record("list_task_intents_initial", _utcnow(), True, {"response": task_intents})
        recorder.record("list_review_requests_initial", _utcnow(), True, {"response": review_requests})
        recorder.record("list_calendar_items_initial", _utcnow(), True, {"response": calendar_items})

        soil_task_intent = next(
            (item for item in task_intents if item["task_subtype"] == "plant_protection.soil_sealing_weed_control"),
            None,
        )
        if soil_task_intent is None:
            raise RuntimeError("The planting plan did not generate a soil-treatment task intent.")

        soil_review_request = next(
            (item for item in review_requests if item["review_type"] == "soil_treatment_recommendation"),
            None,
        )
        if soil_review_request is None:
            raise RuntimeError("The planting plan did not generate a soil-treatment review request.")

        approve_payload = {
            "decision": "approve",
            "decision_payload": {},
            "decision_note": "Approved in run_soil_treatment_trace.py",
            "resolved_by": "reviewer-demo",
        }
        approve_result = _http_json(
            "POST",
            f"{base_url}/api/review-requests/{soil_review_request['id']}/resolve",
            approve_payload,
        )
        recorder.record(
            "resolve_soil_treatment_review",
            _utcnow(),
            True,
            {"request": approve_payload, "response": approve_result},
        )

        tasks = _http_json("GET", f"{base_url}/api/planting-plans/{planting_plan_id}/tasks")
        recorder.record("list_tasks_after_approval", _utcnow(), True, {"response": tasks})
        soil_task = next(
            (item for item in tasks if item["task_subtype"] == "plant_protection.soil_sealing_weed_control"),
            None,
        )
        if soil_task is None:
            raise RuntimeError("Approving the soil-treatment review did not create a farming task.")

        operation_date = str(soil_task["planned_start_at"]).split("T", 1)[0]
        execution_payload = {
            "result_payload": {
                "note": "Soil treatment execution completed in run_soil_treatment_trace.py",
            },
            "operation_date": f"{operation_date}T09:00:00",
            "actual_start_at": f"{operation_date}T09:00:00",
            "actual_end_at": f"{operation_date}T10:00:00",
            "actual_area": 1.25,
            "actual_amount": 1.0,
            "amount_unit": "亩",
        }
        execution_result = _http_json(
            "POST",
            f"{base_url}/api/tasks/{soil_task['id']}/execution-completions",
            execution_payload,
        )
        recorder.record(
            "complete_soil_treatment_task",
            _utcnow(),
            True,
            {"request": execution_payload, "response": execution_result},
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
        recorder.record("failure", _utcnow(), False, failure_detail)
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


def _snapshot_plan_state(planting_plan_id: int) -> dict[str, Any]:
    session = get_session_factory()()
    try:
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
        tasks = list(
            session.scalars(
                select(FarmingTask).where(FarmingTask.planting_plan_id == planting_plan_id).order_by(FarmingTask.id.asc()),
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
            "task_intents": [_serialize_model(item) for item in task_intents],
            "review_requests": [_serialize_model(item) for item in review_requests],
            "tasks": [_serialize_model(item) for item in tasks],
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
        elif isinstance(value, Decimal):
            data[column.name] = str(value)
        else:
            data[column.name] = value
    return data


def _utcnow() -> datetime:
    return datetime.now(UTC)


if __name__ == "__main__":
    main()
