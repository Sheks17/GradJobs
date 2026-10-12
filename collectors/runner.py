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


def observe_unchanged(db, identities):
    for offset in range(0, len(identities), 500):
        db.execute(
            update(Job)
            .where(Job.id.in_(identities[offset : offset + 500]))
            .values(
                last_seen_at=utcnow(),
                missing_since=None,
                consecutive_missing_syncs=0,
                updated_at=Job.updated_at,
            )
        )
    identities.clear()


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


def posting_unchanged(existing, data):
    if not existing or not existing.is_active or existing.matching_version != MATCHING_VERSION:
        return False
    fields = data.model_dump(
        exclude={
            "remote_us_only",
            "remote_states",
            "excluded_states",
            "timezone_requirement",
            "remote_restriction_evidence",
        }
    )
    for key, value in fields.items():
        stored = getattr(existing, key)
        if key in {"posted_at", "closing_at"} and value is None:
            continue  # Preserve a previously supplied date when the provider omits it.
        if key in {"posted_at", "closing_at", "source_updated_at"} and stored and value:
            stored, value = utc(stored), utc(value)
        if stored != value:
            return False
    return True


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
    committed = {key: 0 for key in ("created", "updated", "unchanged")}
    try:
        if collector.source_type == "workday":
            for raw in db.scalars(select(Job.raw_data).where(Job.source_id == source_id)):
                if isinstance(raw, dict) and isinstance(raw.get("listing"), dict):
                    path = raw["listing"].get("externalPath")
                    if path:
                        collector.detail_cache[path] = raw
            db.rollback()  # Never hold a database transaction while retrieving HTTP details.
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
            if index and index % 100 == 0:
                observe_unchanged(db, observed_unchanged)
                source.lease_expires_at = utcnow() + timedelta(
                    minutes=settings.source_lease_minutes
                )
                current_history = db.get(SourceSync, history_id)
                for key in ("fetched", "created", "updated", "unchanged", "skipped"):
                    setattr(current_history, f"jobs_{key}", getattr(result, key))
                current_history.jobs_failed = result.failures
                db.commit()
                committed = {key: getattr(result, key) for key in committed}
                write_lock(db)
                db.refresh(source)
                if source.sync_token != token:
                    raise RuntimeError("Worker lease lost between batches")
            try:
                data = collector.normalize(raw)
                if data is None:
                    result.skipped += 1
                    continue
                if data.source_job_id in seen:
                    raise ValueError("Duplicate posting ID in source snapshot")
                seen.add(data.source_job_id)
                existing = existing_jobs.get(data.source_job_id)
                unchanged = posting_unchanged(existing, data)
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
        observe_unchanged(db, observed_unchanged)
        result.upsert_duration_ms = int((time.monotonic() - upsert_started) * 1000)
        if result.failures or not collector.snapshot_complete:
            result.status = "partial"
            error = f"{result.failures} posting(s) failed; closure reconciliation skipped"
        else:
            result.closed = reconcile_missing(db, source_id, seen, utcnow())
            result.status = "success"
    except Exception as exc:
        db.rollback()
        for key, value in committed.items():
            setattr(result, key, value)
        result.closed = 0
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
        # Earlier validated batches remain committed after a worker failure.
        # Closure reconciliation and final history are committed only after the snapshot.
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
