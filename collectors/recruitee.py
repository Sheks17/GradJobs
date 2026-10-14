"""Published employer careers feed; token-required Careers API is not used."""

from collectors.base import Collector
from collectors.normalizers.location import location_fields
from collectors.normalizers.text import plain_text
from collectors.public_feeds import complete_rows, public_link, salary_fields, source_date
from shared.schemas import NormalizedJob


class RecruiteeCollector(Collector):
    source_type = "recruitee"
    endpoint = "https://{board}.recruitee.com/api/offers"
    capabilities = {
        **Collector.capabilities,
        "posted_date": True,
        "salary": True,
        "closing_date": True,
    }

    def fetch(self):
        return complete_rows(self.get_json(), "offers")

    def normalize(self, row):
        if row.get("status") not in {None, "published"}:
            raise ValueError("Unexpected unpublished offer in public feed")
        description = plain_text(
            "\n".join(str(row.get(key) or "") for key in ("description", "requirements"))
        )
        if not description or not row.get("id"):
            raise ValueError("Recruitee description or stable ID missing")
        host = f"{self.board}.recruitee.com"
        extras = [
            dict(
                location_raw=loc.get("name"),
                country=loc.get("country_code"),
                city=loc.get("city"),
                state=loc.get("state_code") or loc.get("state"),
            )
            for loc in row.get("locations") or []
        ]
        return NormalizedJob(
            source=self.source_type,
            source_job_id=str(row["id"]),
            company_name=self.company,
            title=row["title"],
            description=description,
            source_url=public_link(row["careers_url"], host, "/o/"),
            apply_url=public_link(row["careers_apply_url"], host, "/o/"),
            employment_type=row.get("employment_type_code"),
            posted_at=source_date(row.get("published_at")),
            source_updated_at=source_date(row.get("updated_at")),
            closing_at=source_date(row.get("close_at")),
            **location_fields(
                row.get("location"),
                "hybrid"
                if row.get("hybrid")
                else "remote"
                if row.get("remote")
                else "onsite"
                if row.get("on_site")
                else None,
                row.get("country_code"),
                row.get("city"),
                row.get("state_code") or row.get("state_name"),
                additional=extras,
            ),
            **salary_fields(row.get("salary")),
            provider_metadata={
                "department": row.get("department"),
                "experience_label": row.get("experience_code"),
            },
            raw_data=row,
        )
