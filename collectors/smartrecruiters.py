"""Public company Posting API; detail failures never form a complete snapshot."""

from urllib.parse import quote

from collectors.base import Collector
from collectors.normalizers.location import location_fields
from collectors.normalizers.text import plain_text
from shared.schemas import NormalizedJob


class SmartRecruitersCollector(Collector):
    source_type = "smartrecruiters"
    endpoint = "https://api.smartrecruiters.com/v1/companies/{board}/postings"
    capabilities = {
        **Collector.capabilities,
        "fetch_detail": True,
        "pagination": True,
        "posted_date": True,
    }

    def fetch_detail(self, identity):
        return self.get_json(
            url=self.endpoint.format(board=self.board) + "/" + quote(str(identity), safe="")
        )

    def fetch(self):
        self.snapshot_complete = True
        rows, seen, offset = [], set(), 0
        limit = 100
        for _ in range(int(self.config.get("max_pages", 100))):
            params = {"limit": limit, "offset": offset}
            if self.config.get("country"):
                params["country"] = self.config["country"].lower()
            page = self.get_json(params)
            if not isinstance(page, dict) or not isinstance(page.get("content"), list):
                raise ValueError("Unexpected SmartRecruiters page")
            content = page["content"]
            total = int(page["totalFound"])
            if not content and offset < total:
                raise ValueError("Incomplete SmartRecruiters pagination")
            for listing in content:
                if not isinstance(listing, dict):
                    self.snapshot_complete = False
                    rows.append({"listing": listing, "detail_error": "MalformedListing"})
                    continue
                identity = listing.get("id") or listing.get("uuid")
                if not identity or str(identity) in seen:
                    self.snapshot_complete = False
                    rows.append({"listing": listing, "detail_error": "MissingOrRepeatedIdentity"})
                    continue
                seen.add(str(identity))
                try:
                    detail = self.fetch_detail(identity)
                    if not isinstance(detail, dict) or not detail.get("jobAd"):
                        raise ValueError("Missing SmartRecruiters detail content")
                    rows.append({"listing": listing, "detail": detail})
                except Exception as exc:
                    self.snapshot_complete = False
                    rows.append({"listing": listing, "detail_error": type(exc).__name__})
            offset += len(content)
            if offset >= total:
                return rows
        raise ValueError("SmartRecruiters page limit reached; snapshot incomplete")

    def normalize(self, raw):
        if raw.get("detail_error"):
            raise ValueError("SmartRecruiters detail request failed")
        detail = raw.get("detail", raw)
        listing = raw.get("listing", detail)
        sections = detail.get("jobAd", {}).get("sections", {})
        description = "\n\n".join(
            plain_text(sections.get(key, {}).get("text"))
            for key in ("jobDescription", "qualifications", "additionalInformation")
        ).strip()
        if not description:
            raise ValueError("SmartRecruiters description missing")
        identity = str(listing.get("id") or detail["id"])
        location = detail.get("location") or listing.get("location") or {}
        raw_location = ", ".join(
            str(location[key]) for key in ("city", "region", "country") if location.get(key)
        )
        workplace = (
            "hybrid"
            if location.get("hybrid") is True
            else "remote"
            if location.get("remote") is True
            else "onsite"
            if location.get("remote") is False and location.get("hybrid") is False
            else location.get("workplaceType")
        )
        return NormalizedJob(
            source=self.source_type,
            source_job_id=identity,
            external_id=identity,
            company_name=detail.get("company", {}).get("name") or self.company,
            title=detail["name"],
            description=description,
            source_url=detail.get("postingUrl") or detail.get("jobAdUrl") or listing.get("ref"),
            apply_url=detail.get("applyUrl") or detail.get("postingUrl"),
            posted_at=detail.get("releasedDate") or listing.get("releasedDate"),
            employment_type=(detail.get("typeOfEmployment") or {}).get("label"),
            **location_fields(
                raw_location or None,
                workplace,
                location.get("country"),
                location.get("city"),
                location.get("regionCode") or location.get("region"),
            ),
            raw_data=raw,
        )
