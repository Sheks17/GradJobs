"""Benchmark real list/count queries against isolated SQLite replicas of saved postings."""

import argparse
import json
import math
import statistics
import time
import uuid
from datetime import timedelta
from pathlib import Path

from sqlalchemy import create_engine, event, insert, select, text
from sqlalchemy.orm import Session

from services.api.app.db.session import Base, SessionLocal, utcnow
from services.api.app.models.job import Job, JobLocation, JobSkill, JobSource
from services.api.app.repositories.jobs import list_jobs
from services.api.app.schemas.jobs import JobFilters


def benchmark(output_dir, sizes=(10000, 25000, 50000), repeats=7, reuse_dir=None):
    output_dir.mkdir(parents=True, exist_ok=True)
    # Read-only snapshot. Replicas carry real descriptions and matching distributions,
    # but have synthetic identities and cannot be mistaken for live ingested postings.
    with SessionLocal() as db:
        originals = [
            dict(row)
            for row in db.execute(
                select(Job.__table__)
                .where(Job.is_active.is_(True), Job.is_demo.is_(False))
                .order_by(Job.id)
            ).mappings()
        ]
    if not originals:
        raise ValueError("No real postings available for scale benchmark")
    result = {"kind": "synthetic replicas of real saved postings", "repeats": repeats, "sizes": []}
    cases = {
        "default": {},
        "search_react": {"q": "React"},
        "multiword_search": {"q": "software engineer"},
        "remote_python": {"skill": "Python", "remote_type": "remote"},
        "qa_skill": {"role_family": "QA / Testing", "skill": "Playwright", "max_experience": 2},
        "state_tx": {"state": "TX"},
        "score_sort": {"sort": "early_career_score"},
        "all_dates_search": {"q": "React", "fresh_after": None},
    }
    for size in sizes:
        path = (reuse_dir or output_dir) / f"benchmark-{size}.db"
        if reuse_dir and not path.exists():
            raise ValueError(f"Missing replica: {path}")
        if not reuse_dir and path.exists():
            raise ValueError(
                f"Benchmark file already exists: {path}; choose another output directory"
            )
        engine = create_engine(f"sqlite:///{path.as_posix()}")
        if not reuse_dir:
            Base.metadata.create_all(engine)
            source_id = uuid.uuid4()
            with engine.begin() as connection:
                connection.execute(
                    insert(JobSource),
                    {
                        "id": source_id,
                        "name": "Benchmark replica",
                        "source_type": "manual",
                        "enabled": False,
                        "board_identifier": "benchmark",
                    },
                )
                for start in range(0, size, 250):
                    jobs, skills, locations = [], [], []
                    for index in range(start, min(start + 250, size)):
                        original = originals[index % len(originals)]
                        job = dict(original)
                        job_id = uuid.uuid5(
                            uuid.NAMESPACE_URL, f"gradjobs-benchmark:{size}:{index}"
                        )
                        job.update(
                            id=job_id,
                            source_id=source_id,
                            source_job_id=f"replica-{index}",
                            duplicate_of=None,
                            raw_data={},
                        )
                        jobs.append(job)
                        skills.extend(
                            {"job_id": job_id, "skill": skill} for skill in job["detected_skills"]
                        )
                        locations.extend({"job_id": job_id, **loc} for loc in job["locations"])
                    connection.execute(insert(Job), jobs)
                    if skills:
                        connection.execute(insert(JobSkill), skills)
                    if locations:
                        connection.execute(insert(JobLocation), locations)
                connection.execute(text("ANALYZE"))
        measurements = {}
        plans = {}
        for name, values in cases.items():
            timings = []
            filters = JobFilters(
                **{
                    "page_size": 12,
                    "fresh_after": utcnow() - timedelta(days=7),
                    **values,
                }
            )
            with Session(engine) as db:
                captured = []

                def capture(
                    conn, cursor, statement, parameters, context, executemany, captured=captured
                ):
                    if statement.startswith("SELECT"):
                        captured.append((statement, parameters))

                event.listen(engine, "before_cursor_execute", capture)
                list_jobs(db, filters)  # warmup, excluded from the results
                event.remove(engine, "before_cursor_execute", capture)
                with engine.connect() as connection:
                    plans[name] = [
                        [
                            list(row)
                            for row in connection.exec_driver_sql(
                                "EXPLAIN QUERY PLAN " + sql, params
                            )
                        ]
                        for sql, params in captured
                    ]
                for _ in range(repeats):
                    db.expunge_all()
                    began = time.perf_counter()
                    page = list_jobs(db, filters)
                    timings.append((time.perf_counter() - began) * 1000)
            measurements[name] = {
                "median_ms": round(statistics.median(timings), 2),
                "p95_ms": round(sorted(timings)[math.ceil(len(timings) * 0.95) - 1], 2),
                "matches": page.total,
            }
        with engine.connect() as connection:
            for name, query in {
                "skills": "SELECT job_id FROM job_skills WHERE skill='Python'",
                "location": "SELECT job_id FROM job_locations WHERE country='US' AND state='TX'",
            }.items():
                plans[name] = [
                    list(row) for row in connection.execute(text("EXPLAIN QUERY PLAN " + query))
                ]
        engine.dispose()
        result["sizes"].append({"jobs": size, "queries": measurements, "index_plans": plans})
        print(json.dumps(result["sizes"][-1]), flush=True)
    (output_dir / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/phase3/performance"))
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument(
        "--reuse-dir", type=Path, help="Read existing replicas without populating them"
    )
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("repeats must be positive")
    benchmark(args.output_dir, repeats=args.repeats, reuse_dir=args.reuse_dir)


if __name__ == "__main__":
    main()
