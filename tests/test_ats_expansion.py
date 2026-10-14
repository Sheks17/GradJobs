import copy
import csv
import json

import httpx
import pytest

from collectors.ats_registry import ATS_REGISTRY, detect_url
from collectors.breezyhr import BreezyHRCollector, job_posting
from collectors.discover import detected_page, discover, public_url
from collectors.discover_batch import discover_batch
from collectors.providers import PROVIDERS
from collectors.public_feeds import complete_rows, source_date
from collectors.recruitee import RecruiteeCollector
from collectors.workable import WorkableCollector


@pytest.mark.parametrize(
    ("url", "provider"),
    [
        ("https://example.avature.net/careers", "avature"),
        ("https://krb-sjobs.brassring.com/TGnewUI/Search/Home/Home?partnerid=1", "brassring"),
        ("https://example.breezy.hr/", "breezyhr"),
        ("https://example.darwinbox.in/ms/candidate/careers", "darwinbox"),
        ("https://example.freshteam.com/jobs", "freshteam"),
        ("https://careers-example.icims.com/jobs", "icims"),
        ("https://example.applytojob.com/apply", "jazzhr"),
        ("https://jobs.jobvite.com/example", "jobvite"),
        ("https://careers.kula.ai/example", "kula"),
        (
            "https://example.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1",
            "oracle_recruiting_cloud",
        ),
        ("https://example.recruitee.com/", "recruitee"),
        ("https://ats.rippling.com/example/jobs", "rippling"),
        ("https://career5.successfactors.eu/career?company=example", "sap_successfactors"),
        ("https://example.teamtailor.com/jobs", "teamtailor"),
        ("https://example.na.teamtailor.com/jobs", "teamtailor"),
        ("https://apply.workable.com/example/", "workable"),
        ("https://example.wd2.myworkdayjobs.com/en-US/External", "workday"),
        ("https://example.zohorecruit.com/jobs/Careers", "zoho_recruit"),
    ],
)
def test_detection_host_signatures(url, provider):
    assert detect_url(url) == provider


def test_registry_separates_access_and_implementation():
    assert len(ATS_REGISTRY) == 23  # 22 requested ATS plus existing federal source.
    assert {
        key for key, item in ATS_REGISTRY.items() if item["implementation_status"] == "supported"
    } == set(PROVIDERS)
    assert all(item["evidence_urls"] and item["notes"] for item in ATS_REGISTRY.values())
    assert ATS_REGISTRY["teamtailor"]["authentication_type"] == "employer"
    assert ATS_REGISTRY["linkedin_talent_hub"]["ingestion_status"] == "PARTNER_ONLY"
    assert detect_url("https://example.recruitee.com.evil.invalid/jobs") is None
    assert detect_url("https://user:pass@example.recruitee.com/") is None


def test_known_ats_does_not_become_unknown_when_account_is_missing(monkeypatch):
    import collectors.discover as module

    monkeypatch.setattr(module, "_discover", lambda _: {"provider": "unknown", "verified": False})
    result = discover("https://apply.workable.com/j/ABC")
    assert result["provider"] == "workable" and not result["verified"]
    assert not result.get("board_token")


def test_unsupported_and_linkedin_never_fetch(monkeypatch):
    import collectors.discover as module

    monkeypatch.setattr(
        module,
        "_discover",
        lambda *_: pytest.fail("Unimplemented/provider-private APIs must not be fetched"),
    )
    item = discover("https://example.freshteam.com/jobs")
    assert item["provider"] == "freshteam" and item["verified_ats"] and not item["verified"]
    assert item["public_ingestion"] == "detection_only"
    assert discover("https://www.linkedin.com/jobs")["provider"] == "unknown"
    with pytest.raises(ValueError, match="LinkedIn"):
        public_url("https://www.linkedin.com/jobs")
    assert (
        detected_page(
            "https://example.com",
            '<a href="https://www.linkedin.com/company/example">LinkedIn</a>'
            "<p>HackerRank integrates LinkedIn Talent Hub</p>",
        )
        is None
    )
    result = detected_page(
        "https://example.com", '<meta name="generator" content="LinkedIn Talent Hub">'
    )
    assert result["provider"] == "linkedin_talent_hub" and not result["verified"]


