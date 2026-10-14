"""Compare validated source content without downloading descriptions/raw JSON."""

import hashlib
import json
from datetime import datetime
from types import SimpleNamespace

from sqlalchemy import case, select, update

from collectors.lifecycle import utc
from matching.scoring import MATCHING_VERSION
from services.api.app.db.session import utcnow
from services.api.app.models.job import Job

COMPUTED_REMOTE = {
    "remote_us_only",
    "remote_states",
    "excluded_states",
    "timezone_requirement",
    "remote_restriction_evidence",
}
STATE_COLUMNS = (
    Job.source_job_id,
    case(
        (
            Job.is_active.is_(True) & (Job.matching_version == MATCHING_VERSION),
            Job.ingestion_fingerprint,
        ),
        else_=None,
    ).label("ingestion_fingerprint"),
    Job.posted_at,
    Job.closing_at,
)


def source_fields(data):
    return data.model_dump(exclude=COMPUTED_REMOTE)


def content_fingerprint(data, posted_at=None, closing_at=None):
    fields = data.model_dump(mode="json", exclude=COMPUTED_REMOTE)
    if data.source == "workday":
        fields["raw_data"] = {
            key: value for key, value in fields["raw_data"].items() if key != "_detail_checked_at"
        }
        # This timestamp is GradJobs cache bookkeeping, not employer content.
        # Actual summaries/details and all normalized fields remain hashed.
    for name, fallback in (("posted_at", posted_at), ("closing_at", closing_at)):
        value = getattr(data, name) or fallback
        fields[name] = utc(value).isoformat() if value else None
    if data.source_updated_at:
        fields["source_updated_at"] = utc(data.source_updated_at).isoformat()
    # Hash all normalized source fields, including raw data; never a summary-only
    # change detector. Matching-derived fields/version remain a separate guard.
    payload = json.dumps(fields, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def source_state(db, source_id):
    return {
        row.source_job_id: SimpleNamespace(**row._mapping, source_id=source_id)
        for row in db.execute(select(*STATE_COLUMNS).where(Job.source_id == source_id))
    }


def unchanged(db, existing, data):
    if not existing:
        return False
    digest = content_fingerprint(data, existing.posted_at, existing.closing_at)
    if existing.ingestion_fingerprint:
        return existing.ingestion_fingerprint == digest
    # Legacy bootstrap compares content inside the database. Parameters travel
    # toward Neon; only UPDATE status/count travels back. No full-row download or
    # forced reclassification/rewrite just to initialize a fingerprint.
    conditions = [
        Job.source_id == existing.source_id,
        Job.source_job_id == existing.source_job_id,
        Job.is_active.is_(True),
        Job.matching_version == MATCHING_VERSION,
        Job.ingestion_fingerprint.is_(None),
    ]
    for key, value in source_fields(data).items():
        if key in {"posted_at", "closing_at"} and value is None:
            continue
        if isinstance(value, datetime):
            value = utc(value)
        conditions.append(getattr(Job, key) == value)
    result = db.execute(
        update(Job)
        .where(*conditions)
        .values(
            ingestion_fingerprint=digest,
            last_seen_at=utcnow(),
            missing_since=None,
            consecutive_missing_syncs=0,
            updated_at=Job.updated_at,
        )
        .execution_options(synchronize_session=False)
    )
    return result.rowcount == 1
