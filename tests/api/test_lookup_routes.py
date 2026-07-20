from __future__ import annotations

from dataclasses import dataclass

from fastapi.testclient import TestClient

from app.api.deps import (
    get_administrative_division_query_service,
    get_code_dict_query_service,
    get_rice_variety_query_service,
)
from app.main import app
from app.services import AdministrativeDivisionNode, CodeDictOption, RiceVarietyOption


@dataclass
class FakeCodeDictQueryService:
    last_category: str | None = None

    def list_options(self, category: str):
        self.last_category = category
        return [
            CodeDictOption(code=5, name="早稻", category=category),
            CodeDictOption(code=6, name="中稻", category=category),
        ]


@dataclass
class FakeRiceVarietyQueryService:
    last_query: str | None = None
    last_limit: int | None = None

    def search(self, query: str | None, *, limit: int = 20):
        self.last_query = query
        self.last_limit = limit
        return [
            RiceVarietyOption(id=1, name="黄广农占", approve_region="长江中下游", culti_type_code=5, sub_type_code=9),
            RiceVarietyOption(id=2, name="黄华占", approve_region="湖南", culti_type_code=5, sub_type_code=9),
        ]


@dataclass
class FakeAdministrativeDivisionQueryService:
    last_parent_code: str | None = None
    last_parent_level: int | None = None

    def list_children(self, parent_code: str | None = None, *, parent_level: int | None = None):
        self.last_parent_code = parent_code
        self.last_parent_level = parent_level
        if parent_code == "404":
            raise LookupError("missing parent")
        if parent_level == 9:
            raise ValueError("parent_level must be between 1 and 4.")
        if parent_code is None:
            return [
                AdministrativeDivisionNode(
                    code="430000000000",
                    adcode="430000",
                    name="湖南省",
                    division_type="省",
                    level=1,
                    parent_code=None,
                    has_children=True,
                    is_virtual=False,
                ),
            ]
        return [
            AdministrativeDivisionNode(
                code="430100000000",
                adcode="430100",
                name="长沙市",
                division_type="地级市",
                level=2,
                parent_code=parent_code,
                has_children=True,
                is_virtual=False,
            ),
        ]


def test_list_code_dict_options_route() -> None:
    fake_service = FakeCodeDictQueryService()
    app.dependency_overrides[get_code_dict_query_service] = lambda: fake_service
    client = TestClient(app)

    response = client.get("/api/code-dicts", params={"category": "culti_type"})

    assert response.status_code == 200
    assert response.json() == [
        {"code": 5, "name": "早稻", "category": "culti_type"},
        {"code": 6, "name": "中稻", "category": "culti_type"},
    ]
    assert fake_service.last_category == "culti_type"

    app.dependency_overrides.clear()


def test_search_rice_varieties_route() -> None:
    fake_service = FakeRiceVarietyQueryService()
    app.dependency_overrides[get_rice_variety_query_service] = lambda: fake_service
    client = TestClient(app)

    response = client.get("/api/rice-varieties", params={"query": "黄广", "limit": 10})

    assert response.status_code == 200
    assert response.json() == [
        {"id": 1, "name": "黄广农占", "approve_region": "长江中下游", "culti_type_code": 5, "sub_type_code": 9},
        {"id": 2, "name": "黄华占", "approve_region": "湖南", "culti_type_code": 5, "sub_type_code": 9},
    ]
    assert fake_service.last_query == "黄广"
    assert fake_service.last_limit == 10

    app.dependency_overrides.clear()


def test_list_administrative_division_children_route() -> None:
    fake_service = FakeAdministrativeDivisionQueryService()
    app.dependency_overrides[get_administrative_division_query_service] = lambda: fake_service
    client = TestClient(app)

    root_response = client.get("/api/administrative-divisions")
    child_response = client.get(
        "/api/administrative-divisions",
        params={"parent_code": "430000000000", "parent_level": 1},
    )

    assert root_response.status_code == 200
    assert root_response.json() == [
        {
            "code": "430000000000",
            "adcode": "430000",
            "name": "湖南省",
            "division_type": "省",
            "level": 1,
            "parent_code": None,
            "has_children": True,
            "is_virtual": False,
        },
    ]
    assert child_response.status_code == 200
    assert child_response.json() == [
        {
            "code": "430100000000",
            "adcode": "430100",
            "name": "长沙市",
            "division_type": "地级市",
            "level": 2,
            "parent_code": "430000000000",
            "has_children": True,
            "is_virtual": False,
        },
    ]
    assert fake_service.last_parent_code == "430000000000"
    assert fake_service.last_parent_level == 1

    app.dependency_overrides.clear()


def test_list_administrative_division_children_route_returns_errors() -> None:
    fake_service = FakeAdministrativeDivisionQueryService()
    app.dependency_overrides[get_administrative_division_query_service] = lambda: fake_service
    client = TestClient(app)

    bad_request = client.get(
        "/api/administrative-divisions",
        params={"parent_code": "430000000000", "parent_level": 9},
    )
    not_found = client.get(
        "/api/administrative-divisions",
        params={"parent_code": "404", "parent_level": 1},
    )

    assert bad_request.status_code == 400
    assert not_found.status_code == 404

    app.dependency_overrides.clear()
