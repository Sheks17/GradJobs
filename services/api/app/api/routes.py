from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from services.api.app.db.session import get_db
from services.api.app.models.job import IngestionRun, Job, JobSource
from services.api.app.repositories.jobs import list_jobs, statistics, visible_conditions
from services.api.app.schemas.jobs import JobDetail, JobFilters, JobPage, SourceOut, Stats

router = APIRouter()
Database = Annotated[Session, Depends(get_db)]


@router.get("/health")
def health(db: Database):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database unavailable") from None
    return {"status": "ok", "database": "ok"}


@router.get("/jobs", response_model=JobPage)
def jobs(db: Database, filters: Annotated[JobFilters, Query()]):
    return list_jobs(db, filters)


@router.get("/jobs/{job_id}", response_model=JobDetail)
def job_detail(job_id: UUID, db: Database):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/companies")
def companies(db: Database):
    rows = db.execute(
        select(Job.company_slug, func.min(Job.company_name), func.count(Job.id))
        .where(*visible_conditions())
        .group_by(Job.company_slug)
        .order_by(func.min(Job.company_name))
    ).all()
    return [{"slug": slug, "name": name, "active_jobs": count} for slug, name, count in rows]


@router.get("/sources", response_model=list[SourceOut])
def sources(db: Database, limit: int = Query(500, ge=1, le=1000), offset: int = Query(0, ge=0)):
    return db.scalars(
        select(JobSource).order_by(JobSource.name, JobSource.id).offset(offset).limit(limit)
    ).all()


@router.get("/stats", response_model=Stats)
def stats(db: Database):
    return statistics(db)


@router.get("/stats/providers")
def provider_stats(db: Database):
    from services.api.app.repositories.providers import provider_statistics

    return provider_statistics(db)


@router.get("/stats/ats")
def ats_capabilities(db: Session = Depends(get_db)):
    from services.api.app.repositories.providers import ats_statistics

    return ats_statistics(db)


@router.get("/metadata")
def metadata():
    from matching.aliases import ROLE_FAMILIES
    from matching.skills import SKILL_ALIASES

    return {"role_families": ROLE_FAMILIES, "skills": list(SKILL_ALIASES)}


@router.get("/ingestion")
def ingestion(db: Database, limit: int = Query(20, ge=1, le=100)):
    # Read-only operational summaries contain counters, not credentials or raw payloads.
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    runs = db.scalars(
        select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(limit)
    ).all()
    return {
        "history": [
            {
                "id": str(run.id),
                "started_at": run.started_at,
                "completed_at": run.completed_at,
                "status": run.status,
                "summary": run.summary,
            }
            for run in runs
        ],
        "healthy_sources": db.scalar(
            select(func.count())
            .select_from(JobSource)
            .where(
                JobSource.enabled.is_(True),
                JobSource.last_error.is_(None),
                JobSource.last_successful_sync.is_not(None),
            )
        ),
        "failing_sources": db.scalar(
            select(func.count()).select_from(JobSource).where(JobSource.last_error.is_not(None))
        ),
        "jobs_created_today": db.scalar(
            select(func.count()).select_from(Job).where(Job.first_seen_at >= today)
        ),
        "jobs_updated_today": db.scalar(
            select(func.count()).select_from(Job).where(Job.updated_at >= today)
        ),
    }
