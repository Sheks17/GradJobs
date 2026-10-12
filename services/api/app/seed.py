"""Idempotent, explicitly fictional data. Run only after applying migrations."""

from datetime import timedelta

from sqlalchemy import select

from services.api.app.db.session import SessionLocal, utcnow
from services.api.app.models.job import Job, JobSource
from services.api.app.repositories.ingestion import upsert_job
from shared.schemas import NormalizedJob

DEMO_ROLES = [
    ("Associate Software Engineer", "Austin, TX", "hybrid", "0–2", 72000, 92000),
    ("QA Analyst I", "Remote, United States", "remote", "0–1", 62000, 78000),
    ("Junior Front-End Developer", "Chicago, IL", "hybrid", "1–2", 68000, 88000),
    ("Cloud Support Associate", "Remote, United States", "remote", "0–2", 65000, 84000),
    ("Application Support Analyst", "Atlanta, GA", "onsite", "1–3", 60000, 75000),
    ("Implementation Analyst I", "New York, NY", "hybrid", "0–2", 70000, 85000),
    ("Junior Full-Stack Developer", "Denver, CO", "hybrid", "1–3", 75000, 95000),
    ("IT Analyst I", "Dallas, TX", "onsite", "0–1", 58000, 73000),
    ("Technical Support Engineer", "Remote, United States", "remote", "1–2", 66000, 86000),
    ("Junior Systems Administrator", "Raleigh, NC", "onsite", "1–2", 61000, 80000),
    ("Associate Product Support Engineer", "Boston, MA", "hybrid", "0–2", 64000, 82000),
    ("Software Test Engineer I", "Seattle, WA", "hybrid", "0–2", 78000, 98000),
    ("Business Systems Analyst I", "Minneapolis, MN", "onsite", "1–2", 65000, 80000),
    ("Junior Back-End Developer", "Remote, United States", "remote", "1–3", 76000, 96000),
    ("Cloud Operations Analyst", "Phoenix, AZ", "hybrid", "2–3", 71000, 87000),
    ("Associate Data Analyst", "San Diego, CA", "onsite", "0–2", 68000, 89000),
    ("Junior Security Analyst", "Arlington, VA", "hybrid", "1–2", 74000, 94000),
    ("Software Engineering Intern", "Remote, United States", "remote", "0–1", None, None),
    ("Senior Software Engineer", "New York, NY", "onsite", "5–7", 150000, 190000),
    ("Principal Cloud Architect", "Remote, United States", "remote", "8–10", 180000, 220000),
    ("Application Developer", "Columbus, OH", "hybrid", None, None, None),
]


def main() -> None:
    now = utcnow()
    with SessionLocal() as db:
        source = db.scalar(
            select(JobSource).where(
                JobSource.source_type == "manual", JobSource.board_identifier == "demo"
            )
        )
        if source is None:
            source = JobSource(
                name="GradJobs demo dataset",
                source_type="manual",
                board_identifier="demo",
                enabled=False,
            )
            db.add(source)
            db.flush()
        created_count = 0
        for index, (title, location, remote, experience, low, high) in enumerate(DEMO_ROLES):
            key = f"demo-{index + 1:03d}"
            if db.scalar(
                select(Job.id).where(Job.source_id == source.id, Job.source_job_id == key)
            ):
                continue
            company = f"Demo Company {chr(65 + index % 8)}"
            desc = (
                f"This is a fictional development listing from {company}.\n\n"
                "About the role\nJoin a collaborative technology team that values curiosity, "
                "careful problem solving, and continuous learning. You will work with a mentor "
                "and gradually own well-scoped projects.\n\n"
                "What you will do\n• Investigate technical issues and document solutions.\n"
                "• Collaborate with engineers, analysts, and customer-facing teams.\n"
                "• Write tests, review changes, and improve everyday tools.\n\n"
                "What you bring\nBachelor's degree in IT, computer science, or a related field, "
                "or equivalent practical learning.\n"
            )
            if experience:
                desc += f"{experience} years of relevant professional experience.\n"
            desc += (
                "Familiarity with Python, JavaScript, SQL, or troubleshooting workflows.\n\n"
                "How we support you\nStructured onboarding, a dedicated mentor, and time "
                "to build your skills.\n\nDemo only. Applications are not accepted."
            )
            posted = now - timedelta(hours=index * 9 + 2)
            job, _ = upsert_job(
                db,
                source.id,
                NormalizedJob(
                    source="manual",
                    source_job_id=key,
                    external_id=key,
                    company_name=company,
                    title=title,
                    description=desc,
                    location_raw=location,
                    country="US",
                    city=None if remote == "remote" else location.split(",")[0],
                    state=None if remote == "remote" else location.split(",")[1].strip(),
                    remote_type=remote,
                    salary_min=low,
                    salary_max=high,
                    salary_currency="USD" if low else None,
                    salary_period="year" if low else None,
                    posted_at=posted if index != 20 else None,
                    employment_type="Internship" if index == 17 else "Full-time",
                    source_url=f"https://example.invalid/gradjobs/{key}",
                    apply_url=f"https://example.invalid/gradjobs/{key}/apply",
                    is_demo=True,
                    raw_data={"demo": True, "note": "Fictional listing"},
                ),
            )
            job.first_seen_at = posted + timedelta(hours=1)
            created_count += 1
        db.commit()
        print(f"Created {created_count} clearly labeled demo jobs. Existing demo jobs unchanged.")


if __name__ == "__main__":
    main()
