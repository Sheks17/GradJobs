"""Public position feed plus schema.org JobPosting; no layout-dependent scraping."""

import json

from bs4 import BeautifulSoup

from collectors.base import Collector
from collectors.normalizers.location import location_fields
from collectors.normalizers.text import plain_text
from collectors.public_feeds import complete_rows, public_link, source_date
from shared.schemas import NormalizedJob


def job_posting(html):
    candidates = []

    def visit(value):
        if isinstance(value, list):
            for item in value:
                visit(item)
        elif isinstance(value, dict):
            if value.get("@type") == "JobPosting":
                candidates.append(value)
            if "@graph" in value:
                visit(value["@graph"])

    for script in BeautifulSoup(html, "html.parser").select('script[type="application/ld+json"]'):
        visit(json.loads(script.get_text()))
    if len(candidates) != 1:
        raise ValueError("Expected one public structured JobPosting")
    return candidates[0]


class BreezyHRCollector(Collector):
    source_type = "breezyhr"
    endpoint = "https://{board}.breezy.hr/json"
    capabilities = {
        **Collector.capabilities,
        "fetch_detail": True,
        "posted_date": True,
        "closing_date": True,
        "salary": True,
    }

    def fetch(self):
        from collectors.discover import check_allowed

        host = f"{self.board}.breezy.hr"
        check_allowed(self.client, f"https://{host}/")
        rows = complete_rows(self.get_json())
        result = []
        failures = 0
        for row in rows:
            try:
                url = public_link(row.get("url"), host, "/p/")
                schema = job_posting(self.request_text(url))
                public_link(schema.get("url"), host, "/p/")
                if url.split("?", 1)[0] != schema["url"].split("?", 1)[0]:
                    raise ValueError("Structured posting does not match listed URL")
                result.append({"listing": row, "posting": schema})
                failures = 0
            except Exception as exc:
                self.snapshot_complete = False
                result.append({"listing": row, "detail_error": type(exc).__name__})
                failures += 1
                if failures >= 5:
                    break
        return result

    def normalize(self, raw):
        if raw.get("detail_error"):
            raise ValueError("Breezy public structured posting unavailable")
        row, schema = raw["listing"], raw["posting"]
        description = plain_text(schema.get("description"))
        if not row.get("id") or not description:
            raise ValueError("Breezy stable ID or description missing")
        loc = row.get("location") or {}

        def mapped(value):
            return dict(
                location_raw=value.get("name"),
                country=(value.get("country") or {}).get("id"),
                state=(value.get("state") or {}).get("id"),
                city=value.get("city"),
            )

        salary = schema.get("baseSalary") or {}
        value = salary.get("value") or {} if isinstance(salary, dict) else {}
        salary_fields = {}
        if isinstance(value, dict):
            period = {"HOUR": "hour", "DAY": "day", "MONTH": "month", "YEAR": "year"}.get(
                value.get("unitText")
            )
            if period and (value.get("minValue") is not None or value.get("value") is not None):
                salary_fields = dict(
                    salary_min=value.get("minValue", value.get("value")),
                    salary_max=value.get("maxValue", value.get("value")),
                    salary_currency=salary.get("currency"),
                    salary_period=period,
                )
        url = public_link(row["url"], f"{self.board}.breezy.hr", "/p/")
        return NormalizedJob(
            source=self.source_type,
            source_job_id=str(row["id"]),
            company_name=self.company,
            title=row["name"],
            description=description,
            source_url=url,
            apply_url=url,
            employment_type=(row.get("type") or {}).get("name"),
            posted_at=source_date(row.get("published_date") or schema.get("datePosted")),
            closing_at=source_date(schema.get("validThrough")),
            **location_fields(
                loc.get("name"),
                "remote"
                if loc.get("is_remote") or schema.get("jobLocationType") == "TELECOMMUTE"
                else None,
                (loc.get("country") or {}).get("id"),
                loc.get("city"),
                (loc.get("state") or {}).get("id"),
                additional=[mapped(item) for item in row.get("locations") or []],
            ),
            **salary_fields,
            provider_metadata={
                "department": row.get("department"),
                "salary_text": row.get("salary"),
            },
            raw_data=raw,
        )
