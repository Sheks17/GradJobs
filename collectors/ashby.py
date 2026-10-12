from urllib.parse import urlsplit

from collectors.base import Collector
from collectors.normalizers.location import location_fields
from collectors.normalizers.text import plain_text
from shared.schemas import NormalizedJob


class AshbyCollector(Collector):
    source_type = "ashby"
    endpoint = "https://api.ashbyhq.com/posting-api/job-board/{board}"

    def fetch(self) -> list[dict]:
        data = self.get_json({"includeCompensation": "true"})
        if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
            raise ValueError("Unexpected Ashby response")
        return data["jobs"]

    def normalize(self, raw: dict) -> NormalizedJob | None:
        if raw.get("isListed") is False:
            return None
        address = (raw.get("address") or {}).get("postalAddress") or {}
        salary = next(
            (
                part
                for part in (raw.get("compensation") or {}).get("summaryComponents", [])
                if part.get("compensationType") == "Salary"
            ),
            {},
        )
        period = {"1 YEAR": "year", "1 MONTH": "month", "1 DAY": "day", "1 HOUR": "hour"}.get(
            salary.get("interval")
        )
        job_id = raw.get("id") or urlsplit(raw["jobUrl"]).path.rstrip("/").split("/")[-1]
        return NormalizedJob(
            source="ashby",
            source_job_id=job_id,
            external_id=job_id,
            company_name=self.company,
            title=raw["title"],
            description=raw.get("descriptionPlain") or plain_text(raw.get("descriptionHtml")),
            source_url=raw["jobUrl"],
            apply_url=raw["applyUrl"],
            **location_fields(
                raw.get("location"),
                raw.get("workplaceType") or ("remote" if raw.get("isRemote") else None),
                address.get("addressCountry"),
                address.get("addressLocality"),
                address.get("addressRegion"),
                additional=raw.get("secondaryLocations"),
            ),
            employment_type=raw.get("employmentType"),
            posted_at=raw.get("publishedAt"),
            salary_min=salary.get("minValue"),
            salary_max=salary.get("maxValue"),
            salary_currency=salary.get("currencyCode"),
            salary_period=period,
            raw_data=raw,
        )
