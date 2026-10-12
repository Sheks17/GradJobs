from collectors.base import Collector
from collectors.normalizers.location import location_fields
from collectors.normalizers.text import plain_text
from shared.schemas import NormalizedJob


class GreenhouseCollector(Collector):
    source_type = "greenhouse"
    endpoint = "https://boards-api.greenhouse.io/v1/boards/{board}/jobs"

    def fetch(self) -> list[dict]:
        data = self.get_json({"content": "true"})
        if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
            raise ValueError("Unexpected Greenhouse response")
        total = (data.get("meta") or {}).get("total")
        if total is not None and total != len(data["jobs"]):
            raise ValueError("Incomplete Greenhouse snapshot")
        return data["jobs"]

    def normalize(self, raw: dict) -> NormalizedJob | None:
        if "internal_job_id" in raw and raw["internal_job_id"] is None:
            return None  # Talent-pool prospect posts are not open requisitions.
        return NormalizedJob(
            source="greenhouse",
            source_job_id=str(raw["id"]),
            external_id=str(raw["id"]),
            company_name=self.company,
            title=raw["title"],
            description=plain_text(raw.get("content")),
            source_url=raw["absolute_url"],
            apply_url=raw["absolute_url"],
            posted_at=raw.get("first_published"),
            source_updated_at=raw.get("updated_at"),
            **location_fields((raw.get("location") or {}).get("name")),
            raw_data=raw,
        )
