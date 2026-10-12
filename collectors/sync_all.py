import argparse
import json
import logging
import time
from collections import defaultdict
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import asdict
from uuid import UUID

from sqlalchemy import select

from collectors.lifecycle import expire_deadlines
from collectors.locking import write_lock
from collectors.providers import PROVIDERS, make_collector
from collectors.runner import SyncResult, sync_source
from matching.scoring import score_job
from services.api.app.core.config import get_settings
from services.api.app.core.logging import configure_logging
from services.api.app.db.maintenance import refresh_sqlite_statistics
from services.api.app.db.session import SessionLocal, utcnow
from services.api.app.models.job import IngestionRun, JobSource

logger = logging.getLogger(__name__)


def dry_run_source(db, collector):
    result = SyncResult(status="dry_run")
    started = time.monotonic()
    try:
        rows = collector.fetch()
        result.fetched = len(rows)
        for row in rows:
            try:
                data = collector.normalize(row)
                if data is None:
                    result.skipped += 1
                else:
                    score_job(data.title, data.description)
                    result.validated += 1
            except Exception:
                result.failures += 1
        if result.failures or not collector.snapshot_complete:
            result.status = "partial"
    except Exception as exc:
        logger.warning("dry_run_failed", extra={"error_type": type(exc).__name__})
        result.status = "failed"
        result.failures += 1
    result.duration_seconds = round(time.monotonic() - started, 3)
    for key in ("request_count", "request_latency_ms", "failed_requests", "rate_limit_responses"):
        setattr(result, key, getattr(collector, key))
    return result


def sync_one(source_id: UUID, dry_run=False) -> SyncResult:
    with SessionLocal() as db:
        source = db.get(JobSource, source_id)
        if source is None:
            raise ValueError("Source not found")
        if source.source_type not in PROVIDERS:
            raise ValueError("This source has no automated collector")
        collector = make_collector(
            source.source_type,
            source.board_identifier,
            source.company_name or source.name,
            source.provider_config,
        )
        try:
            return dry_run_source(db, collector) if dry_run else sync_source(db, collector)
        finally:
            collector.close()


