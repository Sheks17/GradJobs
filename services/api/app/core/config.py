from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://gradjobs:gradjobs@localhost:5432/gradjobs"
    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:3000"]
    collector_user_agent: str = "GradJobs/0.1 (public job discovery)"
    collector_request_interval: float = 0.5
    collector_timeout_seconds: float = Field(default=30, ge=1, le=120)
    collector_max_concurrency: int = Field(default=3, ge=1, le=12)
    collector_provider_concurrency: dict[str, int] = Field(
        default_factory=lambda: {"smartrecruiters": 2, "usajobs": 1, "workday": 1}
    )
    usajobs_api_key: str = ""
    usajobs_user_agent: str = ""
    stale_missing_syncs: int = Field(default=3, ge=2)
    stale_after_hours: int = Field(default=72, ge=1)
    source_lease_minutes: int = Field(default=30, ge=5)
    source_failure_threshold: int = Field(default=3, ge=1, le=20)
    source_cooldown_minutes: int = Field(default=60, ge=1, le=1440)
    workday_detail_cache_hours: int = Field(default=6, ge=0, le=24)
    new_job_hours: int = Field(default=24, ge=1)
    sync_interval_minutes: int = Field(default=30, ge=1)
    enable_admin_api: bool = False

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_postgres_url(cls, value: str) -> str:
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value[len(prefix) :]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
