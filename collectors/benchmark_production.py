"""Read-only public production smoke and latency snapshot (no credentials)."""

import argparse
import json
import statistics
import time
from datetime import timedelta
from pathlib import Path

import httpx

from services.api.app.db.session import utcnow


def benchmark(base, output):
    fresh_after = (
        (utcnow() - timedelta(days=7)).isoformat(timespec="seconds").replace("+00:00", "Z")
    )
    cases = {
        "homepage": "/",
        "health": "/api/health",
        "stats": "/api/stats",
        "providers": "/api/stats/providers",
        "sources": "/api/sources",
        "default_jobs": (
            "/api/jobs?min_early_career_score=50&include_senior=false&page_size=12&fresh_after="
            + fresh_after
        ),
        "text_search": "/api/jobs?q=software&page_size=12",
        "skill": "/api/jobs?skill=python&page_size=12",
        "freshness": "/api/jobs?fresh_after="
        + utcnow().isoformat()[:10]
        + "T00:00:00Z&page_size=12",
        "provider": "/api/jobs?provider=greenhouse&page_size=12",
    }
    report = {"measured_at": utcnow().isoformat(), "base_url": base, "measurements": {}}
    with httpx.Client(timeout=60) as client:
        for name, path in cases.items():
            elapsed = []
            for _ in range(3):
                started = time.perf_counter()
                response = client.get(base + path)
                response.raise_for_status()
                elapsed.append(round((time.perf_counter() - started) * 1000, 1))
            report["measurements"][name] = {
                "status": response.status_code,
                "samples_ms": elapsed,
                "median_ms": statistics.median(elapsed),
            }
            if name in {"stats", "providers", "sources"}:
                report[name] = response.json()
            if name == "default_jobs" and response.json()["items"]:
                job = response.json()["items"][0]
                detail = client.get(base + "/api/jobs/" + job["id"])
                detail.raise_for_status()
                report["detail"] = {
                    "status": detail.status_code,
                    "id": job["id"],
                    "apply_url": detail.json()["apply_url"],
                }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "active_us_jobs": report["stats"]["active_jobs"],
                "registered_sources": len(report["sources"]),
                "measurements": report["measurements"],
            },
            indent=2,
        )
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="https://gradjobs-drab.vercel.app")
    parser.add_argument(
        "--output", type=Path, default=Path("artifacts/phase4b/production-benchmark.json")
    )
    args = parser.parse_args()
    benchmark(args.base, args.output)
