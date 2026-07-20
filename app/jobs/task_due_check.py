from __future__ import annotations

from datetime import date

from app.models import FarmingTask
from app.services.calendar_tasks import TaskGenerationService


class TaskDueCheckJob:
    def __init__(self, service: TaskGenerationService) -> None:
        self.service = service

    def run(self, planting_plan_id: int, *, check_date: date) -> list[FarmingTask]:
        return self.service.generate_due_tasks(planting_plan_id, check_date=check_date)
