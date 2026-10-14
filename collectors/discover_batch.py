"""Resumable candidate verification. Never registers or enables a source."""

import argparse
import csv
import json
from pathlib import Path

from collectors.discover import discover
from services.api.app.db.session import utcnow


def discover_batch(path, output, retry=False):
    records = json.loads(output.read_text(encoding="utf-8")) if output.exists() else []
    previous = {row["careers_url"]: row for row in records}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        candidates = list(csv.DictReader(handle))
    for candidate in candidates:
        url = candidate["careers_url"].strip()
        if url in previous and (
            previous[url].get("verified")
            or previous[url].get("stage") == "unsupported_provider"
            or not retry
        ):
            continue
        record = {**candidate, "stage": "discovered", "verified": False}
        try:
            result = discover(url)
            record.update(result)
            if result.get("verified") and result.get("jobs") == 0:
                record.update(
                    verified=False,
                    reason="Endpoint reachable but no usable postings; not eligible for activation",
                )
            record["stage"] = (
                "unsupported_provider"
                if result.get("public_ingestion") == "detection_only"
                else "verified"
                if record["verified"]
                else "provider_detected"
                if result["provider"] != "unknown"
                else "rejected"
            )
        except Exception as exc:
            record.update(stage="temporarily_unavailable", reason=type(exc).__name__)
        record["checked_at"] = utcnow().isoformat()
        if record["stage"] == "unsupported_provider":
            record["last_checked"] = record["checked_at"]
            record["future_review_after"] = None
        previous[url] = record
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(".tmp")
        temporary.write_text(json.dumps(list(previous.values()), indent=2), encoding="utf-8")
        temporary.replace(output)
        print(
            json.dumps(
                {key: record.get(key) for key in ("company_name", "stage", "provider", "jobs")}
            ),
            flush=True,
        )
    return list(previous.values())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, default=Path("artifacts/discovery/candidates.json"))
    parser.add_argument("--retry", action="store_true", help="Retry unsuccessful candidates")
    args = parser.parse_args()
    discover_batch(args.input, args.output, args.retry)
