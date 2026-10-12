import copy
import json
import threading
import time
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path

import httpx
import pytest
from sqlalchemy import func, select

from collectors.discover import ats_from_url, page_candidates
from collectors.lifecycle import expire_deadlines
from collectors.runner import sync_source
from collectors.smartrecruiters import SmartRecruitersCollector
from collectors.sync_all import dry_run_source
from collectors.usajobs import USAJobsCollector
from services.api.app.core.config import get_settings
from services.api.app.db.session import utcnow
from services.api.app.models.job import Job, JobSource, SourceSync
from services.api.app.repositories.ingestion import upsert_job
from services.api.app.repositories.providers import provider_statistics
from services.api.app.schemas.sources import SourceCreate
from services.api.app.services.sources import register_source

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def smart_client(broken=False):
    raw = fixture("smartrecruiters")

    def respond(request):
        if request.url.path.endswith("/postings"):
            offset = int(request.url.params["offset"])
            row = {**raw["listing"], "id": str(offset + 1)}
            return httpx.Response(200, json={"totalFound": 2, "content": [row]})
        if broken and request.url.path.endswith("/2"):
            return httpx.Response(404)
        return httpx.Response(200, json=raw["detail"])

    return httpx.Client(transport=httpx.MockTransport(respond))


def test_smart_pagination_details_location_dates_and_repeat_sync(db, monkeypatch):
    with smart_client() as client:
        collector = SmartRecruitersCollector("Example", "Sopra", client, lambda _: None)
        rows = collector.fetch()
        assert len(rows) == 2 and collector.request_count == 4
        data = collector.normalize(rows[0])
        assert data.country == "US" and data.state == "NC" and data.remote_type == "hybrid"
        assert data.posted_at.tzinfo and len(data.description) > 100
        assert data.source_url.startswith("https://") and data.apply_url.startswith("https://")
        first = sync_source(db, collector)
        original = {job.id: job.first_seen_at for job in db.scalars(select(Job))}
        second = sync_source(db, collector)
        normalize = collector.normalize
        monkeypatch.setattr(
            collector,
            "normalize",
            lambda raw: normalize(raw).model_copy(update={"provider_metadata": {"revision": 2}}),
        )
        normalized_update = sync_source(db, collector)
    assert first.created == 2 and second.unchanged == 2
    assert normalized_update.updated == 2 and normalized_update.unchanged == 0
    assert {job.id: job.first_seen_at for job in db.scalars(select(Job))} == original
    assert all(job.raw_data.get("detail") for job in db.scalars(select(Job)))


def test_smart_detail_failure_is_partial_and_does_not_reconcile_missing(db):
    with smart_client(broken=True) as client:
        collector = SmartRecruitersCollector("Example", "Sopra", client, lambda _: None)
        result = sync_source(db, collector)
    assert result.status == "partial" and result.created == 1 and result.failures == 1
    assert result.failed_requests == 1 and result.closed == 0
    source = db.scalar(select(JobSource))
    assert source.last_error and source.last_successful_sync is None


