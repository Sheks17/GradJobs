import json
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from collectors.discover import ats_from_url, public_url
from collectors.greenhouse import GreenhouseCollector
from collectors.lifecycle import reconcile_missing, utc
from collectors.normalizers.location import location_fields
from collectors.runner import sync_source
from matching.experience import early_career_signals, extract_experience
from matching.role_classifier import classify_seniority
from services.api.app.core.config import get_settings
from services.api.app.db.session import get_db, utcnow
from services.api.app.main import app
from services.api.app.models.job import Job, JobSource, SourceSync
from services.api.app.repositories.ingestion import upsert_job
from services.api.app.repositories.jobs import list_jobs
from services.api.app.schemas.jobs import JobFilters, JobSummary
from services.api.app.schemas.sources import SourceCreate
from services.api.app.services.sources import register_source
from tests.test_deduplication import data


@pytest.fixture
def board():
    payload = json.loads((Path(__file__).parent / "fixtures/greenhouse.json").read_text())
    state = {"payload": payload, "status": 200}
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda req: httpx.Response(state["status"], json=state["payload"])
        )
    ) as client:
        yield GreenhouseCollector("test", "Test Company", client, lambda _: None), state


def test_missing_lifecycle_reappearance_and_history(db, board):
    collector, state = board
    original = state["payload"]
    assert sync_source(db, collector).created == 1
    job = db.scalar(select(Job))
    discovered = job.first_seen_at
    state["payload"] = {"jobs": []}
    for expected in (1, 2):
        assert sync_source(db, collector).closed == 0
        db.refresh(job)
        assert job.is_active and job.consecutive_missing_syncs == expected
    assert sync_source(db, collector).closed == 1
    db.refresh(job)
    assert not job.is_active and job.closed_at and job.missing_since
    state["payload"] = original
    assert sync_source(db, collector).updated == 1
    db.refresh(job)
    assert job.is_active and job.closed_at is None and job.missing_since is None
    assert job.consecutive_missing_syncs == 0 and utc(job.first_seen_at) == utc(discovered)
    history = db.scalars(select(SourceSync).order_by(SourceSync.started_at)).all()
    assert len(history) == 5 and all(run.status == "success" for run in history)
    assert history[0].jobs_created == 1 and history[3].jobs_closed == 1
    assert all(run.completed_at and run.duration_ms is not None for run in history)


def test_failed_and_partial_snapshots_never_increment_missing(db, board):
    collector, state = board
    sync_source(db, collector)
    source = db.scalar(select(JobSource))
    success = source.last_successful_sync
    state["status"] = 503
    assert sync_source(db, collector).status == "failed"
    state.update(status=200, payload={"jobs": [{"id": "bad", "internal_job_id": 123}]})
    assert sync_source(db, collector).status == "partial"
    job = db.scalar(select(Job))
    assert job.is_active and job.missing_since is None and job.consecutive_missing_syncs == 0
    assert source.failure_count == 2 and utc(source.last_successful_sync) == utc(success)
    assert source.active_jobs == 1
    assert sorted(db.scalars(select(SourceSync.status))) == ["failed", "partial", "success"]


def test_time_threshold_requires_two_complete_observations(db, board):
    collector, state = board
    sync_source(db, collector)
    state["payload"] = {"jobs": []}
    sync_source(db, collector)
    job = db.scalar(select(Job))
    job.missing_since = utcnow() - timedelta(hours=73)
    db.commit()
    assert sync_source(db, collector).closed == 1


def test_disabled_busy_and_expired_lease(db, board):
    collector, state = board
    sync_source(db, collector)
    source = db.scalar(select(JobSource))
    source.enabled = False
    db.commit()
    assert sync_source(db, collector).status == "disabled"
    source.enabled = True
    source.sync_token = source.id
    source.lease_expires_at = utcnow() + timedelta(minutes=10)
    db.commit()
    assert sync_source(db, collector).status == "busy"
    source.lease_expires_at = utcnow() - timedelta(minutes=1)
    interrupted = SourceSync(source_id=source.id, started_at=utcnow() - timedelta(hours=1))
    db.add(interrupted)
    db.commit()
    assert sync_source(db, collector).unchanged == 1
    db.refresh(interrupted)
    assert interrupted.status == "interrupted" and source.sync_token is None


