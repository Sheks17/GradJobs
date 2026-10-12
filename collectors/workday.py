"""Public Workday CXS snapshots; no login, browser impersonation or challenge bypass."""

import re
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Lock
from urllib.parse import urlsplit

from collectors.base import Collector
from collectors.normalizers.location import location_fields
from collectors.normalizers.text import plain_text
from services.api.app.core.config import get_settings
from shared.schemas import NormalizedJob


def workday_config(url):
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    match = re.fullmatch(r"([a-z0-9-]+)\.wd\d+\.myworkdayjobs\.com", host)
    if parsed.scheme != "https" or not match or parsed.username or parsed.password or parsed.port:
        raise ValueError("Expected an HTTPS employer Workday careers URL")
    parts = [part for part in parsed.path.split("/") if part]
    locale = parts.pop(0) if parts and re.fullmatch(r"[a-z]{2}-[A-Z]{2}", parts[0]) else "en-US"
    if not parts or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", parts[0]):
        raise ValueError("Workday site identifier could not be determined")
    tenant, site = match[1], parts[0]
    return {
        "hostname": host,
        "tenant": tenant,
        "site": site,
        "locale": locale,
        "careers_url": f"https://{host}/{locale}/{site}",
    }


def source_token(config):
    # Includes hostname shard: two boards never collide solely because site names match.
    return re.sub(r"[^A-Za-z0-9_-]", "-", f"{config['hostname']}-{config['site']}")


