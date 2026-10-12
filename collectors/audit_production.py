"""Read-only PostgreSQL schema and population audit; no URLs or job payloads."""

import argparse
import json
from pathlib import Path

from sqlalchemy import text

from collectors.production_check import require_postgres
from services.api.app.db.session import engine, utcnow


def audit():
    require_postgres()
    with engine.connect() as connection:
        connection.execute(text("SET TRANSACTION READ ONLY"))
        revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
        counts = {
            table: connection.scalar(text(f"SELECT count(*) FROM {table}"))
            for table in ("jobs", "job_sources", "source_syncs", "ingestion_runs", "job_locations")
        }
        indexes = connection.execute(
            text(
                "SELECT tablename, indexname FROM pg_indexes "
                "WHERE schemaname = current_schema() ORDER BY tablename, indexname"
            )
        ).all()
        json_columns = connection.execute(
            text(
                "SELECT table_name, column_name, udt_name FROM information_schema.columns "
                "WHERE table_schema = current_schema() AND udt_name = 'jsonb' "
                "ORDER BY table_name, column_name"
            )
        ).all()
        canonical = connection.scalar(
            text(
                "SELECT count(*) FROM jobs WHERE is_active AND NOT is_demo AND duplicate_of IS NULL"
            )
        )
    return {
        "measured_at": utcnow().isoformat(),
        "database": "PostgreSQL",
        "alembic_revision": revision,
        "row_counts": counts,
        "active_canonical_jobs_all_countries": canonical,
        "indexes": [{"table": table, "name": name} for table, name in indexes],
        "jsonb_columns": [{"table": table, "column": column} for table, column, _ in json_columns],
        "scope": "Read-only catalog and count queries; no credentials or posting content.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("artifacts/database-audit.json"))
    args = parser.parse_args()
    report = audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("database", "alembic_revision", "row_counts")}))
