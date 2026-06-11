import json
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_CONFIG_PATH = REPO_ROOT / "database" / "sql" / "db_config.json"


def _load_database_url_from_json(config_path: Path = DEFAULT_DB_CONFIG_PATH) -> str | None:
    if not config_path.exists():
        return None

    config = json.loads(config_path.read_text(encoding="utf-8"))
    user = quote_plus(config["user"])
    password = quote_plus(config["password"])
    host = config["host"]
    port = config["port"]
    dbname = config["dbname"]
    sslmode = config.get("sslmode")
    base_url = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{dbname}"
    return f"{base_url}?sslmode={sslmode}" if sslmode else base_url


class Settings(BaseSettings):
    app_name: str = "CropFlow API"
    environment: str = "development"
    debug: bool = False
    api_prefix: str = "/api"
    sql_echo: bool = False
    require_real_integrations: bool = False
    database_url: str | None = None
    weed_diagnosis_base_url: str | None = None
    pest_disease_survey_base_url: str | None = None
    pest_disease_control_base_url: str | None = None
    stage_prediction_base_url: str | None = None
    weather_api_base_url: str | None = None
    weather_api_token: str | None = None
    weather_alert_api_base_url: str | None = None
    weather_alert_api_token: str | None = None
    weather_api_timeout_seconds: float = 10.0
    weather_climatology_reference_years: int = 3
    background_jobs_enabled: bool = False
    weather_check_interval_seconds: int = 300
    survey_recommendation_interval_seconds: int = 300
    task_due_check_interval_seconds: int = 300
    log_dir: str = "logs"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="CROPFLOW_",
        extra="ignore",
    )

    def get_database_url(self) -> str:
        if self.database_url:
            return self.database_url

        fallback_url = _load_database_url_from_json()
        if fallback_url:
            return fallback_url

        raise RuntimeError(
            "Database URL is not configured. Set CROPFLOW_DATABASE_URL or provide database/sql/db_config.json.",
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