def test_unsupported_candidates_survive_resume_without_retry(tmp_path, monkeypatch):
    import collectors.discover_batch as module

    input_file, output = tmp_path / "urls.csv", tmp_path / "out.json"
    with input_file.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["company_name", "careers_url"])
        writer.writeheader()
        writer.writerow(
            {"company_name": "Fixture", "careers_url": "https://example.freshteam.com/jobs"}
        )
    calls = []

    def inspect(url):
        calls.append(url)
        return discover(url)

    monkeypatch.setattr(module, "discover", inspect)
    first = discover_batch(input_file, output)
    assert first[0]["stage"] == "unsupported_provider" and first[0]["unsupported_reason"]
    assert first[0]["last_checked"] and "enabled" not in first[0]
    assert discover_batch(input_file, output, retry=True) == first and len(calls) == 1


def workable_response(request):
    if "/widget/" in request.url.path:
        return httpx.Response(
            200,
            json={
                "jobs": [
                    {
                        "shortcode": "ABC",
                        "title": "Engineer",
                        "url": "https://apply.workable.com/j/ABC",
                        "application_url": "https://apply.workable.com/j/ABC/apply",
                    }
                ]
            },
        )
    return httpx.Response(
        200,
        json={
            "shortcode": "ABC",
            "state": "published",
            "title": "Engineer",
            "description": "<p>Python. 0-2 years experience.</p>",
            "requirements": "<p>SQL</p>",
            "workplace": "hybrid",
            "published": "2026-10-01",
            "location": {"city": "Austin", "countryCode": "US", "region": "TX"},
            "locations": [
                {"city": "Austin", "countryCode": "US", "region": "TX"},
                {"city": "Denver", "countryCode": "US", "region": "CO"},
            ],
        },
    )


def test_workable_complete_feed_details_and_locations():
    client = httpx.Client(transport=httpx.MockTransport(workable_response))
    collector = WorkableCollector("fixture", "Fixture", client=client, sleep=lambda _: None)
    rows = collector.fetch()
    job = collector.normalize(rows[0])
    assert job.source_job_id == "ABC" and job.remote_type == "hybrid"
    assert "Python" in job.description and "SQL" in job.description
    assert job.country == "US" and job.posted_at.tzinfo and len(job.locations) == 2
    assert collector.snapshot_complete and collector.request_count == 2


def test_public_feed_completeness_rejects_truncation():
    with pytest.raises(ValueError):
        complete_rows({"offers": [{}], "next": "secret-page"}, "offers")
    with pytest.raises(ValueError):
        complete_rows({"offers": [{}], "total": 2}, "offers")
    with pytest.raises(ValueError):
        complete_rows({"offers": None}, "offers")
    assert source_date(None) is None
    assert source_date("2026-10-01 12:00:00 UTC").utcoffset().total_seconds() == 0


def test_workable_detail_outage_is_partial_and_bounded():
    def fail(request):
        if "/widget/" in request.url.path:
            return httpx.Response(200, json={"jobs": [{"shortcode": str(i)} for i in range(20)]})
        return httpx.Response(404)

    collector = WorkableCollector(
        "fixture",
        "Fixture",
        client=httpx.Client(transport=httpx.MockTransport(fail)),
        sleep=lambda _: None,
    )
    assert len(collector.fetch()) == 5 and not collector.snapshot_complete
    assert collector.request_count == 6  # Permanent failures not retried.


def test_recruitee_anonymous_feed_metadata_and_salary():
    row = {
        "id": 123,
        "title": "Junior Engineer",
        "description": "<p>Python</p>",
        "requirements": "<p>No experience required</p>",
        "careers_url": "https://fixture.recruitee.com/o/engineer",
        "careers_apply_url": "https://fixture.recruitee.com/o/engineer/c/new",
        "location": "Austin, TX",
        "country_code": "US",
        "city": "Austin",
        "state_code": "TX",
        "hybrid": True,
        "salary": {"min": 60000, "max": 80000, "currency": "USD", "period": "yearly"},
        "published_at": "2026-10-01 12:00:00 UTC",
    }
    collector = RecruiteeCollector(
        "fixture",
        "Fixture",
        client=httpx.Client(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"offers": [row]}))
        ),
        sleep=lambda _: None,
    )
    job = collector.normalize(collector.fetch()[0])
    assert (
        job.source_job_id == "123" and job.remote_type == "hybrid" and job.salary_period == "year"
    )
    assert job.source == "recruitee" and not job.raw_data.get("human_label")
    row["careers_url"] = "https://evil.invalid/position"
    with pytest.raises(ValueError):
        collector.normalize(row)