@pytest.fixture
def usa_credentials(monkeypatch):
    monkeypatch.setenv("USAJOBS_API_KEY", "test-key")
    monkeypatch.setenv("USAJOBS_USER_AGENT", "test@example.invalid")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_usa_auth_pagination_and_query_overlap_dedup(usa_credentials):
    calls = []
    item = fixture("usajobs")

    def respond(request):
        assert request.headers["Authorization-Key"] == "test-key"
        assert request.headers["User-Agent"] == "test@example.invalid"
        assert request.headers["Host"] == "data.usajobs.gov"
        assert request.url.params["Fields"] == "Full"
        page = int(request.url.params["Page"])
        calls.append(page)
        return httpx.Response(
            200,
            json={
                "SearchResult": {
                    "SearchResultCountAll": 2,
                    "SearchResultItems": [{**item, "MatchedObjectId": str(page)}],
                }
            },
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        collector = USAJobsCollector(
            "tech",
            "Federal",
            client,
            lambda _: None,
            config={
                "queries": [{"Keyword": "Software"}, {"Keyword": "Data"}],
                "results_per_page": 1,
            },
        )
        assert len(collector.fetch()) == 2
    assert calls == [1, 2, 1, 2]


def test_usa_salary_locations_deadline_and_explicit_programs():
    raw = fixture("usajobs")
    details = raw["MatchedObjectDescriptor"]["UserArea"]["Details"]
    details.update(
        HiringPath=["graduates", "student", "fed-internal-search"],
        Requirements=(
            "You must be a U.S. citizen. This is a Pathways internship. "
            "Veterans' preference applies."
        ),
        SecurityClearance="Top Secret",
        RemoteIndicator=True,
    )
    data = USAJobsCollector("tech", "Federal", sleep=lambda _: None).normalize(raw)
    assert data.salary_period == "year" and data.salary_currency == "USD"
    assert data.salary_min == 117284 and data.salary_max == 172980
    assert data.country == "US" and data.city == "San Francisco"
    assert len(data.locations) == 8 and data.remote_type == "remote"
    assert data.closing_at.tzinfo and data.closing_at.year == 2026
    assert data.requires_us_citizenship and data.requires_security_clearance
    assert data.provider_metadata["recent_graduate"] and data.provider_metadata["pathways"]
    assert data.provider_metadata["student"] and data.provider_metadata["internship"]
    assert data.provider_metadata["federal_status_restrictions"] == ["fed-internal-search"]
    assert data.provider_metadata["veterans_preference_evidence"]
    from matching.experience import early_career_signals

    assert early_career_signals(data.description)
    assert data.raw_data == raw


def test_usa_does_not_infer_clearance_from_public_trust_or_citizenship_from_missing_text():
    raw = fixture("usajobs")
    details = raw["MatchedObjectDescriptor"]["UserArea"]["Details"]
    for field in ("Requirements", "OtherInformation", "JobSummary", "MajorDuties"):
        details.pop(field, None)
    raw["MatchedObjectDescriptor"]["QualificationSummary"] = "Technical skills required."
    details["SecurityClearance"] = "Public Trust - Background Investigation"
    data = USAJobsCollector("tech", "Federal", sleep=lambda _: None).normalize(raw)
    assert data.requires_us_citizenship is None and data.requires_security_clearance is None
    assert "Public Trust" in data.provider_metadata["public_trust"]


def test_long_federal_paragraph_does_not_backtrack_in_citizenship_extraction():
    raw = fixture("usajobs")
    details = raw["MatchedObjectDescriptor"]["UserArea"]["Details"]
    details["Requirements"] = "Professional technical qualifications. " * 3000
    started = time.monotonic()
    data = USAJobsCollector("tech", "Federal", sleep=lambda _: None).normalize(raw)
    assert time.monotonic() - started < 2
    assert data.raw_data == raw


def test_malformed_federal_posting_isolated(db, usa_credentials):
    good = fixture("usajobs")
    bad = {"MatchedObjectId": "broken", "MatchedObjectDescriptor": {"PositionTitle": "Broken"}}
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "SearchResult": {"SearchResultCountAll": 2, "SearchResultItems": [bad, good]}
                },
            )
        )
    ) as client:
        result = sync_source(
            db,
            USAJobsCollector(
                "tech",
                "Federal",
                client,
                lambda _: None,
                config={"queries": [{"Keyword": "Software"}]},
            ),
        )
    assert result.created == 1 and result.failures == 1 and result.status == "partial"


def test_dry_run_has_no_jobs_history_or_health_writes(db):
    with smart_client() as client:
        result = dry_run_source(
            db, SmartRecruitersCollector("Example", "Example", client, lambda _: None)
        )
    assert result.status == "dry_run" and result.validated == 2 and result.created == 0
    for model in (Job, JobSource, SourceSync):
        assert db.scalar(select(func.count()).select_from(model)) == 0


def test_closing_deadline_preserves_id_and_discovery_history(db):
    source, _ = register_source(
        db, SourceCreate(company_name="Federal", provider="usajobs", board_token="tech")
    )
    data = USAJobsCollector("tech", "Federal", sleep=lambda _: None).normalize(fixture("usajobs"))
    data = data.model_copy(update={"closing_at": utcnow() + timedelta(days=3)})
    job, _ = upsert_job(db, source.id, data)
    identity, discovered = job.id, job.first_seen_at
    job.closing_at = utcnow() - timedelta(seconds=1)
    assert expire_deadlines(db, utcnow()) == 1
    assert job.id == identity and job.first_seen_at == discovered and not job.is_active
    job, created = upsert_job(db, source.id, data.model_copy(update={"closing_at": None}))
    assert not created and not job.is_active  # Missing closing date cannot resurrect expired jobs.


