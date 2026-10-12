from fastapi.testclient import TestClient

from services.api.app.core.config import Settings
from services.api.app.db.session import get_db
from services.api.app.main import app as api_app
from services.api.app.repositories.ingestion import upsert_job
from shared.schemas import NormalizedJob
from vercel_app import app


def test_vercel_api_prefix_and_production_admin_guard(db, monkeypatch):
    api_app.dependency_overrides[get_db] = lambda: db
    monkeypatch.setattr(
        "services.api.app.api.sources.get_settings",
        lambda: Settings(app_env="production", enable_admin_api=True),
    )
    try:
        with TestClient(app) as client:
            assert client.get("/api/health").json() == {"status": "ok", "database": "ok"}
            assert client.get("/api/jobs").status_code == 200
            assert client.get("/api/stats/providers").status_code == 200
            assert client.post("/api/sources", json={}).status_code == 403
    finally:
        api_app.dependency_overrides.clear()


def test_hosted_postgres_urls_use_psycopg():
    for prefix in ("postgres://", "postgresql://", "postgresql+psycopg://"):
        settings = Settings(
            database_url=prefix + "user:password@db.example/gradjobs?sslmode=require"
        )
        assert settings.database_url == (
            "postgresql+psycopg://user:password@db.example/gradjobs?sslmode=require"
        )


def test_long_provider_employment_description_is_preserved(db, source):
    employment = "Multiple appointment types and work schedules. " * 4
    job, created = upsert_job(
        db,
        source.id,
        NormalizedJob(
            source="usajobs",
            source_job_id="long-employment-description",
            source_url="https://www.usajobs.gov/job/123456789",
            apply_url="https://www.usajobs.gov/job/123456789",
            company_name="Example agency",
            title="Software Developer",
            description="Entry-level software development with Python.",
            employment_type=employment,
        ),
    )
    db.commit()
    db.refresh(job)
    assert created and job.employment_type == employment
