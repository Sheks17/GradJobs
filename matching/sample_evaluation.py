"""Sample real postings for human review. Generated predictions are never labels."""

import argparse
import json
import random
import re
from collections import Counter
from pathlib import Path

from sqlalchemy import select

from matching.aliases import ROLE_FAMILIES
from matching.experience import extract_experience
from matching.role_classifier import classify_role, classify_seniority
from services.api.app.db.session import SessionLocal, utcnow
from services.api.app.models.job import Job

LABELS = ["strong_fit", "possible_fit", "stretch", "not_early_career"]


def sample_jobs(db, size=200, seed=20261008):
    jobs = db.scalars(
        select(Job).where(Job.is_active.is_(True), Job.is_demo.is_(False)).order_by(Job.id)
    ).all()
    rng = random.Random(seed)
    rng.shuffle(jobs)
    chosen = {}
    for family in ROLE_FAMILIES:
        if family == "Other":
            continue
        pool = [job for job in jobs if classify_role(job.title) == family]
        for job in pool[:6]:
            chosen[job.id] = job
    strata = [
        lambda j: classify_seniority(j.title) == "internship",
        lambda j: classify_seniority(j.title) in {"entry", "junior", "associate", "new_grad"},
        lambda j: classify_seniority(j.title) == "level_1",
        lambda j: extract_experience(j.description).category == "no_experience_required",
        lambda j: (
            bool(re.search(r"\b(?:junior|associate)\b", j.title, re.I))
            and (j.experience_min_years or 0) >= 4
        ),
        lambda j: j.experience_min_years is None,
        lambda j: j.experience_min_years is not None and j.experience_min_years <= 2,
        lambda j: j.experience_min_years == 3,
        lambda j: j.experience_min_years is not None and j.experience_min_years >= 4,
        lambda j: j.seniority_level in {"senior", "staff", "lead", "principal"},
        lambda j: j.experience_is_preferred,
    ]
    for predicate in strata:
        for job in [row for row in jobs if predicate(row)][:8]:
            if len(chosen) < size:
                chosen[job.id] = job
    for job in jobs:
        if len(chosen) >= size:
            break
        chosen[job.id] = job
    records = []
    for job in list(chosen.values())[:size]:
        records.append(
            {
                "job_id": str(job.id),
                "source": job.source,
                "source_job_id": job.source_job_id,
                "company": job.company_name,
                "title": job.title,
                "source_url": job.source_url,
                "description": job.description,
                "location": job.location_raw,
                "posted_at": job.posted_at.isoformat() if job.posted_at else None,
                "first_seen_at": job.first_seen_at.isoformat(),
                "sample_role": classify_role(job.title),
                "stored_prediction": {
                    "score": job.early_career_score,
                    "seniority": job.seniority_level,
                    "experience_min": job.experience_min_years,
                },
                "label": None,
                "notes": "",
                "reviewer": "",
            }
        )
    return {
        "created_at": utcnow().isoformat(),
        "random_seed": seed,
        "label_policy": (
            "Only a human reviewer should populate label. Store"
            "d predictions are unverified model output."
        ),
        "allowed_labels": LABELS,
        "sample_counts": dict(Counter(row["sample_role"] for row in records)),
        "jobs": records,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/evaluation/jobs.json"))
    parser.add_argument("--size", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20261008)
    args = parser.parse_args()
    if not 1 <= args.size <= 1000:
        parser.error("size must be between 1 and 1000")
    if args.output.exists():
        parser.error("Output exists; choose another path to preserve human review labels")
    with SessionLocal() as db:
        report = sample_jobs(db, args.size, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "sampled": len(report["jobs"]),
                "labeled": 0,
                "sample_counts": report["sample_counts"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
