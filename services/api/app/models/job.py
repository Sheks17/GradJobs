import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    false,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from services.api.app.db.session import Base, utcnow

JsonType = JSON().with_variant(JSONB(), "postgresql")


class Timestamps:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class JobSource(Timestamps, Base):
    __tablename__ = "job_sources"
    __table_args__ = (UniqueConstraint("source_type", "board_identifier"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(300))
    source_type: Mapped[str] = mapped_column(String(30))
    board_identifier: Mapped[str] = mapped_column(String(200))
    company_name: Mapped[str | None] = mapped_column(String(300))
    base_url: Mapped[str | None] = mapped_column(Text)
    careers_url: Mapped[str | None] = mapped_column(Text)
    provider_config: Mapped[dict] = mapped_column(JsonType, default=dict, server_default="{}")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_successful_sync: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sync_attempt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    disabled_reason: Mapped[str | None] = mapped_column(Text)
    active_jobs: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    sync_token: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="running")
    summary: Mapped[dict] = mapped_column(JsonType, default=dict, server_default="{}")
    __table_args__ = (Index("ix_ingestion_runs_started_at", "started_at"),)


class Job(Timestamps, Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("source_id", "source_job_id"),
        CheckConstraint("early_career_score BETWEEN 0 AND 100"),
        CheckConstraint("salary_min IS NULL OR salary_min >= 0"),
        CheckConstraint("salary_max IS NULL OR salary_max >= 0"),
        CheckConstraint("salary_min IS NULL OR salary_max IS NULL OR salary_max >= salary_min"),
        Index("ix_jobs_dashboard", "is_active", "country", "early_career_score", "posted_at"),
        Index("ix_jobs_active_freshness", "is_active", text("coalesce(posted_at, first_seen_at)")),
        Index("ix_jobs_dedup", "company_slug", "normalized_title", "description_fingerprint"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("job_sources.id"))
    external_id: Mapped[str | None] = mapped_column(String(500))
    source: Mapped[str] = mapped_column(String(30))
    source_job_id: Mapped[str] = mapped_column(String(500))
    source_url: Mapped[str] = mapped_column(Text)
    apply_url: Mapped[str] = mapped_column(Text)
    normalized_apply_url: Mapped[str] = mapped_column(Text, index=True)
    company_name: Mapped[str] = mapped_column(String(300))
    company_slug: Mapped[str] = mapped_column(String(300), index=True)
    company_website: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str] = mapped_column(String(500))
    normalized_title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text)
    description_fingerprint: Mapped[str] = mapped_column(String(64))
    location_raw: Mapped[str | None] = mapped_column(Text)
    normalized_location: Mapped[str] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(200))
    state: Mapped[str | None] = mapped_column(String(100), index=True)
    country: Mapped[str | None] = mapped_column(String(2))
    remote_type: Mapped[str] = mapped_column(String(20), default="unknown", index=True)
    employment_type: Mapped[str | None] = mapped_column(Text().with_variant(String(100), "sqlite"))
    salary_min: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    salary_max: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    salary_currency: Mapped[str | None] = mapped_column(String(3))
    salary_period: Mapped[str | None] = mapped_column(String(10))
    experience_min_years: Mapped[int | None] = mapped_column(Integer)
    experience_max_years: Mapped[int | None] = mapped_column(Integer)
    experience_text: Mapped[str | None] = mapped_column(Text)
    experience_is_preferred: Mapped[bool] = mapped_column(Boolean, default=False)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    provider_metadata: Mapped[dict] = mapped_column(JsonType, default=dict, server_default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    role_family: Mapped[str] = mapped_column(String(100), index=True)
    seniority_level: Mapped[str] = mapped_column(String(30), index=True)
    early_career_score: Mapped[int] = mapped_column(Integer)
    match_score: Mapped[int | None] = mapped_column(Integer)
    fit_label: Mapped[str] = mapped_column(String(100))
    score_reasons: Mapped[list[str]] = mapped_column(JsonType)
    requires_us_citizenship: Mapped[bool | None] = mapped_column(Boolean)
    requires_security_clearance: Mapped[bool | None] = mapped_column(Boolean)
    sponsorship_text: Mapped[str | None] = mapped_column(Text)
    work_authorization_text: Mapped[str | None] = mapped_column(Text)
    raw_data: Mapped[dict[str, Any]] = mapped_column(JsonType)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    duplicate_of: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("jobs.id"), index=True)
    locations: Mapped[list[dict]] = mapped_column(JsonType, default=list, server_default="[]")
    missing_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consecutive_missing_syncs: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    required_min_years: Mapped[int | None] = mapped_column(Integer)
    required_max_years: Mapped[int | None] = mapped_column(Integer)
    preferred_min_years: Mapped[int | None] = mapped_column(Integer)
    preferred_max_years: Mapped[int | None] = mapped_column(Integer)
    requirement_type: Mapped[str] = mapped_column(
        String(30), default="unspecified", server_default="unspecified"
    )
    experience_category: Mapped[str] = mapped_column(
        String(30), default="unspecified", server_default="unspecified", index=True
    )
    experience_confidence: Mapped[float] = mapped_column(
        Numeric(4, 3), default=0, server_default="0"
    )
    experience_evidence: Mapped[list[dict]] = mapped_column(
        JsonType, default=list, server_default="[]"
    )
    score_evidence: Mapped[list[dict]] = mapped_column(JsonType, default=list, server_default="[]")
    classification_confidence: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    classification_conflict: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false()
    )
    conflict_reasons: Mapped[list[str]] = mapped_column(JsonType, default=list, server_default="[]")
    detected_skills: Mapped[list[str]] = mapped_column(JsonType, default=list, server_default="[]")
    matching_version: Mapped[str | None] = mapped_column(String(30))
    remote_us_only: Mapped[bool | None] = mapped_column(Boolean)
    remote_states: Mapped[list[str]] = mapped_column(JsonType, default=list, server_default="[]")
    excluded_states: Mapped[list[str]] = mapped_column(JsonType, default=list, server_default="[]")
    timezone_requirement: Mapped[str | None] = mapped_column(String(250))
    remote_restriction_evidence: Mapped[list[str]] = mapped_column(
        JsonType, default=list, server_default="[]"
    )


class JobLocation(Base):
    __tablename__ = "job_locations"
    __table_args__ = (Index("ix_job_locations_filter", "country", "state", "job_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    location_raw: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(200))
    state: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str | None] = mapped_column(String(2))


class JobSkill(Base):
    __tablename__ = "job_skills"
    __table_args__ = (Index("ix_job_skills_filter", "skill", "job_id"),)
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True
    )
    skill: Mapped[str] = mapped_column(String(50), primary_key=True)


class SourceSync(Base):
    __tablename__ = "source_syncs"
    __table_args__ = (Index("ix_source_syncs_history", "source_id", "started_at"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("job_sources.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="running")
    jobs_fetched: Mapped[int] = mapped_column(Integer, default=0)
    jobs_created: Mapped[int] = mapped_column(Integer, default=0)
    jobs_updated: Mapped[int] = mapped_column(Integer, default=0)
    jobs_unchanged: Mapped[int] = mapped_column(Integer, default=0)
    jobs_skipped: Mapped[int] = mapped_column(Integer, default=0)
    jobs_failed: Mapped[int] = mapped_column(Integer, default=0)
    jobs_closed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    request_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    request_latency_ms: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    failed_requests: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    rate_limit_responses: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    upsert_duration_ms: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
