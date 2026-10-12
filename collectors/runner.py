import logging
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import timedelta

from sqlalchemy import func, select, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from collectors.base import Collector
from collectors.lifecycle import reconcile_missing, utc
from collectors.locking import write_lock
from collectors.providers import CAREERS
from matching.scoring import MATCHING_VERSION
from services.api.app.core.config import get_settings
from services.api.app.db.session import utcnow
from services.api.app.models.job import Job, JobSource, SourceSync
from services.api.app.repositories.ingestion import upsert_job

logger = logging.getLogger(__name__)


def upsert_with_retry(db, source_id, data):
    for attempt in range(3):
        try:
            with db.begin_nested():
                return upsert_job(db, source_id, data)
        except OperationalError as exc:
            # Retry only transaction-safe transient errors after savepoint rollback.
            code = getattr(exc.orig, "sqlstate", None)
            if code not in {"40001", "40P01", "55P03"} or attempt == 2:
                raise
            time.sleep(0.1 * 2**attempt)
    raise RuntimeError("Database retry budget exhausted")


@dataclass
class SyncResult:
    fetched: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped: int = 0
    failures: int = 0
    closed: int = 0
    status: str = "running"
    duration_seconds: float = 0
    request_count: int = 0
    request_latency_ms: int = 0
    failed_requests: int = 0
    rate_limit_responses: int = 0
    upsert_duration_ms: int = 0
    validated: int = 0


