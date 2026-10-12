"""Keep SQLite planner estimates current after bulk ingestion or table rebuilding."""

from sqlalchemy import text

from collectors.locking import write_lock


def refresh_sqlite_statistics(db) -> bool:
    if db.get_bind().dialect.name != "sqlite":
        return False
    write_lock(db)
    previous_limit = db.execute(text("PRAGMA analysis_limit")).scalar_one()
    try:
        # Bound index sampling so periodic ingestion does not scan the entire database.
        db.execute(text("PRAGMA analysis_limit=1000"))
        db.execute(text("ANALYZE"))
    finally:
        db.execute(text(f"PRAGMA analysis_limit={int(previous_limit)}"))
    db.commit()
    return True
