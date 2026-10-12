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
