"""Optional official endpoint smoke checks; normal CI stays offline."""

import os

import pytest

from collectors.smartrecruiters import SmartRecruitersCollector
from collectors.usajobs import USAJobsCollector
from services.api.app.core.config import get_settings

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.environ.get("RUN_LIVE_TESTS") != "1",
        reason="Set RUN_LIVE_TESTS=1 for public endpoint checks",
    ),
]


def test_live_smartrecruiters_public_list_and_detail():
    collector = SmartRecruitersCollector("SopraSteria1", "Sopra Steria")
    try:
        page = collector.get_json({"limit": 1, "country": "us"})
        assert page["content"]
        row = page["content"][0]
        data = collector.normalize({"listing": row, "detail": collector.fetch_detail(row["id"])})
        assert data.description and data.country == "US" and data.source_job_id
    finally:
        collector.close()


def test_live_usajobs_official_authenticated_search():
    settings = get_settings()
    if not settings.usajobs_api_key or not settings.usajobs_user_agent:
        pytest.skip("Configure USAJOBS_API_KEY and USAJOBS_USER_AGENT")
    collector = USAJobsCollector("tech", "Federal")
    try:
        response = collector.get_json(
            {
                "Keyword": "Software",
                "JobCategoryCode": "2210",
                "ResultsPerPage": 1,
                "Fields": "Full",
            },
            headers={
                "Host": "data.usajobs.gov",
                "User-Agent": settings.usajobs_user_agent,
                "Authorization-Key": settings.usajobs_api_key,
            },
        )
        rows = response["SearchResult"]["SearchResultItems"]
        assert rows
        data = collector.normalize(rows[0])
        assert data.description and data.source_job_id and data.provider_metadata["federal"]
    finally:
        collector.close()


def test_live_existing_workday_discovery_and_detail():
    import json
    from pathlib import Path

    from collectors.discover import discover

    sources = json.loads(Path("data/sources.json").read_text())
    source = next(
        row
        for row in sources
        if row["provider"] == "workday" and row["company_name"] == "Guidewire"
    )
    result = discover(source["careers_url"])
    assert result["provider"] == "workday" and result["verified"] and result["jobs"] > 0
