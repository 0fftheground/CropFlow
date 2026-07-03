from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from fastapi.testclient import TestClient

from app.api.deps import (
    get_farm_field_query_service,
    get_farm_field_service,
    get_farm_query_service,
    get_farm_service,
)
from app.db.session import get_db
from app.main import app
from app.models import Farm, Field
from app.services import ConflictError
from app.services.farms import UNSET


def _make_farm(farm_id: int) -> Farm:
    return Farm(
        id=farm_id,
        farm_name=f"农场 {farm_id}",
        external_farm_id=f"ext-{farm_id}",
        province="湖南省",
        city="长沙市",
        district_county="岳麓区",
        adcode=f"43010{farm_id}",
        boundary_wkt=None,
        centroid_lat=Decimal("28.194090"),
        centroid_lon=Decimal("112.982279"),
        created_at=datetime(2026, 5, 28, 10, 0, 0),
        updated_at=datetime(2026, 5, 28, 10, 0, 0),
    )


def _make_field(field_id: int) -> Field:
    return Field(
        id=field_id,
        field_name=f"地块 {field_id}",
        external_field_id=f"field-ext-{field_id}",
        boundary_wkt="POLYGON((0 0,1 0,1 1,0 1,0 0))",
        centroid_lat=Decimal("28.194090"),
        centroid_lon=Decimal("112.982279"),
        area_ha=Decimal("12.5000"),
        created_at=datetime(2026, 5, 28, 10, 0, 0),
        updated_at=datetime(2026, 5, 28, 10, 0, 0),
    )


@dataclass
class FakeFarmService:
    created_payload: object | None = None
    updated_payload: object | None = None
    deleted_farm_id: int | None = None

    def create(self, payload):
        self.created_payload = payload
        return _make_farm(1)

    def update(self, farm_id: int, payload):
        if farm_id == 404:
            raise LookupError("missing")
        self.updated_payload = payload
        farm = _make_farm(farm_id)
        if payload.city is not UNSET:
            farm.city = payload.city
        if payload.external_farm_id is not UNSET:
            farm.external_farm_id = payload.external_farm_id
        if payload.boundary_wkt is not UNSET:
            farm.boundary_wkt = payload.boundary_wkt
        if payload.centroid_lat is not UNSET:
            farm.centroid_lat = payload.centroid_lat
        if payload.centroid_lon is not UNSET:
            farm.centroid_lon = payload.centroid_lon
        return farm

    def delete(self, farm_id: int):
        if farm_id == 404:
            raise LookupError("missing")
        if farm_id == 409:
            raise ConflictError("linked plan")
        self.deleted_farm_id = farm_id


class FakeFarmQueryService:
    def list_all(self):
        return [_make_farm(2), _make_farm(1)]

    def get(self, farm_id: int):
        if farm_id == 404:
            raise LookupError("missing")
        return _make_farm(farm_id)


@dataclass
class FakeFarmFieldService:
    created_payload: object | None = None
    batch_created_payloads: list[object] | None = None
    updated_payload: object | None = None
    deleted_farm_id: int | None = None
    deleted_field_id: int | None = None
    batch_deleted_field_ids: list[int] | None = None

    def create(self, farm_id: int, payload):
        if farm_id == 404:
            raise LookupError("missing farm")
        self.created_payload = payload
        field = _make_field(11)
        field.field_name = payload.field_name
        field.external_field_id = payload.external_field_id
        return field

    def create_batch(self, farm_id: int, payloads):
        if farm_id == 404:
            raise LookupError("missing farm")
        self.batch_created_payloads = list(payloads)
        return [
            Field(
                id=11 + index,
                field_name=payload.field_name,
                external_field_id=payload.external_field_id,
                boundary_wkt=payload.boundary_wkt,
                centroid_lat=payload.centroid_lat,
                centroid_lon=payload.centroid_lon,
                area_ha=payload.area_ha,
                created_at=datetime(2026, 5, 28, 10, 0, 0),
                updated_at=datetime(2026, 5, 28, 10, 0, 0),
            )
            for index, payload in enumerate(payloads)
        ]

    def update(self, farm_id: int, field_id: int, payload):
        if farm_id == 404 or field_id == 404:
            raise LookupError("missing field")
        self.updated_payload = payload
        field = _make_field(field_id)
        if payload.field_name is not UNSET:
            field.field_name = payload.field_name
        if payload.external_field_id is not UNSET:
            field.external_field_id = payload.external_field_id
        if payload.boundary_wkt is not UNSET:
            field.boundary_wkt = payload.boundary_wkt
        if payload.centroid_lat is not UNSET:
            field.centroid_lat = payload.centroid_lat
        if payload.centroid_lon is not UNSET:
            field.centroid_lon = payload.centroid_lon
        if payload.area_ha is not UNSET:
            field.area_ha = payload.area_ha
        return field

    def delete(self, farm_id: int, field_id: int):
        if farm_id == 404 or field_id == 404:
            raise LookupError("missing field")
        if field_id == 409:
            raise ConflictError("linked plan")
        self.deleted_farm_id = farm_id
        self.deleted_field_id = field_id

    def delete_batch(self, farm_id: int, field_ids: list[int]):
        if farm_id == 404:
            raise LookupError("missing field")
        if 409 in field_ids:
            raise ConflictError("linked plan")
        self.deleted_farm_id = farm_id
        self.batch_deleted_field_ids = field_ids