def test_partial_pagination_failure_keeps_snapshot_atomic(db, board):
    from collectors.lever import LeverCollector

    collector, _ = board
    sync_source(db, collector)
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: (
                httpx.Response(200, json=[{"id": str(i)} for i in range(100)])
                if request.url.params["skip"] == "0"
                else httpx.Response(503)
            )
        )
    ) as client:
        result = sync_source(db, LeverCollector("test", "Test Company", client, lambda _: None))
    assert result.status == "failed" and result.created == 0
    assert db.scalar(select(Job)).is_active


def test_cross_provider_alias_survives_canonical_closure_and_return(db, source):
    other = JobSource(name="Other", source_type="lever", board_identifier="other")
    db.add(other)
    db.flush()
    first, _ = upsert_job(db, source.id, data())
    alias, _ = upsert_job(db, other.id, data(source="lever", apply_url="https://other.example/job"))
    assert alias.duplicate_of == first.id
    for _ in range(3):
        reconcile_missing(db, source.id, set(), utcnow())
    assert alias.duplicate_of is None and first.duplicate_of == alias.id
    upsert_job(db, source.id, data())
    assert first.is_active and first.duplicate_of == alias.id


def test_multilocation_country_state_filter_and_no_fake_remote(db, source):
    fields = location_fields("Toronto, Canada", additional=["Austin, TX", "Boston, MA"])
    job, _ = upsert_job(db, source.id, data(**fields))
    assert job.remote_type == "unknown"
    assert len(job.locations) == 3
    assert list_jobs(db, JobFilters(state="TX")).total == 1
    assert list_jobs(db, JobFilters(state="MA")).total == 1
    assert list_jobs(db, JobFilters(state="NY")).total == 0
    assert list_jobs(db, JobFilters(country="CA")).total == 1
    assert location_fields("Remote")["country"] is None
    assert location_fields("Remote - US")["country"] == "US"
    assert len(location_fields("New York, NY / Boston, MA")["locations"]) == 2


def test_new_badge_uses_first_seen_not_posted_or_last_seen(db, source):
    job, _ = upsert_job(db, source.id, data(posted_at=utcnow() - timedelta(days=90)))
    assert JobSummary.model_validate(job).is_new
    job.first_seen_at = utcnow() - timedelta(hours=25)
    job.last_seen_at = utcnow()
    assert not JobSummary.model_validate(job).is_new


@pytest.mark.parametrize(
    "text,minimum,maximum,preferred",
    [
        ("1-2 years preferred", 1, 2, True),
        ("up to 3 years", 0, 3, False),
        ("less than 3 years", 0, 2, False),
        ("no professional experience required", 0, 0, False),
    ],
)
def test_experience_variants(text, minimum, maximum, preferred):
    result = extract_experience(text)
    assert (result.minimum, result.maximum, result.preferred) == (minimum, maximum, preferred)


@pytest.mark.parametrize(
    "title,expected",
    [
        ("Architect Intern", "internship"),
        ("Junior Cloud Architect", "junior"),
        ("Head of Engineering", "executive"),
        ("Senior Internship Program Manager", "manager"),
        ("Principal Software Engineer", "principal"),
        ("Lead Software Engineer", "lead"),
    ],
)
def test_senior_exceptions(title, expected):
    assert classify_seniority(title) == expected


def test_education_and_graduate_signals_are_explained():
    text = (
        "Recent graduates welcome. Internship experience accepted. "
        "Equivalent combination of education and experience."
    )
    assert len(early_career_signals(text)) == 3
    assert extract_experience(text).minimum is None


