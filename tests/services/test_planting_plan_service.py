from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

import pytest

from app.models import EventRecord, Field, PlantingPlan, RiceVariety
from app.services.planting_plans import (
    PLANTING_PLAN_ALLOWED_STATUSES,
    PlantingPlanCreateInput,
    PlantingPlanService,
    PlantingPlanUpdateInput,
)


@dataclass
class FakePlantingPlanRepository:
    items: dict[int, PlantingPlan] = field(default_factory=dict)
    next_id: int = 1

    def add(self, plan: PlantingPlan) -> PlantingPlan:
        if plan.id is None:
            plan.id = self.next_id
            self.next_id += 1
        self.items[plan.id] = plan
        return plan

    def flush(self) -> None:
        return None

    def get(self, planting_plan_id: int) -> PlantingPlan | None:
        return self.items.get(planting_plan_id)

    def get_by_plan_code(self, plan_code: str) -> PlantingPlan | None:
        for plan in self.items.values():
            if plan.plan_code == plan_code:
                return plan
        return None

    def list_by_statuses(self, statuses: list[str] | None = None) -> list[PlantingPlan]:
        plans = list(self.items.values())
        if statuses:
            plans = [plan for plan in plans if plan.status in statuses]
        return sorted(plans, key=lambda plan: plan.id, reverse=True)


@dataclass
class FakeFieldRepository:
    fields: dict[int, Field]

    def list_by_ids(self, field_ids: list[int]) -> list[Field]:
        return [self.fields[field_id] for field_id in field_ids if field_id in self.fields]


@dataclass
class FakePlanFieldRelationRepository:
    mapping: dict[int, list[int]] = field(default_factory=dict)

    def replace_for_plan(self, planting_plan_id: int, field_ids: list[int]) -> None:
        self.mapping[planting_plan_id] = sorted(field_ids)

    def list_field_ids_by_plan(self, planting_plan_id: int) -> list[int]:
        return self.mapping.get(planting_plan_id, [])

    def list_field_ids_by_plan_ids(self, planting_plan_ids: list[int]) -> dict[int, list[int]]:
        return {plan_id: self.mapping.get(plan_id, []) for plan_id in planting_plan_ids}


@dataclass
class FakeRiceVarietyRepository:
    items: dict[int, RiceVariety]

    def get(self, rice_variety_id: int) -> RiceVariety | None:
        return self.items.get(rice_variety_id)


@dataclass
class FakeEventRecordRepository:
    items: list[EventRecord] = field(default_factory=list)

    def add(self, event_record: EventRecord) -> EventRecord:
        self.items.append(event_record)
        return event_record


class FakePlanOrchestrator:
    def __init__(self) -> None:
        self.triggered_plan_ids: list[int] = []

    def handle(self, event_record: EventRecord):
        self.triggered_plan_ids.append(event_record.planting_plan_id)


def test_create_plan_derives_variety_name_and_field_relations() -> None:
    plan_orchestrator = FakePlanOrchestrator()
    service = PlantingPlanService(
        planting_plan_repository=FakePlantingPlanRepository(),
        field_repository=FakeFieldRepository(
            {
                10: Field(id=10, field_name="田块 A"),
                11: Field(id=11, field_name="田块 B"),
            },
        ),
        planting_plan_field_relation_repository=FakePlanFieldRelationRepository(),
        rice_variety_repository=FakeRiceVarietyRepository({3: RiceVariety(id=3, name="黄广农占")}),
        event_record_repository=FakeEventRecordRepository(),
        plan_orchestrator=plan_orchestrator,
    )

    result = service.create(
        PlantingPlanCreateInput(
            plan_code="PLAN-001",
            plan_name="早稻计划",
            farm_id=1,
            field_ids=[10, 11],
            culti_type_code=5,
            planting_method_code=1,
            crop_name="水稻",
            variety_id=3,
            sowing_date=date(2026, 4, 10),
            metadata_payload={"source": "frontend"},
        ),
    )

    assert result.planting_plan.variety_name == "黄广农占"
    assert result.field_ids == [10, 11]
    assert plan_orchestrator.triggered_plan_ids == [result.planting_plan.id]