class FakeFarmFieldQueryService:
    def list_by_farm(self, farm_id: int):
        if farm_id == 404:
            raise LookupError("missing farm")
        return [_make_field(12), _make_field(10)]

    def get(self, farm_id: int, field_id: int):
        if farm_id == 404 or field_id == 404:
            raise LookupError("missing field")
        return _make_field(field_id)


class DummySession:
    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None


def test_create_list_get_patch_and_delete_farm_routes() -> None:
    fake_service = FakeFarmService()
    app.dependency_overrides[get_farm_service] = lambda: fake_service
    app.dependency_overrides[get_farm_query_service] = lambda: FakeFarmQueryService()
    app.dependency_overrides[get_db] = lambda: DummySession()
    client = TestClient(app)

    create_response = client.post(
        "/api/farms",
        json={
            "farm_name": "联调农场",
            "external_farm_id": "84911829811210",
            "province": "湖南省",
            "city": "长沙市",
            "district_county": "岳麓区",
            "adcode": "430104",
            "centroid_lat": 28.19409,
            "centroid_lon": 112.982279,
        },
    )
    list_response = client.get("/api/farms")
    get_response = client.get("/api/farms/1")
    patch_response = client.patch("/api/farms/1", json={"city": "株洲市", "external_farm_id": "47035753446400"})
    delete_response = client.delete("/api/farms/1")

    assert create_response.status_code == 201
    assert create_response.json()["farm_name"] == "农场 1"
    assert fake_service.created_payload.external_farm_id == "84911829811210"
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [2, 1]
    assert get_response.status_code == 200
    assert patch_response.status_code == 200
    assert patch_response.json()["city"] == "株洲市"
    assert patch_response.json()["external_farm_id"] == "47035753446400"
    assert delete_response.status_code == 204
    assert fake_service.deleted_farm_id == 1

    app.dependency_overrides.clear()


def test_delete_farm_returns_conflict_when_linked() -> None:
    fake_service = FakeFarmService()
    app.dependency_overrides[get_farm_service] = lambda: fake_service
    app.dependency_overrides[get_db] = lambda: DummySession()
    client = TestClient(app)

    response = client.delete("/api/farms/409")

    assert response.status_code == 409

    app.dependency_overrides.clear()


def test_farm_field_routes_cover_crud() -> None:
    fake_service = FakeFarmFieldService()
    app.dependency_overrides[get_farm_field_service] = lambda: fake_service
    app.dependency_overrides[get_farm_field_query_service] = lambda: FakeFarmFieldQueryService()
    app.dependency_overrides[get_db] = lambda: DummySession()
    client = TestClient(app)

    create_response = client.post(
        "/api/farms/1/fields",
        json={
            "field_name": "一号田",
            "external_field_id": "plot-001",
            "boundary_wkt": "POLYGON((0 0,1 0,1 1,0 1,0 0))",
            "centroid_lat": 28.2,
            "centroid_lon": 112.9,
            "area_ha": 5.5,
        },
    )
    list_response = client.get("/api/farms/1/fields")
    get_response = client.get("/api/farms/1/fields/10")
    patch_response = client.patch(
        "/api/farms/1/fields/10",
        json={"field_name": "二号田", "external_field_id": "plot-002"},
    )
    delete_response = client.delete("/api/farms/1/fields/10")

    assert create_response.status_code == 201
    assert create_response.json()["id"] == "11"
    assert create_response.json()["farm_id"] == 1
    assert create_response.json()["external_field_id"] == "plot-001"
    assert fake_service.created_payload.external_field_id == "plot-001"
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == ["12", "10"]
    assert get_response.status_code == 200
    assert get_response.json()["id"] == "10"
    assert patch_response.status_code == 200
    assert patch_response.json()["id"] == "10"
    assert patch_response.json()["field_name"] == "二号田"
    assert patch_response.json()["external_field_id"] == "plot-002"
    assert delete_response.status_code == 204
    assert fake_service.deleted_field_id == 10

    app.dependency_overrides.clear()


