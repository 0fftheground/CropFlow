from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

import pytest

from app.models import Farm, Field, FarmFieldRelation
from app.services.farms import (
    ConflictError,
    FarmCreateInput,
    FarmFieldQueryService,
    FarmFieldService,
    FarmService,
    FarmUpdateInput,
    FieldCreateInput,
    FieldUpdateInput,
)


@dataclass
class FakeFarmRepository:
    items: dict[int, Farm] = field(default_factory=dict)
    next_id: int = 1

    def add(self, farm: Farm) -> Farm:
        if farm.id is None:
            farm.id = self.next_id
            self.next_id += 1
        self.items[farm.id] = farm
        return farm

    def flush(self) -> None:
        return None

    def get(self, farm_id: int) -> Farm | None:
        return self.items.get(farm_id)

    def get_by_external_farm_id(self, external_farm_id: str) -> Farm | None:
        return next((item for item in self.items.values() if item.external_farm_id == external_farm_id), None)

    def list_all(self) -> list[Farm]:
        return list(self.items.values())

    def delete(self, farm: Farm) -> None:
        self.items.pop(farm.id, None)


@dataclass
class FakeFieldRepository:
    items: dict[int, Field] = field(default_factory=dict)
    next_id: int = 10

    def add(self, item: Field) -> Field:
        if item.id is None:
            item.id = self.next_id
            self.next_id += 1
        self.items[item.id] = item
        return item

    def flush(self) -> None:
        return None

    def get(self, field_id: int) -> Field | None:
        return self.items.get(field_id)

    def get_by_external_field_id(self, external_field_id: str) -> Field | None:
        return next((item for item in self.items.values() if item.external_field_id == external_field_id), None)

    def list_by_ids(self, field_ids: list[int]) -> list[Field]:
        return [self.items[field_id] for field_id in field_ids if field_id in self.items]

    def delete(self, field: Field) -> None:
        self.items.pop(field.id, None)


@dataclass
class FakeFarmFieldRelationRepository:
    items: list[FarmFieldRelation] = field(default_factory=list)
    next_id: int = 100

    def create(self, farm_id: int, field_id: int) -> FarmFieldRelation:
        relation = FarmFieldRelation(id=self.next_id, farm_id=farm_id, field_id=field_id)
        self.next_id += 1
        self.items.append(relation)
        return relation

    def flush(self) -> None:
        return None

    def get_by_farm_field(self, farm_id: int, field_id: int) -> FarmFieldRelation | None:
        return next((item for item in self.items if item.farm_id == farm_id and item.field_id == field_id), None)

    def list_field_ids_by_farm(self, farm_id: int) -> list[int]:
        return sorted(item.field_id for item in self.items if item.farm_id == farm_id)

    def count_by_field(self, field_id: int) -> int:
        return sum(1 for item in self.items if item.field_id == field_id)

    def delete(self, relation: FarmFieldRelation) -> None:
        self.items = [item for item in self.items if item.id != relation.id]

    def delete_by_farm(self, farm_id: int) -> None:
        self.items = [item for item in self.items if item.farm_id != farm_id]


@dataclass
class FakePlantingPlanRepository:
    farm_ids_with_plans: set[int] = field(default_factory=set)

    def exists_by_farm_id(self, farm_id: int) -> bool:
        return farm_id in self.farm_ids_with_plans


@dataclass
class FakePlantingPlanFieldRelationRepository:
    linked_field_ids: set[int] = field(default_factory=set)

    def list_linked_field_ids(self, field_ids: list[int]) -> list[int]:
        return sorted(field_id for field_id in field_ids if field_id in self.linked_field_ids)


def test_create_field_creates_relation_and_external_id() -> None:
    farm_repo = FakeFarmRepository({1: Farm(id=1, farm_name="测试农场")})
    field_repo = FakeFieldRepository()
    relation_repo = FakeFarmFieldRelationRepository()
    service = FarmFieldService(field_repo, farm_repo, relation_repo)

    result = service.create(
        1,
        FieldCreateInput(
            field_name="一号田",
            external_field_id="plot-001",
            centroid_lat=Decimal("28.100000"),
            centroid_lon=Decimal("112.900000"),
        ),
    )

    assert result.id == 10
    assert result.external_field_id == "plot-001"
    assert relation_repo.list_field_ids_by_farm(1) == [10]


