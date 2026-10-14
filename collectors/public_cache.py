"""Disposable public Workday details, kept outside Neon and Git."""

import gzip
import json
import os
import re
from pathlib import Path


def cache_path(board):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", board):
        raise ValueError("Invalid cache board identifier")
    root = Path(os.environ.get("COLLECTOR_CACHE_DIR", "artifacts/collector-cache"))
    return root / (board + ".json.gz")


def load_detail_cache(board):
    path = cache_path(board)
    try:
        if path.stat().st_size > 20_000_000:
            return {}
        with gzip.open(path, "rb") as handle:
            data = handle.read(100_000_001)
        if len(data) > 100_000_000:
            return {}
        value = json.loads(data)
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, EOFError):
        return {}  # A cache miss fetches public details; never queries stored raw_data.


def save_detail_cache(board, cache, validate=None):
    if validate:
        valid = {}
        for path, raw in cache.items():
            try:
                validate(raw)
                valid[path] = raw
            except Exception:
                continue  # Invalid details must retry, not remain cached for six hours.
        cache = valid
    path = cache_path(board)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_bytes(gzip.compress(json.dumps(cache).encode("utf-8")))
        temporary.replace(path)
    except (OSError, TypeError, ValueError):
        pass  # Cache persistence is optional; database correctness is independent.
