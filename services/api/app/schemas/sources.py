import re
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from services.api.app.schemas.jobs import UtcDatetime


class SourceCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    company_name: str = Field(min_length=1, max_length=250)
    provider: Literal["greenhouse", "lever", "ashby", "smartrecruiters", "usajobs", "workday"]
    board_token: str = Field(pattern=r"^[A-Za-z0-9_-]{1,200}$")
    careers_url: str | None = None
    enabled: bool = True
    provider_config: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def workday_required(self):
        if self.provider == "workday":
            from collectors.workday import source_token, workday_config

            config = workday_config(self.provider_config.get("careers_url", ""))
            if self.board_token != source_token(config):
                raise ValueError("Workday board token must match observed hostname and site")
        return self

    @field_validator("provider_config")
    @classmethod
    def public_configuration(cls, value):
        if value is None:
            return value
        allowed = {
            "company_identifier",
            "country",
            "queries",
            "results_per_page",
            "max_pages",
            "hostname",
            "tenant",
            "site",
            "locale",
            "careers_url",
        }
        if set(value) - allowed:
            raise ValueError(
                "Unknown provider configuration keys; credentials belong in environment variables"
            )
        if any(key in value for key in ("hostname", "tenant", "site", "locale", "careers_url")):
            from collectors.workday import workday_config

            observed = workday_config(value.get("careers_url", ""))
            if any(value[key] != observed[key] for key in observed if key in value):
                raise ValueError("Workday configuration conflicts with careers URL")
        if "max_pages" in value and not 1 <= int(value["max_pages"]) <= 100:
            raise ValueError("max_pages must be 1–100")
        if "results_per_page" in value and not 1 <= int(value["results_per_page"]) <= 500:
            raise ValueError("results_per_page must be 1–500")
        if "country" in value and not re.fullmatch(r"[A-Za-z]{2}", str(value["country"])):
            raise ValueError("country must be a two-letter code")
        if "queries" in value:
            from collectors.usajobs import SEARCH_FIELDS

            if not isinstance(value["queries"], list) or not 1 <= len(value["queries"]) <= 12:
                raise ValueError("Configure 1–12 USAJOBS queries")
            for query in value["queries"]:
                if not isinstance(query, dict) or set(query) - SEARCH_FIELDS:
                    raise ValueError("Unknown USAJOBS query fields")
                if not any(
                    query.get(key) for key in ("Keyword", "JobCategoryCode", "Organization")
                ):
                    raise ValueError("USAJOBS queries must be scoped")
        return value

    @field_validator("careers_url")
    @classmethod
    def validate_url(cls, value):
        if value:
            url = HttpUrl(value)
            if url.username or url.password:
                raise ValueError("Credentials are not allowed in source URLs")
        return value


class SourcePatch(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    company_name: str | None = Field(default=None, min_length=1, max_length=250)
    careers_url: str | None = None
    enabled: bool | None = None
    provider_config: dict | None = None
    public_configuration = field_validator("provider_config")(
        SourceCreate.public_configuration.__func__
    )
    validate_url = field_validator("careers_url")(SourceCreate.validate_url.__func__)


class SyncOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    source_id: UUID
    started_at: UtcDatetime
    completed_at: UtcDatetime | None
    status: str
    jobs_fetched: int
    jobs_created: int
    jobs_updated: int
    jobs_unchanged: int
    jobs_skipped: int
    jobs_failed: int
    jobs_closed: int
    error_message: str | None
    duration_ms: int | None
