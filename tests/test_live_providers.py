"""Real public response samples; network integration is opt-in via RUN_LIVE_TESTS=1."""

import json
import os
from pathlib import Path

import pytest

from collectors.providers import PROVIDERS

FIXTURES = Path(__file__).parent / "fixtures/live"
EXAMPLES = json.loads((FIXTURES / "provenance.json").read_text())


@pytest.mark.parametrize(
    "example", EXAMPLES, ids=lambda item: f"{item['provider']}-{item['board']}"
)
def test_real_public_fixture(example):
    collector = PROVIDERS[example["provider"]](example["board"], example["board"])
    try:
        raw = json.loads(
            (FIXTURES / f"{example['provider']}-{example['board']}.json").read_text(
                encoding="utf-8"
            )
        )
        job = collector.normalize(raw)
        assert job and job.title and job.description and job.source_job_id
        assert job.apply_url.startswith("https://") and job.raw_data == raw
        assert job.source == example["provider"]
    finally:
        collector.close()


@pytest.mark.live
@pytest.mark.skipif(
    os.getenv("RUN_LIVE_TESTS") != "1", reason="Set RUN_LIVE_TESTS=1 to access public boards"
)
@pytest.mark.parametrize(
    "example", EXAMPLES, ids=lambda item: f"{item['provider']}-{item['board']}"
)
def test_live_public_board(example):
    collector = PROVIDERS[example["provider"]](example["board"], example["board"])
    try:
        rows = collector.fetch()
        assert isinstance(rows, list)
        for raw in rows:
            job = collector.normalize(raw)
            if job:
                assert job.source_job_id and job.apply_url.startswith("https://")
    finally:
        collector.close()