def test_create_fields_batch_creates_multiple_relations() -> None:
    farm_repo = FakeFarmRepository({1: Farm(id=1, farm_name="测试农场")})
    field_repo = FakeFieldRepository()
    relation_repo = FakeFarmFieldRelationRepository()
    service = FarmFieldService(field_repo, farm_repo, relation_repo)

    results = service.create_batch(
        1,
        [
            FieldCreateInput(field_name="一号田", external_field_id="plot-001"),
            FieldCreateInput(field_name="二号田", external_field_id="plot-002"),
        ],
    )

    assert [item.id for item in results] == [10, 11]
    assert relation_repo.list_field_ids_by_farm(1) == [10, 11]


def test_create_fields_batch_rejects_duplicate_external_field_ids() -> None:
    farm_repo = FakeFarmRepository({1: Farm(id=1, farm_name="测试农场")})
    field_repo = FakeFieldRepository()
    relation_repo = FakeFarmFieldRelationRepository()
    service = FarmFieldService(field_repo, farm_repo, relation_repo)

    with pytest.raises(ValueError, match="Duplicate external_field_id values in batch"):
        service.create_batch(
            1,
            [
                FieldCreateInput(field_name="一号田", external_field_id="plot-001"),
                FieldCreateInput(field_name="二号田", external_field_id="plot-001"),
            ],
        )


def test_create_field_allows_same_external_field_id_in_different_farms() -> None:
    farm_repo = FakeFarmRepository(
        {
            1: Farm(id=1, farm_name="测试农场一"),
            2: Farm(id=2, farm_name="测试农场二"),
        },
    )
    field_repo = FakeFieldRepository(
        {
            10: Field(id=10, field_name="一号田", external_field_id="plot-001"),
        },
        next_id=11,
    )
    relation_repo = FakeFarmFieldRelationRepository([FarmFieldRelation(id=101, farm_id=1, field_id=10)])
    service = FarmFieldService(field_repo, farm_repo, relation_repo)

    result = service.create(
        2,
        FieldCreateInput(
            field_name="二号田",
            external_field_id="plot-001",
        ),
    )

    assert result.id == 11
    assert result.external_field_id == "plot-001"
    assert relation_repo.list_field_ids_by_farm(2) == [11]


def test_update_field_rejects_duplicate_external_field_id() -> None:
    farm_repo = FakeFarmRepository({1: Farm(id=1, farm_name="测试农场")})
    field_repo = FakeFieldRepository(
        {
            10: Field(id=10, field_name="一号田", external_field_id="plot-001"),
            11: Field(id=11, field_name="二号田", external_field_id="plot-002"),
        },
    )
    relation_repo = FakeFarmFieldRelationRepository(
        [FarmFieldRelation(id=101, farm_id=1, field_id=10), FarmFieldRelation(id=102, farm_id=1, field_id=11)],
    )
    service = FarmFieldService(field_repo, farm_repo, relation_repo)

    with pytest.raises(ValueError, match="external_field_id plot-002 already exists"):
        service.update(1, 10, FieldUpdateInput(external_field_id="plot-002"))


def test_update_field_allows_same_external_field_id_in_different_farms() -> None:
    farm_repo = FakeFarmRepository(
        {
            1: Farm(id=1, farm_name="测试农场一"),
            2: Farm(id=2, farm_name="测试农场二"),
        },
    )
    field_repo = FakeFieldRepository(
        {
            10: Field(id=10, field_name="一号田", external_field_id="plot-010"),
            11: Field(id=11, field_name="二号田", external_field_id="plot-001"),
        },
    )
    relation_repo = FakeFarmFieldRelationRepository(
        [FarmFieldRelation(id=101, farm_id=1, field_id=10), FarmFieldRelation(id=102, farm_id=2, field_id=11)],
    )
    service = FarmFieldService(field_repo, farm_repo, relation_repo)

    result = service.update(1, 10, FieldUpdateInput(external_field_id="plot-001"))

    assert result.external_field_id == "plot-001"


