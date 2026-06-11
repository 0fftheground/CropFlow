from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from sqlalchemy import Select, func, select, text
from sqlalchemy.orm import Session

from app.models import CodeDict, CropStageDict, Field, Farm, RiceControlWindowLevel1, RiceVariety

REPO_ROOT = Path(__file__).resolve().parents[2]
CODE_DICT_CSV = REPO_ROOT / "database" / "sql" / "agri_code_dict_202605181653.csv"
STAGE_DICT_CSV = REPO_ROOT / "database" / "sql" / "cf_crop_stage_dict_20260601.csv"
RICE_VARIETY_CSV = REPO_ROOT / "database" / "sql" / "agri_rice_variety_202605181649.csv"
RICE_CONTROL_WINDOW_LEVEL1_CSV = REPO_ROOT / "database" / "sql" / "pp_rice_control_window_level_1.csv"
SEED_ACTOR = "seed_reference_data"


@dataclass(slots=True)
class ReferenceSeedSummary:
    code_dict_count: int
    crop_stage_dict_count: int
    rice_variety_count: int
    rice_control_window_level1_count: int
    farm_id: int
    field_ids: list[int]
    farm_field_relation_count: int


def seed_reference_data(session: Session) -> ReferenceSeedSummary:
    code_dict_count = _seed_code_dicts(session)
    crop_stage_dict_count = _seed_crop_stage_dict(session)
    rice_variety_count = _seed_rice_varieties(session)
    rice_control_window_level1_count = _seed_rice_control_window_level1(session)
    farm = _upsert_default_farm(session)
    fields = _upsert_default_fields(session)
    farm_field_relation_count = _ensure_farm_field_relations(
        session,
        farm_id=farm.id,
        field_ids=[field.id for field in fields],
    )

    return ReferenceSeedSummary(
        code_dict_count=code_dict_count,
        crop_stage_dict_count=crop_stage_dict_count,
        rice_variety_count=rice_variety_count,
        rice_control_window_level1_count=rice_control_window_level1_count,
        farm_id=farm.id,
        field_ids=[field.id for field in fields],
        farm_field_relation_count=farm_field_relation_count,
    )


def _seed_code_dicts(session: Session) -> int:
    with CODE_DICT_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            item = session.get(CodeDict, int(row["id"]))
            if item is None:
                item = CodeDict(id=int(row["id"]))
                session.add(item)

            item.code = int(row["code"])
            item.code_name = row["code_name"]
            item.category = row["category"]
            item.is_active = row["is_active"].lower() == "true"
            item.created_by_type = "system"
            item.created_by_id = SEED_ACTOR

    session.flush()
    _sync_id_sequence(session, "cf_code_dict")
    return _count_rows(session, select(func.count()).select_from(CodeDict))


def _seed_crop_stage_dict(session: Session) -> int:
    with STAGE_DICT_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            item = session.get(CropStageDict, int(row["id"]))
            if item is None:
                item = CropStageDict(id=int(row["id"]))
                session.add(item)

            item.stage_code = row["stage_code"].strip()
            item.stage_name = row["stage_name"].strip()
            item.season_scope = row["season_scope"].strip()
            item.business_stage_code = row["business_stage_code"].strip() or None
            item.display_order = int(row["display_order"])
            item.is_active = str(row["is_active"]).strip().lower() == "true"
            item.created_by_type = "system"
            item.created_by_id = SEED_ACTOR

    session.flush()
    _sync_id_sequence(session, "cf_crop_stage_dict")
    return _count_rows(session, select(func.count()).select_from(CropStageDict))


def _seed_rice_varieties(session: Session) -> int:
    with RICE_VARIETY_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            item = session.get(RiceVariety, int(row["id"]))
            if item is None:
                item = RiceVariety(id=int(row["id"]))
                session.add(item)

            item.name = row["name"]
            item.approve_year = _parse_optional_int(row["approve_year"])
            item.approve_no = row["approve_no"] or None
            item.approve_region = row["approve_region"] or None
            item.suitable_region = row["suitable_region"] or None
            item.culti_type_code = _parse_optional_int(row["culti_type"])
            item.sub_type_code = _parse_optional_int(row["sub_type"])
            item.maturity_code = _parse_optional_int(row["maturity"])
            item.control_variety = row["control_variety"] or None
            item.growth_days = _parse_optional_decimal(row["growth_days"])
            item.compare_days = _parse_optional_decimal(row["compare_days"])
            item.rice_code = row["rice_code"] or None
            item.created_by_type = "system"
            item.created_by_id = SEED_ACTOR

    session.flush()
    _sync_id_sequence(session, "cf_rice_variety")
    return _count_rows(session, select(func.count()).select_from(RiceVariety))


