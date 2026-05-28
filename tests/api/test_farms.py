from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from fastapi.testclient import TestClient

from app.api.deps import get_farm_query_service, get_farm_service
from app.db.session import get_db
from app.main import app
from app.models import Farm


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


@dataclass
class FakeFarmService:
    created_payload: object | None = None
    updated_payload: object | None = None

    def create(self, payload):
        self.created_payload = payload
        return _make_farm(1)

    def update(self, farm_id: int, payload):
        if farm_id == 404:
            raise LookupError("missing")
        self.updated_payload = payload
        farm = _make_farm(farm_id)
        if payload.city is not None:
            farm.city = payload.city
        if payload.external_farm_id is not None:
            farm.external_farm_id = payload.external_farm_id
        return farm


class FakeFarmQueryService:
    def list_all(self):
        return [_make_farm(2), _make_farm(1)]

    def get(self, farm_id: int):
        if farm_id == 404:
            raise LookupError("missing")
        return _make_farm(farm_id)


class DummySession:
    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None


def test_create_and_list_farms_routes() -> None:
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

    assert create_response.status_code == 201
    assert create_response.json()["farm_name"] == "农场 1"
    assert create_response.json()["external_farm_id"] == "ext-1"
    assert fake_service.created_payload.external_farm_id == "84911829811210"
    assert fake_service.created_payload.adcode == "430104"
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [2, 1]

    app.dependency_overrides.clear()


def test_get_and_patch_farm_routes() -> None:
    fake_service = FakeFarmService()
    app.dependency_overrides[get_farm_service] = lambda: fake_service
    app.dependency_overrides[get_farm_query_service] = lambda: FakeFarmQueryService()
    app.dependency_overrides[get_db] = lambda: DummySession()
    client = TestClient(app)

    get_response = client.get("/api/farms/1")
    patch_response = client.patch("/api/farms/1", json={"city": "株洲市", "external_farm_id": "47035753446400"})

    assert get_response.status_code == 200
    assert get_response.json()["adcode"] == "430101"
    assert get_response.json()["external_farm_id"] == "ext-1"
    assert patch_response.status_code == 200
    assert patch_response.json()["city"] == "株洲市"
    assert patch_response.json()["external_farm_id"] == "47035753446400"
    assert fake_service.updated_payload.external_farm_id == "47035753446400"
    assert fake_service.updated_payload.city == "株洲市"

    app.dependency_overrides.clear()