def test_update_field_allows_clearing_optional_values() -> None:
    farm_repo = FakeFarmRepository({1: Farm(id=1, farm_name="测试农场")})
    field_repo = FakeFieldRepository(
        {
            10: Field(
                id=10,
                field_name="一号田",
                external_field_id="plot-001",
                boundary_wkt="POLYGON((0 0,1 0,1 1,0 1,0 0))",
                centroid_lat=Decimal("28.100000"),
                centroid_lon=Decimal("112.900000"),
                area_ha=Decimal("5.5000"),
            ),
        },
    )
    relation_repo = FakeFarmFieldRelationRepository([FarmFieldRelation(id=101, farm_id=1, field_id=10)])
    service = FarmFieldService(field_repo, farm_repo, relation_repo)

    result = service.update(
        1,
        10,
        FieldUpdateInput(
            external_field_id=None,
            boundary_wkt=None,
            centroid_lat=None,
            centroid_lon=None,
            area_ha=None,
        ),
    )

    assert result.external_field_id is None
    assert result.boundary_wkt is None
    assert result.centroid_lat is None
    assert result.centroid_lon is None
    assert result.area_ha is None


def test_delete_field_rejects_linked_plan() -> None:
    farm_repo = FakeFarmRepository({1: Farm(id=1, farm_name="测试农场")})
    field_repo = FakeFieldRepository({10: Field(id=10, field_name="一号田")})
    relation_repo = FakeFarmFieldRelationRepository([FarmFieldRelation(id=101, farm_id=1, field_id=10)])
    plan_field_repo = FakePlantingPlanFieldRelationRepository({10})
    service = FarmFieldService(
        field_repo,
        farm_repo,
        relation_repo,
        planting_plan_field_relation_repository=plan_field_repo,
    )

    with pytest.raises(ConflictError, match="cannot be deleted"):
        service.delete(1, 10)


def test_create_field_rejects_invalid_coordinates_and_area() -> None:
    farm_repo = FakeFarmRepository({1: Farm(id=1, farm_name="测试农场")})
    field_repo = FakeFieldRepository()
    relation_repo = FakeFarmFieldRelationRepository()
    service = FarmFieldService(field_repo, farm_repo, relation_repo)

    with pytest.raises(ValueError, match="centroid_lat must be between -90 and 90"):
        service.create(
            1,
            FieldCreateInput(
                field_name="一号田",
                centroid_lat=Decimal("100"),
            ),
        )

    with pytest.raises(ValueError, match="area_ha must be greater than 0"):
        service.create(
            1,
            FieldCreateInput(
                field_name="一号田",
                area_ha=Decimal("0"),
            ),
        )


def test_delete_fields_batch_rejects_linked_plan() -> None:
    farm_repo = FakeFarmRepository({1: Farm(id=1, farm_name="测试农场")})
    field_repo = FakeFieldRepository({10: Field(id=10, field_name="一号田"), 11: Field(id=11, field_name="二号田")})
    relation_repo = FakeFarmFieldRelationRepository(
        [FarmFieldRelation(id=101, farm_id=1, field_id=10), FarmFieldRelation(id=102, farm_id=1, field_id=11)],
    )
    plan_field_repo = FakePlantingPlanFieldRelationRepository({11})
    service = FarmFieldService(
        field_repo,
        farm_repo,
        relation_repo,
        planting_plan_field_relation_repository=plan_field_repo,
    )

    with pytest.raises(ConflictError, match="cannot be deleted"):
        service.delete_batch(1, [10, 11])


def test_delete_fields_batch_deletes_all_unlinked_fields() -> None:
    farm_repo = FakeFarmRepository({1: Farm(id=1, farm_name="测试农场")})
    field_repo = FakeFieldRepository({10: Field(id=10, field_name="一号田"), 11: Field(id=11, field_name="二号田")})
    relation_repo = FakeFarmFieldRelationRepository(
        [FarmFieldRelation(id=101, farm_id=1, field_id=10), FarmFieldRelation(id=102, farm_id=1, field_id=11)],
    )
    service = FarmFieldService(
        field_repo,
        farm_repo,
        relation_repo,
        planting_plan_field_relation_repository=FakePlantingPlanFieldRelationRepository(),
    )

    service.delete_batch(1, [10, 11])

    assert field_repo.items == {}
    assert relation_repo.items == []


