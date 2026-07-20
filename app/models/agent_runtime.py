from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AgentSession(Base):
    __tablename__ = "cf_agent_session"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    planting_plan_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("cf_planting_plan.id", ondelete="CASCADE"),
    )
    user_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("cf_user.id", ondelete="RESTRICT"),
    )
    selected_role: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(30), server_default=text("'active'"))
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class AgentMessage(Base):
    __tablename__ = "cf_agent_message"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("cf_agent_session.id", ondelete="CASCADE"),
    )
    run_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("cf_agent_run.id", ondelete="SET NULL"),
    )
    role: Mapped[str] = mapped_column(String(30))
    content: Mapped[str] = mapped_column(Text)
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class AgentRun(Base):
    __tablename__ = "cf_agent_run"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("cf_agent_session.id", ondelete="CASCADE"),
    )
    user_message_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("cf_agent_message.id", ondelete="RESTRICT"),
    )
    status: Mapped[str] = mapped_column(String(30), server_default=text("'pending'"))
    iteration: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    provider_name: Mapped[str] = mapped_column(String(100))
    provider_state: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class AgentToolCall(Base):
    __tablename__ = "cf_agent_tool_call"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("cf_agent_run.id", ondelete="CASCADE"),
    )
    action_name: Mapped[str] = mapped_column(String(100))
    arguments: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    status: Mapped[str] = mapped_column(String(30), server_default=text("'proposed'"))
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    approval_required: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class AgentApprovalRequest(Base):
    __tablename__ = "cf_agent_approval_request"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("cf_agent_run.id", ondelete="CASCADE"),
    )
    tool_call_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("cf_agent_tool_call.id", ondelete="CASCADE"),
        unique=True,
    )
    status: Mapped[str] = mapped_column(String(30), server_default=text("'pending'"))
    action_name: Mapped[str] = mapped_column(String(100))
    action_summary: Mapped[str] = mapped_column(Text)
    requested_by: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("cf_user.id", ondelete="RESTRICT"),
    )
    decided_by: Mapped[str | None] = mapped_column(
        String(100),
        ForeignKey("cf_user.id", ondelete="RESTRICT"),
    )
    decision_note: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class AgentEvent(Base):
    __tablename__ = "cf_agent_event"
    __table_args__ = (UniqueConstraint("run_id", "sequence", name="uk_cf_agent_event_run_sequence"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("cf_agent_run.id", ondelete="CASCADE"),
    )
    sequence: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class AgentAuditRecord(Base):
    __tablename__ = "cf_agent_audit_record"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("cf_agent_run.id", ondelete="CASCADE"),
    )
    audit_type: Mapped[str] = mapped_column(String(100))
    actor_user_id: Mapped[str | None] = mapped_column(String(100))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


__all__ = [
    "AgentApprovalRequest",
    "AgentAuditRecord",
    "AgentEvent",
    "AgentMessage",
    "AgentRun",
    "AgentSession",
    "AgentToolCall",
]
