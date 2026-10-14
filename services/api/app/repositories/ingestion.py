import uuid
from datetime import UTC

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session, load_only

from collectors.normalizers.location import remote_restrictions
from collectors.normalizers.text import (
    description_fingerprint,
    normalize_company,
    normalize_text,
    normalize_title,
    normalize_url,
)
from matching.scoring import score_job
from services.api.app.db.session import utcnow
from services.api.app.models.job import Job, JobLocation, JobSkill
from shared.schemas import NormalizedJob


def duplicate_candidate(db: Session, fields: dict, job_id: uuid.UUID) -> Job | None:
    candidates = db.scalars(
        select(Job)
        .options(
            load_only(
                Job.id,
                Job.normalized_location,
                Job.normalized_apply_url,
                Job.source,
                raiseload=True,
            )
        )
        .where(
            Job.id != job_id,
            Job.duplicate_of.is_(None),
            Job.is_active.is_(True),
            Job.company_slug == fields["company_slug"],
            Job.normalized_title == fields["normalized_title"],
            Job.is_demo == fields["is_demo"],
            or_(
                Job.normalized_apply_url == fields["normalized_apply_url"],
                Job.description_fingerprint == fields["description_fingerprint"],
            ),
        )
        .order_by(Job.first_seen_at, Job.id)
    )
    for candidate in candidates:
        if (
            candidate.normalized_location
            and fields["normalized_location"]
            and candidate.normalized_location != fields["normalized_location"]
        ):
            continue
        if candidate.normalized_apply_url == fields["normalized_apply_url"]:
            return candidate
        if (
            candidate.source != fields["source"]
            and len(fields["description"]) >= 160
            and fields["normalized_location"]
            and candidate.normalized_location == fields["normalized_location"]
        ):
            return candidate
    return None


def upsert_job(db: Session, source_id: uuid.UUID, data: NormalizedJob) -> tuple[Job, bool]:
    job = db.scalar(
        select(Job)
        .options(load_only(Job.id, Job.posted_at, Job.closing_at, Job.closed_at, raiseload=True))
        .where(Job.source_id == source_id, Job.source_job_id == data.source_job_id)
    )
    created = job is None
    job_id = job.id if job else uuid.uuid4()
    fields = data.model_dump()
    from collectors.ingestion_state import content_fingerprint

    fields["ingestion_fingerprint"] = content_fingerprint(
        data, job.posted_at if job else None, job.closing_at if job else None
    )
    fields.update(
        company_slug=normalize_company(data.company_name).replace(" ", "-"),
        normalized_title=normalize_title(data.title),
        normalized_location=normalize_text(data.location_raw),
        normalized_apply_url=normalize_url(data.apply_url),
        description_fingerprint=description_fingerprint(data.description),
        **score_job(data.title, data.description).to_dict(),
        **(
            {
                key: getattr(data, key)
                for key in (
                    "remote_us_only",
                    "remote_states",
                    "excluded_states",
                    "timezone_requirement",
                    "remote_restriction_evidence",
                )
            }
            if "remote_restrictions" in data.provider_metadata
            else remote_restrictions(data.location_raw or "", data.description)
        ),
    )
    duplicate = duplicate_candidate(db, fields, job_id)
    fields.update(
        duplicate_of=duplicate.id if duplicate else None,
        last_seen_at=utcnow(),
        is_active=True,
        closed_at=None,
        missing_since=None,
        consecutive_missing_syncs=0,
    )
    if data.closing_at and data.closing_at.astimezone(UTC) <= utcnow():
        fields.update(is_active=False, closed_at=utcnow())
    if job is None:
        job = Job(id=job_id, source_id=source_id, **fields)
        db.add(job)
    else:
        # Do not erase an employer posting date if a later response omits it.
        if fields["posted_at"] is None:
            fields.pop("posted_at")
        if fields["closing_at"] is None:
            fields.pop("closing_at")
            if job.closing_at:
                deadline = (
                    job.closing_at.replace(tzinfo=UTC)
                    if job.closing_at.tzinfo is None
                    else job.closing_at
                )
                if deadline <= utcnow():
                    fields.update(is_active=False, closed_at=job.closed_at or utcnow())
        for name, value in fields.items():
            setattr(job, name, value)
    db.flush()
    db.execute(delete(JobLocation).where(JobLocation.job_id == job.id))
    locations = data.locations or [
        {key: getattr(data, key) for key in ("location_raw", "city", "state", "country")}
    ]
    db.add_all(
        [
            JobLocation(
                job_id=job.id,
                **{key: loc.get(key) for key in ("location_raw", "city", "state", "country")},
            )
            for loc in locations
        ]
    )
    db.flush()
    replace_skills(db, job)
    return job, created


def replace_skills(db: Session, job: Job) -> None:
    db.execute(delete(JobSkill).where(JobSkill.job_id == job.id))
    db.add_all([JobSkill(job_id=job.id, skill=skill) for skill in job.detected_skills])
    db.flush()
