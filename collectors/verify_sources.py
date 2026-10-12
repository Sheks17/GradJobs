"""Explicit opt-in live verification; no database writes. Cache snapshots for review."""

import argparse
import json
from pathlib import Path

from sqlalchemy import select

from collectors.providers import CAREERS, PROVIDERS, make_collector
from services.api.app.db.session import SessionLocal, utcnow
from services.api.app.models.job import JobSource
from services.api.app.schemas.sources import SourceCreate


def verify_file(input_path: Path, output_path: Path, cache_dir: Path) -> None:
    candidates = json.loads(input_path.read_text(encoding="utf-8"))
    verified, report = [], []
    cache_dir.mkdir(parents=True, exist_ok=True)
    for candidate in candidates:
        candidate = {
            **candidate,
            "provider": candidate.get("provider", candidate.get("detected_provider")),
            "board_token": candidate.get("board_token", candidate.get("provider_identifier")),
            "company_name": candidate.get("company_name", candidate.get("company")),
        }
        provider, board = candidate["provider"], candidate["board_token"]
        collector = None
        record = {**candidate, "verified_at": utcnow().isoformat()}
        try:
            SourceCreate.model_validate(candidate)
            collector = make_collector(
                provider, board, candidate["company_name"], candidate.get("provider_config")
            )
            rows = collector.fetch()
            failures = []
            for index, row in enumerate(rows):
                try:
                    collector.normalize(row)
                except Exception as exc:
                    failures.append({"row": index, "error": str(exc)[:400]})
            record.update(
                verified=not failures and collector.snapshot_complete,
                jobs=len(rows),
                normalization_failures=len(failures),
            )
            (cache_dir / f"{provider}-{board}.json").write_text(json.dumps(rows), encoding="utf-8")
            if rows and record["verified"]:
                verified.append(
                    {
                        **candidate,
                        "enabled": True,
                        "careers_url": getattr(collector, "careers_url", None)
                        or CAREERS[provider].format(board=board),
                        "verified_at": record["verified_at"],
                        "verification_url": collector.endpoint.format(board=board),
                    }
                )
            record["errors"] = failures[:5]
        except Exception as exc:
            record.update(verified=False, error=type(exc).__name__)
        finally:
            if collector is not None:
                collector.close()
        report.append(record)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(verified, indent=2), encoding="utf-8")
        (cache_dir / "verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(
            json.dumps({key: value for key, value in record.items() if key != "errors"}), flush=True
        )


def verify_registered(provider=None):
    with SessionLocal() as db:
        query = select(JobSource).where(
            JobSource.enabled.is_(True), JobSource.source_type.in_(PROVIDERS)
        )
        if provider:
            query = query.where(JobSource.source_type == provider)
        records = [
            {
                "provider": source.source_type,
                "board_token": source.board_identifier,
                "company_name": source.company_name or source.name,
                "provider_config": source.provider_config,
            }
            for source in db.scalars(query)
        ]
    report = []
    for record in records:
        collector = make_collector(
            record["provider"],
            record["board_token"],
            record["company_name"],
            record["provider_config"],
        )
        try:
            rows = collector.fetch()
            failures = 0
            for row in rows:
                try:
                    collector.normalize(row)
                except Exception:
                    failures += 1
            report.append(
                {
                    **record,
                    "verified": not failures and collector.snapshot_complete,
                    "jobs": len(rows),
                    "normalization_failures": failures,
                    "checked_at": utcnow().isoformat(),
                }
            )
        except Exception as exc:
            report.append(
                {
                    **record,
                    "verified": False,
                    "error": type(exc).__name__,
                    "checked_at": utcnow().isoformat(),
                }
            )
        finally:
            collector.close()
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, nargs="?")
    parser.add_argument("--provider", choices=PROVIDERS)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--cache", type=Path, default=Path("artifacts/live"))
    args = parser.parse_args()
    if args.input:
        verify_file(args.input, args.output or Path("artifacts/verified-sources.json"), args.cache)
    else:
        report = verify_registered(args.provider)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
