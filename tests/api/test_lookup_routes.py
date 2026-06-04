from __future__ import annotations

from dataclasses import dataclass

from fastapi.testclient import TestClient

from app.api.deps import get_code_dict_query_service, get_rice_variety_query_service
from app.main import app
from app.services import CodeDictOption, RiceVarietyOption


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
