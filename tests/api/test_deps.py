from __future__ import annotations

from app.api.deps import build_survey_date_recommendation_service, build_weather_provider
from app.core.config import Settings
from app.services import HttpWeatherProvider, HttpWeedDiagnosisClient, MockWeatherProvider, MockWeedDiagnosisClient


class DummySession:
    pass


def test_build_survey_date_recommendation_service_uses_mock_client_without_base_url() -> None:
    service = build_survey_date_recommendation_service(
        DummySession(),
        Settings(
            weed_diagnosis_base_url=None,
            weather_api_base_url=None,
            weather_api_token=None,
        ),
    )

    assert service is not None
    assert isinstance(service.diagnosis_client, MockWeedDiagnosisClient)
    assert isinstance(service.weather_provider, MockWeatherProvider)


def test_build_survey_date_recommendation_service_builds_runtime_service() -> None:
    service = build_survey_date_recommendation_service(
        DummySession(),
        Settings(
            weed_diagnosis_base_url="http://diagnosis.local",
            weather_api_base_url=None,
            weather_api_token=None,
        ),
    )

    assert service is not None
    assert isinstance(service.diagnosis_client, HttpWeedDiagnosisClient)
    assert isinstance(service.weather_provider, MockWeatherProvider)


def test_build_weather_provider_uses_http_weather_provider_when_configured() -> None:
    provider = build_weather_provider(
        DummySession(),
        Settings(
            weather_api_base_url="http://weather.local",
            weather_api_token="secret-token",
        ),
    )

    assert isinstance(provider, HttpWeatherProvider)
