from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EventRecord(Base):
    __tablename__ = "cf_event_record"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    planting_plan_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("cf_planting_plan.id", ondelete="SET NULL"),
    )
    event_type: Mapped[str] = mapped_column(String(100))
    event_category: Mapped[str] = mapped_column(String(50))
    event_source: Mapped[str] = mapped_column(String(50))
    source_system: Mapped[str | None] = mapped_column(String(100))
    source_record_id: Mapped[str | None] = mapped_column(String(100))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    occurred_at: Mapped[datetime] = mapped_column(DateTime)
    received_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime)
    processing_status: Mapped[str] = mapped_column(String(50), server_default=text("'received'"))
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_by_type: Mapped[str] = mapped_column(String(20), server_default=text("'system'"))
    created_by_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class CalendarItem(Base):
    __tablename__ = "cf_calendar_item"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    planting_plan_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("cf_planting_plan.id", ondelete="CASCADE"))
    stage_code: Mapped[str | None] = mapped_column(String(50))
    task_category: Mapped[str] = mapped_column(String(50))
    task_subtype: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    suggested_start_date: Mapped[date] = mapped_column(Date)
    suggested_end_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(50), server_default=text("'active'"))
    calendar_version: Mapped[int] = mapped_column(Integer, server_default=text("1"))
    source_snapshot_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("cf_stage_prediction_snapshot.id", ondelete="SET NULL"),
    )
    parent_task_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("cf_farming_task.id", ondelete="SET NULL"))
    source_execution_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("cf_execution.id", ondelete="SET NULL"),
    )
    source_execution_record_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("cf_execution_record.id", ondelete="SET NULL"),
    )
    generation_condition: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    generated_task_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("cf_farming_task.id", ondelete="SET NULL"),
    )
    last_generation_checked_at: Mapped[datetime | None] = mapped_column(DateTime)
    invalidated_reason: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True)
    created_by_type: Mapped[str] = mapped_column(String(20), server_default=text("'system'"))
    created_by_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class TaskIntent(Base):
    __tablename__ = "cf_task_intent"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    planting_plan_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("cf_planting_plan.id", ondelete="CASCADE"))
    task_category: Mapped[str] = mapped_column(String(50))
    task_subtype: Mapped[str] = mapped_column(String(100))
    priority: Mapped[str] = mapped_column(String(20), server_default=text("'normal'"))
    status: Mapped[str] = mapped_column(String(50), server_default=text("'pending'"))
    trigger_type: Mapped[str] = mapped_column(String(50))
    trigger_summary: Mapped[str | None] = mapped_column(Text)
    rule_result: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    suggested_action: Mapped[str | None] = mapped_column(Text)
    need_more_info_fields: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    no_action_reason: Mapped[str | None] = mapped_column(Text)
    parent_task_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("cf_farming_task.id", ondelete="SET NULL"))
    source_execution_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("cf_execution.id", ondelete="SET NULL"),
    )
    source_execution_record_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("cf_execution_record.id", ondelete="SET NULL"),
    )
    converted_task_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("cf_farming_task.id", ondelete="SET NULL"),
    )
    source_event_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("cf_event_record.id", ondelete="SET NULL"),
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True)
    created_by_type: Mapped[str] = mapped_column(String(20), server_default=text("'system'"))
    created_by_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class ReviewRequest(Base):
    __tablename__ = "cf_review_request"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    planting_plan_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("cf_planting_plan.id", ondelete="CASCADE"))
    review_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50), server_default=text("'open'"))
    priority: Mapped[str] = mapped_column(String(20), server_default=text("'normal'"))
    assigned_user_id: Mapped[str | None] = mapped_column(String(100), ForeignKey("cf_user.id", ondelete="SET NULL"))
    source_entity_type: Mapped[str] = mapped_column(String(100))
    source_entity_id: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    decision: Mapped[str | None] = mapped_column(String(50))
    decision_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    resolved_by: Mapped[str | None] = mapped_column(String(100), ForeignKey("cf_user.id", ondelete="SET NULL"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True)
    created_by_type: Mapped[str] = mapped_column(String(20), server_default=text("'system'"))
    created_by_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class FarmingTask(Base):
    __tablename__ = "cf_farming_task"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    planting_plan_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("cf_planting_plan.id", ondelete="CASCADE"))
    calendar_item_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("cf_calendar_item.id", ondelete="SET NULL"),
    )
    task_intent_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("cf_task_intent.id", ondelete="SET NULL"))
    review_request_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("cf_review_request.id", ondelete="SET NULL"),
    )
    task_category: Mapped[str] = mapped_column(String(50))
    task_subtype: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    target_stage_code: Mapped[str | None] = mapped_column(String(50))
    planned_start_at: Mapped[datetime | None] = mapped_column(DateTime)
    planned_end_at: Mapped[datetime | None] = mapped_column(DateTime)
    priority: Mapped[str] = mapped_column(String(20), server_default=text("'normal'"))
    status: Mapped[str] = mapped_column(String(50), server_default=text("'pending'"))
    execution_mode: Mapped[str] = mapped_column(String(50), server_default=text("'manual'"))
    generation_reason: Mapped[str | None] = mapped_column(Text)
    parent_task_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("cf_farming_task.id", ondelete="SET NULL"))
    source_execution_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("cf_execution.id", ondelete="SET NULL"),
    )
    source_execution_record_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("cf_execution_record.id", ondelete="SET NULL"),
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True)
    created_by_type: Mapped[str] = mapped_column(String(20), server_default=text("'system'"))
    created_by_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class OperationPlan(Base):
    __tablename__ = "cf_operation_plan"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    planting_plan_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("cf_planting_plan.id", ondelete="CASCADE"))
    farming_task_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("cf_farming_task.id", ondelete="CASCADE"))
    plan_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50), server_default=text("'draft'"))
    version: Mapped[int] = mapped_column(Integer, server_default=text("1"))
    algorithm_code: Mapped[str | None] = mapped_column(String(100))
    algorithm_version: Mapped[str | None] = mapped_column(String(100))
    operation_area: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    operation_window_start: Mapped[datetime | None] = mapped_column(DateTime)
    operation_window_end: Mapped[datetime | None] = mapped_column(DateTime)
    execution_mode: Mapped[str] = mapped_column(String(50), server_default=text("'manual'"))
    parameters: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    prescription_map: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    acceptance_criteria: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    basis: Mapped[str | None] = mapped_column(Text)
    source_event_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("cf_event_record.id", ondelete="SET NULL"),
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True)
    created_by_type: Mapped[str] = mapped_column(String(20), server_default=text("'system'"))
    created_by_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


__all__ = [
    "CalendarItem",
    "EventRecord",
    "FarmingTask",
    "OperationPlan",
    "ReviewRequest",
    "TaskIntent",
]
