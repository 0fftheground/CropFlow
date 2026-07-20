from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Farm(Base):
    __tablename__ = "cf_farm"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    farm_name: Mapped[str] = mapped_column(String(100))
    external_farm_id: Mapped[str | None] = mapped_column(String(50), unique=True)
    province: Mapped[str | None] = mapped_column(String(100))
    city: Mapped[str | None] = mapped_column(String(100))
    district_county: Mapped[str | None] = mapped_column(String(100))
    adcode: Mapped[str | None] = mapped_column(String(20))
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
    external_field_id: Mapped[str | None] = mapped_column(String(50), index=True)
    boundary_wkt: Mapped[str | None] = mapped_column(Text)
    centroid_lat: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    centroid_lon: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    area_ha: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    created_by_type: Mapped[str] = mapped_column(String(20), server_default=text("'system'"))
    created_by_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class FarmFieldRelation(Base):
    __tablename__ = "cf_farm_field_relation"
    __table_args__ = (UniqueConstraint("farm_id", "field_id", name="uk_cf_farm_field_relation"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    farm_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("cf_farm.id", ondelete="CASCADE"))
    field_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("cf_field.id", ondelete="CASCADE"))
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


class RiceControlWindowLevel1(Base):
    __tablename__ = "pp_rice_control_window_level_1"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    province: Mapped[str] = mapped_column(String(100))
    city: Mapped[str] = mapped_column(String(100))
    county: Mapped[str] = mapped_column(String(100))
    data_year: Mapped[int] = mapped_column(Integer)
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class CropStageDict(Base):
    __tablename__ = "cf_crop_stage_dict"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    stage_code: Mapped[str] = mapped_column(String(50), unique=True)
    stage_name: Mapped[str] = mapped_column(String(100))
    season_scope: Mapped[str] = mapped_column(String(20))
    business_stage_code: Mapped[str | None] = mapped_column(String(50))
    display_order: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(server_default=text("true"))
    created_by_type: Mapped[str] = mapped_column(String(20), server_default=text("'system'"))
    created_by_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class AdministrativeDivision(Base):
    __tablename__ = "cf_administrative_division"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(12), unique=True)
    adcode: Mapped[str] = mapped_column(String(6))
    name: Mapped[str] = mapped_column(String(100))
    division_type: Mapped[str] = mapped_column(String(50))
    level: Mapped[int] = mapped_column(Integer)
    parent_code: Mapped[str | None] = mapped_column(String(12))
    sort_order: Mapped[int] = mapped_column(Integer)
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


__all__ = [
    "AdministrativeDivision",
    "CodeDict",
    "CropStageDict",
    "Farm",
    "FarmFieldRelation",
    "Field",
    "RiceControlWindowLevel1",
    "RiceVariety",
    "User",
]
