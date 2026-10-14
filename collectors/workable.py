"""Anonymous Workable widget/hosted-careers data; never uses SPI employer APIs."""

import re

from collectors.base import Collector
from collectors.normalizers.location import location_fields
from collectors.normalizers.text import plain_text
from collectors.public_feeds import complete_rows, public_link, source_date
from shared.schemas import NormalizedJob


class WorkableCollector(Collector):
    source_type = "workable"
    endpoint = "https://apply.workable.com/api/v1/widget/accounts/{board}"
    capabilities = {**Collector.capabilities, "fetch_detail": True, "posted_date": True}

    def fetch(self):
        # The widget returns the entire published board, not a paginated SPI list.
        rows = complete_rows(self.get_json(params={"details": "true"}), "jobs")
        output = []
        seen = set()
        for summary in rows:
            code = summary.get("shortcode")
            if (
                not isinstance(code, str)
                or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", code)
                or code in seen
            ):
                raise ValueError("Missing or duplicate Workable shortcode")
            seen.add(code)
            try:
                detail = self.get_json(
                    url=f"https://apply.workable.com/api/v2/accounts/{self.board}/jobs/{code}"
                )
                if (
                    not isinstance(detail, dict)
                    or detail.get("shortcode") != code
                    or detail.get("state") != "published"
                    or detail.get("isInternal")
                ):
                    raise ValueError("Workable public detail does not match listing")
                output.append({"summary": summary, "detail": detail})
            except Exception as exc:
                self.snapshot_complete = False
                output.append({"summary": summary, "detail_error": type(exc).__name__})
                if sum(bool(row.get("detail_error")) for row in output[-5:]) == 5:
                    break  # Bound requests during an outage; never reconcile closures.
        return output

    def normalize(self, raw):
        if raw.get("detail_error"):
            raise ValueError("Workable public detail unavailable")
        row, detail = raw["summary"], raw["detail"]
        description = plain_text(
            "\n".join(
                str(detail.get(key) or "") for key in ("description", "requirements", "benefits")
            )
        )
        if not description:
            raise ValueError("Workable description missing")
        locations = detail.get("locations") or row.get("locations") or []
        primary = detail.get("location") or (locations[0] if locations else {})
        extras = [
            dict(
                location_raw=", ".join(
                    str(loc[key]) for key in ("city", "region", "country") if loc.get(key)
                ),
                country=loc.get("countryCode"),
                city=loc.get("city"),
                state=loc.get("region"),
            )
            for loc in locations
            if not loc.get("hidden")
        ]
        return NormalizedJob(
            source=self.source_type,
            source_job_id=row["shortcode"],
            company_name=self.company,
            title=detail["title"],
            description=description,
            source_url=public_link(row["url"], "apply.workable.com"),
            apply_url=public_link(row["application_url"], "apply.workable.com"),
            employment_type=row.get("employment_type"),
            posted_at=source_date(detail.get("published") or row.get("published_on")),
            **location_fields(
                ", ".join(
                    str(primary[key]) for key in ("city", "region", "country") if primary.get(key)
                ),
                detail.get("workplace") or ("remote" if detail.get("remote") else None),
                primary.get("countryCode"),
                primary.get("city"),
                primary.get("region"),
                additional=extras,
            ),
            provider_metadata={
                "department": detail.get("department"),
                "experience_label": row.get("experience"),
            },
            raw_data=raw,
        )
