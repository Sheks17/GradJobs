"""Shared validation for complete public career feeds, not recruiter APIs."""

from datetime import UTC, datetime
from urllib.parse import urlsplit


def source_date(value):
    if not value:
        return None
    value = str(value).replace(" UTC", "+00:00").replace("Z", "+00:00")
    result = datetime.fromisoformat(value)
    return result.replace(tzinfo=UTC) if result.tzinfo is None else result


def complete_rows(payload, key=None):
    rows = payload.get(key) if key and isinstance(payload, dict) else payload
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("Malformed public jobs feed")
    if isinstance(payload, dict):
        if payload.get("next") or payload.get("next_page") or payload.get("has_more"):
            raise ValueError("Unexpected pagination; incomplete snapshot")
        total = payload.get("total")
        if total is not None and (not isinstance(total, int) or total != len(rows)):
            raise ValueError("Incomplete public jobs feed")
    return rows


def public_link(value, host, prefix="/"):
    parts = urlsplit(value or "")
    if (
        parts.scheme != "https"
        or parts.hostname != host
        or parts.username
        or parts.password
        or parts.port
        or not parts.path.startswith(prefix)
    ):
        raise ValueError("Posting link is outside the public career board")
    return value


def salary_fields(value):
    if not isinstance(value, dict):
        return {}
    period = {
        "hourly": "hour",
        "yearly": "year",
        "annually": "year",
        "monthly": "month",
        "daily": "day",
    }.get(value.get("period"), value.get("period"))
    if period not in {"hour", "day", "month", "year"}:
        period = None
    return dict(
        salary_min=value.get("min"),
        salary_max=value.get("max"),
        salary_currency=value.get("currency"),
        salary_period=period,
    )