def test_recruitee_missing_description_rejected():
    collector = RecruiteeCollector("fixture", "Fixture")
    with pytest.raises(ValueError, match="description"):
        collector.normalize({"id": 1})
    collector.close()


def test_structured_breezy_without_layout_dependency():
    posting = {
        "@type": "JobPosting",
        "title": "Junior Engineer",
        "description": "<p>No experience required</p>",
    }
    html = '<script type="application/ld+json">' + json.dumps({"@graph": [posting]}) + "</script>"
    assert job_posting(html)["title"] == "Junior Engineer"
    with pytest.raises(ValueError):
        job_posting("<article>Unstructured job</article>")
    collector = BreezyHRCollector("fixture", "Fixture")
    job = collector.normalize(
        {
            "listing": {
                "id": "abc",
                "name": "Junior Engineer",
                "url": "https://fixture.breezy.hr/p/abc-engineer",
                "location": {
                    "name": "Austin, TX",
                    "country": {"id": "US"},
                    "state": {"id": "TX"},
                    "city": "Austin",
                    "is_remote": True,
                },
            },
            "posting": posting,
        }
    )
    assert job.remote_type == "remote" and job.posted_at is None and job.description
    collector.close()


def test_capability_reporting_includes_unimplemented_and_federal(db):
    from fastapi.testclient import TestClient

    from services.api.app.db.session import get_db
    from services.api.app.main import app

    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app) as client:
            response = client.get("/stats/ats")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    rows = {row["provider"]: row for row in response.json()}
    assert len(rows) == 23 and not rows["linkedin_talent_hub"]["ingestion_supported"]
    assert rows["workable"]["ingestion_supported"] and rows["usajobs"]["verified_employers"] == 0


def test_registry_survives_database_outage_without_inventing_counts(db, monkeypatch):
    from sqlalchemy.exc import SQLAlchemyError

    import services.api.app.repositories.providers as module

    def unavailable(_):
        raise SQLAlchemyError("unavailable")

    monkeypatch.setattr(module, "provider_statistics", unavailable)
    rows = module.ats_statistics(db)
    assert len(rows) == 23
    assert all(row["active_jobs"] is None and not row["database_available"] for row in rows)


@pytest.mark.parametrize("provider", ["workable", "recruitee", "breezyhr"])
def test_new_providers_duplicate_change_and_closed_lifecycle(db, provider, monkeypatch):
    from datetime import timedelta

    from sqlalchemy import select

    from collectors.runner import sync_source
    from services.api.app.db.session import utcnow
    from services.api.app.models.job import Job

    if provider == "workable":
        collector = WorkableCollector(
            "fixture",
            "Fixture",
            client=httpx.Client(transport=httpx.MockTransport(workable_response)),
            sleep=lambda _: None,
        )
        rows = collector.fetch()
    elif provider == "recruitee":
        collector = RecruiteeCollector("fixture", "Fixture")
        rows = [
            {
                "id": 1,
                "title": "Junior Engineer",
                "description": "0-2 years Python",
                "careers_url": "https://fixture.recruitee.com/o/junior",
                "careers_apply_url": "https://fixture.recruitee.com/o/junior/c/new",
                "country_code": "US",
            }
        ]
    else:
        collector = BreezyHRCollector("fixture", "Fixture")
        rows = [
            {
                "listing": {
                    "id": "abc",
                    "name": "Junior Engineer",
                    "url": "https://fixture.breezy.hr/p/abc-engineer",
                },
                "posting": {"description": "0-2 years Python"},
            }
        ]
    rows = copy.deepcopy(rows)
    monkeypatch.setattr(collector, "fetch", lambda: rows)
    try:
        assert sync_source(db, collector).created == 1
        original = db.scalar(select(Job))
        original_id = original.id
        assert sync_source(db, collector).unchanged == 1
        changed = rows[0].get("detail") or rows[0].get("posting") or rows[0]
        changed["description"] = "Updated SQL requirements, 0-2 years."
        assert sync_source(db, collector).updated == 1
        assert original.id == original_id
        rows.clear()
        assert sync_source(db, collector).closed == 0
        assert sync_source(db, collector).closed == 0
        original.missing_since = utcnow() - timedelta(days=4)
        db.commit()
        assert sync_source(db, collector).closed == 1
        assert not original.is_active
    finally:
        collector.close()
