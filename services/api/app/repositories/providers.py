"""Provider health and request costs from the latest attempt per configured source."""

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import load_only

from collectors.ats_registry import ATS_REGISTRY
from collectors.providers import PROVIDERS
from services.api.app.models.job import Job, JobSource, SourceSync
from services.api.app.schemas.jobs import ensure_utc


def provider_statistics(db):
    sources = db.scalars(
        select(JobSource).options(
            load_only(
                JobSource.id,
                JobSource.name,
                JobSource.source_type,
                JobSource.company_name,
                JobSource.enabled,
                JobSource.last_successful_sync,
                JobSource.last_error,
                raiseload=True,
            )
        )
    ).all()
    ranked = select(
        SourceSync.id,
        func.row_number()
        .over(
            partition_by=SourceSync.source_id,
            order_by=(SourceSync.started_at.desc(), SourceSync.id),
        )
        .label("position"),
    ).subquery()
    latest = db.scalars(
        select(SourceSync)
        .options(
            load_only(
                SourceSync.id,
                SourceSync.source_id,
                SourceSync.jobs_fetched,
                SourceSync.jobs_created,
                SourceSync.jobs_updated,
                SourceSync.request_count,
                SourceSync.request_latency_ms,
                SourceSync.failed_requests,
                SourceSync.rate_limit_responses,
                SourceSync.upsert_duration_ms,
                raiseload=True,
            )
        )
        .join(ranked, SourceSync.id == ranked.c.id)
        .where(ranked.c.position == 1)
    ).all()
    histories = {row.source_id: row for row in latest}
    active = dict(
        db.execute(
            select(Job.source, func.count())
            .where(Job.is_active.is_(True), Job.duplicate_of.is_(None), Job.is_demo.is_(False))
            .group_by(Job.source)
        ).all()
    )
    output = []
    for provider in PROVIDERS:
        group = [source for source in sources if source.source_type == provider]
        runs = [histories[source.id] for source in group if source.id in histories]
        requests = sum(run.request_count for run in runs)
        successes = [
            ensure_utc(source.last_successful_sync)
            for source in group
            if source.last_successful_sync
        ]
        output.append(
            {
                "provider": provider,
                "access_classification": ATS_REGISTRY[provider]["ingestion_status"],
                "detection_supported": ATS_REGISTRY[provider]["source_discovery_supported"],
                "ingestion_supported": True,
                "verified_employers": len(
                    {
                        source.company_name.casefold()
                        for source in group
                        if source.enabled and source.company_name and source.last_successful_sync
                    }
                )
                if provider != "usajobs"
                else 0,
                "sources": len(group),
                "enabled_sources": sum(source.enabled for source in group),
                "healthy": sum(
                    source.enabled and bool(source.last_successful_sync) and not source.last_error
                    for source in group
                ),
                "failing": sum(source.enabled and bool(source.last_error) for source in group),
                "active_jobs": active.get(provider, 0),
                "jobs_fetched": sum(run.jobs_fetched for run in runs),
                "jobs_created": sum(run.jobs_created for run in runs),
                "jobs_updated": sum(run.jobs_updated for run in runs),
                "request_count": requests,
                "average_request_latency_ms": round(
                    sum(run.request_latency_ms for run in runs) / requests, 2
                )
                if requests
                else None,
                "failed_requests": sum(run.failed_requests for run in runs),
                "rate_limit_responses": sum(run.rate_limit_responses for run in runs),
                "upsert_duration_ms": sum(run.upsert_duration_ms for run in runs),
                "last_successful_sync": max(successes).isoformat() if successes else None,
                "recent_errors": [
                    {"source": source.name, "error": source.last_error}
                    for source in group
                    if source.last_error
                ][:5],
                "capabilities": PROVIDERS[provider].capabilities,
                "metrics_scope": (
                    "Latest sync attempt per source; active jobs exclude "
                    "duplicate aliases across all countries"
                ),
            }
        )
    return output


def ats_statistics(db):
    available = True
    try:
        statistics = {row["provider"]: row for row in provider_statistics(db)}
    except SQLAlchemyError:
        db.rollback()
        available = False
        statistics = {}
    return [
        {
            **record,
            "provider": provider,
            "ingestion_supported": provider in PROVIDERS,
            "detection_supported": record["source_discovery_supported"],
            "database_available": available,
            "verified_employers": 0 if available else None,
            "active_jobs": 0 if available else None,
            "last_successful_sync": None,
            "healthy": 0 if available else None,
            "failing": 0 if available else None,
            **statistics.get(provider, {}),
        }
        for provider, record in ATS_REGISTRY.items()
    ]
