"""Create an unlabeled provider-balanced holdout from public production job records."""

import argparse
import json
import random
from collections import Counter
from pathlib import Path

import httpx

from matching.review import export_review
from matching.sample_evaluation import LABELS
from services.api.app.db.session import utcnow

PROVIDERS = ("workday", "smartrecruiters", "usajobs", "greenhouse", "lever", "ashby")


def sample(base, exclude, output, seed=20261012):
    csv_path = output.with_suffix(".csv")
    if output.exists() or csv_path.exists():
        raise ValueError("Holdout exists; use a new output path to preserve human review")
    old = json.loads(exclude.read_text(encoding="utf-8"))["jobs"]
    identities = {(job["source"], str(job["source_job_id"])) for job in old}
    urls = {job["source_url"] for job in old}
    rng, records = random.Random(seed), []
    with httpx.Client(timeout=60) as client:
        for provider in PROVIDERS:
            pool = []
            for page in range(1, 4):
                response = client.get(
                    base + "/api/jobs",
                    params={
                        "provider": provider,
                        "country": "all",
                        "include_senior": True,
                        "min_early_career_score": 0,
                        "max_experience": 40,
                        "page_size": 100,
                        "page": page,
                        "sort": "company",
                    },
                )
                response.raise_for_status()
                pool.extend(response.json()["items"])
                if page >= response.json()["total_pages"]:
                    break
            rng.shuffle(pool)
            chosen = 0
            for row in pool:
                response = client.get(base + "/api/jobs/" + row["id"])
                response.raise_for_status()
                job = response.json()
                identity = (provider, str(job["source_job_id"]))
                if identity in identities or job["source_url"] in urls:
                    continue
                identities.add(identity)
                records.append(
                    {
                        "job_id": job["id"],
                        "source": provider,
                        "source_job_id": job["source_job_id"],
                        "company": job["company_name"],
                        "title": job["title"],
                        "description": job["description"],
                        "source_url": job["source_url"],
                        "location": job["location_raw"],
                        "posted_at": job["posted_at"],
                        "first_seen_at": job["first_seen_at"],
                        "label": None,
                        "notes": "",
                        "reviewer": "",
                    }
                )
                chosen += 1
                if chosen == 25:
                    break
            if chosen < 25:
                raise ValueError(
                    f"Only {chosen} eligible holdout postings for {provider}; "
                    "no partial file written"
                )
    dataset = {
        "created_at": utcnow().isoformat(),
        "random_seed": seed,
        "allowed_labels": LABELS,
        "label_policy": "Human review only; matching engine frozen.",
        "sampling_policy": (
            "25 per provider, random within first 300 company-sorted active canonical postings; "
            "excludes prior source IDs and URLs. Not prevalence weighted."
        ),
        "provider_counts": dict(Counter(row["source"] for row in records)),
        "jobs": records,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(dataset, indent=2), encoding="utf-8")
    export_review(dataset, csv_path)
    print(
        json.dumps(
            {
                "postings": len(records),
                "provider_counts": dataset["provider_counts"],
                "human_labels": 0,
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="https://gradjobs-drab.vercel.app")
    parser.add_argument("--exclude", type=Path, default=Path("data/evaluation/jobs.json"))
    parser.add_argument(
        "--output", type=Path, default=Path("data/evaluation/final_holdout_review.json")
    )
    args = parser.parse_args()
    sample(args.base, args.exclude, args.output)
