"""Export a spreadsheet-safe review CSV; only humans supply review fields."""

import argparse
import copy
import csv
import hashlib
import json
import re
from pathlib import Path

from matching.sample_evaluation import LABELS
from matching.scoring import score_job

ERROR_CATEGORIES = (
    "experience_parser",
    "seniority_title",
    "role_family",
    "misleading_title",
    "education_equivalency",
    "preferred_vs_required",
    "description_ambiguity",
    "internship_wording",
    "management_wording",
    "location",
)


def fingerprint(job):
    content = json.dumps([job["job_id"], job["title"], job["description"]], ensure_ascii=False)
    return hashlib.sha256(content.encode()).hexdigest()


def safe_cell(value):
    text = str(value) if value is not None else ""
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text


def excerpt(description):
    lines = re.split(r"(?<=[.!?])\s+|\n+", description)
    relevant = [
        line
        for line in lines
        if re.search(
            r"experience|years?|qualifications|graduate|intern|required|preferred|leadership|manage",
            line,
            re.I,
        )
    ]
    return "\n".join(relevant)[:6000] or description[:2000]


def export_review(dataset, path):
    if not dataset["jobs"]:
        raise ValueError("Cannot export an empty evaluation sample")
    rows = []
    for job in dataset["jobs"]:
        result = score_job(job["title"], job["description"])
        # Import lazily to avoid a circular module import in the CLI.
        from matching.evaluate import prediction

        rows.append(
            {
                "job_id": job["job_id"],
                "title": job["title"],
                "company": job.get("company", ""),
                "role_family": result.role_family,
                "detected_seniority": result.seniority_level,
                "required_experience": json.dumps(
                    [result.required_min_years, result.required_max_years]
                ),
                "preferred_experience": json.dumps(
                    [result.preferred_min_years, result.preferred_max_years]
                ),
                "experience_category": result.experience_category,
                "early_career_score": result.early_career_score,
                "confidence_score": result.classification_confidence,
                "description_excerpt": excerpt(job["description"]),
                "full_description": job["description"],
                "location": job.get("location", ""),
                "source_url": job.get("source_url", ""),
                "predicted_classification": prediction(result.early_career_score),
                "matching_version": result.matching_version,
                "content_hash": fingerprint(job),
                "human_label": job.get("label") or "",
                "reviewer_notes": job.get("notes", ""),
                "reviewer": job.get("reviewer", ""),
                "error_categories": (
                    ";".join(job["error_categories"])
                    if isinstance(job.get("error_categories"), list)
                    else job.get("error_categories", "")
                ),
            }
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents accidental destruction of completed reviews.
    with path.open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows({key: safe_cell(value) for key, value in row.items()} for row in rows)
    return len(rows)


def load_reviews(dataset, path):
    """Join only human fields by immutable ID; never trust spreadsheet predictions."""
    result = copy.deepcopy(dataset)
    jobs = {job["job_id"]: job for job in result["jobs"]}
    if len(jobs) != len(result["jobs"]):
        raise ValueError("Duplicate job IDs in evaluation dataset")
    seen = set()
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"job_id", "content_hash", "human_label", "reviewer_notes", "error_categories"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("Missing review CSV columns")
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("Duplicate review CSV columns")
        for row in reader:
            if None in row or any(row.get(key) is None for key in required):
                raise ValueError("Malformed review CSV row")
            identity = row["job_id"]
            if identity in seen or identity not in jobs:
                raise ValueError(f"Duplicate or unknown review job ID: {identity}")
            seen.add(identity)
            job = jobs[identity]
            if row["content_hash"] != fingerprint(job):
                raise ValueError(f"Review content does not match dataset: {identity}")
            label = (row["human_label"] or "").strip()
            if label and label not in LABELS:
                raise ValueError(f"Invalid human label for {identity}: {label}")
            categories = [
                value.strip()
                for value in (row["error_categories"] or "").split(";")
                if value.strip()
            ]
            if set(categories) - set(ERROR_CATEGORIES):
                raise ValueError(f"Invalid error categories for {identity}")
            if categories and not label:
                raise ValueError(f"Error categories require a human label: {identity}")
            if job.get("label") and label != job["label"]:
                raise ValueError(f"Conflicting existing human label: {identity}")
            job.update(
                label=label or None,
                notes=row["reviewer_notes"] or "",
                reviewer=row.get("reviewer", ""),
                error_categories=categories,
            )
    if seen != set(jobs):
        raise ValueError("Review CSV must contain every sample ID (labels may be blank)")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/evaluation/jobs.json"))
    parser.add_argument("--output", type=Path, default=Path("data/evaluation/review.csv"))
    args = parser.parse_args()
    try:
        count = export_review(json.loads(args.input.read_text(encoding="utf-8")), args.output)
    except (ValueError, FileExistsError) as exc:
        parser.error(str(exc))
    print(f"Exported {count} review rows to {args.output}; no labels generated.")


if __name__ == "__main__":
    main()
