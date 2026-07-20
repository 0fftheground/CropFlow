from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agent_runtime import ApprovalRejected, RunCommand, RuntimeRejected
from app.agent_runtime.runtime import AgentRuntime
from app.api.deps import get_agent_runtime
from app.db.session import get_db


router = APIRouter(prefix="/agent")


class AgentRunRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)
    planting_plan_id: int = Field(gt=0)
    message: str = Field(min_length=1, max_length=10000)
    session_id: str | None = Field(default=None, min_length=1, max_length=64)
    role: Literal["observer", "operator", "reviewer"] | None = None


class AgentRunResponse(BaseModel):
    run_id: str
    session_id: str
    status: str
    iteration: int
    pending_approvals: list[dict[str, Any]]
    events_url: str


class ApprovalDecisionRequest(BaseModel):
    decision: Literal["approved", "denied"]
    decided_by: str = Field(min_length=1, max_length=100)
    decision_note: str | None = Field(default=None, max_length=2000)


@router.get("/ontology")
async def get_agent_ontology(
    runtime: AgentRuntime = Depends(get_agent_runtime),
) -> dict[str, Any]:
    return runtime.action_executor.ontology.to_dict()


@router.post("/runs", response_model=AgentRunResponse)
async def create_agent_run(
    payload: AgentRunRequest,
    runtime: AgentRuntime = Depends(get_agent_runtime),
    db: Session = Depends(get_db),
) -> AgentRunResponse:
    command = _to_command(payload)
    try:
        prepared = runtime.prepare_run(command)
        db.commit()
        async for _ in runtime.run(command, prepared=prepared):
            db.commit()
    except RuntimeRejected as exc:
        db.rollback()
        raise _runtime_http_exception(exc) from exc
    except Exception:
        db.rollback()
        raise
    return _serialize_run(runtime, prepared.run_id)


@router.post("/runs/stream")
async def stream_agent_run(
    payload: AgentRunRequest,
    runtime: AgentRuntime = Depends(get_agent_runtime),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    command = _to_command(payload)
    try:
        prepared = runtime.prepare_run(command)
        db.commit()
    except RuntimeRejected as exc:
        db.rollback()
        raise _runtime_http_exception(exc) from exc

    async def event_stream() -> AsyncIterator[str]:
        yield "retry: 3000\n\n"
        try:
            async for event in runtime.run(command, prepared=prepared):
                db.commit()
                yield event.to_sse()
        except Exception:
            db.rollback()
            raise

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/runs/{run_id}", response_model=AgentRunResponse)
async def get_agent_run(
    run_id: str,
    runtime: AgentRuntime = Depends(get_agent_runtime),
) -> AgentRunResponse:
    return _serialize_run(runtime, run_id)


@router.get("/runs/{run_id}/events")
async def get_agent_run_events(
    run_id: str,
    after: int = Query(default=0, ge=0),
    runtime: AgentRuntime = Depends(get_agent_runtime),
) -> StreamingResponse:
    if runtime.repository.get_run(run_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent run {run_id} does not exist.")
    events = runtime.repository.list_events(run_id, after_sequence=after)

    async def event_stream() -> AsyncIterator[str]:
        yield "retry: 3000\n\n"
        for event in events:
            yield event.to_sse()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/approvals/{approval_id}/decide", response_model=AgentRunResponse)
async def decide_agent_approval(
    approval_id: str,
    payload: ApprovalDecisionRequest,
    runtime: AgentRuntime = Depends(get_agent_runtime),
    db: Session = Depends(get_db),
) -> AgentRunResponse:
    approval = runtime.repository.get_approval(approval_id)
    if approval is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent approval {approval_id} does not exist.",
        )
    try:
        async for _ in runtime.decide_approval(
            approval_id=approval_id,
            decision=payload.decision,
            decided_by=payload.decided_by,
            decision_note=payload.decision_note,
        ):
            db.commit()
    except (ApprovalRejected, RuntimeRejected) as exc:
        db.rollback()
        raise _runtime_http_exception(exc) from exc
    except Exception:
        db.rollback()
        raise
    return _serialize_run(runtime, approval.run_id)


def _to_command(payload: AgentRunRequest) -> RunCommand:
    return RunCommand(
        user_id=payload.user_id,
        planting_plan_id=payload.planting_plan_id,
        message=payload.message,
        session_id=payload.session_id,
        role=payload.role,
    )


def _serialize_run(runtime: AgentRuntime, run_id: str) -> AgentRunResponse:
    run = runtime.repository.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent run {run_id} does not exist.")
    approvals = runtime.repository.list_pending_approvals(run_id)
    return AgentRunResponse(
        run_id=run.id,
        session_id=run.session_id,
        status=run.status,
        iteration=run.iteration,
        pending_approvals=[
            {
                "approval_id": item.id,
                "tool_call_id": item.tool_call_id,
                "action_name": item.action_name,
                "summary": item.action_summary,
                "status": item.status,
            }
            for item in approvals
        ],
        events_url=f"/api/agent/runs/{run.id}/events",
    )


def _runtime_http_exception(exc: RuntimeRejected) -> HTTPException:
    status_code = status.HTTP_409_CONFLICT
    if exc.code in {"user_not_found", "planting_plan_not_found", "run_not_found", "approval_not_found"}:
        status_code = status.HTTP_404_NOT_FOUND
    elif exc.code in {"role_not_assigned", "approval_actor_mismatch", "user_inactive"}:
        status_code = status.HTTP_403_FORBIDDEN
    elif exc.code in {"invalid_role", "invalid_approval_decision"}:
        status_code = status.HTTP_400_BAD_REQUEST
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": exc.message})
