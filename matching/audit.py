"""Reproducible quality indicators from stored jobs; flags are review cues, not labels."""

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

from sqlalchemy import select

from services.api.app.db.session import SessionLocal, utcnow
from services.api.app.models.job import Job, SourceSync

SENIOR = {"senior", "staff", "principal", "lead", "manager", "director", "executive"}
EARLY = {"internship", "entry", "new_grad", "junior", "associate", "early_career", "level_1"}


def indicators(job) -> list[str]:
    flags = []
    minimum = job.required_min_years if job.matching_version else job.experience_min_years
    if job.seniority_level in SENIOR and job.early_career_score >= 80:
        flags.append("high_score_senior")
    if job.seniority_level in EARLY and minimum is not None and minimum >= 5:
        flags.append("early_title_high_experience")
    if job.seniority_level == "junior" and minimum is not None and minimum >= 4:
        flags.append("junior_four_plus")
    if job.seniority_level in EARLY and job.early_career_score < 50:
        flags.append("low_score_early_title")
    if minimum is not None and minimum >= 3 and job.early_career_score >= 80:
        flags.append("high_score_required_three_plus")
    if job.role_family == "Other":
        flags.append("unknown_role")
        if re.search(
            r"\b(?:software|developer|support engineer|machine learning|devops|sre)\b",
            job.title,
            re.I,
        ):
            flags.append("technical_title_unknown_role")
    locations = job.locations or [{"country": job.country}]
    if not any(loc.get("country") for loc in locations):
        flags.append("ambiguous_location")
    if minimum is None and re.search(
        r"\b(?:extensive|significant|substantial)\s+(?:professional\s+)?experience\b",
        job.description,
        re.I,
    ):
        flags.append("unquantified_experience")
    if not job.description.strip():
        flags.append("empty_description")
    if job.classification_conflict:
        flags.append("classification_conflict")
    return flags


def collect_audit(db, source: str | None = None) -> dict:
    query = select(Job).where(Job.is_active.is_(True), Job.is_demo.is_(False))
    if source:
        query = query.where(Job.source == source)
    jobs = db.scalars(query.order_by(Job.id)).all()
    counts = Counter()
    review = []
    for job in jobs:
        flags = indicators(job)
        counts.update(flags)
        if flags:
            review.append(
                {
                    "id": str(job.id),
                    "title": job.title,
                    "company": job.company_name,
                    "source": job.source,
                    "role_family": job.role_family,
                    "seniority": job.seniority_level,
                    "score": job.early_career_score,
                    "experience_min_years": job.experience_min_years,
                    "required_min_years": job.required_min_years,
                    "preferred_min_years": job.preferred_min_years,
                    "confidence": job.classification_confidence,
                    "conflict_reasons": job.conflict_reasons,
                    "location": job.location_raw,
                    "flags": flags,
                }
            )

    def score_band(score):
        return f"{score // 10 * 10}-{score // 10 * 10 + 9}" if score < 90 else "90-100"

    def experience_band(job):
        years = job.experience_min_years
        if years is None:
            return "unspecified"
        return str(years) if years < 5 else "5+"

    failed_rows = sum(db.scalars(select(SourceSync.jobs_failed)))
    return {
        "generated_at": utcnow().isoformat(),
        "source_filter": source,
        "active_jobs": len(jobs),
        "canonical_jobs": sum(job.duplicate_of is None for job in jobs),
        "role_families": dict(sorted(Counter(job.role_family for job in jobs).items())),
        "seniority": dict(sorted(Counter(job.seniority_level for job in jobs).items())),
        "experience_minimum": dict(sorted(Counter(experience_band(job) for job in jobs).items())),
        "experience_categories": dict(
            sorted(Counter(getattr(job, "experience_category", "legacy") for job in jobs).items())
        ),
        "score_bands": dict(
            sorted(Counter(score_band(job.early_career_score) for job in jobs).items())
        ),
        "high_score_jobs": sum(job.early_career_score >= 80 for job in jobs),
        "missing_experience": sum(job.experience_min_years is None for job in jobs),
        "missing_posting_date": sum(job.posted_at is None for job in jobs),
        "remote_jobs": sum(job.remote_type == "remote" for job in jobs),
        "preferred_only": sum(job.experience_is_preferred for job in jobs),
        "stored_conflicts": sum(getattr(job, "classification_conflict", False) for job in jobs),
        "failed_postings_in_history": failed_rows,
        "flags": dict(sorted(counts.items())),
        "review": review,
    }


def markdown_report(report: dict) -> str:
    lines = [
        "# GradJobs Matching Audit",
        "",
        f"Generated: {report['generated_at']}",
        "",
        "Active non-demo source records; flags are deterministic review cues, not proven errors.",
        "",
    ]
    for name in (
        "active_jobs",
        "canonical_jobs",
        "high_score_jobs",
        "missing_experience",
        "missing_posting_date",
        "remote_jobs",
        "preferred_only",
        "stored_conflicts",
        "failed_postings_in_history",
    ):
        lines.append(f"- {name.replace('_', ' ').capitalize()}: **{report[name]:,}**")
    for group in (
        "score_bands",
        "role_families",
        "seniority",
        "experience_minimum",
        "experience_categories",
        "flags",
    ):
        lines.extend(
            [
                "",
                f"## {group.replace('_', ' ').title()}",
                "",
                "| Category | Jobs |",
                "| --- | ---: |",
            ]
        )
        lines.extend(f"| {name} | {count:,} |" for name, count in report[group].items())
    lines.extend(
        [
            "",
            "## Reproduce",
            "",
            "```sh",
            (
                "python -m matching.audit --json artifacts/phase3/a"
                "udit.json --csv artifacts/phase3/review.csv --mark"
                "down docs/matching-audit.md"
            ),
            "```",
            "",
            (
                "Review flags use stored title levels and effective"
                " required years (legacy preferred years before Pha"
                "se 3). Ambiguous location means no normalized coun"
                "try in any location. Unknown role includes nontech"
                "nical occupations and is not automatically a class"
                "ification failure. History failures are cumulative"
                ", not a matching precision metric."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source")
    parser.add_argument("--json", type=Path)
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args()
    with SessionLocal() as db:
        report = collect_audit(db, args.source)
    for path in (args.json, args.csv, args.markdown):
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
    if args.json:
        args.json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.markdown:
        args.markdown.write_text(markdown_report(report), encoding="utf-8")
    if args.csv:
        with args.csv.open("w", newline="", encoding="utf-8") as handle:
            fields = [
                "id",
                "title",
                "company",
                "source",
                "role_family",
                "seniority",
                "score",
                "experience_min_years",
                "required_min_years",
                "preferred_min_years",
                "confidence",
                "conflict_reasons",
                "location",
                "flags",
            ]
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for row in report["review"]:
                safe = {
                    key: "; ".join(value) if isinstance(value, list) else value
                    for key, value in row.items()
                }
                # CSVs are for review; prevent employer text becoming spreadsheet formulas.
                writer.writerow(
                    {
                        key: "'" + value
                        if isinstance(value, str) and value.startswith(("=", "+", "-", "@"))
                        else value
                        for key, value in safe.items()
                    }
                )
    print(
        "GradJobs Matching Audit\n"
        + json.dumps({key: value for key, value in report.items() if key != "review"}, indent=2)
    )


if __name__ == "__main__":
    main()
