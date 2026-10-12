import copy
import json

import httpx
import pytest
from sqlalchemy import select

from collectors.runner import sync_source
from collectors.workday import WorkdayCollector, source_token, workday_config
from services.api.app.models.job import Job

CONFIG = workday_config("https://example.wd12.myworkdayjobs.com/en-US/External")
DETAIL = {
    "jobPostingInfo": {
        "id": "stable-id",
        "title": "Software Engineer I",
        "jobReqId": "R1",
        "jobDescription": "<p>Python developer. No experience required.</p>",
        "location": "US, TX, Austin",
        "additionalLocations": ["US, CA, Remote"],
        "startDate": "2026-10-12",
        "timeType": "Full time",
        "jobRequisitionLocation": {"country": {"alpha2Code": "US"}},
    }
}


def collector(handler):
    return WorkdayCollector(
        source_token(CONFIG),
        "Example",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=lambda _: None,
        config=CONFIG,
    )


def test_workday_configuration_and_no_guesses():
    assert CONFIG["tenant"] == "example" and CONFIG["site"] == "External"
    assert "wd12" in source_token(CONFIG)
    for url in [
        "https://example.wd5.myworkdayjobs.com",
        "http://example.wd5.myworkdayjobs.com/External",
        "https://example.wd5.myworkdayjobs.com.evil.test/External",
    ]:
        with pytest.raises(ValueError):
            workday_config(url)


def test_detail_outage_opens_circuit_and_stops_pagination():
    detail_requests = []
    pages = []

    def handler(request):
        if request.method == "POST":
            pages.append(request)
            return httpx.Response(
                200,
                json={
                    "total": 100,
                    "jobPostings": [{"externalPath": f"/job/X/R{i}"} for i in range(20)],
                },
            )
        detail_requests.append(request)
        return httpx.Response(503)

    c = collector(handler)
    rows = c.fetch()
    assert c.circuit_open and not c.snapshot_complete
    assert len(pages) == 1 and len(rows) == 20
    assert len(detail_requests) <= 6 * 4  # Five failures, at most one concurrent request.
    assert any(row.get("detail_error") == "CircuitOpen" for row in rows)
    c.client.close()


def test_pagination_details_dates_locations_duplicate_sync_and_changes(db, monkeypatch):
    revision = [0]

    def handler(request):
        if request.method == "POST":
            offset = json.loads(request.content)["offset"]
            return httpx.Response(
                200,
                json={
                    "total": 2 if offset == 0 else 0,
                    "jobPostings": [{"externalPath": f"/job/Austin/Engineer_R{offset}"}]
                    if offset < 2
                    else [],
                },
            )
        detail = copy.deepcopy(DETAIL)
        detail["jobPostingInfo"]["id"] += request.url.path[-1]
        detail["jobPostingInfo"]["jobDescription"] += " Python" * revision[0]
        return httpx.Response(200, json=detail)

    c = collector(handler)
    rows = c.fetch()
    assert len(rows) == 2 and c.request_count == 4
    data = c.normalize(rows[0])
    assert data.posted_at.tzinfo and data.state == "TX" and data.country == "US"
    assert len(data.locations) == 2 and "<p>" not in data.description
    assert data.apply_url.startswith(CONFIG["careers_url"])
    first = sync_source(db, c)
    identities = {job.id: job.first_seen_at for job in db.scalars(select(Job))}
    second = sync_source(db, c)
    revision[0] = 1
    from services.api.app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "workday_detail_cache_hours", 0)
    third = sync_source(db, c)
    assert first.created == 2 and second.unchanged == 2 and third.updated == 2
    assert {job.id: job.first_seen_at for job in db.scalars(select(Job))} == identities
    c.client.close()


@pytest.mark.parametrize("status", [404, 429, 503])
def test_detail_failures_isolate_and_skip_closure(db, status):
    requests = []

    def handler(request):
        if request.method == "POST":
            return httpx.Response(
                200, json={"total": 1, "jobPostings": [{"externalPath": "/job/X/R1"}]}
            )
        requests.append(request)
        return httpx.Response(status, headers={"Retry-After": "0"})

    c = collector(handler)
    result = sync_source(db, c)
    assert result.status == "partial" and result.closed == 0
    assert len(requests) == (1 if status == 404 else 4)
    c.client.close()


@pytest.mark.parametrize("missing", ["jobDescription", "startDate"])
def test_missing_fields(missing):
    c = collector(lambda _: httpx.Response(200))
    detail = copy.deepcopy(DETAIL)
    del detail["jobPostingInfo"][missing]
    raw = {"listing": {"externalPath": "/job/X/R1"}, "detail": detail}
    if missing == "jobDescription":
        with pytest.raises(ValueError):
            c.normalize(raw)
    else:
        assert c.normalize(raw).posted_at is None
    c.client.close()


@pytest.mark.parametrize(
    "payload", [{}, {"total": 1, "jobPostings": []}, {"total": -1, "jobPostings": []}]
)
def test_malformed_snapshot(payload):
    c = collector(lambda _: httpx.Response(200, json=payload))
    with pytest.raises(ValueError):
        c.fetch()
    c.client.close()


def test_workday_closed_posting_requires_complete_missing_snapshots(db):
    from datetime import timedelta

    from collectors.lifecycle import utc
    from services.api.app.db.session import utcnow

    open_board = [True]

    def handler(request):
        if request.method == "POST":
            return httpx.Response(
                200,
                json={
                    "total": int(open_board[0]),
                    "jobPostings": [{"externalPath": "/job/X/R1"}] if open_board[0] else [],
                },
            )
        return httpx.Response(200, json=DETAIL)

    c = collector(handler)
    assert sync_source(db, c).created == 1
    job = db.scalar(select(Job))
    original_id, first_seen = job.id, job.first_seen_at
    open_board[0] = False
    assert sync_source(db, c).closed == 0
    assert sync_source(db, c).closed == 0
    job.missing_since = utcnow() - timedelta(days=4)
    db.commit()
    assert sync_source(db, c).closed == 1
    db.refresh(job)
    assert not job.is_active
    open_board[0] = True
    assert sync_source(db, c).updated == 1
    db.refresh(job)
    assert job.is_active and job.id == original_id and utc(job.first_seen_at) == utc(first_seen)
    c.client.close()
