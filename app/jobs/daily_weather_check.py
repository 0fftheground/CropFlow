from __future__ import annotations

from datetime import date

from app.models import EventRecord
from app.services.calendar_tasks import WeatherUpdateService


class DailyWeatherCheckJob:
    def __init__(self, service: WeatherUpdateService) -> None:
        self.service = service

    def run(self, planting_plan_id: int, *, check_date: date) -> list[EventRecord]:
        return self.service.generate_weather_updates(planting_plan_id, check_date=check_date)
