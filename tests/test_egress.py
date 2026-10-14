from contextlib import contextmanager
from datetime import timedelta

from sqlalchemy import event, select, update

from collectors.base import Collector
from collectors.ingestion_state import content_fingerprint
from collectors.public_cache import load_detail_cache, save_detail_cache
from collectors.runner import sync_source
from services.api.app.db.session import utcnow
from services.api.app.models.job import Job
from services.api.app.repositories.jobs import list_jobs
from services.api.app.schemas.jobs import JobFilters
from shared.schemas import NormalizedJob


class FixtureCollector(Collector):
    source_type = "lever"
    endpoint = "https://api.lever.co/{board}"

    def __init__(self):
        super().__init__("egress-fixture", "Fixture")
        self.data = NormalizedJob(
            source="lever",
            source_job_id="one",
            title="Junior Developer",
            company_name="Fixture",
            description="Required: 0-2 years Python. " + ("Public description. " * 100),
            source_url="https://example.com/job",
            apply_url="https://example.com/apply",
            country="US",
            raw_data={"large": "x" * 100_000},
            posted_at=utcnow() - timedelta(days=1),
        )

    def fetch(self):
        return [self.data]

    def normalize(self, row):
        return row


@contextmanager
def capture_selects(db):
    queries = []

    def capture(_, __, statement, ___, ____, _____):
        if statement.lstrip().upper().startswith("SELECT"):
            queries.append(statement.split("FROM", 1)[0].lower())

    engine = db.get_bind()
    event.listen(engine, "before_cursor_execute", capture)
    try:
        yield queries
    finally:
        event.remove(engine, "before_cursor_execute", capture)


def test_unchanged_sync_never_selects_body_and_preserves_updates(db):
    collector = FixtureCollector()
    try:
        assert sync_source(db, collector).created == 1
        original = db.execute(select(Job.id, Job.updated_at)).one()
        db.expunge_all()
        with capture_selects(db) as statements:
            result = sync_source(db, collector)
        assert result.unchanged == 1 and result.updated == 0
        assert all(
            "jobs.description" not in sql and "jobs.raw_data" not in sql for sql in statements
        )
        assert len([sql for sql in statements if "jobs." in sql]) <= 4
        assert db.execute(select(Job.id, Job.updated_at)).one() == original
    finally:
        collector.close()


def test_legacy_backfill_compares_inside_db_without_reclassifying(db):
    collector = FixtureCollector()
    try:
        sync_source(db, collector)
        original = db.scalar(select(Job.updated_at))
        db.execute(update(Job).values(ingestion_fingerprint=None, updated_at=Job.updated_at))
        db.commit()
        db.expunge_all()
        with capture_selects(db) as statements:
            result = sync_source(db, collector)
        assert result.unchanged == 1 and result.updated == 0
        assert db.scalar(select(Job.ingestion_fingerprint))
        assert db.scalar(select(Job.updated_at)) == original
        assert all(
            "jobs.raw_data" not in sql and "jobs.description" not in sql for sql in statements
        )
    finally:
        collector.close()


def test_raw_only_change_and_missing_dates_do_not_hide_changes(db):
    collector = FixtureCollector()
    try:
        sync_source(db, collector)
        posted = collector.data.posted_at
        collector.data.posted_at = None
        assert sync_source(db, collector).unchanged == 1
        collector.data.raw_data = {"large": "changed"}
        assert sync_source(db, collector).updated == 1
        assert db.scalar(select(Job.posted_at)).replace(tzinfo=posted.tzinfo) == posted
    finally:
        collector.close()


def test_content_hash_canonicalizes_json_key_order():
    collector = FixtureCollector()
    try:
        collector.data.raw_data = {"a": 1, "b": 2}
        first = content_fingerprint(collector.data)
        collector.data.raw_data = {"b": 2, "a": 1}
        assert content_fingerprint(collector.data) == first
    finally:
        collector.close()


def test_workday_cache_timestamp_does_not_trigger_a_posting_update():
    collector = FixtureCollector()
    try:
        data = collector.data.model_copy(
            update={
                "source": "workday",
                "raw_data": {"detail": {"description": "same"}, "_detail_checked_at": "2026-10-01"},
            }
        )
        digest = content_fingerprint(data)
        data.raw_data["_detail_checked_at"] = "2026-10-14"
        assert content_fingerprint(data) == digest
        data.raw_data["detail"]["description"] = "changed"
        assert content_fingerprint(data) != digest
    finally:
        collector.close()


def test_list_api_projection_does_not_select_description_or_raw(db):
    collector = FixtureCollector()
    try:
        sync_source(db, collector)
        db.expunge_all()
        with capture_selects(db) as statements:
            result = list_jobs(db, JobFilters())
        assert result.total == 1 and result.items[0].title == "Junior Developer"
        assert len(statements) == 2
        assert all(
            "jobs.raw_data" not in sql and "jobs.description" not in sql for sql in statements
        )
        assert "description" not in result.items[0].model_dump()
    finally:
        collector.close()


def test_public_detail_cache_is_optional_and_corruption_safe(tmp_path):
    payload = {"/job/one": {"detail": {"jobPostingInfo": {"id": "one"}}}}
    save_detail_cache("fixture", payload)
    assert load_detail_cache("fixture") == payload
    from collectors.public_cache import cache_path

    cache_path("fixture").write_bytes(b"bad gzip")
    assert load_detail_cache("fixture") == {}


def test_invalid_public_details_are_not_persisted_in_cache():
    def validate(value):
        if not value.get("description"):
            raise ValueError("missing description")

    save_detail_cache("fixture", {"good": {"description": "public"}, "bad": {}}, validate)
    assert load_detail_cache("fixture") == {"good": {"description": "public"}}
