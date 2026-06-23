from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


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


__all__ = [
    "Execution",
    "ExecutionRecord",
]
