from __future__ import annotations

import logging
from dataclasses import dataclass

from fastapi.testclient import TestClient

from app.api.deps import get_planting_plan_service
from app.db.session import get_db
from app.main import app


@dataclass
class FailingPlantingPlanService:
    def create(self, payload):
        raise ValueError("invalid plan payload")


class DummySession:
    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None


def test_http_exception_logging_includes_request_context(caplog) -> None:
    app.dependency_overrides[get_planting_plan_service] = lambda: FailingPlantingPlanService()
    app.dependency_overrides[get_db] = lambda: DummySession()
    client = TestClient(app)

    with caplog.at_level(logging.WARNING):
        response = client.post(
            "/api/planting-plans",
            json={
                "plan_name": "失败计划",
                "farm_id": 1,
                "field_ids": [10],
                "culti_type_code": 5,
                "planting_method_code": 1,
                "crop_name": "水稻",
                "variety_id": 3,
                "sowing_date": "2026-04-10",
            },
        )

    assert response.status_code == 400
    assert "API request failed with HTTPException" in caplog.text
    assert "/api/planting-plans" in caplog.text
    assert "失败计划" in caplog.text

    app.dependency_overrides.clear()
