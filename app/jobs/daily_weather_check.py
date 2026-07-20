from __future__ import annotations

import logging
from datetime import date

from app.models import EventRecord
from app.services.calendar_tasks import WeatherUpdateService

logger = logging.getLogger(__name__)


class DailyWeatherCheckJob:
    def __init__(self, service: WeatherUpdateService, max_retries: int = 2) -> None:
        self.service = service
        self.max_retries = max_retries

    def run(self, planting_plan_id: int, *, check_date: date) -> list[EventRecord]:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return self.service.generate_weather_updates(planting_plan_id, check_date=check_date)
            except Exception as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                logger.warning(
                    "DailyWeatherCheckJob failed, retrying planting_plan_id=%s check_date=%s attempt=%s.",
                    planting_plan_id,
                    check_date,
                    attempt + 1,
                    exc_info=True,
                )
        assert last_error is not None
        raise last_error