def test_update_plan_replaces_field_relations_and_refreshes_calendar_on_key_changes() -> None:
    repository = FakePlantingPlanRepository(
        {
            1: PlantingPlan(
                id=1,
                plan_code="PLAN-001",
                plan_name="原计划",
                farm_id=1,
                culti_type_code=5,
                planting_method_code=1,
                crop_name="水稻",
                variety_id=3,
                variety_name="黄广农占",
                sowing_date=date(2026, 4, 10),
                status="draft",
                task_generation_window_days=14,
                metadata_payload={},
            ),
        },
    )
    relation_repository = FakePlanFieldRelationRepository({1: [10]})
    plan_orchestrator = FakePlanOrchestrator()
    service = PlantingPlanService(
        planting_plan_repository=repository,
        field_repository=FakeFieldRepository({10: Field(id=10, field_name="田块 A"), 12: Field(id=12, field_name="田块 C")}),
        planting_plan_field_relation_repository=relation_repository,
        rice_variety_repository=FakeRiceVarietyRepository({4: RiceVariety(id=4, name="新优品种")}),
        event_record_repository=FakeEventRecordRepository(),
        plan_orchestrator=plan_orchestrator,
    )

    result = service.update(
        1,
        PlantingPlanUpdateInput(
            plan_name="新计划",
            field_ids=[12],
            variety_id=4,
            sowing_date=date(2026, 4, 12),
            transplant_leaf_age=Decimal("4.50"),
        ),
    )

    assert result.planting_plan.plan_name == "新计划"
    assert result.planting_plan.variety_name == "新优品种"
    assert result.field_ids == [12]
    assert plan_orchestrator.triggered_plan_ids == [1]


def test_list_by_statuses_filters_plans() -> None:
    repository = FakePlantingPlanRepository(
        {
            1: PlantingPlan(
                id=1,
                plan_code="PLAN-001",
                plan_name="草稿计划",
                farm_id=1,
                culti_type_code=5,
                planting_method_code=1,
                crop_name="水稻",
                variety_id=3,
                variety_name="黄广农占",
                sowing_date=date(2026, 4, 10),
                status="draft",
                task_generation_window_days=14,
                metadata_payload={},
            ),
            2: PlantingPlan(
                id=2,
                plan_code="PLAN-002",
                plan_name="活跃计划",
                farm_id=1,
                culti_type_code=5,
                planting_method_code=1,
                crop_name="水稻",
                variety_id=3,
                variety_name="黄广农占",
                sowing_date=date(2026, 4, 11),
                status="active",
                task_generation_window_days=14,
                metadata_payload={},
            ),
        },
    )
    service = PlantingPlanService(
        planting_plan_repository=repository,
        field_repository=FakeFieldRepository({}),
        planting_plan_field_relation_repository=FakePlanFieldRelationRepository({1: [10], 2: [11]}),
        rice_variety_repository=FakeRiceVarietyRepository({}),
        plan_orchestrator=None,
    )

    results = service.list_by_statuses(["active"])

    assert [item.planting_plan.id for item in results] == [2]
    assert set(PLANTING_PLAN_ALLOWED_STATUSES) == {"draft", "active", "completed", "cancelled"}


def test_create_plan_records_plan_created_event_before_orchestration() -> None:
    event_repository = FakeEventRecordRepository()
    plan_orchestrator = FakePlanOrchestrator()
    service = PlantingPlanService(
        planting_plan_repository=FakePlantingPlanRepository(),
        field_repository=FakeFieldRepository({10: Field(id=10, field_name="田块 A")}),
        planting_plan_field_relation_repository=FakePlanFieldRelationRepository(),
        rice_variety_repository=FakeRiceVarietyRepository({3: RiceVariety(id=3, name="黄广农占")}),
        event_record_repository=event_repository,
        plan_orchestrator=plan_orchestrator,
    )

    result = service.create(
        PlantingPlanCreateInput(
            plan_code="PLAN-001",
            plan_name="早稻计划",
            farm_id=1,
            field_ids=[10],
            culti_type_code=5,
            planting_method_code=1,
            crop_name="水稻",
            variety_id=3,
            sowing_date=date(2026, 4, 10),
        ),
    )

    assert result.planting_plan.id is not None
    assert event_repository.items[-1].event_type == "PlanCreated"
    assert event_repository.items[-1].processing_status == "received"
    assert plan_orchestrator.triggered_plan_ids == [result.planting_plan.id]