def test_source_registry_and_admin_guard(db, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.setattr(settings, "enable_admin_api", False)
    app.dependency_overrides[get_db] = lambda: db
    record = {"company_name": "Example", "provider": "greenhouse", "board_token": "example"}
    try:
        with TestClient(app) as client:
            assert client.post("/sources", json=record).status_code == 403
            monkeypatch.setattr(settings, "enable_admin_api", True)
            with patch.object(GreenhouseCollector, "fetch", return_value=[]):
                assert client.post("/sources", json=record).status_code == 422
            fixture = json.loads((Path(__file__).parent / "fixtures/greenhouse.json").read_text())
            with patch.object(GreenhouseCollector, "fetch", return_value=fixture["jobs"]):
                response = client.post("/sources", json=record)
                assert response.status_code == 201, response.text
                source_id = response.json()["id"]
                assert client.post("/sources", json=record).status_code == 409
            assert client.get(f"/sources/{source_id}/history").json() == []
            assert (
                client.patch(f"/sources/{source_id}", json={"enabled": False}).json()["status"]
                == "disabled"
            )
            assert (
                client.patch(
                    f"/sources/{source_id}", json={"careers_url": "javascript:bad"}
                ).status_code
                == 422
            )
            assert client.post(f"/sources/{source_id}/sync").status_code == 409
            monkeypatch.setattr(settings, "app_env", "production")
            assert client.patch(f"/sources/{source_id}", json={"enabled": True}).status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_import_registration_preserves_operator_settings(db):
    record = SourceCreate(company_name="Example", provider="lever", board_token="example")
    source, created = register_source(db, record)
    db.flush()
    source.enabled = False
    db.flush()
    again, created_again = register_source(db, record)
    assert created and not created_again and again.id == source.id and not again.enabled


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://job-boards.greenhouse.io/example", ("greenhouse", "example")),
        ("https://boards.greenhouse.io/embed/job_board?for=example", ("greenhouse", "example")),
        ("https://jobs.lever.co/example/123", ("lever", "example")),
        ("https://jobs.ashbyhq.com/example", ("ashby", "example")),
        ("https://jobs.lever.co.evil.example/example", None),
    ],
)
def test_discovery_requires_observed_provider_host(url, expected):
    assert ats_from_url(url) == expected


def test_discovery_rejects_private_urls():
    with pytest.raises(ValueError):
        public_url("http://127.0.0.1/careers")


def test_sync_all_isolates_source_failures(db, monkeypatch):
    from contextlib import contextmanager

    import collectors.sync_all as module

    records = [
        SourceCreate(company_name=name, provider="greenhouse", board_token=name)
        for name in ("a", "b")
    ]
    for record in records:
        register_source(db, record)
    db.commit()

    @contextmanager
    def session():
        yield db

    monkeypatch.setattr(module, "SessionLocal", session)
    calls = []

    def sync_one(source_id):
        calls.append(source_id)
        if len(calls) == 1:
            raise RuntimeError("unavailable")
        return module.SyncResult(status="success", created=2)

    monkeypatch.setattr(module, "sync_one", sync_one)
    result = module.sync_all()
    assert len(calls) == 2 and result["sources_failed"] == 1
    assert result["sources_successful"] == 1 and result["jobs_created"] == 2


def test_discovery_follows_observed_careers_link_and_verifies(monkeypatch):
    import collectors.discover as module

    pages = {
        "https://company.example": ("https://company.example", '<a href="/careers">Careers</a>'),
        "https://company.example/careers": (
            "https://company.example/careers",
            '<script type="application/ld+json">{"url":"https://jobs.ashbyhq.com/example"}</script>',
        ),
    }
    monkeypatch.setattr(module, "allowed_page", lambda client, url: pages[url])
    with patch.object(module.PROVIDERS["ashby"], "fetch", return_value=[]):
        assert module.discover("company.example")["board_token"] == "example"


def test_discovery_honors_robots_on_redirect_target(monkeypatch):
    import collectors.discover as module

    visited = []

    def handler(request):
        visited.append(str(request.url))
        if request.url.path == "/robots.txt":
            body = (
                "User-agent: *\nDisallow: /private"
                if request.url.host == "other.example"
                else "User-agent: *\nAllow: /"
            )
            return httpx.Response(200, text=body)
        if request.url.host == "company.example":
            return httpx.Response(302, headers={"location": "https://other.example/private"})
        raise AssertionError("Disallowed page must not be fetched")

    monkeypatch.setattr(module, "public_url", lambda url: None)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ValueError, match="robots"):
            module.allowed_page(client, "https://company.example/careers")
    assert "https://other.example/private" not in visited


def test_incomplete_greenhouse_count_is_not_a_successful_snapshot():
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda req: httpx.Response(200, json={"jobs": [], "meta": {"total": 12}})
        )
    ) as client:
        with pytest.raises(ValueError, match="Incomplete"):
            GreenhouseCollector("test", "Test", client, lambda _: None).fetch()