def test_mirrored_provider_records_preserve_references_and_do_not_merge_employers(db):
    first, _ = register_source(
        db, SourceCreate(company_name="Example", provider="smartrecruiters", board_token="one")
    )
    second, _ = register_source(
        db, SourceCreate(company_name="Example", provider="greenhouse", board_token="two")
    )
    data = SmartRecruitersCollector("Example", "Example", sleep=lambda _: None).normalize(
        fixture("smartrecruiters")
    )
    canonical, _ = upsert_job(db, first.id, data)
    mirror, _ = upsert_job(db, second.id, data.model_copy(update={"source": "greenhouse"}))
    assert mirror.duplicate_of == canonical.id and mirror.source_id != canonical.source_id
    unrelated, _ = upsert_job(
        db,
        second.id,
        data.model_copy(
            update={
                "source": "greenhouse",
                "source_job_id": "other",
                "company_name": "Unrelated Employer",
            }
        ),
    )
    assert unrelated.duplicate_of is None
    canonical.closing_at = utcnow() - timedelta(seconds=1)
    assert expire_deadlines(db, utcnow()) == 1
    assert mirror.is_active and mirror.duplicate_of is None
    assert canonical.duplicate_of == mirror.id


def test_provider_metrics_are_actual_latest_attempts(db):
    with smart_client() as client:
        sync_source(db, SmartRecruitersCollector("Example", "Example", client, lambda _: None))
    report = next(row for row in provider_statistics(db) if row["provider"] == "smartrecruiters")
    assert report["sources"] == report["healthy"] == 1 and report["failing"] == 0
    assert report["jobs_created"] == 2 and report["request_count"] == 4
    assert report["last_successful_sync"]


def test_source_verification_is_read_only(db, monkeypatch):
    import collectors.verify_sources as module

    source, _ = register_source(
        db, SourceCreate(company_name="Example", provider="smartrecruiters", board_token="Example")
    )
    db.commit()

    @contextmanager
    def session():
        yield db

    monkeypatch.setattr(module, "SessionLocal", session)
    with smart_client() as client:
        monkeypatch.setattr(
            module,
            "make_collector",
            lambda *args: SmartRecruitersCollector("Example", "Example", client, lambda _: None),
        )
        report = module.verify_registered("smartrecruiters")
    assert report[0]["verified"] and report[0]["jobs"] == 2
    assert db.scalar(select(func.count()).select_from(Job)) == 0
    assert db.scalar(select(func.count()).select_from(SourceSync)) == 0
    assert source.last_sync_attempt is None


def test_pilot_sample_excludes_old_ids_and_never_creates_labels(db):
    from matching.sample_pilot import sample_pilot

    excluded = set()
    for provider in ("smartrecruiters", "usajobs", "greenhouse", "lever", "ashby"):
        source, _ = register_source(
            db, SourceCreate(company_name="Example", provider=provider, board_token="Example")
        )
        data = SmartRecruitersCollector("Example", "Example", sleep=lambda _: None).normalize(
            fixture("smartrecruiters")
        )
        for number in range(3):
            job, _ = upsert_job(
                db,
                source.id,
                data.model_copy(
                    update={
                        "source": provider,
                        "source_job_id": str(number),
                        "apply_url": f"https://example.com/{provider}/{number}",
                        "company_name": f"Example {provider} {number}",
                    }
                ),
            )
            if number == 0:
                excluded.add(str(job.id))
    report = sample_pilot(db, excluded)
    assert len(report["jobs"]) == 10
    assert not {row["job_id"] for row in report["jobs"]} & excluded
    assert all(row["label"] is None for row in report["jobs"])
    assert len(report["provider_counts"]) == 5


def test_discovery_recognizes_observed_smartrecruiters_links():
    assert ats_from_url("https://careers.smartrecruiters.com/Example") == (
        "smartrecruiters",
        "Example",
    )
    assert page_candidates(
        "https://example.com/careers",
        '<a href="https://jobs.smartrecruiters.com/Example/123-job">Jobs</a>',
    ) == [("smartrecruiters", "Example")]
    assert ats_from_url("https://jobs.smartrecruiters.com.evil.invalid/Example") is None


