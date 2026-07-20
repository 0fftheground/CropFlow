from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.models import PlantingPlan, FarmingTask
from app.services import PlantingPlanQueryService


@dataclass
class FakePlantingPlanRepository:
    item: PlantingPlan

    def get(self, planting_plan_id: int) -> PlantingPlan | None:
        return self.item if self.item.id == planting_plan_id else None


@dataclass
class FakePlantingPlanFieldRelationRepository:
    field_ids: list[int]

    def list_field_ids_by_plan(self, planting_plan_id: int) -> list[int]:
        return list(self.field_ids)


@dataclass
class FakeCalendarItemRepository:
    def list_current_by_plan(self, planting_plan_id: int):
        return []


@dataclass
class FakeFarmingTaskRepository:
    items: list[FarmingTask]

    def list_by_plan(self, planting_plan_id: int) -> list[FarmingTask]:
        return [item for item in self.items if item.planting_plan_id == planting_plan_id]


@dataclass
class FakeTaskIntentRepository:
    def list_current_by_plan(self, planting_plan_id: int):
        return []


@dataclass
class FakeReviewRequestRepository:
    def list_current_by_plan(self, planting_plan_id: int):
        return []


@dataclass
class FakeOperationPlanRepository:
    def list_by_plan(self, planting_plan_id: int):
        return []


@dataclass
class FakeEventRecordRepository:
    def list_by_plan(self, planting_plan_id: int):
        return []


@dataclass
class FakeCropStageStateRepository:
    def get_by_plan(self, planting_plan_id: int):
        return None


@dataclass
class FakeCropThermalTimeStateRepository:
    def get_by_plan(self, planting_plan_id: int):
        return None


@dataclass
class FakeStagePredictionSnapshotRepository:
    def get_latest_by_plan(self, planting_plan_id: int):
        return None

    def list_by_plan(self, planting_plan_id: int):
        return []


def test_list_farming_tasks_includes_completed_tasks() -> None:
    service = PlantingPlanQueryService(
        planting_plan_repository=FakePlantingPlanRepository(
            PlantingPlan(
                id=26,
                plan_code="PLAN-026",
                plan_name="测试计划",
                farm_id=1,
                culti_type_code=5,
                planting_method_code=1,
                crop_name="水稻",
                variety_id=3,
                variety_name="黄广农占",
                sowing_date=date(2026, 5, 10),
                status="active",
                task_generation_window_days=14,
                metadata_payload={},
            ),
        ),
        planting_plan_field_relation_repository=FakePlantingPlanFieldRelationRepository([]),
        calendar_item_repository=FakeCalendarItemRepository(),
        farming_task_repository=FakeFarmingTaskRepository(
            [
                FarmingTask(
                    id=52,
                    planting_plan_id=26,
                    task_category="plant_protection",
                    task_subtype="plant_protection.stem_leaf_weed_pre_survey",
                    title="药前调查",
                    status="pending",
                    execution_mode="manual",
                    idempotency_key="task:52",
                ),
                FarmingTask(
                    id=53,
                    planting_plan_id=26,
                    task_category="plant_protection",
                    task_subtype="plant_protection.regular_disease_pest_survey",
                    title="常规病虫调查",
                    status="completed",
                    execution_mode="manual",
                    idempotency_key="task:53",
                ),
            ],
        ),
        task_intent_repository=FakeTaskIntentRepository(),
        review_request_repository=FakeReviewRequestRepository(),
        operation_plan_repository=FakeOperationPlanRepository(),
        event_record_repository=FakeEventRecordRepository(),
        crop_stage_state_repository=FakeCropStageStateRepository(),
        crop_thermal_time_state_repository=FakeCropThermalTimeStateRepository(),
        stage_prediction_snapshot_repository=FakeStagePredictionSnapshotRepository(),
    )

    tasks = service.list_farming_tasks(26)

    assert [item.id for item in tasks] == [52, 53]
    assert [item.status for item in tasks] == ["pending", "completed"]
