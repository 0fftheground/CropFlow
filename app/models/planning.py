from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


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


class CropStageState(Base):
    __tablename__ = "cf_crop_stage_state"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    planting_plan_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("cf_planting_plan.id", ondelete="CASCADE"),
        unique=True,
    )
    current_stage_code: Mapped[str] = mapped_column(String(50))
    current_stage_name: Mapped[str] = mapped_column(String(100))
    stage_source: Mapped[str] = mapped_column(String(50))
    effective_date: Mapped[date] = mapped_column(Date)
    source_snapshot_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("cf_stage_prediction_snapshot.id", ondelete="SET NULL"),
    )
    last_updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    version: Mapped[int] = mapped_column(Integer, server_default=text("1"))
    created_by_type: Mapped[str] = mapped_column(String(20), server_default=text("'system'"))
    created_by_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class CropThermalTimeState(Base):
    __tablename__ = "cf_crop_thermal_time_state"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    planting_plan_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("cf_planting_plan.id", ondelete="CASCADE"),
        unique=True,
    )
    accumulated_thermal_time: Mapped[Decimal] = mapped_column(Numeric(10, 2), server_default=text("0"))
    thermal_time_unit: Mapped[str] = mapped_column(String(20), server_default=text("'degree_day'"))
    base_temperature: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    start_date: Mapped[date | None] = mapped_column(Date)
    last_calculated_date: Mapped[date | None] = mapped_column(Date)
    threshold_snapshot_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("cf_stage_prediction_snapshot.id", ondelete="SET NULL"),
    )
    data_version: Mapped[str | None] = mapped_column(String(100))
    created_by_type: Mapped[str] = mapped_column(String(20), server_default=text("'system'"))
    created_by_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class WeatherSnapshot(Base):
    __tablename__ = "cf_weather_snapshot"
    __table_args__ = (
        UniqueConstraint(
            "farm_id",
            "weather_year",
            "weather_date",
            "source_type",
            "data_version",
            "data_hash",
            name="uq_weather_snapshot_identity",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    farm_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("cf_farm.id", ondelete="CASCADE"))
    weather_year: Mapped[int] = mapped_column(Integer)
    weather_date: Mapped[date] = mapped_column(Date)
    source_type: Mapped[str] = mapped_column(String(50))
    data_version: Mapped[str] = mapped_column(String(100))
    data_hash: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    is_active: Mapped[bool] = mapped_column(server_default=text("true"))
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime)
    superseded_by_snapshot_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("cf_weather_snapshot.id", ondelete="SET NULL"),
    )
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


__all__ = [
    "CropStageState",
    "CropThermalTimeState",
    "PlantingPlan",
    "PlantingPlanFieldRelation",
    "StagePredictionSnapshot",
    "WeatherSnapshot",
]