def test_concurrency_global_and_provider_limits(db, monkeypatch):
    import collectors.sync_all as module

    settings = copy.copy(get_settings())
    settings.collector_provider_concurrency = {"smartrecruiters": 1, "lever": 2}
    for provider in ("smartrecruiters", "lever"):
        for number in range(3):
            register_source(
                db,
                SourceCreate(company_name=str(number), provider=provider, board_token=str(number)),
            )
    db.commit()
    identities = {row.id: row.source_type for row in db.scalars(select(JobSource))}

    @contextmanager
    def session():
        yield db

    monkeypatch.setattr(module, "SessionLocal", session)
    monkeypatch.setattr(module, "get_settings", lambda: settings)
    lock = threading.Lock()
    active = {"all": 0, "lever": 0, "smartrecruiters": 0}
    peaks = active.copy()

    def run(identity, dry_run=False):
        provider = identities[identity]
        with lock:
            for kind in ("all", provider):
                active[kind] += 1
                peaks[kind] = max(peaks[kind], active[kind])
        time.sleep(0.03)
        with lock:
            for kind in ("all", provider):
                active[kind] -= 1
        return module.SyncResult(status="dry_run")

    monkeypatch.setattr(module, "sync_one", run)
    report = module.sync_all(dry_run=True, concurrency=3)
    assert report["sources_attempted"] == 6
    assert 2 <= peaks["all"] <= 3 and peaks["smartrecruiters"] <= 1 and peaks["lever"] <= 2
    assert module.sync_all(provider="lever", dry_run=True)["sources_attempted"] == 3
    release_slow_provider = threading.Event()
    completed_fast = []

    def slow_provider(identity, dry_run=False):
        if identities[identity] == "smartrecruiters":
            assert release_slow_provider.wait(2), "Fast provider queue was starved"
        else:
            with lock:
                completed_fast.append(identity)
                if len(completed_fast) == 3:
                    release_slow_provider.set()
        return module.SyncResult(status="dry_run")

    monkeypatch.setattr(module, "sync_one", slow_provider)
    assert module.sync_all(dry_run=True, concurrency=2)["sources_successful"] == 6


@pytest.mark.parametrize("status,retries", [(400, 1), (401, 1), (404, 1), (429, 4), (503, 4)])
def test_provider_retries_only_transient_statuses(status, retries):
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(status))
    ) as client:
        collector = SmartRecruitersCollector("Example", "Example", client, lambda _: None)
        with pytest.raises(httpx.HTTPStatusError):
            collector.fetch()
    assert collector.request_count == retries
    assert collector.failed_requests == retries
    assert collector.rate_limit_responses == (retries if status == 429 else 0)


def test_sqlite_workers_queue_before_busy_timeout(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session

    from collectors.locking import write_lock

    engine = create_engine(
        f"sqlite:///{tmp_path / 'writers.db'}",
        connect_args={"timeout": 0.01, "check_same_thread": False},
    )
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE attempts (id INTEGER PRIMARY KEY)"))
    first_ready = threading.Event()

    def write(identity):
        if identity == 2:
            assert first_ready.wait(2)
        with Session(engine) as session:
            write_lock(session)
            session.execute(text("INSERT INTO attempts VALUES (:id)"), {"id": identity})
            if identity == 1:
                first_ready.set()
                time.sleep(0.1)  # Exceeds SQLite's busy timeout, but queued workers still succeed.
            session.commit()

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(write, [1, 2]))
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT COUNT(*) FROM attempts")) == 2
    engine.dispose()


def test_federal_application_deadline_is_not_remote_work_timezone(db):
    raw = fixture("usajobs")
    details = raw["MatchedObjectDescriptor"]["UserArea"]["Details"]
    details["HowToApply"] = "Applications received after 11:59 pm Eastern Standard Time are late."
    collector = USAJobsCollector("tech", "Federal", sleep=lambda _: None)
    data = collector.normalize(raw)
    assert data.provider_metadata["remote_restrictions"]["timezone_requirement"] is None
    source, _ = register_source(
        db, SourceCreate(company_name="Federal", provider="usajobs", board_token="tech")
    )
    job, _ = upsert_job(db, source.id, data)
    assert job.timezone_requirement is None
    details["Requirements"] = "Remote employees must work Eastern Time hours."
    revised = collector.normalize(raw)
    job, _ = upsert_job(db, source.id, revised)
    assert "Eastern Time" in job.timezone_requirement


def test_candidate_verification_isolates_invalid_identifiers(tmp_path, monkeypatch):
    import collectors.verify_sources as module

    candidates = tmp_path / "candidates.json"
    candidates.write_text(
        json.dumps(
            [
                {"provider": "unknown", "board_token": "../outside", "company_name": "Bad"},
                {
                    "detected_provider": "smartrecruiters",
                    "provider_identifier": "Example",
                    "company": "Example",
                },
            ]
        )
    )
    output, cache = tmp_path / "verified.json", tmp_path / "cache"
    with smart_client() as client:
        monkeypatch.setattr(
            module,
            "make_collector",
            lambda *args: SmartRecruitersCollector("Example", "Example", client, lambda _: None),
        )
        module.verify_file(candidates, output, cache)
    report = json.loads((cache / "verification.json").read_text())
    assert not report[0]["verified"] and report[1]["verified"]
    assert len(json.loads(output.read_text())) == 1
    assert not (tmp_path / "outside.json").exists()
