import json
from pathlib import Path

import httpx
import pytest
from sqlalchemy import func, select

from collectors.ashby import AshbyCollector
from collectors.greenhouse import GreenhouseCollector
from collectors.lever import LeverCollector
from collectors.runner import sync_source
from services.api.app.models.job import Job, JobSource

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize(
    "name,cls",
    [("greenhouse", GreenhouseCollector), ("lever", LeverCollector), ("ashby", AshbyCollector)],
)
def test_provider_normalization_and_idempotent_sync(name, cls, db):
    payload = json.loads((FIXTURES / f"{name}.json").read_text())
    with httpx.Client(
        transport=httpx.MockTransport(lambda req: httpx.Response(200, json=payload))
    ) as c:
        collector = cls("demo", "Demo Company A", client=c, sleep=lambda _: None)
        first = sync_source(db, collector)
        job = db.scalar(select(Job))
        discovered = job.first_seen_at
        second = sync_source(db, collector)
    assert first.created == 1 and second.unchanged == 1 and second.updated == 0
    assert db.scalar(select(func.count()).select_from(Job)) == 1
    assert job.first_seen_at == discovered
    assert job.country == "US"
    assert job.experience_max_years == 2
    assert job.raw_data
    if name == "greenhouse":
        assert job.posted_at is None  # updated_at must not masquerade as publication.
        assert job.source_updated_at is not None
    else:
        assert job.salary_min is not None


def test_partial_failure_does_not_poison_transaction(db):
    payload = json.loads((FIXTURES / "greenhouse.json").read_text())
    payload["jobs"].insert(0, {"id": "broken"})
    with httpx.Client(
        transport=httpx.MockTransport(lambda req: httpx.Response(200, json=payload))
    ) as c:
        result = sync_source(db, GreenhouseCollector("demo", "Demo Company A", c, lambda _: None))
    assert result.failures == 1 and result.created == 1
    source = db.scalar(select(JobSource))
    assert source.last_sync_attempt is not None
    assert source.last_successful_sync is None
    assert source.last_error


def test_network_failure_does_not_close_existing_jobs(db):
    payload = json.loads((FIXTURES / "greenhouse.json").read_text())
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=payload) if len(calls) == 1 else httpx.Response(503)

    with httpx.Client(transport=httpx.MockTransport(handler)) as c:
        collector = GreenhouseCollector("demo", "Demo Company A", c, lambda _: None)
        sync_source(db, collector)
        result = sync_source(db, collector)
    assert result.failures == 1
    assert len(calls) == 5
    assert db.scalar(select(Job)).is_active


def test_rate_limit_retry():
    calls = []

    def handler(request):
        calls.append(request)
        return (
            httpx.Response(429, headers={"Retry-After": "1"})
            if len(calls) == 1
            else httpx.Response(200, json={"jobs": []})
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as c:
        assert GreenhouseCollector("demo", "Demo", c, lambda _: None).fetch() == []
    assert len(calls) == 2


def test_lever_pagination():
    offsets = []

    def handler(request):
        skip = int(request.url.params["skip"])
        offsets.append(skip)
        return httpx.Response(
            200, json=[{"id": str(skip + i)} for i in range(100 if skip == 0 else 1)]
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as c:
        assert len(LeverCollector("demo", "Demo", c, lambda _: None).fetch()) == 101
    assert offsets == [0, 100]


def test_unlisted_ashby_and_prospect_greenhouse_are_skipped():
    with httpx.Client() as c:
        assert AshbyCollector("demo", "Demo", c).normalize({"isListed": False}) is None
        assert GreenhouseCollector("demo", "Demo", c).normalize({"internal_job_id": None}) is None


def test_collector_rejects_urls_as_board_identifiers():
    with pytest.raises(ValueError):
        GreenhouseCollector("https://example.com", "Demo")
