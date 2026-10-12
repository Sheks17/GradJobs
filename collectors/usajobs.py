"""Official keyed USAJOBS search, bounded configured queries and explicit eligibility."""

import re
from datetime import UTC, datetime, time

from collectors.base import Collector
from collectors.normalizers.location import location_fields, remote_restrictions
from collectors.normalizers.text import plain_text
from services.api.app.core.config import get_settings
from shared.schemas import NormalizedJob

SEARCH_FIELDS = {
    "Keyword",
    "JobCategoryCode",
    "LocationName",
    "Organization",
    "HiringPath",
    "RemoteIndicator",
}


def source_date(value, closing=False):
    if not value:
        return None
    if len(value) == 10:
        # API dates lack a timezone. Treat closing day as inclusive, conservatively in UTC.
        return datetime.combine(
            datetime.fromisoformat(value).date(), time.max if closing else time.min, UTC
        )
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed


class USAJobsCollector(Collector):
    source_type = "usajobs"
    endpoint = "https://data.usajobs.gov/api/Search"
    capabilities = {
        **Collector.capabilities,
        "pagination": True,
        "source_discovery": False,
        "salary": True,
        "posted_date": True,
        "closing_date": True,
    }

    def fetch(self):
        settings = get_settings()
        if not settings.usajobs_api_key or not settings.usajobs_user_agent:
            raise ValueError("USAJOBS_API_KEY and USAJOBS_USER_AGENT are required")
        queries = self.config.get("queries", [])
        if not queries or len(queries) > 12:
            raise ValueError("USAJOBS requires 1–12 bounded configured search queries")
        headers = {
            "Host": "data.usajobs.gov",
            "User-Agent": settings.usajobs_user_agent,
            "Authorization-Key": settings.usajobs_api_key,
        }
        rows = {}
        limit = int(self.config.get("results_per_page", 100))
        if not 1 <= limit <= 500:
            raise ValueError("USAJOBS page size must be 1–500")
        for query in queries:
            if set(query) - SEARCH_FIELDS or not any(
                query.get(key) for key in ("Keyword", "JobCategoryCode", "Organization")
            ):
                raise ValueError(
                    "USAJOBS search must be scoped by keyword, category or organization"
                )
            for page in range(1, int(self.config.get("max_pages", 20)) + 1):
                payload = self.get_json(
                    {**query, "Page": page, "ResultsPerPage": limit, "Fields": "Full"},
                    headers=headers,
                )
                result = payload["SearchResult"]
                items = result["SearchResultItems"]
                if not isinstance(items, list):
                    raise ValueError("Unexpected USAJOBS search response")
                for item in items:
                    identity = item.get("MatchedObjectId") or item.get(
                        "MatchedObjectDescriptor", {}
                    ).get("PositionID")
                    if not identity:
                        raise ValueError("Missing USAJOBS external identity")
                    rows[str(identity)] = item
                total = int(result["SearchResultCountAll"])
                if page * limit >= total:
                    break
                if not items:
                    raise ValueError("Incomplete USAJOBS pagination")
            else:
                raise ValueError("USAJOBS page limit reached; snapshot incomplete")
        return list(rows.values())

    def normalize(self, raw):
        job = raw["MatchedObjectDescriptor"]
        details = job.get("UserArea", {}).get("Details", {})
        hiring_paths = details.get("HiringPath", [])
        if isinstance(hiring_paths, str):
            hiring_paths = [hiring_paths]
        text_fields = {
            key: plain_text(details.get(key))
            for key in (
                "JobSummary",
                "MajorDuties",
                "Requirements",
                "Education",
                "Evaluations",
                "OtherInformation",
                "HowToApply",
                "WhoMayApply",
            )
            if isinstance(details.get(key), str)
        }
        if isinstance(details.get("MajorDuties"), list):
            text_fields["MajorDuties"] = "\n".join(
                plain_text(value) for value in details["MajorDuties"]
            )
        qualifications = plain_text(job.get("QualificationSummary"))
        description = "\n\n".join([*text_fields.values(), "Qualifications\n" + qualifications])
        programs = []
        if "graduates" in hiring_paths:
            programs.append("Recent graduate program (USAJOBS hiring path: graduates)")
        if "student" in hiring_paths:
            programs.append("Students program")
        # Only explicit API hiring paths feed existing textual signals; never add artificial years.
        description += "\n\n" + "\n".join(programs)
        eligibility_text = "\n".join(text_fields.values()) + "\n" + qualifications
        citizenship = [
            line
            for line in eligibility_text.splitlines()
            if re.search(
                r"\b(?:must be (?:a )?(?:U\.?S\.?|United States) citizen|"
                r"(?:U\.?S\.?|United States) citizenship (?:is )?required)\b",
                line,
                re.I,
            )
        ]
        clearance = details.get("SecurityClearance")
        clearance_required = (
            False
            if str(clearance).lower() == "not required"
            else True
            if clearance
            and re.search(
                r"\b(?:secret|confidential|sensitive compartmented)\b", str(clearance), re.I
            )
            else None
        )
        # Application deadlines mention time zones but do not restrict remote work.
        remote_text = "\n".join(
            sentence
            for sentence in re.split(r"(?<=[.!?])\s+|\n+", description)
            if not re.search(
                r"\b(?:applications?|apply|closing|deadline|announcement)\b", sentence, re.I
            )
        )
        metadata = {
            "federal": True,
            "department": job.get("DepartmentName"),
            "agency": job.get("OrganizationName"),
            "hiring_paths": hiring_paths,
            "recent_graduate": "graduates" in hiring_paths,
            "student": "student" in hiring_paths,
            "pathways": bool(re.search(r"\bPathways\b", eligibility_text, re.I)),
            "internship": bool(
                re.search(r"\binternships?\b", job["PositionTitle"] + " " + eligibility_text, re.I)
            ),
            "citizenship_evidence": citizenship,
            "security_clearance": clearance,
            "public_trust": clearance
            if clearance and "public trust" in str(clearance).lower()
            else None,
            "federal_status_restrictions": [
                path for path in hiring_paths if path.startswith("fed-")
            ],
            "veterans_preference_evidence": [
                line
                for line in eligibility_text.splitlines()
                if re.search(r"veterans.? preference", line, re.I)
            ],
            "requirements": text_fields.get("Requirements"),
            "qualifications": qualifications,
            "closing_date_source": job.get("ApplicationCloseDate"),
            "remote_restrictions": remote_restrictions(
                job.get("PositionLocationDisplay") or "", remote_text
            ),
        }
        locations = []
        for location in job.get("PositionLocation", []):
            fields = location_fields(
                location.get("LocationName"),
                country=location.get("CountryCode"),
                city=(location.get("CityName") or "").split(",")[0] or None,
                state=location.get("CountrySubDivisionCode"),
            )
            locations.append(
                {key: fields[key] for key in ("location_raw", "country", "city", "state")}
            )
        remote = details.get("RemoteIndicator")
        workplace = "remote" if remote is True or str(remote).lower() == "true" else None
        loc = location_fields(job.get("PositionLocationDisplay"), workplace)
        loc.update(metadata["remote_restrictions"])
        loc["locations"] = locations or loc["locations"]
        if locations:
            for key in ("country", "city", "state"):
                loc[key] = locations[0][key]
        salary = next(iter(job.get("PositionRemuneration", [])), {})
        periods = {
            "per year": "year",
            "per hour": "hour",
            "per month": "month",
            "per day": "day",
            "pa": "year",
            "ph": "hour",
            "pd": "day",
            "pm": "month",
        }
        identity = str(raw.get("MatchedObjectId") or job["PositionID"])
        return NormalizedJob(
            source=self.source_type,
            source_job_id=identity,
            external_id=job.get("PositionID"),
            title=job["PositionTitle"],
            company_name=job["OrganizationName"],
            description=description,
            source_url=job["PositionURI"],
            apply_url=next(iter(job.get("ApplyURI", [])), job["PositionURI"]),
            **loc,
            posted_at=source_date(job.get("PublicationStartDate")),
            closing_at=source_date(job.get("ApplicationCloseDate"), closing=True),
            salary_min=salary.get("MinimumRange"),
            salary_max=salary.get("MaximumRange"),
            salary_period=periods.get(str(salary.get("RateIntervalCode", "")).lower())
            or periods.get(str(salary.get("Description", "")).lower()),
            salary_currency="USD" if salary else None,
            employment_type="; ".join(
                value["Name"] for value in job.get("PositionOfferingType", [])
            ),
            requires_us_citizenship=True if citizenship else None,
            requires_security_clearance=clearance_required,
            provider_metadata=metadata,
            raw_data=raw,
        )
