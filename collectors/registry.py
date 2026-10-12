import argparse
import json

from collectors.locking import write_lock
from collectors.providers import PROVIDERS, make_collector
from services.api.app.db.session import SessionLocal
from services.api.app.schemas.sources import SourceCreate
from services.api.app.services.sources import register_source

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify and register an employer board")
    parser.add_argument("provider", choices=PROVIDERS)
    parser.add_argument("board")
    parser.add_argument("--company", required=True)
    parser.add_argument("--careers-url")
    parser.add_argument("--config", help="Provider configuration JSON; never credentials")
    args = parser.parse_args()
    data = SourceCreate(
        provider=args.provider,
        board_token=args.board,
        company_name=args.company,
        careers_url=args.careers_url,
        provider_config=json.loads(args.config) if args.config else {},
    )
    collector = make_collector(
        data.provider, data.board_token, data.company_name, data.provider_config
    )
    try:
        rows = collector.fetch()
        for row in rows:
            collector.normalize(row)
        if not collector.snapshot_complete or not rows:
            raise ValueError("Registration requires a complete, nonempty verified snapshot")
    finally:
        collector.close()
    with SessionLocal() as db:
        write_lock(db)
        source, created = register_source(db, data)
        db.commit()
        print(f"Verified {len(rows)} postings. Source {source.id}. Created: {created}")
