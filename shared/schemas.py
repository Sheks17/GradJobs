from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from shared.constants import RemoteType, SalaryPeriod, SourceType


class NormalizedJob(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    source: SourceType
    source_job_id: str = Field(min_length=1, max_length=500)
    external_id: str | None = None
    source_url: str
    apply_url: str
    company_name: str = Field(min_length=1, max_length=300)
    company_website: str | None = None
    title: str = Field(min_length=1, max_length=500)
    description: str = ""
    location_raw: str | None = None
    locations: list[dict[str, str | None]] = Field(default_factory=list)
    city: str | None = None
    state: str | None = None
    country: str | None = None
    remote_type: RemoteType = "unknown"
    remote_us_only: bool | None = None
    remote_states: list[str] = Field(default_factory=list)
    excluded_states: list[str] = Field(default_factory=list)
    timezone_requirement: str | None = None
    remote_restriction_evidence: list[str] = Field(default_factory=list)
    employment_type: str | None = None
    salary_min: Decimal | None = Field(default=None, ge=0)
    salary_max: Decimal | None = Field(default=None, ge=0)
    salary_currency: str | None = None
    salary_period: SalaryPeriod | None = None
    posted_at: datetime | None = None
    source_updated_at: datetime | None = None
    closing_at: datetime | None = None
    provider_metadata: dict[str, Any] = Field(default_factory=dict)
    requires_us_citizenship: bool | None = None
    requires_security_clearance: bool | None = None
    sponsorship_text: str | None = None
    work_authorization_text: str | None = None
    raw_data: dict[str, Any] = Field(default_factory=dict)
    is_demo: bool = False

    @field_validator("source_url", "apply_url", "company_website")
    @classmethod
    def safe_url(cls, value: str | None) -> str | None:
        if value is not None:
            parsed = HttpUrl(value)
            if parsed.username or parsed.password:
                raise ValueError("URL must not contain credentials")
        return value

    @field_validator("posted_at", "source_updated_at", "closing_at")
    @classmethod
    def timezone_required(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("Source dates must include a timezone")
        return value

    @model_validator(mode="after")
    def valid_salary(self) -> "NormalizedJob":
        if self.salary_min is not None and self.salary_max is not None:
            if self.salary_min > self.salary_max:
                raise ValueError("Salary minimum exceeds maximum")
        return self
