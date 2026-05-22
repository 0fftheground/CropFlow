from __future__ import annotations

from datetime import date

from app.models import CalendarItem
from app.services.calendar_tasks import SurveyDateRecommendationService


class SurveyDateRecommendationJob:
    def __init__(self, service: SurveyDateRecommendationService) -> None:
        self.service = service

    def run_pre_treatment(self, planting_plan_id: int, *, check_date: date | None = None) -> CalendarItem:
        return self.service.recommend_pre_treatment_survey(planting_plan_id, check_date=check_date)

    def run_post_treatment(
        self,
        planting_plan_id: int,
        *,
        operation_date: date,
        parent_task_id: int,
        source_execution_id: int,
        source_execution_record_id: int,
    ) -> tuple[CalendarItem, CalendarItem]:
        return self.service.recommend_post_treatment_surveys(
            planting_plan_id,
            operation_date=operation_date,
            parent_task_id=parent_task_id,
            source_execution_id=source_execution_id,
            source_execution_record_id=source_execution_record_id,
        )
