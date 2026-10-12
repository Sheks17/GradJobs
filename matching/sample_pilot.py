"""Create a fresh provider-balanced, unlabeled pilot sample without reusing Phase 3 IDs."""

import argparse
import json
import random
from collections import Counter
from pathlib import Path

from sqlalchemy import select

from matching.review import export_review
from matching.sample_evaluation import LABELS
from services.api.app.db.session import SessionLocal, utcnow
from services.api.app.models.job import Job


def sample_pilot(db, excluded_ids, seed=20261010):
    budgets = {"smartrecruiters": 35, "usajobs": 35, "greenhouse": 10, "lever": 10, "ashby": 10}
    rng = random.Random(seed)
    records = []
    for provider, size in budgets.items():
        pool = list(
            db.scalars(
                select(Job)
                .where(
                    Job.source == provider,
                    Job.is_active.is_(True),
                    Job.is_demo.is_(False),
                    Job.duplicate_of.is_(None),
                )
                .order_by(Job.id)
            )
        )
        pool = [job for job in pool if str(job.id) not in excluded_ids]
        rng.shuffle(pool)
        # Include both accessible and experienced postings, not just highest-scoring rows.
        positive = [job for job in pool if job.early_career_score >= 50]
        negative = [job for job in pool if job.early_career_score < 50]
        chosen = positive[: size // 2] + negative[: size - size // 2]
        selected = {job.id for job in chosen}
        for job in pool:
            if len(chosen) >= size:
                break
            if job.id not in selected:
                chosen.append(job)
                selected.add(job.id)
        for job in chosen:
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
                    "closing_at": job.closing_at.isoformat() if job.closing_at else None,
                    "provider_metadata": job.provider_metadata,
                    "sample_role": job.role_family,
                    "stored_prediction": {
                        "score": job.early_career_score,
                        "seniority": job.seniority_level,
                    },
                    "label": None,
                    "notes": "",
                    "reviewer": "",
                }
            )
    return {
        "created_at": utcnow().isoformat(),
        "random_seed": seed,
        "allowed_labels": LABELS,
        "label_policy": "Human review only. No labels generated.",
        "sampling_policy": (
            "Provider and score stratified; not prevalence weighted. "
            "Excludes all Phase 3 sample IDs."
        ),
        "provider_counts": dict(Counter(job["source"] for job in records)),
        "jobs": records,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/evaluation/phase4-pilot.json"))
    parser.add_argument("--exclude", type=Path, default=Path("data/evaluation/jobs.json"))
    args = parser.parse_args()
    csv_path = args.output.with_suffix(".csv")
    if args.output.exists() or csv_path.exists():
        parser.error("Pilot files exist; choose a new version to preserve review labels")
    excluded = {
        job["job_id"] for job in json.loads(args.exclude.read_text(encoding="utf-8"))["jobs"]
    }
    with SessionLocal() as db:
        result = sample_pilot(db, excluded)
    if not result["provider_counts"].get("smartrecruiters") or not result["provider_counts"].get(
        "usajobs"
    ):
        parser.error("Both new providers need active pilot jobs before sampling")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    export_review(result, csv_path)
    print(
        json.dumps(
            {
                "sampled": len(result["jobs"]),
                "provider_counts": result["provider_counts"],
                "human_labeled": 0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
