"""Short database write locks; HTTP fetches run outside write transactions."""

from threading import Lock

from sqlalchemy import event, text
from sqlalchemy.orm import Session

_sqlite_writer = Lock()


@event.listens_for(Session, "after_transaction_end")
def release_sqlite_writer(db, transaction):
    if transaction.parent is None and db.info.pop("sqlite_writer_held", False):
        _sqlite_writer.release()


def write_lock(db: Session) -> None:
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(7142301)"))
    elif db.get_bind().dialect.name == "sqlite":
        if db.info.get("sqlite_writer_held"):
            return
        # Queue workers before entering SQLite's finite busy timeout. HTTP stays concurrent.
        _sqlite_writer.acquire()
        db.info["sqlite_writer_held"] = True
        try:
            db.execute(text("BEGIN IMMEDIATE"))
        except Exception:
            db.info.pop("sqlite_writer_held", None)
            _sqlite_writer.release()
            raise
