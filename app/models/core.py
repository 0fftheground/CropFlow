from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Farm(Base):
    __tablename__ = "cf_farm"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    farm_name: Mapped[str] = mapped_column(String(100))
    boundary_wkt: Mapped[str | None] = mapped_column(Text)
    centroid_lat: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    centroid_lon: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    created_by_type: Mapped[str] = mapped_column(String(20), server_default=text("'system'"))
    created_by_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class Field(Base):
    __tablename__ = "cf_field"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    field_name: Mapped[str] = mapped_column(String(100))
    boundary_wkt: Mapped[str | None] = mapped_column(Text)
    centroid_lat: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    centroid_lon: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    area_ha: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    created_by_type: Mapped[str] = mapped_column(String(20), server_default=text("'system'"))
    created_by_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class CodeDict(Base):
    __tablename__ = "cf_code_dict"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[int] = mapped_column(BigInteger, unique=True)
    code_name: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(server_default=text("true"))
    created_by_type: Mapped[str] = mapped_column(String(20), server_default=text("'system'"))
    created_by_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class User(Base):
    __tablename__ = "cf_user"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    user_code: Mapped[str | None] = mapped_column(String(100), unique=True)
    username: Mapped[str] = mapped_column(String(100))
    display_name: Mapped[str | None] = mapped_column(String(100))
    mobile: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), server_default=text("'active'"))
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        server_default=text("'{}'::jsonb"),
    )
    created_by_type: Mapped[str] = mapped_column(String(20), server_default=text("'system'"))
    created_by_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class RiceVariety(Base):
    __tablename__ = "cf_rice_variety"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    approve_year: Mapped[int | None] = mapped_column(Integer)
    approve_no: Mapped[str | None] = mapped_column(String(64))
    approve_region: Mapped[str | None] = mapped_column(String(255))
    suitable_region: Mapped[str | None] = mapped_column(String(255))
    culti_type_code: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("cf_code_dict.code", ondelete="RESTRICT"),
    )
    sub_type_code: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("cf_code_dict.code", ondelete="RESTRICT"),
    )
    maturity_code: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("cf_code_dict.code", ondelete="RESTRICT"),
    )
    control_variety: Mapped[str | None] = mapped_column(String(255))
    growth_days: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    compare_days: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    rice_code: Mapped[str | None] = mapped_column(String(64))
    created_by_type: Mapped[str] = mapped_column(String(20), server_default=text("'system'"))
    created_by_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class StagePredictionSnapshot(Base):
    __tablename__ = "cf_stage_prediction_snapshot"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    planting_plan_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("cf_planting_plan.id", ondelete="CASCADE"))
    prediction_version: Mapped[int] = mapped_column(Integer)
    prediction_source: Mapped[str] = mapped_column(String(50))
    algorithm_code: Mapped[str] = mapped_column(String(100))
    algorithm_version: Mapped[str | None] = mapped_column(String(100))
    generated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    stage_timeline: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    thermal_thresholds: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    source_event_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("cf_event_record.id", ondelete="SET NULL"),
    )
    created_by_type: Mapped[str] = mapped_column(String(20), server_default=text("'system'"))
    created_by_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class PlantingPlan(Base):
    __tablename__ = "cf_planting_plan"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    plan_code: Mapped[str] = mapped_column(String(100), unique=True)
    plan_name: Mapped[str] = mapped_column(String(255))
    farm_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("cf_farm.id", ondelete="RESTRICT"))
    year: Mapped[int | None] = mapped_column(Integer)
    culti_type_code: Mapped[int] = mapped_column(BigInteger, ForeignKey("cf_code_dict.code", ondelete="RESTRICT"))
    planting_method_code: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("cf_code_dict.code", ondelete="RESTRICT"),
    )
    crop_name: Mapped[str] = mapped_column(String(50))
    variety_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("cf_rice_variety.id", ondelete="RESTRICT"))
    variety_name: Mapped[str] = mapped_column(String(255))
    sowing_date: Mapped[date] = mapped_column(Date)
    transplant_date: Mapped[date | None] = mapped_column(Date)
    harvest_date: Mapped[date | None] = mapped_column(Date)
    transplant_leaf_age: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    previous_harvest_date: Mapped[date | None] = mapped_column(Date)
    ratoon_first_season_harvest_date: Mapped[date | None] = mapped_column(Date)
    expected_harvest_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(50), server_default=text("'draft'"))
    task_generation_window_days: Mapped[int] = mapped_column(Integer, server_default=text("14"))
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        server_default=text("'{}'::jsonb"),
    )
    created_by_type: Mapped[str] = mapped_column(String(20), server_default=text("'system'"))
    created_by_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class PlantingPlanFieldRelation(Base):
    __tablename__ = "cf_planting_plan_field_relation"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    planting_plan_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("cf_planting_plan.id", ondelete="CASCADE"),
    )
    field_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("cf_field.id", ondelete="RESTRICT"),
    )
    created_by_type: Mapped[str] = mapped_column(String(20), server_default=text("'system'"))
    created_by_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


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


class Execution(Base):
    __tablename__ = "cf_execution"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    planting_plan_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("cf_planting_plan.id", ondelete="CASCADE"))
    farming_task_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("cf_farming_task.id", ondelete="CASCADE"))
    operation_plan_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("cf_operation_plan.id", ondelete="SET NULL"),
    )
    execution_mode: Mapped[str] = mapped_column(String(50), server_default=text("'manual'"))
    status: Mapped[str] = mapped_column(String(50), server_default=text("'pending'"))
    assigned_to_type: Mapped[str | None] = mapped_column(String(50))
    assigned_to_id: Mapped[str | None] = mapped_column(String(100))
    external_system_code: Mapped[str | None] = mapped_column(String(100))
    external_execution_id: Mapped[str | None] = mapped_column(String(100))
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    failure_reason: Mapped[str | None] = mapped_column(Text)
    created_by_type: Mapped[str] = mapped_column(String(20), server_default=text("'system'"))
    created_by_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class ExecutionRecord(Base):
    __tablename__ = "cf_execution_record"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    planting_plan_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("cf_planting_plan.id", ondelete="CASCADE"))
    execution_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("cf_execution.id", ondelete="CASCADE"))
    record_type: Mapped[str] = mapped_column(String(50))
    record_time: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    actual_start_at: Mapped[datetime | None] = mapped_column(DateTime)
    actual_end_at: Mapped[datetime | None] = mapped_column(DateTime)
    actual_area: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    actual_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    amount_unit: Mapped[str | None] = mapped_column(String(50))
    result_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    attachments: Mapped[list[Any]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    created_by_type: Mapped[str] = mapped_column(String(20), server_default=text("'system'"))
    created_by_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
