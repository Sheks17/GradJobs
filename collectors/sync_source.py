import argparse
import json
from dataclasses import asdict
from uuid import UUID

from collectors.sync_all import sync_one
from services.api.app.core.config import get_settings
from services.api.app.core.logging import configure_logging

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync one registered source")
    parser.add_argument("source_id", type=UUID)
    args = parser.parse_args()
    configure_logging(get_settings().log_level)
    result = sync_one(args.source_id)
    print(json.dumps(asdict(result), indent=2))
    raise SystemExit(1 if result.failures else 0)
