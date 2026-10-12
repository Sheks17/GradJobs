from datetime import timedelta
from uuid import UUID

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from collectors.runner import sync_source
from collectors.workday import WorkdayCollector, source_token, workday_config
from services.api.app.core.config import get_settings
from services.api.app.db.session import utcnow
from services.api.app.models.job import IngestionRun, JobSource


def test_repeated_failures_cool_down_without_deleting_source(db):
    config = workday_config("https://example.wd5.myworkdayjobs.com/en-US/External")
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    collector = WorkdayCollector(source_token(config), "Example", client, lambda _: None, config)
    threshold = get_settings().source_failure_threshold
    for _ in range(threshold):
        assert sync_source(db, collector).status == "failed"
    source = db.scalar(select(JobSource))
    assert source.failure_count == threshold and source.disabled_reason and source.enabled
    assert sync_source(db, collector).status == "cooldown"
    assert len(calls) == threshold
    source.last_error_at = utcnow() - timedelta(days=2)
    db.commit()
    assert sync_source(db, collector).status == "failed"
    assert len(calls) == threshold + 1
    client.close()


def test_run_summary_persists_success_and_failure(db, monkeypatch):
    import collectors.sync_all as module

    monkeypatch.setattr(module, "SessionLocal", lambda: Session(db.bind))
    monkeypatch.setattr(module, "_sync_all", lambda *args: {"status": "success", "jobs_fetched": 7})
    result = module.sync_all()
    run = db.get(IngestionRun, UUID(result["run_id"]))
    assert run.status == "success" and run.completed_at and run.summary["jobs_fetched"] == 7

    def failed(*args):
        raise RuntimeError("Test worker failure")

    monkeypatch.setattr(module, "_sync_all", failed)
    with pytest.raises(RuntimeError):
        module.sync_all()
    run = db.scalar(select(IngestionRun).where(IngestionRun.status == "failed"))
    assert run.completed_at and run.summary["error_type"] == "RuntimeError"


def test_retryable_database_failure_uses_savepoint(db, source, monkeypatch):
    import collectors.runner as module
    from tests.test_deduplication import data

    original = module.upsert_job
    calls = []

    class SerializationFailure(Exception):
        sqlstate = "40001"

    def flaky(*args):
        calls.append(1)
        if len(calls) == 1:
            raise OperationalError("redacted", {}, SerializationFailure())
        return original(*args)

    monkeypatch.setattr(module, "upsert_job", flaky)
    job, created = module.upsert_with_retry(db, source.id, data(source_job_id="1"))
    assert created and job.source_job_id == "1" and len(calls) == 2


def test_lifecycle_maintenance_failure_is_visible_in_run_status(db, monkeypatch):
    import collectors.sync_all as module

    monkeypatch.setattr(module, "SessionLocal", lambda: Session(db.bind))

    def unavailable(*args):
        raise OperationalError("redacted", {}, RuntimeError("Fixture failure"))

    monkeypatch.setattr(module, "expire_deadlines", unavailable)
    summary = module.sync_all()
    assert summary["status"] == "partial"
    assert summary["maintenance_error_type"] == "OperationalError"
    run = db.get(IngestionRun, UUID(summary["run_id"]))
    assert run.status == "partial" and run.summary["maintenance_error_type"] == "OperationalError"


def test_large_snapshots_release_writer_between_batches(db, monkeypatch):
    from sqlalchemy import event, func

    from collectors.greenhouse import GreenhouseCollector
    from services.api.app.models.job import Job, SourceSync
    from tests.test_deduplication import data

    collector = GreenhouseCollector("batch", "Fixture")
    monkeypatch.setattr(collector, "fetch", lambda: [{"id": index} for index in range(250)])
    monkeypatch.setattr(
        collector,
        "normalize",
        lambda row: data(
            source_job_id=str(row["id"]),
            source_url=f"https://example.com/batch/{row['id']}",
            apply_url=f"https://example.com/batch/{row['id']}",
        ),
    )
    commits = []
    event.listen(db, "after_commit", lambda _: commits.append(1))
    try:
        result = sync_source(db, collector)
        assert result.status == "success" and result.created == 250
        assert len(commits) >= 4  # Claim, two bounded batches, final reconciliation.
        assert db.scalar(select(func.count()).select_from(Job)) == 250
        history = db.scalar(select(SourceSync))
        assert history.status == "success" and history.jobs_created == 250
    finally:
        collector.close()
