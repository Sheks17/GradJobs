"""Retry completed partial/failed sources without repeating the full import."""

import json
from dataclasses import asdict

from sqlalchemy import select

from collectors.sync_all import sync_one
from services.api.app.core.config import get_settings
from services.api.app.core.logging import configure_logging
from services.api.app.db.session import SessionLocal
from services.api.app.models.job import JobSource


def main() -> None:
    configure_logging(get_settings().log_level)
    with SessionLocal() as db:
        identities = db.scalars(
            select(JobSource.id)
            .where(
                JobSource.enabled.is_(True),
                JobSource.last_error.is_not(None),
                JobSource.sync_token.is_(None),
            )
            .order_by(JobSource.name)
        ).all()
    results = [asdict(sync_one(identity)) for identity in identities]
    print(json.dumps({"sources_retried": len(results), "results": results}, indent=2))
    raise SystemExit(1 if any(result["failures"] for result in results) else 0)


if __name__ == "__main__":
    main()
