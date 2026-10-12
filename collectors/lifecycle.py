from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from services.api.app.core.config import get_settings
from services.api.app.models.job import Job


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def expire_deadlines(db, now):
    """Retain postings whose source-supplied deadline has elapsed."""
    count = 0
    for job in db.scalars(select(Job).where(Job.is_active.is_(True), Job.closing_at <= now)):
        job.is_active = False
        job.closed_at = job.closed_at or now
        count += 1
    db.flush()
    promote_active_aliases(db)
    return count


def reconcile_missing(db: Session, source_id, seen: set[str], now: datetime) -> int:
    """Call only after a complete, fully validated snapshot."""
    settings = get_settings()
    closed = 0
    for job in db.scalars(select(Job).where(Job.source_id == source_id, Job.is_active.is_(True))):
        if job.source_job_id in seen:
            continue
        job.missing_since = job.missing_since or now
        job.consecutive_missing_syncs += 1
        elapsed = now - utc(job.missing_since)
        if job.consecutive_missing_syncs >= settings.stale_missing_syncs or (
            job.consecutive_missing_syncs >= 2
            and elapsed >= timedelta(hours=settings.stale_after_hours)
        ):
            job.is_active = False
            job.closed_at = now
            closed += 1
    db.flush()
    promote_active_aliases(db)
    return closed


def promote_active_aliases(db: Session) -> None:
    """Keep a surviving source visible when its canonical posting closes."""
    alias = aliased(Job)
    surviving_canonical_ids = (
        select(alias.duplicate_of)
        .where(alias.duplicate_of.is_not(None), alias.is_active.is_(True))
        .distinct()
    )
    for canonical in db.scalars(
        select(Job).where(
            Job.is_active.is_(False),
            Job.duplicate_of.is_(None),
            Job.id.in_(surviving_canonical_ids),
        )
    ):
        aliases = db.scalars(
            select(Job)
            .where(Job.duplicate_of == canonical.id, Job.is_active.is_(True))
            .order_by(Job.first_seen_at, Job.id)
        ).all()
        if aliases:
            replacement = aliases[0]
            replacement.duplicate_of = None
            for alias in aliases[1:]:
                alias.duplicate_of = replacement.id
            canonical.duplicate_of = replacement.id