def sync_source(db: Session, collector: Collector) -> SyncResult:
    result = SyncResult()
    for key in ("request_count", "request_latency_ms", "failed_requests", "rate_limit_responses"):
        setattr(collector, key, 0)
    started = time.monotonic()
    now = utcnow()
    db.commit()
    write_lock(db)
    source = db.scalar(
        select(JobSource).where(
            JobSource.source_type == collector.source_type,
            JobSource.board_identifier == collector.board,
        )
    )
    if source is None:
        source = JobSource(
            name=f"{collector.company} · {collector.source_type}",
            source_type=collector.source_type,
            board_identifier=collector.board,
            company_name=collector.company,
            base_url=collector.endpoint.format(board=collector.board),
            careers_url=getattr(collector, "careers_url", None)
            or CAREERS[collector.source_type].format(board=collector.board),
            provider_config=collector.config,
        )
        db.add(source)
        db.flush()
    if not source.enabled:
        db.rollback()
        result.status = "disabled"
        return result
    settings = get_settings()
    if (
        source.failure_count >= settings.source_failure_threshold
        and source.last_error_at
        and utc(source.last_error_at) + timedelta(minutes=settings.source_cooldown_minutes) > now
    ):
        db.rollback()
        result.status = "cooldown"
        return result
    if source.sync_token and source.lease_expires_at and utc(source.lease_expires_at) > now:
        db.rollback()
        result.status = "busy"
        return result
    source_id = source.id
    db.execute(
        update(SourceSync)
        .where(SourceSync.source_id == source_id, SourceSync.status == "running")
        .values(status="interrupted", completed_at=now, error_message="Worker lease expired")
    )
    token = uuid.uuid4()
    source.sync_token = token
    source.lease_expires_at = now + timedelta(minutes=get_settings().source_lease_minutes)
    source.last_sync_attempt = now
    history = SourceSync(source_id=source_id, started_at=now)
    db.add(history)
    db.commit()
    history_id = history.id
    logger.info(
        "source_started", extra={"provider": collector.source_type, "board": collector.board}
    )
    error = None
    try:
        rows = collector.fetch()
        result.fetched = len(rows)
        write_lock(db)
        db.refresh(source)
        if source.sync_token != token:
            raise RuntimeError("Worker lease lost")
        seen: set[str] = set()
        existing_jobs = {
            job.source_job_id: job
            for job in db.scalars(select(Job).where(Job.source_id == source_id))
        }
        observed_unchanged = []
        upsert_started = time.monotonic()
        for index, raw in enumerate(rows):
            try:
                data = collector.normalize(raw)
                if data is None:
                    result.skipped += 1
                    continue
                if data.source_job_id in seen:
                    raise ValueError("Duplicate posting ID in source snapshot")
                seen.add(data.source_job_id)
                existing = existing_jobs.get(data.source_job_id)
                unchanged = bool(
                    existing
                    and existing.is_active
                    and existing.matching_version == MATCHING_VERSION
                    and existing.raw_data == data.raw_data
                    and existing.company_name == data.company_name
                    and existing.title == data.title
                    and existing.description == data.description
                    and existing.source_url == data.source_url
                    and existing.apply_url == data.apply_url
                    and existing.remote_type == data.remote_type
                    and existing.provider_metadata == data.provider_metadata
                    and existing.locations == data.locations
                )
                if unchanged:
                    observed_unchanged.append(existing.id)
                    result.unchanged += 1
                    continue
                _, created = upsert_with_retry(db, source_id, data)
                if created:
                    result.created += 1
                else:
                    result.updated += 1
            except Exception as exc:
                result.failures += 1
                logger.warning(
                    "job_failed",
                    extra={
                        "row": index,
                        "board": collector.board,
                        "error_type": type(exc).__name__,
                    },
                )
        for offset in range(0, len(observed_unchanged), 500):
            db.execute(
                update(Job)
                .where(Job.id.in_(observed_unchanged[offset : offset + 500]))
                .values(
                    last_seen_at=utcnow(),
                    missing_since=None,
                    consecutive_missing_syncs=0,
                    updated_at=Job.updated_at,
                )
            )
        result.upsert_duration_ms = int((time.monotonic() - upsert_started) * 1000)
        if result.failures or not collector.snapshot_complete:
            result.status = "partial"
            error = f"{result.failures} posting(s) failed; closure reconciliation skipped"
        else:
            result.closed = reconcile_missing(db, source_id, seen, utcnow())
            result.status = "success"
    except Exception as exc:
        db.rollback()
        result.created = result.updated = result.unchanged = result.closed = 0
        result.failures += 1
        result.status = "failed"
        error = f"Sync failed: {type(exc).__name__}"
        logger.error(
            "source_failed", extra={"board": collector.board, "error_type": type(exc).__name__}
        )
    finally:
        result.duration_seconds = round(time.monotonic() - started, 3)
        for key in (
            "request_count",
            "request_latency_ms",
            "failed_requests",
            "rate_limit_responses",
        ):
            setattr(result, key, getattr(collector, key))
        # Successful data, lifecycle changes and history commit atomically.
        # Failed snapshots were rolled back and require a fresh metadata transaction.
        if not db.in_transaction():
            write_lock(db)
        db.refresh(source)
        if source.sync_token == token:
            source.sync_token = None
            source.lease_expires_at = None
            source.last_error = error
            source.failure_count = source.failure_count + 1 if error else 0
            if error:
                source.last_error_at = utcnow()
            source.disabled_reason = (
                "Repeated failures; review source. Automatic cooldown retries remain enabled."
                if source.failure_count >= settings.source_failure_threshold
                else None
            )
            if result.status == "success":
                source.last_successful_sync = utcnow()
            source.active_jobs = (
                db.scalar(
                    select(func.count())
                    .select_from(Job)
                    .where(Job.source_id == source_id, Job.is_active.is_(True))
                )
                or 0
            )
            history = db.get(SourceSync, history_id)
            history.status = result.status
            history.completed_at = utcnow()
            history.duration_ms = int(result.duration_seconds * 1000)
            history.error_message = error
            for key in ("fetched", "created", "updated", "unchanged", "skipped", "closed"):
                setattr(history, f"jobs_{key}", getattr(result, key))
            history.jobs_failed = result.failures
            for key in (
                "request_count",
                "request_latency_ms",
                "failed_requests",
                "rate_limit_responses",
                "upsert_duration_ms",
            ):
                setattr(history, key, getattr(result, key))
            db.commit()
        else:
            db.rollback()
        logger.info("source_finished", extra={"board": collector.board, "summary": asdict(result)})
    return result
