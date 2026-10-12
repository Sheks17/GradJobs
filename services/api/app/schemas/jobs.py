from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
)

from services.api.app.core.config import get_settings
from services.api.app.db.session import utcnow
from shared.constants import RemoteType, Seniority


def ensure_utc(value: datetime) -> datetime:
    # SQLite strips tzinfo on round-trip; all stored observation times originate in UTC.
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


UtcDatetime = Annotated[datetime, AfterValidator(ensure_utc)]


class JobFilters(BaseModel):
    provider: Literal["greenhouse", "lever", "ashby", "smartrecruiters", "usajobs"] | None = None
    q: str | None = Field(default=None, max_length=200)
    role_family: str | None = Field(default=None, max_length=100)
    seniority: Seniority | None = None
    remote_type: RemoteType | None = None
    state: str | None = Field(default=None, max_length=100)
    country: str = Field(default="US", pattern=r"^(?:[A-Z]{2}|all)$")
    company: str | None = Field(default=None, max_length=300)
    skill: str | None = Field(default=None, max_length=50)
    role_group: Literal["software", "support", "cloud"] | None = None
    experience_category: (
        Literal[
            "no_experience_required",
            "0_1",
            "0_2",
            "1_2",
            "1_3",
            "2_3",
            "3_plus",
            "4_plus",
            "5_plus",
            "unspecified",
            "ambiguous",
        ]
        | None
    ) = None
    min_salary: Decimal | None = Field(default=None, ge=0)
    max_experience: int | None = Field(default=3, ge=0, le=40)
    include_unknown_experience: bool = True
    include_senior: bool = False
    include_demo: bool = False
    min_early_career_score: int = Field(default=50, ge=0, le=100)
    posted_after: AwareDatetime | None = None
    fresh_after: AwareDatetime | None = None
    sort: Literal[
        "best_match",
        "relevance",
        "newest",
        "newest_posted",
        "recently_discovered",
        "early_career_score",
        "company",
        "salary",
    ] = "best_match"
    page: int = Field(default=1, ge=1, le=10000)
    page_size: int = Field(default=20, ge=1, le=100)

    @field_validator("skill")
    @classmethod
    def valid_skill(cls, value):
        if value is None:
            return value
        from matching.skills import normalize_skill

        skill = normalize_skill(value)
        if not skill:
            raise ValueError("Unknown skill; use a value from /metadata")
        return skill


class JobSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    company_name: str
    company_slug: str
    location_raw: str | None
    city: str | None
    state: str | None
    country: str | None
    remote_type: str
    employment_type: str | None
    salary_min: Decimal | None
    salary_max: Decimal | None
    salary_currency: str | None
    salary_period: str | None
    experience_min_years: int | None
    experience_max_years: int | None
    experience_is_preferred: bool
    role_family: str
    seniority_level: str
    early_career_score: int
    fit_label: str
    posted_at: UtcDatetime | None
    closing_at: UtcDatetime | None = None
    provider_metadata: dict = Field(default_factory=dict)
    requires_us_citizenship: bool | None = None
    requires_security_clearance: bool | None = None
    first_seen_at: UtcDatetime
    last_seen_at: UtcDatetime
    source: str
    apply_url: str
    is_active: bool
    is_demo: bool
    locations: list[dict] = Field(default_factory=list)
    required_min_years: int | None = None
    required_max_years: int | None = None
    preferred_min_years: int | None = None
    preferred_max_years: int | None = None
    requirement_type: str = "unspecified"
    experience_category: str = "unspecified"
    classification_confidence: int = 0
    classification_conflict: bool = False
    conflict_reasons: list[str] = Field(default_factory=list)
    detected_skills: list[str] = Field(default_factory=list)
    score_evidence: list[dict] = Field(default_factory=list)
    remote_us_only: bool | None = None
    remote_states: list[str] = Field(default_factory=list)
    excluded_states: list[str] = Field(default_factory=list)
    timezone_requirement: str | None = None

    @computed_field
    @property
    def is_new(self) -> bool:
        age = utcnow() - self.first_seen_at
        return timedelta(0) <= age <= timedelta(hours=get_settings().new_job_hours)


class JobDetail(JobSummary):
    description: str
    source_url: str
    source_job_id: str
    source_updated_at: UtcDatetime | None
    company_website: str | None
    experience_text: str | None
    score_reasons: list[str]
    experience_confidence: float = 0
    experience_evidence: list[dict] = Field(default_factory=list)
    matching_version: str | None = None
    remote_restriction_evidence: list[str] = Field(default_factory=list)
    requires_us_citizenship: bool | None
    requires_security_clearance: bool | None
    sponsorship_text: str | None
    work_authorization_text: str | None


class JobPage(BaseModel):
    items: list[JobSummary]
    page: int
    page_size: int
    total: int
    total_pages: int


class Stats(BaseModel):
    active_jobs: int
    discovered_today: int
    discovered_this_week: int
    remote_jobs: int
    entry_level_jobs: int
    average_early_career_score: float
    demo_jobs: int


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    source_type: str
    company_name: str | None
    careers_url: str | None
    provider_config: dict = Field(default_factory=dict)
    enabled: bool
    last_successful_sync: UtcDatetime | None
    last_sync_attempt: UtcDatetime | None
    last_error: str | None
    board_identifier: str
    active_jobs: int
    failure_count: int
    created_at: UtcDatetime
    updated_at: UtcDatetime
    lease_expires_at: UtcDatetime | None

    @computed_field
    @property
    def status(self) -> str:
        if not self.enabled:
            return "disabled"
        if self.lease_expires_at and self.lease_expires_at > utcnow():
            return "syncing"
        if self.lease_expires_at:
            return "interrupted"
        return "error" if self.last_error else "healthy" if self.last_successful_sync else "pending"
