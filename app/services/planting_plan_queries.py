from __future__ import annotations

from dataclasses import dataclass

from app.models import CalendarItem, FarmingTask, PlantingPlan, ReviewRequest, TaskIntent
from app.repositories import (
    CalendarItemRepository,
    FarmingTaskRepository,
    PlantingPlanRepository,
    ReviewRequestRepository,
    TaskIntentRepository,
)


@dataclass(slots=True)
class PlantingPlanM2Snapshot:
    planting_plan: PlantingPlan
    calendar_items: list[CalendarItem]
    farming_tasks: list[FarmingTask]
    task_intents: list[TaskIntent]
    review_requests: list[ReviewRequest]


class PlantingPlanQueryService:
    def __init__(
        self,
        planting_plan_repository: PlantingPlanRepository,
        calendar_item_repository: CalendarItemRepository,
        farming_task_repository: FarmingTaskRepository,
        task_intent_repository: TaskIntentRepository,
        review_request_repository: ReviewRequestRepository,
    ) -> None:
        self.planting_plan_repository = planting_plan_repository
        self.calendar_item_repository = calendar_item_repository
        self.farming_task_repository = farming_task_repository
        self.task_intent_repository = task_intent_repository
        self.review_request_repository = review_request_repository

    def list_calendar_items(self, planting_plan_id: int) -> list[CalendarItem]:
        self._get_plan(planting_plan_id)
        return self.calendar_item_repository.list_current_by_plan(planting_plan_id)

    def list_farming_tasks(self, planting_plan_id: int) -> list[FarmingTask]:
        self._get_plan(planting_plan_id)
        return self.farming_task_repository.list_current_by_plan(planting_plan_id)

    def list_task_intents(self, planting_plan_id: int) -> list[TaskIntent]:
        self._get_plan(planting_plan_id)
        return self.task_intent_repository.list_current_by_plan(planting_plan_id)

    def list_review_requests(self, planting_plan_id: int) -> list[ReviewRequest]:
        self._get_plan(planting_plan_id)
        return self.review_request_repository.list_current_by_plan(planting_plan_id)

    def get_m2_snapshot(self, planting_plan_id: int) -> PlantingPlanM2Snapshot:
        planting_plan = self._get_plan(planting_plan_id)
        return PlantingPlanM2Snapshot(
            planting_plan=planting_plan,
            calendar_items=self.calendar_item_repository.list_current_by_plan(planting_plan_id),
            farming_tasks=self.farming_task_repository.list_current_by_plan(planting_plan_id),
            task_intents=self.task_intent_repository.list_current_by_plan(planting_plan_id),
            review_requests=self.review_request_repository.list_current_by_plan(planting_plan_id),
        )

    def _get_plan(self, planting_plan_id: int) -> PlantingPlan:
        planting_plan = self.planting_plan_repository.get(planting_plan_id)
        if planting_plan is None:
            raise LookupError(f"Planting plan {planting_plan_id} does not exist.")
        return planting_plan