def _sync_all(provider=None, dry_run=False, limit=None, concurrency=None) -> dict:
    started = time.monotonic()
    with SessionLocal() as db:
        query = select(JobSource.id, JobSource.source_type)
        query = query.where(JobSource.enabled.is_(True), JobSource.source_type.in_(PROVIDERS))
        if provider:
            query = query.where(JobSource.source_type == provider)
        records = db.execute(query.order_by(JobSource.source_type, JobSource.name)).all()
    if limit:
        records = records[:limit]
    groups = defaultdict(list)
    for identity, kind in records:
        groups[kind].append(identity)
    # Interleave providers so a long employer queue cannot starve another provider.
    records = [
        (groups[kind][index], kind)
        for index in range(max((len(v) for v in groups.values()), default=0))
        for kind in groups
        if index < len(groups[kind])
    ]
    settings = get_settings()
    workers = concurrency or settings.collector_max_concurrency
    if not 1 <= workers <= 12:
        raise ValueError("Concurrency must be 1–12")
    provider_limits = {
        kind: max(1, min(workers, settings.collector_provider_concurrency.get(kind, workers)))
        for kind in groups
    }

    def execute(record):
        source_id, kind = record
        try:
            result = sync_one(source_id, dry_run=True) if dry_run else sync_one(source_id)
        except Exception as exc:
            logger.error(
                "source_unavailable",
                extra={"source_id": str(source_id), "error_type": type(exc).__name__},
            )
            result = SyncResult(status="failed", failures=1)
        return {"source_id": str(source_id), "provider": kind, **asdict(result)}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        queued, running, results = list(records), {}, []
        active = defaultdict(int)
        while queued or running:
            while len(running) < workers:
                eligible = next(
                    (
                        index
                        for index, (_, kind) in enumerate(queued)
                        if active[kind] < provider_limits[kind]
                    ),
                    None,
                )
                if eligible is None:
                    break
                record = queued.pop(eligible)
                active[record[1]] += 1
                running[pool.submit(execute, record)] = record[1]
            completed, _ = wait(running, return_when=FIRST_COMPLETED)
            for future in completed:
                active[running.pop(future)] -= 1
                results.append(future.result())
        source_order = {str(identity): index for index, (identity, _) in enumerate(records)}
        results.sort(key=lambda row: source_order[row["source_id"]])
    expired = 0
    maintenance_error = None
    if not dry_run:
        try:
            with SessionLocal() as db:
                write_lock(db)
                expired = expire_deadlines(db, utcnow())
                db.commit()
                refresh_sqlite_statistics(db)
        except Exception as exc:
            maintenance_error = type(exc).__name__
            logger.warning("post_sync_maintenance_failed", extra={"error_type": type(exc).__name__})
    provider_results = []
    for kind in groups:
        runs = [row for row in results if row["provider"] == kind]
        requests = sum(row["request_count"] for row in runs)
        latency = sum(row["request_latency_ms"] for row in runs)
        provider_results.append(
            {
                "provider": kind,
                "sources": len(runs),
                "successful": sum(row["status"] in {"success", "dry_run"} for row in runs),
                **{
                    key: sum(row[key] for row in runs)
                    for key in (
                        "fetched",
                        "created",
                        "updated",
                        "unchanged",
                        "validated",
                        "failures",
                        "request_count",
                        "failed_requests",
                        "rate_limit_responses",
                        "upsert_duration_ms",
                    )
                },
                "average_request_latency_ms": round(latency / requests, 2) if requests else None,
            }
        )
    summary = {
        "dry_run": dry_run,
        "concurrency": workers,
        "jobs_expired": expired,
        "maintenance_error_type": maintenance_error,
        "sources_attempted": len(records),
        "sources_successful": sum(r["status"] in {"success", "dry_run"} for r in results),
        "sources_failed": sum(r["status"] == "failed" for r in results),
        "sources_partial": sum(r["status"] == "partial" for r in results),
        "sources_skipped": sum(r["status"] in {"busy", "disabled", "cooldown"} for r in results),
        **{
            f"jobs_{key}": sum(r[key] for r in results)
            for key in (
                "fetched",
                "created",
                "updated",
                "unchanged",
                "validated",
                "skipped",
                "failures",
                "closed",
            )
        },
        "duration_seconds": round(time.monotonic() - started, 3),
        "providers": provider_results,
        "sources": results,
    }
    summary["status"] = (
        "failed"
        if results and summary["sources_failed"] == len(results)
        else "partial"
        if summary["sources_failed"]
        or summary["sources_partial"]
        or summary["sources_skipped"]
        or maintenance_error
        else "success"
    )
    return summary


def sync_all(provider=None, dry_run=False, limit=None, concurrency=None):
    if dry_run:
        return _sync_all(provider, dry_run, limit, concurrency)
    with SessionLocal() as db:
        run = IngestionRun(summary={"provider_filter": provider})
        db.add(run)
        db.commit()
        identity = run.id
    try:
        summary = _sync_all(provider, dry_run, limit, concurrency)
    except Exception as exc:
        with SessionLocal() as db:
            run = db.get(IngestionRun, identity)
            run.status = "failed"
            run.completed_at = utcnow()
            run.summary = {"error_type": type(exc).__name__, "provider_filter": provider}
            db.commit()
        raise
    with SessionLocal() as db:
        run = db.get(IngestionRun, identity)
        run.completed_at = utcnow()
        run.status = summary["status"]
        run.summary = {
            **{k: v for k, v in summary.items() if k != "sources"},
            "provider_filter": provider,
        }
        db.commit()
    summary["run_id"] = str(identity)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Synchronize every enabled employer board")
    parser.add_argument("--output", help="Optional JSON run summary file")
    parser.add_argument("--provider", choices=PROVIDERS)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--concurrency", type=int)
    args = parser.parse_args()
    configure_logging(get_settings().log_level)
    summary = sync_all(args.provider, args.dry_run, args.limit, args.concurrency)
    if args.output:
        from pathlib import Path

        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(
        "GradJobs Sync Complete\n"
        + json.dumps({k: v for k, v in summary.items() if k != "sources"}, indent=2)
    )
    raise SystemExit(1 if summary["status"] in {"failed", "partial"} else 0)


if __name__ == "__main__":
    main()
