from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from services.api.app.db.session import get_db, utcnow
from services.api.app.main import app
from services.api.app.repositories.ingestion import upsert_job
from shared.schemas import NormalizedJob


@pytest.fixture
def client(db, source):
    now = utcnow()
    rows = [
        ("Associate Software Engineer", "0-2", "remote", "TX", "US", 80000, "year", 1),
        ("QA Analyst I", "1-3", "hybrid", "IL", "US", 65000, "year", 3),
        ("Senior Software Engineer", "5-7", "onsite", "TX", "US", 140000, "year", 2),
        ("Junior Developer", "0-2", "remote", None, "CA", 90000, "year", 1),
        ("Application Developer", None, "unknown", "OH", "US", None, None, None),
        ("Junior Software Tester", "0-2", "onsite", "TX", "US", 40, "hour", 20),
    ]
    for i, (title, exp, remote, state, country, salary, period, days) in enumerate(rows):
        job, _ = upsert_job(
            db,
            source.id,
            NormalizedJob(
                source="manual",
                source_job_id=str(i),
                title=title,
                company_name=f"Demo Company {chr(65 + i)}",
                description=f"{exp} years of experience" if exp else "SQL troubleshooting",
                apply_url=f"https://example.com/jobs/{i}",
                source_url=f"https://example.com/jobs/{i}",
                remote_type=remote,
                state=state,
                country=country,
                salary_min=salary,
                salary_currency="USD" if salary else None,
                salary_period=period,
                posted_at=now - timedelta(days=days) if days else None,
            ),
        )
        job.first_seen_at = now - timedelta(hours=2)
    db.commit()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_default_filters_and_pagination(client):
    result = client.get("/jobs", params={"page_size": 2}).json()
    assert result["total"] == 4 and result["total_pages"] == 2
    assert len(result["items"]) == 2
    assert all(
        job["country"] == "US" and job["early_career_score"] >= 50 for job in result["items"]
    )
    assert client.get("/jobs", params={"page": 99}).json()["items"] == []


@pytest.mark.parametrize(
    "params,count",
    [
        ({"q": "QA"}, 2),
        ({"q": "SQL"}, 1),
        ({"q": "%"}, 0),
        ({"remote_type": "remote"}, 1),
        ({"state": "Texas"}, 2),
        ({"company": "demo-company-b"}, 1),
        ({"role_family": "QA / Testing"}, 2),
        ({"seniority": "associate"}, 1),
        ({"min_salary": 70000}, 1),
        ({"max_experience": 0, "include_unknown_experience": "false"}, 2),
        ({"min_early_career_score": 85}, 3),
        ({"country": "CA"}, 1),
        ({"max_experience": 40, "min_early_career_score": 0}, 4),
        ({"max_experience": 40, "min_early_career_score": 0, "include_senior": True}, 5),
    ],
)
def test_filters(client, params, count):
    response = client.get("/jobs", params=params)
    assert response.status_code == 200, response.text
    assert response.json()["total"] == count


def test_freshness_does_not_invent_posted_dates(client):
    since = (utcnow() - timedelta(days=7)).isoformat()
    assert client.get("/jobs", params={"posted_after": since}).json()["total"] == 2
    fresh = client.get("/jobs", params={"fresh_after": since}).json()
    assert fresh["total"] == 3
    assert any(job["posted_at"] is None for job in fresh["items"])


@pytest.mark.parametrize(
    "sort",
    ["newest", "newest_posted", "recently_discovered", "early_career_score", "company", "salary"],
)
def test_sorts_are_stable(client, sort):
    first = client.get("/jobs", params={"sort": sort}).json()["items"]
    second = client.get("/jobs", params={"sort": sort}).json()["items"]
    assert [job["id"] for job in first] == [job["id"] for job in second]
    if sort == "salary":
        assert first[0]["salary_min"] == "80000.00"


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"page_size": 101},
        {"sort": "bad"},
        {"max_experience": -1},
        {"remote_type": "anywhere"},
    ],
)
def test_invalid_filters(client, params):
    assert client.get("/jobs", params=params).status_code == 422


def test_details_stats_and_metadata(client):
    job = client.get("/jobs").json()["items"][0]
    detail = client.get(f"/jobs/{job['id']}").json()
    assert detail["score_reasons"] and "raw_data" not in detail
    assert detail["first_seen_at"].endswith("Z")
    assert client.get(f"/jobs/{uuid4()}").status_code == 404
    assert client.get("/health").json()["status"] == "ok"
    stats = client.get("/stats").json()
    assert stats["active_jobs"] == 5 and stats["remote_jobs"] == 1
    assert len(client.get("/companies").json()) == 5
    assert len(client.get("/sources").json()) == 1
