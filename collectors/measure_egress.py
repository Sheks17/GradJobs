"""Read-only local row-payload estimate; never downloads production job bodies."""

import argparse
import json
import sqlite3
from collections import Counter
from pathlib import Path

from services.api.app.schemas.jobs import JobDetail, JobSummary


def wire_size(values):
    # PostgreSQL text DataRow framing: type+length+column count, then length/value.
    # SQLite representations differ slightly from PG text/JSONB. This is an
    # application-row estimate, not TLS/protocol overhead or a billed-byte audit.
    return 7 + sum(
        4 + (len(str(value).encode("utf-8")) if value is not None else 0) for value in values
    )


def measure(path, output):
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    columns = [row[1] for row in connection.execute("PRAGMA table_info(jobs)")]
    state = ("source_job_id", "posted_at", "closing_at")
    totals = Counter()
    providers = Counter()
    api = Counter()
    sample_count = 0
    for row in connection.execute(
        "SELECT " + ",".join('"' + name + '"' for name in columns) + " FROM jobs"
    ):
        totals["rows"] += 1
        providers[row["source"]] += 1
        size = wire_size([row[name] for name in columns if name != "ingestion_fingerprint"])
        totals["baseline_source_prefetch_bytes"] += size
        if row["is_active"]:
            totals["baseline_lifecycle_bytes"] += size
        if row["source"] == "workday":
            totals["baseline_workday_cache_bytes"] += wire_size([row["raw_data"]])
        totals["warm_state_bytes"] += wire_size([row[name] for name in state] + ["0" * 64])
        if (
            sample_count < 12
            and row["is_active"]
            and row["country"] == "US"
            and row["early_career_score"] >= 50
        ):
            sample_count += 1
            api["list_before_bytes"] += size
            api["list_after_bytes"] += wire_size([row[name] for name in JobSummary.model_fields])
            api["detail_before_bytes"] += size
            api["detail_after_bytes"] += wire_size([row[name] for name in JobDetail.model_fields])
    connection.close()
    before = sum(
        totals[key]
        for key in (
            "baseline_source_prefetch_bytes",
            "baseline_lifecycle_bytes",
            "baseline_workday_cache_bytes",
        )
    )
    # Unchanged snapshot reconciliation returns no missing job rows. Control
    # records, SQL command statuses, changed postings and TLS overhead are separate.
    after = totals["warm_state_bytes"]
    report = dict(
        dataset=path.name,
        real_rows=totals["rows"],
        provider_rows=dict(providers),
        row_bytes=dict(totals),
        unchanged_sync_before_bytes=before,
        unchanged_sync_after_bytes=after,
        estimated_reduction_percent=round(100 * (1 - after / before), 2),
        api_sample_rows=sample_count,
        api_row_bytes=dict(api),
        caveats=(
            "Local real-posting snapshot. Text-row estimate, not measured Neon billing. "
            "Excludes control records, changed/expired postings and protocol/TLS overhead. "
            "Legacy initialization compares server-side, no job bodies returned. "
            "No production data read."
        ),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=Path("gradjobs-live.db"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/egress/estimate.json"))
    args = parser.parse_args()
    measure(args.database, args.output)
