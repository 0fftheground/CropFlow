from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import Select, func, select, text
from sqlalchemy.orm import Session

from app.db.session import get_session_factory
from app.models import (
    CalendarItem,
    CodeDict,
    CropStageDict,
    Farm,
    FarmingTask,
    Field,
    RiceControlWindowLevel1,
    RiceVariety,
    User,
)
from app.orchestrator import build_plan_orchestrator
from app.repositories import (
    CalendarItemRepository,
    CodeDictRepository,
    CropStageDictRepository,
    CropStageStateRepository,
    CropThermalTimeStateRepository,
    EventRecordRepository,
    FarmRepository,
    FieldRepository,
    FarmingTaskRepository,
    OperationPlanRepository,
    PlantingPlanFieldRelationRepository,
    PlantingPlanRepository,
    RiceControlWindowLevel1Repository,
    RiceVarietyRepository,
    ReviewRequestRepository,
    StagePredictionSnapshotRepository,
    TaskIntentRepository,
)
from app.services import (
    MockPestDiseaseControlClient,
    MockStagePredictionClient,
    MockWeatherProvider,
    MockWeedDiagnosisClient,
    PestDiseaseControlPlanningService,
    PlantingPlanCreateInput,
    PlantingPlanService,
    PlantProtectionPlanContextResolver,
    StageManagementService,
    SurveyDateRecommendationService,
    TaskGenerationService,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CODE_DICT_CSV = REPO_ROOT / "database" / "sql" / "agri_code_dict_202605181653.csv"
STAGE_DICT_CSV = REPO_ROOT / "database" / "sql" / "cf_crop_stage_dict_20260601.csv"
RICE_VARIETY_CSV = REPO_ROOT / "database" / "sql" / "agri_rice_variety_202605181649.csv"
RICE_CONTROL_WINDOW_LEVEL1_CSV = REPO_ROOT / "database" / "sql" / "pp_rice_control_window_level_1.csv"
SEED_ACTOR = "seed_local_dev_data"
DEMO_PLAN_CODE = "DEV-PLAN-001"


@dataclass(slots=True)
class SeedSummary:
    code_dict_count: int
    crop_stage_dict_count: int
    rice_variety_count: int
    rice_control_window_level1_count: int
    farm_id: int
    field_ids: list[int]
    reviewer_user_id: str
    planting_plan_id: int
    calendar_item_ids: list[int]
    farming_task_ids: list[int]


def main() -> None:
    session_factory = get_session_factory()
    with session_factory() as session:
        summary = seed_local_dev_data(session)
        session.commit()

    print("Seed completed.")
    print(f"code_dict_count={summary.code_dict_count}")
    print(f"crop_stage_dict_count={summary.crop_stage_dict_count}")
    print(f"rice_variety_count={summary.rice_variety_count}")
    print(f"rice_control_window_level1_count={summary.rice_control_window_level1_count}")
    print(f"farm_id={summary.farm_id}")
    print(f"field_ids={summary.field_ids}")
    print(f"reviewer_user_id={summary.reviewer_user_id}")
    print(f"planting_plan_id={summary.planting_plan_id}")
    print(f"calendar_item_ids={summary.calendar_item_ids}")
    print(f"farming_task_ids={summary.farming_task_ids}")


def seed_local_dev_data(session: Session) -> SeedSummary:
    code_dict_count = _seed_code_dicts(session)
    crop_stage_dict_count = _seed_crop_stage_dict(session)
    rice_variety_count = _seed_rice_varieties(session)
    rice_control_window_level1_count = _seed_rice_control_window_level1(session)
    farm = _upsert_demo_farm(session)
    fields = _upsert_demo_fields(session)
    _ensure_farm_field_relations(session, farm_id=farm.id, field_ids=[field.id for field in fields])
    reviewer = _upsert_demo_reviewer(session)

    planting_plan_id = _ensure_demo_plan(session, farm_id=farm.id, field_ids=[field.id for field in fields])
    session.flush()
    calendar_item_ids = _list_calendar_item_ids(session, planting_plan_id)
    farming_task_ids = _ensure_due_tasks(session, planting_plan_id)

    return SeedSummary(
        code_dict_count=code_dict_count,
        crop_stage_dict_count=crop_stage_dict_count,
        rice_variety_count=rice_variety_count,
        rice_control_window_level1_count=rice_control_window_level1_count,
        farm_id=farm.id,
        field_ids=[field.id for field in fields],
        reviewer_user_id=reviewer.id,
        planting_plan_id=planting_plan_id,
        calendar_item_ids=calendar_item_ids,
        farming_task_ids=farming_task_ids,
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


def _upsert_demo_farm(session: Session) -> Farm:
    farm = session.get(Farm, 1)
    if farm is None:
        farm = Farm(id=1)
        session.add(farm)

    farm.farm_name = "本地联调农场"
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


def _upsert_demo_fields(session: Session) -> list[Field]:
    field_specs = [
        (10, "联调田块 A", Decimal("1.2500"), Decimal("28.194180"), Decimal("112.982310")),
        (11, "联调田块 B", Decimal("0.9800"), Decimal("28.193940"), Decimal("112.982020")),
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


def _ensure_farm_field_relations(session: Session, *, farm_id: int, field_ids: list[int]) -> None:
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


def _upsert_demo_reviewer(session: Session) -> User:
    reviewer = session.get(User, "reviewer-demo")
    if reviewer is None:
        reviewer = User(id="reviewer-demo")
        session.add(reviewer)

    reviewer.user_code = "reviewer-demo"
    reviewer.username = "reviewer-demo"
    reviewer.display_name = "联调复核员"
    reviewer.mobile = "13800000000"
    reviewer.email = "reviewer-demo@cropflow.local"
    reviewer.status = "active"
    reviewer.metadata_payload = {"seed": True}
    reviewer.created_by_type = "system"
    reviewer.created_by_id = SEED_ACTOR
    session.flush()
    return reviewer


def _ensure_demo_plan(session: Session, *, farm_id: int, field_ids: list[int]) -> int:
    planting_plan_repository = PlantingPlanRepository(session)
    existing = planting_plan_repository.get_by_plan_code(DEMO_PLAN_CODE)
    if existing is not None:
        return existing.id

    event_record_repository = EventRecordRepository(session)
    survey_date_service = SurveyDateRecommendationService(
        planting_plan_repository=planting_plan_repository,
        farm_repository=FarmRepository(session),
        rice_variety_repository=RiceVarietyRepository(session),
        code_dict_repository=CodeDictRepository(session),
        rice_control_window_level1_repository=RiceControlWindowLevel1Repository(session),
        calendar_item_repository=CalendarItemRepository(session),
        event_record_repository=event_record_repository,
        weather_provider=MockWeatherProvider(),
        diagnosis_client=MockWeedDiagnosisClient(),
    )
    stage_management_service = _build_seed_stage_management_service(session)
    context_resolver = PlantProtectionPlanContextResolver(
        code_dict_repository=CodeDictRepository(session),
        rice_variety_repository=RiceVarietyRepository(session),
    )
    pest_disease_control_planning_service = PestDiseaseControlPlanningService(
        planting_plan_repository=planting_plan_repository,
        farm_repository=FarmRepository(session),
        rice_control_window_level1_repository=RiceControlWindowLevel1Repository(session),
        stage_prediction_snapshot_repository=StagePredictionSnapshotRepository(session),
        calendar_item_repository=CalendarItemRepository(session),
        operation_plan_repository=OperationPlanRepository(session),
        context_resolver=context_resolver,
        weather_provider=MockWeatherProvider(),
        control_client=MockPestDiseaseControlClient(),
    )
    plan_orchestrator = build_plan_orchestrator(
        planting_plan_repository=planting_plan_repository,
        calendar_item_repository=CalendarItemRepository(session),
        farming_task_repository=FarmingTaskRepository(session),
        event_record_repository=event_record_repository,
        task_intent_repository=TaskIntentRepository(session),
        review_request_repository=ReviewRequestRepository(session),
        operation_plan_repository=OperationPlanRepository(session),
        stage_management_service=stage_management_service,
        survey_date_recommendation_service=survey_date_service,
        weather_provider=MockWeatherProvider(),
        diagnosis_client=MockWeedDiagnosisClient(),
        context_resolver=context_resolver,
        pest_disease_control_planning_service=pest_disease_control_planning_service,
    )
    service = PlantingPlanService(
        planting_plan_repository=planting_plan_repository,
        field_repository=FieldRepository(session),
        planting_plan_field_relation_repository=PlantingPlanFieldRelationRepository(session),
        rice_variety_repository=RiceVarietyRepository(session),
        event_record_repository=event_record_repository,
        plan_orchestrator=plan_orchestrator,
    )
    details = service.create(
        PlantingPlanCreateInput(
            plan_code=DEMO_PLAN_CODE,
            plan_name="本地联调早稻样板计划",
            farm_id=farm_id,
            field_ids=field_ids,
            culti_type_code=5,
            planting_method_code=1,
            crop_name="水稻",
            variety_id=1,
            sowing_date=date(2026, 4, 10),
            status="active",
            task_generation_window_days=14,
            metadata_payload={
                "seed": True,
                "notes": "Created by seed_local_dev_data.py using mock diagnosis for deterministic startup data.",
            },
        ),
    )
    return details.planting_plan.id


def _list_calendar_item_ids(session: Session, planting_plan_id: int) -> list[int]:
    stmt = (
        select(CalendarItem.id)
        .where(CalendarItem.planting_plan_id == planting_plan_id)
        .order_by(CalendarItem.id.asc())
    )
    return list(session.scalars(stmt))


def _ensure_due_tasks(session: Session, planting_plan_id: int) -> list[int]:
    existing_task_stmt = (
        select(FarmingTask.id)
        .where(FarmingTask.planting_plan_id == planting_plan_id)
        .order_by(FarmingTask.id.asc())
    )
    existing_task_ids = list(session.scalars(existing_task_stmt))
    if existing_task_ids:
        return existing_task_ids

    planting_plan_repository = PlantingPlanRepository(session)
    event_record_repository = EventRecordRepository(session)
    survey_date_service = SurveyDateRecommendationService(
        planting_plan_repository=planting_plan_repository,
        farm_repository=FarmRepository(session),
        rice_variety_repository=RiceVarietyRepository(session),
        code_dict_repository=CodeDictRepository(session),
        rice_control_window_level1_repository=RiceControlWindowLevel1Repository(session),
        calendar_item_repository=CalendarItemRepository(session),
        event_record_repository=event_record_repository,
        weather_provider=MockWeatherProvider(),
        diagnosis_client=MockWeedDiagnosisClient(),
    )
    stage_management_service = _build_seed_stage_management_service(session)
    context_resolver = PlantProtectionPlanContextResolver(
        code_dict_repository=CodeDictRepository(session),
        rice_variety_repository=RiceVarietyRepository(session),
    )
    pest_disease_control_planning_service = PestDiseaseControlPlanningService(
        planting_plan_repository=planting_plan_repository,
        farm_repository=FarmRepository(session),
        rice_control_window_level1_repository=RiceControlWindowLevel1Repository(session),
        stage_prediction_snapshot_repository=StagePredictionSnapshotRepository(session),
        calendar_item_repository=CalendarItemRepository(session),
        operation_plan_repository=OperationPlanRepository(session),
        context_resolver=context_resolver,
        weather_provider=MockWeatherProvider(),
        control_client=MockPestDiseaseControlClient(),
    )
    plan_orchestrator = build_plan_orchestrator(
        planting_plan_repository=planting_plan_repository,
        calendar_item_repository=CalendarItemRepository(session),
        farming_task_repository=FarmingTaskRepository(session),
        event_record_repository=event_record_repository,
        task_intent_repository=TaskIntentRepository(session),
        review_request_repository=ReviewRequestRepository(session),
        operation_plan_repository=OperationPlanRepository(session),
        stage_management_service=stage_management_service,
        survey_date_recommendation_service=survey_date_service,
        weather_provider=MockWeatherProvider(),
        diagnosis_client=MockWeedDiagnosisClient(),
        context_resolver=context_resolver,
        pest_disease_control_planning_service=pest_disease_control_planning_service,
    )
    task_generation_service = TaskGenerationService(
        planting_plan_repository=planting_plan_repository,
        event_record_repository=event_record_repository,
        plan_orchestrator=plan_orchestrator,
    )
    task_generation_service.generate_due_tasks(
        planting_plan_id,
        check_date=date(2026, 4, 18),
    )
    return list(session.scalars(existing_task_stmt))


def _build_seed_stage_management_service(session: Session) -> StageManagementService:
    return StageManagementService(
        planting_plan_repository=PlantingPlanRepository(session),
        farm_repository=FarmRepository(session),
        rice_variety_repository=RiceVarietyRepository(session),
        stage_prediction_snapshot_repository=StagePredictionSnapshotRepository(session),
        crop_stage_state_repository=CropStageStateRepository(session),
        crop_thermal_time_state_repository=CropThermalTimeStateRepository(session),
        stage_prediction_client=MockStagePredictionClient(),
        weather_provider=MockWeatherProvider(),
        crop_stage_dict_repository=CropStageDictRepository(session),
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


if __name__ == "__main__":
    main()