def test_delete_farm_rejects_when_linked_to_plan() -> None:
    service = FarmService(
        farm_repository=FakeFarmRepository({1: Farm(id=1, farm_name="测试农场")}),
        planting_plan_repository=FakePlantingPlanRepository({1}),
    )

    with pytest.raises(ConflictError, match="referenced by planting plans"):
        service.delete(1)


def test_delete_farm_removes_owned_fields_without_plan_links() -> None:
    farm_repo = FakeFarmRepository({1: Farm(id=1, farm_name="测试农场")})
    field_repo = FakeFieldRepository(
        {
            10: Field(id=10, field_name="一号田"),
            11: Field(id=11, field_name="二号田"),
        },
    )
    relation_repo = FakeFarmFieldRelationRepository(
        [FarmFieldRelation(id=101, farm_id=1, field_id=10), FarmFieldRelation(id=102, farm_id=1, field_id=11)],
    )
    service = FarmService(
        farm_repository=farm_repo,
        field_repository=field_repo,
        farm_field_relation_repository=relation_repo,
        planting_plan_repository=FakePlantingPlanRepository(),
        planting_plan_field_relation_repository=FakePlantingPlanFieldRelationRepository(),
    )

    service.delete(1)

    assert farm_repo.get(1) is None
    assert field_repo.items == {}
    assert relation_repo.items == []


def test_list_and_get_fields_require_existing_farm() -> None:
    query_service = FarmFieldQueryService(
        field_repository=FakeFieldRepository({10: Field(id=10, field_name="一号田")}),
        farm_repository=FakeFarmRepository({1: Farm(id=1, farm_name="测试农场")}),
        farm_field_relation_repository=FakeFarmFieldRelationRepository([FarmFieldRelation(id=101, farm_id=1, field_id=10)]),
    )

    assert [item.id for item in query_service.list_by_farm(1)] == [10]
    assert query_service.get(1, 10).field_name == "一号田"


def test_create_farm_validates_external_farm_id_uniqueness() -> None:
    farm_repo = FakeFarmRepository({1: Farm(id=1, farm_name="测试农场", external_farm_id="farm-ext-1")})
    service = FarmService(farm_repository=farm_repo)

    with pytest.raises(ValueError, match="external_farm_id farm-ext-1 already exists"):
        service.create(
            FarmCreateInput(
                farm_name="联调农场",
                external_farm_id="farm-ext-1",
                province="湖南省",
                city="长沙市",
                district_county="岳麓区",
                adcode="430104",
            ),
        )


def test_update_farm_changes_external_farm_id() -> None:
    farm_repo = FakeFarmRepository({1: Farm(id=1, farm_name="测试农场", external_farm_id="farm-ext-1")})
    service = FarmService(farm_repository=farm_repo)

    result = service.update(1, FarmUpdateInput(external_farm_id="farm-ext-2"))

    assert result.external_farm_id == "farm-ext-2"


def test_update_farm_allows_clearing_optional_values() -> None:
    farm_repo = FakeFarmRepository(
        {
            1: Farm(
                id=1,
                farm_name="测试农场",
                external_farm_id="farm-ext-1",
                boundary_wkt="POLYGON((0 0,1 0,1 1,0 1,0 0))",
                centroid_lat=Decimal("28.100000"),
                centroid_lon=Decimal("112.900000"),
            ),
        },
    )
    service = FarmService(farm_repository=farm_repo)

    result = service.update(
        1,
        FarmUpdateInput(
            external_farm_id=None,
            boundary_wkt=None,
            centroid_lat=None,
            centroid_lon=None,
        ),
    )

    assert result.external_farm_id is None
    assert result.boundary_wkt is None
    assert result.centroid_lat is None
    assert result.centroid_lon is None


def test_create_farm_rejects_invalid_coordinates() -> None:
    service = FarmService(farm_repository=FakeFarmRepository())

    with pytest.raises(ValueError, match="centroid_lon must be between -180 and 180"):
        service.create(
            FarmCreateInput(
                farm_name="联调农场",
                province="湖南省",
                city="长沙市",
                district_county="岳麓区",
                adcode="430104",
                centroid_lon=Decimal("181"),
            ),
        )
