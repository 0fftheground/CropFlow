import json
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import quote_plus

from pydantic import AliasChoices, Field
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
    agent_model_provider: str = "scripted"
    agent_model_base_url: str | None = None
    agent_model_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "agent_model_api_key",
            "CROPFLOW_AGENT_MODEL_API_KEY",
            "DEEPSEEK_API_KEY",
        ),
    )
    agent_model_name: str = ""
    agent_model_timeout_seconds: float = 60.0
    agent_model_thinking: Literal["enabled", "disabled"] = "enabled"
    agent_model_reasoning_effort: Literal["high", "max"] = "high"
    agent_model_max_output_tokens: int = Field(default=4096, ge=256, le=384000)
    agent_model_max_attempts: int = Field(default=3, ge=1, le=10)
    agent_model_retry_base_delay_seconds: float = Field(default=0.5, ge=0, le=60)
    agent_model_retry_max_delay_seconds: float = Field(default=4.0, ge=0, le=300)
    agent_model_retry_jitter_ratio: float = Field(default=0.2, ge=0, le=1)
    agent_model_retry_after_max_seconds: float = Field(default=10.0, ge=0, le=300)
    agent_run_execution_timeout_seconds: float = Field(default=180.0, gt=0, le=3600)
    agent_run_max_total_tokens: int | None = Field(default=16000, ge=1)
    agent_run_max_estimated_cost_usd: float | None = Field(default=None, gt=0)
    agent_model_input_cache_hit_price_per_million_usd: float | None = Field(default=None, ge=0)
    agent_model_input_cache_miss_price_per_million_usd: float | None = Field(default=None, ge=0)
    agent_model_output_price_per_million_usd: float | None = Field(default=None, ge=0)
    agent_max_iterations: int = 8
    agent_max_parallel_queries: int = 4
    agent_context_task_limit: int = 20
    agent_context_review_limit: int = 20
    agent_default_role: str = "observer"

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
