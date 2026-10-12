import argparse
import json
from pathlib import Path

import yaml

from collectors.locking import write_lock
from services.api.app.db.session import SessionLocal
from services.api.app.schemas.sources import SourceCreate
from services.api.app.services.sources import register_source


def seed(path: Path) -> int:
    content = path.read_text(encoding="utf-8-sig")
    records = yaml.safe_load(content) if path.suffix in {".yaml", ".yml"} else json.loads(content)
    sources = [SourceCreate.model_validate(row) for row in records]
    with SessionLocal() as db:
        write_lock(db)
        created = sum(register_source(db, source)[1] for source in sources)
        db.commit()
    return created


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import a JSON/YAML source registry idempotently")
    parser.add_argument("--file", type=Path, default=Path("data/sources.json"))
    args = parser.parse_args()
    print(f"Created {seed(args.file)} sources; existing source settings preserved.")
