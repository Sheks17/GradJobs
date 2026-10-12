import argparse
import json
import sys

from collectors.providers import PROVIDERS, make_collector
from collectors.runner import sync_source
from services.api.app.core.config import get_settings
from services.api.app.core.logging import configure_logging
from services.api.app.db.session import SessionLocal


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync one public employer job board")
    parser.add_argument("provider", choices=PROVIDERS)
    parser.add_argument("board", help="Provider board identifier (not a URL)")
    parser.add_argument("--company", required=True, help="Employer's actual display name")
    parser.add_argument("--config", default="{}", help="Provider configuration JSON")
    args = parser.parse_args()
    configure_logging(get_settings().log_level)
    collector = make_collector(args.provider, args.board, args.company, json.loads(args.config))
    try:
        with SessionLocal() as db:
            result = sync_source(db, collector)
        sys.exit(1 if result.failures else 0)
    finally:
        collector.close()


if __name__ == "__main__":
    main()
