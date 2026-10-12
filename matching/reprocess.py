"""Recompute derived fields only, in atomic batches; no employer requests."""

import argparse
import json
import time
from contextlib import ExitStack
from decimal import Decimal
from pathlib import Path

import httpx
from sqlalchemy import delete, select

from collectors.locking import write_lock
from collectors.normalizers.location import location_fields, remote_restrictions
from collectors.providers import PROVIDERS
from matching.role_classifier import classify_role
from matching.scoring import MATCHING_VERSION, score_job
from services.api.app.db.maintenance import refresh_sqlite_statistics
from services.api.app.db.session import SessionLocal
from services.api.app.models.job import Job, JobLocation, JobSource
from services.api.app.repositories.ingestion import replace_skills

LOCATION_KEYS = ("location_raw", "city", "state", "country", "remote_type", "locations")


def derived_fields(job: Job, collector=None) -> dict:
    normalized = collector.normalize(job.raw_data) if collector and job.raw_data else None
    if normalized:
        location = {key: getattr(normalized, key) for key in LOCATION_KEYS}
    else:
        location = location_fields(
            job.location_raw,
            job.remote_type if job.remote_type != "unknown" else None,
            job.country,
            job.city,
            job.state,
            additional=job.locations[1:] if job.locations else [],
        )
    return {
        **score_job(job.title, job.description).to_dict(),
        **location,
        **remote_restrictions(job.location_raw or "", job.description),
    }


def apply_fields(db, job: Job, fields: dict) -> None:
    for key, value in fields.items():
        setattr(job, key, value)
    db.execute(delete(JobLocation).where(JobLocation.job_id == job.id))
    locations = fields["locations"] or [
        {key: fields[key] for key in ("location_raw", "city", "state", "country")}
    ]
    db.add_all([JobLocation(job_id=job.id, **loc) for loc in locations])
    replace_skills(db, job)


def reprocess(
    db, *, dry_run=False, source=None, batch_size=250, limit=None, changed_roles_only=False
) -> dict:
    started = time.monotonic()
    processed = changed = failed = 0
    skipped = 0
    errors = []
    cursor = None
    with ExitStack() as stack:
        # A client is constructed for adapter normalization only: transport forbids network.
        def forbidden(request):
            raise RuntimeError("Reprocessing must never perform HTTP requests")

        client = stack.enter_context(httpx.Client(transport=httpx.MockTransport(forbidden)))
        sources = {row.id: row for row in db.scalars(select(JobSource))}
        collectors = {
            key: PROVIDERS[row.source_type](
                row.board_identifier, row.company_name or row.name, client=client
            )
            for key, row in sources.items()
            if row.source_type in PROVIDERS
        }
        db.commit()
        while True:
            if not dry_run:
                write_lock(db)
            query = (
                select(Job)
                .order_by(Job.id)
                .limit(min(batch_size, limit - processed) if limit else batch_size)
            )
            if source:
                query = query.where(Job.source == source)
            if cursor:
                query = query.where(Job.id > cursor)
            jobs = db.scalars(query).all()
            if not jobs:
                db.rollback()
                break
            for job in jobs:
                if (
                    changed_roles_only
                    and job.matching_version == MATCHING_VERSION
                    and classify_role(job.title) == job.role_family
                ):
                    processed += 1
                    skipped += 1
                    continue
                try:
                    fields = derived_fields(job, collectors.get(job.source_id))
                    different = any(
                        (float(current) if isinstance(current, Decimal) else current) != value
                        for key, value in fields.items()
                        for current in [getattr(job, key)]
                    )
                    if not dry_run:
                        with db.begin_nested():
                            apply_fields(db, job, fields)
                    changed += different
                except Exception as exc:
                    failed += 1
                    errors.append({"job_id": str(job.id), "error_type": type(exc).__name__})
                processed += 1
            cursor = jobs[-1].id
            if dry_run:
                db.rollback()
            else:
                db.commit()
            db.expunge_all()
            if limit and processed >= limit:
                break
    refreshed = refresh_sqlite_statistics(db) if not dry_run else False
    return {
        "version": MATCHING_VERSION,
        "dry_run": dry_run,
        "processed": processed,
        "changed": changed,
        "failed": failed,
        "skipped_unchanged_roles": skipped,
        "planner_statistics_refreshed": refreshed,
        "errors": errors,
        "duration_seconds": round(time.monotonic() - started, 3),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--source", choices=["greenhouse", "lever", "ashby", "manual"])
    parser.add_argument("--batch-size", type=int, default=250)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--changed-roles-only", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.batch_size < 1 or (args.limit is not None and args.limit < 1):
        parser.error("batch-size and limit must be positive")
    with SessionLocal() as db:
        result = reprocess(
            db,
            dry_run=args.dry_run,
            source=args.source,
            batch_size=args.batch_size,
            limit=args.limit,
            changed_roles_only=args.changed_roles_only,
        )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if result["failed"] else 0)


if __name__ == "__main__":
    main()