class WorkdayCollector(Collector):
    source_type = "workday"
    endpoint = "https://{board}"
    capabilities = {
        **Collector.capabilities,
        "fetch_detail": True,
        "pagination": True,
        "posted_date": True,
        "closing_date": True,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        observed = workday_config(self.config.get("careers_url", ""))
        for key in ("hostname", "tenant", "site", "locale"):
            if key in self.config and self.config[key] != observed[key]:
                raise ValueError("Workday configuration conflicts with careers URL")
        self.config = {**self.config, **observed}
        if self.board != source_token(observed):
            self.close()
            raise ValueError("Workday board token conflicts with careers URL")
        self.detail_cache = {}
        self.failure_lock = Lock()
        self.detail_failures = 0
        self.circuit_open = False
        self.careers_url = observed["careers_url"]
        self.endpoint = (
            f"https://{observed['hostname']}/wday/cxs/{observed['tenant']}/{observed['site']}"
        )

    def fetch(self):
        self.snapshot_complete = True
        self.detail_failures = 0
        self.circuit_open = False
        rows, seen, offset, snapshot_total = [], set(), 0, None
        for _ in range(int(self.config.get("max_pages", 100))):
            page = self.request_json(
                "POST",
                url=self.endpoint + "/jobs",
                headers={"Accept-Language": self.config["locale"]},
                json={
                    "limit": 20,
                    "offset": offset,
                    "searchText": "",
                    "appliedFacets": {},
                },
            )
            if not isinstance(page, dict) or not isinstance(page.get("jobPostings"), list):
                raise ValueError("Unexpected Workday page")
            total = page.get("total")
            if not isinstance(total, int) or total < 0:
                raise ValueError("Missing Workday total")
            # Real CXS boards return total=0 on subsequent pages even while
            # returning jobs. Only the first page supplies the snapshot count.
            if snapshot_total is None:
                snapshot_total = total
            elif total not in {0, snapshot_total}:
                raise ValueError("Workday board changed during pagination; retry next sync")
            listings = page["jobPostings"]
            if not listings and offset < snapshot_total:
                raise ValueError("Incomplete Workday pagination")
            valid = []
            for listing in listings:
                path = listing.get("externalPath") if isinstance(listing, dict) else None
                if (
                    not isinstance(path, str)
                    or not path.startswith("/job/")
                    or ".." in path
                    or "?" in path
                ):
                    self.snapshot_complete = False
                    rows.append({"listing": listing, "detail_error": "InvalidPath"})
                    continue
                if path in seen:
                    raise ValueError("Repeated Workday page or posting")
                seen.add(path)
                valid.append(listing)
            with ThreadPoolExecutor(max_workers=2) as pool:
                details = list(pool.map(self.fetch_detail, valid))
            if any(row.get("detail_error") for row in details):
                self.snapshot_complete = False
            rows.extend(details)
            if self.circuit_open:
                return rows  # Partial snapshot: never reconcile closures after an outage.
            offset += len(listings)
            if offset >= snapshot_total:
                return rows
        raise ValueError("Workday page limit reached; snapshot incomplete")

    def fetch_detail(self, listing):
        with self.failure_lock:
            if self.circuit_open:
                return {"listing": listing, "detail_error": "CircuitOpen"}
        path = listing["externalPath"]
        cached = self.detail_cache.get(path)
        if cached and cached.get("detail") and cached.get("_detail_checked_at"):
            try:
                checked = datetime.fromisoformat(cached["_detail_checked_at"])
                ttl = timedelta(hours=get_settings().workday_detail_cache_hours)

                def stable(summary):
                    return {k: v for k, v in summary.items() if k != "postedOn"}

                if checked + ttl > datetime.now(UTC) and stable(cached["listing"]) == stable(
                    listing
                ):
                    return {**cached, "listing": listing}
            except (ValueError, TypeError, KeyError):
                pass  # Ignore invalid cache entries; retrieve a current public detail.
        try:
            detail = self.get_json(
                url=self.endpoint + listing["externalPath"],
                headers={"Accept-Language": self.config["locale"]},
            )
            if not isinstance(detail, dict) or not isinstance(detail.get("jobPostingInfo"), dict):
                raise ValueError("Missing Workday detail")
            result = {
                "listing": listing,
                "detail": detail,
                "_detail_checked_at": datetime.now(UTC).isoformat(),
            }
            self.detail_cache[path] = result
            with self.failure_lock:
                self.detail_failures = 0
            return result
        except Exception as exc:
            with self.failure_lock:
                self.detail_failures += 1
                if self.detail_failures >= 5:
                    self.circuit_open = True
            return {"listing": listing, "detail_error": type(exc).__name__}

    def normalize(self, raw):
        if raw.get("detail_error"):
            raise ValueError("Workday detail unavailable")
        info = raw["detail"]["jobPostingInfo"]
        description = plain_text(info.get("jobDescription"))
        if not description or not info.get("id"):
            raise ValueError("Workday description or stable ID missing")
        url = self.careers_url + raw["listing"]["externalPath"]
        country = (info.get("jobRequisitionLocation") or {}).get("country") or {}
        location = info.get("location")
        # Workday's US, CA, City form differs from conventional City, CA.
        if location and re.match(r"^US, [A-Z]{2}, ", location):
            _, state, city = location.split(", ", 2)
        else:
            state = city = None
        workplace = info.get("remoteType")
        if (
            workplace
            and workplace.lower() == "flex"
            and re.search(r"in.person time and remote", description, re.I)
        ):
            workplace = "hybrid"  # Explicit employer Flex Work policy, not a label assumption.
        if not workplace:
            tag = re.search(r"#LI-(Remote|Hybrid|Onsite)", description, re.I)
            workplace = tag[1] if tag else None

        def date(key):
            value = info.get(key)
            if not value:
                return None
            result = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return result.replace(tzinfo=UTC) if result.tzinfo is None else result

        additional = []
        for value in info.get("additionalLocations") or []:
            if isinstance(value, str) and re.match(r"^US, [A-Z]{2}, ", value):
                _, state_code, city_name = value.split(", ", 2)
                additional.append(
                    {"location_raw": value, "state": state_code, "city": city_name, "country": "US"}
                )
            else:
                additional.append(value)
        salary = {}
        explicit = re.search(
            r"\$([\d,]+(?:\.\d+)?)\s*(?:USD|US Dollars)?\s*(?:-|–|to)\s*"
            r"\$?([\d,]+(?:\.\d+)?)\s*(?:USD|US Dollars)",
            description,
            re.I,
        )
        if explicit:
            nearby = description[max(0, explicit.start() - 100) : explicit.end() + 100].lower()
            preceding = description[max(0, explicit.start() - 1200) : explicit.start()].lower()
            period = (
                "hour"
                if "hour" in nearby
                else "year"
                if re.search(r"annual|per year|yearly", nearby)
                or re.search(r"annual(?:ized)?\s+(?:base\s+)?salary\s+ranges?", preceding)
                else None
            )
            if period:
                salary = {
                    "salary_min": explicit[1].replace(",", ""),
                    "salary_max": explicit[2].replace(",", ""),
                    "salary_currency": "USD",
                    "salary_period": period,
                }

        return NormalizedJob(
            source=self.source_type,
            source_job_id=info["id"],
            external_id=info.get("jobReqId"),
            company_name=self.company,
            title=info["title"],
            description=description,
            source_url=url,
            apply_url=url,
            employment_type=info.get("timeType"),
            posted_at=date("startDate"),
            closing_at=date("endDate"),
            **location_fields(
                location,
                workplace,
                country.get("alpha2Code"),
                city,
                state,
                additional=additional,
            ),
            provider_metadata={
                "tenant": self.config["tenant"],
                "site": self.config["site"],
                "posted_on": info.get("postedOn"),
                "can_apply": info.get("canApply"),
                "workplace_label": info.get("remoteType"),
            },
            raw_data=raw,
            **salary,
        )
