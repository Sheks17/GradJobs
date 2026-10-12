from datetime import timedelta

from sqlalchemy import func, select

from services.api.app.db.session import utcnow
from services.api.app.models.job import Job, JobSource
from services.api.app.repositories.ingestion import upsert_job
from shared.schemas import NormalizedJob


def data(**changes):
    fields = dict(
        source="greenhouse",
        source_job_id="1",
        company_name="Demo Company A, Inc.",
        title="Junior Software Engineer",
        description="Build software with the team. " * 12,
        location_raw="Austin, TX",
        country="US",
        apply_url="https://example.com/jobs/1",
        source_url="https://example.com/jobs/1",
    )
    return NormalizedJob(**(fields | changes))


def test_upsert_keeps_id_and_first_seen(db, source):
    first, created = upsert_job(db, source.id, data())
    first.first_seen_at = utcnow() - timedelta(days=3)
    original_date = first.first_seen_at
    second, created_again = upsert_job(db, source.id, data(title="Junior Developer"))
    assert created and not created_again
    assert second.id == first.id and second.first_seen_at == original_date
    assert second.title == "Junior Developer"


def test_cross_source_duplicate_preserves_both_raw_records(db, source):
    other = JobSource(name="Other", source_type="lever", board_identifier="demo")
    db.add(other)
    db.flush()
    first, _ = upsert_job(db, source.id, data())
    second, _ = upsert_job(
        db,
        other.id,
        data(source="lever", source_job_id="other", apply_url="https://other.example/jobs/1"),
    )
    assert second.duplicate_of == first.id
    assert db.scalar(select(func.count()).select_from(Job)) == 2
    assert db.scalar(select(func.count()).select_from(Job).where(Job.duplicate_of.is_(None))) == 1


def test_do_not_merge_distinct_requisitions_on_same_board(db, source):
    first, _ = upsert_job(db, source.id, data())
    second, _ = upsert_job(
        db, source.id, data(source_job_id="2", apply_url="https://example.com/jobs/2")
    )
    assert first.id != second.id and second.duplicate_of is None


def test_do_not_merge_different_locations_or_short_boilerplate(db, source):
    other = JobSource(name="Other", source_type="lever", board_identifier="demo")
    db.add(other)
    db.flush()
    upsert_job(db, source.id, data())
    second, _ = upsert_job(
        db,
        other.id,
        data(
            source="lever",
            source_job_id="2",
            location_raw="Seattle, WA",
            apply_url="https://other.example/jobs/2",
        ),
    )
    assert second.duplicate_of is None
    third, _ = upsert_job(
        db,
        other.id,
        data(
            source="lever",
            source_job_id="3",
            description="Join us",
            apply_url="https://other.example/3",
        ),
    )
    assert third.duplicate_of is None