def _seed_rice_control_window_level1(session: Session) -> int:
    with RICE_CONTROL_WINDOW_LEVEL1_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            item = session.get(RiceControlWindowLevel1, int(row["id"]))
            if item is None:
                item = RiceControlWindowLevel1(id=int(row["id"]))
                session.add(item)

            item.province = row["province"].strip()
            item.city = row["city"].strip()
            item.county = row["county"].strip()
            item.data_year = int(str(row["data_year"]).strip().strip('"'))
            item.detail = json.loads(row["detail"])

    session.flush()
    _sync_id_sequence(session, "pp_rice_control_window_level_1")
    return _count_rows(session, select(func.count()).select_from(RiceControlWindowLevel1))


def _upsert_default_farm(session: Session) -> Farm:
    farm = session.get(Farm, 1)
    if farm is None:
        farm = Farm(id=1)
        session.add(farm)

    farm.farm_name = "部署初始化农场"
    farm.province = "湖南省"
    farm.city = "益阳市"
    farm.district_county = "桃江县"
    farm.adcode = "430922"
    farm.centroid_lat = Decimal("28.514220")
    farm.centroid_lon = Decimal("112.139118")
    farm.created_by_type = "system"
    farm.created_by_id = SEED_ACTOR
    session.flush()
    _sync_id_sequence(session, "cf_farm")
    return farm


def _upsert_default_fields(session: Session) -> list[Field]:
    field_specs = [
        (10, "部署初始化田块 A", Decimal("1.2500"), Decimal("28.194180"), Decimal("112.982310")),
        (11, "部署初始化田块 B", Decimal("0.9800"), Decimal("28.193940"), Decimal("112.982020")),
    ]
    fields: list[Field] = []
    for field_id, field_name, area_ha, centroid_lat, centroid_lon in field_specs:
        field = session.get(Field, field_id)
        if field is None:
            field = Field(id=field_id)
            session.add(field)

        field.field_name = field_name
        field.area_ha = area_ha
        field.centroid_lat = centroid_lat
        field.centroid_lon = centroid_lon
        field.created_by_type = "system"
        field.created_by_id = SEED_ACTOR
        fields.append(field)

    session.flush()
    _sync_id_sequence(session, "cf_field")
    return fields


def _ensure_farm_field_relations(session: Session, *, farm_id: int, field_ids: list[int]) -> int:
    for field_id in field_ids:
        exists_stmt = text(
            """
            SELECT 1
            FROM cf_farm_field_relation
            WHERE farm_id = :farm_id AND field_id = :field_id
            """,
        )
        exists = session.execute(exists_stmt, {"farm_id": farm_id, "field_id": field_id}).scalar_one_or_none()
        if exists:
            continue

        session.execute(
            text(
                """
                INSERT INTO cf_farm_field_relation (
                    farm_id,
                    field_id,
                    created_by_type,
                    created_by_id
                ) VALUES (
                    :farm_id,
                    :field_id,
                    'system',
                    :created_by_id
                )
                """,
            ),
            {
                "farm_id": farm_id,
                "field_id": field_id,
                "created_by_id": SEED_ACTOR,
            },
        )

    session.flush()
    return int(
        session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM cf_farm_field_relation
                WHERE farm_id = :farm_id
                """,
            ),
            {"farm_id": farm_id},
        ).scalar_one(),
    )


def _sync_id_sequence(session: Session, table_name: str) -> None:
    session.execute(
        text(
            f"""
            SELECT setval(
                pg_get_serial_sequence('{table_name}', 'id'),
                COALESCE((SELECT MAX(id) FROM {table_name}), 1),
                true
            )
            """,
        ),
    )


def _count_rows(session: Session, stmt: Select[tuple[int]]) -> int:
    return int(session.execute(stmt).scalar_one())


def _parse_optional_int(raw_value: str) -> int | None:
    value = raw_value.strip()
    return int(value) if value else None


def _parse_optional_decimal(raw_value: str) -> Decimal | None:
    value = raw_value.strip()
    return Decimal(value) if value else None
