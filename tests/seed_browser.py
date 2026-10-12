"""Synthetic browser-test data only. Refuse any database except browser-test.db."""

from datetime import timedelta
from pathlib import Path

from sqlalchemy.engine import make_url

from services.api.app.core.config import get_settings
from services.api.app.db.session import SessionLocal, utcnow
from services.api.app.models.job import IngestionRun, JobSource, SourceSync
from services.api.app.repositories.ingestion import upsert_job
from shared.schemas import NormalizedJob


def seed():
    url = make_url(get_settings().database_url)
    if url.get_backend_name() != "sqlite" or Path(url.database).name != "browser-test.db":
        raise ValueError("Browser fixtures require an isolated browser-test.db database")
    now = utcnow()
    with SessionLocal() as db:
        for provider in ("greenhouse", "lever", "ashby", "smartrecruiters", "usajobs", "workday"):
            source = JobSource(
                name=f"Browser fixture {provider}",
                company_name=f"Fixture {provider}",
                source_type=provider,
                board_identifier="browser-fixture",
                enabled=True,
                careers_url="https://example.com/test-fixture",
                last_successful_sync=now,
            )
            db.add(source)
            db.flush()
            for index, title in enumerate(
                (
                    "Junior Software Engineer",
                    "QA Analyst I",
                    "Cloud Support Associate",
                    "Application Support Analyst",
                )
            ):
                upsert_job(
                    db,
                    source.id,
                    NormalizedJob(
                        source=provider,
                        source_job_id=str(index),
                        company_name=f"Fixture {provider}",
                        title=title,
                        description=(
                            "Required: 0-2 years of experience. Build and test software "
                            "using Python, SQL and JavaScript. Collaborate with a "
                            "supportive technical team."
                        ),
                        source_url=f"https://example.com/test-fixture/{provider}/{index}",
                        apply_url=f"https://example.com/test-fixture/{provider}/{index}",
                        location_raw="Remote, United States",
                        country="US",
                        state="TX",
                        remote_type="remote",
                        posted_at=now,
                        closing_at=now + timedelta(days=30) if provider == "usajobs" else None,
                        provider_metadata={"agency": "Browser fixture agency"}
                        if provider == "usajobs"
                        else {},
                    ),
                )
            source.active_jobs = 4
            db.add(
                SourceSync(
                    source_id=source.id,
                    started_at=now,
                    completed_at=now,
                    status="success",
                    jobs_fetched=4,
                    jobs_created=4,
                )
            )
        db.add(
            IngestionRun(
                started_at=now,
                completed_at=now,
                status="success",
                summary={
                    "jobs_fetched": 24,
                    "sources_successful": 6,
                    "sources_failed": 0,
                    "duration_seconds": 1,
                },
            )
        )
        db.commit()
    print("Created isolated synthetic browser fixtures; no production sources contacted")


if __name__ == "__main__":
    seed()
