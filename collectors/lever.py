from datetime import UTC, datetime

from collectors.base import Collector
from collectors.normalizers.location import location_fields
from collectors.normalizers.text import plain_text
from shared.schemas import NormalizedJob


class LeverCollector(Collector):
    source_type = "lever"
    endpoint = "https://api.lever.co/v0/postings/{board}"

    def fetch(self) -> list[dict]:
        rows: list[dict] = []
        for skip in range(0, 100_000, 100):
            batch = self.get_json({"mode": "json", "skip": skip, "limit": 100})
            if not isinstance(batch, list):
                raise ValueError("Unexpected Lever response")
            rows.extend(batch)
            if len(batch) < 100:
                return rows
        raise ValueError("Lever pagination limit exceeded; snapshot is incomplete")

    def normalize(self, raw: dict) -> NormalizedJob:
        categories = raw.get("categories") or {}
        sections = [raw.get("descriptionPlain") or plain_text(raw.get("description"))]
        for item in raw.get("lists") or []:
            sections.extend([item.get("text", ""), plain_text(item.get("content"))])
        sections.append(raw.get("additionalPlain") or plain_text(raw.get("additional")))
        salary = raw.get("salaryRange") or {}
        period = {
            "per-year": "year",
            "per-hour": "hour",
            "per-month": "month",
            "per-day": "day",
            "year": "year",
            "hour": "hour",
        }.get(salary.get("interval"))
        return NormalizedJob(
            source="lever",
            source_job_id=raw["id"],
            external_id=raw["id"],
            company_name=self.company,
            title=raw["text"],
            description="\n\n".join(sections),
            source_url=raw["hostedUrl"],
            apply_url=raw["applyUrl"],
            **location_fields(
                categories.get("location"),
                raw.get("workplaceType"),
                raw.get("country"),
                additional=categories.get("allLocations"),
            ),
            employment_type=categories.get("commitment"),
            salary_min=salary.get("min"),
            salary_max=salary.get("max"),
            salary_currency=salary.get("currency"),
            salary_period=period,
            posted_at=(
                datetime.fromtimestamp(raw["createdAt"] / 1000, UTC)
                if raw.get("createdAt") is not None
                else None
            ),
            raw_data=raw,
        )
