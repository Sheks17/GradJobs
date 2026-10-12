"""Foreground scheduler: stop with Ctrl+C. A service manager should own its lifetime."""

import argparse
import json
import logging
import time

from collectors.sync_all import sync_all
from services.api.app.core.config import get_settings
from services.api.app.core.logging import configure_logging


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    parser.add_argument(
        "--wait-first", action="store_true", help="Wait one interval before the first pass"
    )
    args = parser.parse_args()
    settings = get_settings()
    configure_logging(settings.log_level)
    try:
        if args.wait_first:
            print(f"Next sync in {settings.sync_interval_minutes} minutes.", flush=True)
            time.sleep(settings.sync_interval_minutes * 60)
        while True:
            try:
                result = sync_all()
                print(json.dumps({k: v for k, v in result.items() if k != "sources"}), flush=True)
                if args.once:
                    raise SystemExit(1 if result["status"] == "failed" else 0)
            except Exception as exc:
                logging.error("scheduler_run_failed", extra={"error_type": type(exc).__name__})
                if args.once:
                    raise SystemExit(1) from exc
            time.sleep(settings.sync_interval_minutes * 60)
    except KeyboardInterrupt:
        print("Scheduler stopped.")


if __name__ == "__main__":
    main()