def test_patch_routes_allow_clearing_optional_fields() -> None:
    fake_farm_service = FakeFarmService()
    fake_field_service = FakeFarmFieldService()
    app.dependency_overrides[get_farm_service] = lambda: fake_farm_service
    app.dependency_overrides[get_farm_field_service] = lambda: fake_field_service
    app.dependency_overrides[get_db] = lambda: DummySession()
    client = TestClient(app)

    farm_response = client.patch(
        "/api/farms/1",
        json={
            "external_farm_id": None,
            "boundary_wkt": None,
            "centroid_lat": None,
            "centroid_lon": None,
        },
    )
    field_response = client.patch(
        "/api/farms/1/fields/10",
        json={
            "external_field_id": None,
            "boundary_wkt": None,
            "centroid_lat": None,
            "centroid_lon": None,
            "area_ha": None,
        },
    )

    assert farm_response.status_code == 200
    assert farm_response.json()["external_farm_id"] is None
    assert farm_response.json()["boundary_wkt"] is None
    assert fake_farm_service.updated_payload.external_farm_id is None
    assert field_response.status_code == 200
    assert field_response.json()["external_field_id"] is None
    assert field_response.json()["area_ha"] is None
    assert fake_field_service.updated_payload.external_field_id is None

    app.dependency_overrides.clear()


def test_farm_field_batch_routes_cover_create_and_delete() -> None:
    fake_service = FakeFarmFieldService()
    app.dependency_overrides[get_farm_field_service] = lambda: fake_service
    app.dependency_overrides[get_db] = lambda: DummySession()
    client = TestClient(app)

    create_response = client.post(
        "/api/farms/1/fields/batch",
        json={
            "fields": [
                {
                    "field_name": "一号田",
                    "external_field_id": "plot-001",
                    "centroid_lat": 28.2,
                    "centroid_lon": 112.9,
                },
                {
                    "field_name": "二号田",
                    "external_field_id": "plot-002",
                    "centroid_lat": 28.3,
                    "centroid_lon": 113.0,
                },
            ],
        },
    )
    delete_response = client.post(
        "/api/farms/1/fields/batch-delete",
        json={"field_ids": [11, 12]},
    )

    assert create_response.status_code == 201
    assert [item["id"] for item in create_response.json()] == ["11", "12"]
    assert [item.external_field_id for item in fake_service.batch_created_payloads] == ["plot-001", "plot-002"]
    assert delete_response.status_code == 204
    assert fake_service.batch_deleted_field_ids == [11, 12]

    app.dependency_overrides.clear()


def test_delete_field_returns_conflict_when_linked() -> None:
    fake_service = FakeFarmFieldService()
    app.dependency_overrides[get_farm_field_service] = lambda: fake_service
    app.dependency_overrides[get_db] = lambda: DummySession()
    client = TestClient(app)

    response = client.delete("/api/farms/1/fields/409")

    assert response.status_code == 409

    app.dependency_overrides.clear()


def test_delete_fields_batch_returns_conflict_when_linked() -> None:
    fake_service = FakeFarmFieldService()
    app.dependency_overrides[get_farm_field_service] = lambda: fake_service
    app.dependency_overrides[get_db] = lambda: DummySession()
    client = TestClient(app)

    response = client.post("/api/farms/1/fields/batch-delete", json={"field_ids": [10, 409]})

    assert response.status_code == 409

    app.dependency_overrides.clear()
