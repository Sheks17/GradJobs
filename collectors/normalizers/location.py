import re

STATE_NAMES = """Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|
Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|
Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|
Nevada|New Hampshire|New Jersey|New Mexico|New York|North Carolina|North Dakota|
Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|
Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming|District of Columbia"""
STATE_CODES = (
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV "
    "NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC"
)
STATES = dict(
    zip([name.strip() for name in STATE_NAMES.split("|")], STATE_CODES.split(), strict=True)
)


def normalize_state(value: str | None) -> str | None:
    if not value:
        return None
    return next(
        (
            code
            for name, code in STATES.items()
            if value.casefold() in {name.casefold(), code.casefold()}
        ),
        value,
    )


def _single_location(
    raw: str | None,
    workplace: str | None = None,
    country: str | None = None,
    city: str | None = None,
    state: str | None = None,
) -> dict:
    text = raw or ""
    work = (workplace or text).lower()
    remote = (
        "hybrid"
        if "hybrid" in work
        else "remote"
        if "remote" in work
        else "onsite"
        if re.search(r"on.?site", work)
        else "unknown"
    )
    country = {
        "usa": "US",
        "us": "US",
        "united states": "US",
        "united states of america": "US",
        "canada": "CA",
        "united kingdom": "GB",
    }.get((country or "").lower(), country)
    if country and len(country) != 2:
        country = None
    if not country:
        for label, code in {
            "canada": "CA",
            "united kingdom": "GB",
            "germany": "DE",
            "india": "IN",
            "australia": "AU",
            "ireland": "IE",
        }.items():
            if re.search(rf"\b{label}\b", text, re.I):
                country = code
    if not country and (
        re.search(r"\b(?:united states|usa)\b", text, re.I)
        or re.search(r"\bUS\b|\bU\.S\.?(?!\w)", text)
    ):
        country = "US"
    state = normalize_state(state)
    country = country.upper() if country else None
    # Only infer US from a city-comma-state pattern, not ambiguous bare 'CA'/'IN'.
    parts = [part.strip() for part in text.split(",")]
    if len(parts) >= 2 and not state:
        token = re.split(r"[;(]|\s+-\s+", parts[1])[0].strip()
        token = "DC" if token in {"D.C.", "D.C"} else token
        if token in STATES.values() or token.title() in STATES:
            state = normalize_state(token.title() if len(token) > 2 else token)
            city = city or re.sub(
                r"^(?:Hybrid|Remote|On.?site)\s*[-:]\s*", "", parts[0], flags=re.I
            )
            country = country or "US"
    if not state and not re.search(r"\b(?:except|excluding)\b", text, re.I):
        state_label = re.sub(
            r"^(?:Remote|Hybrid|On.?site)\s*[-,:]?\s*", "", text, flags=re.I
        ).strip()
        if state_label.title() in STATES:
            state = STATES[state_label.title()]
            country = country or "US"
    return {
        "location_raw": raw,
        "remote_type": remote,
        "country": country,
        "city": city,
        "state": state,
    }


def location_fields(
    raw: str | None,
    workplace: str | None = None,
    country: str | None = None,
    city: str | None = None,
    state: str | None = None,
    additional: list | None = None,
) -> dict:
    primary = _single_location(raw, workplace, country, city, state)
    chunks = re.split(r"\s+[\/|]\s+|;\s*|\s+or\s+", raw or "", flags=re.I)
    locations = []
    for index, chunk in enumerate(chunks):
        if chunk.strip():
            loc = _single_location(
                chunk.strip(),
                workplace,
                country if index == 0 else None,
                city if index == 0 else None,
                state if index == 0 else None,
            )
            locations.append({k: loc[k] for k in ("location_raw", "city", "state", "country")})
    for item in additional or []:
        address = (item.get("address") or {}) if isinstance(item, dict) else {}
        address = address.get("postalAddress", address)
        text = (
            (item.get("location") or item.get("location_raw")) if isinstance(item, dict) else item
        )
        loc = _single_location(
            text,
            workplace,
            address.get("addressCountry")
            or (item.get("country") if isinstance(item, dict) else None),
            address.get("addressLocality")
            or (item.get("city") if isinstance(item, dict) else None),
            address.get("addressRegion") or (item.get("state") if isinstance(item, dict) else None),
        )
        record = {k: loc[k] for k in ("location_raw", "city", "state", "country")}
        if record not in locations:
            locations.append(record)
    if len(chunks) > 1:
        primary["city"] = primary["state"] = None
        countries = {loc["country"] for loc in locations if loc["country"]}
        primary["country"] = next(iter(countries)) if len(countries) == 1 else None
    primary["locations"] = locations
    primary.update(remote_restrictions(raw or ""))
    return primary


def states_in(text: str) -> list[str]:
    found = {code for code in STATES.values() if re.search(rf"\b{code}\b", text)}
    found.update(
        code for name, code in STATES.items() if re.search(rf"\b{re.escape(name)}\b", text, re.I)
    )
    return sorted(found)


def remote_restrictions(raw: str, description: str = "") -> dict:
    """Capture explicit restrictions and preserve the employer's language."""
    text = raw + "\n" + description
    evidence = []
    excluded, allowed = [], []
    for match in re.finditer(
        r"\bremote[^.\n;]{0,50}\b(?:except|excluding)\s+([^.;\n]+)", text, re.I
    ):
        excluded.extend(states_in(match[1]))
        evidence.append(match[0])
    for match in re.finditer(
        r"\bremote\s+(?:only\s+)?(?:within|in|limited to)\s+([^.;\n]+)", text, re.I
    ):
        if not re.search(r"except|excluding", match[1], re.I):
            allowed.extend(states_in(match[1]))
            if states_in(match[1]):
                evidence.append(match[0])
    us = re.search(
        r"\bremote[^.;\n]{0,50}\b(?:United States|USA|(?-i:US)(?: only)?)\b"
        r"|\b(?:(?-i:US)|USA|United States)[^.;\n]{0,25}\bremote\b",
        text,
        re.I,
    )
    other_remote = re.search(
        r"\bremote[^.;\n]{0,40}\b(?:Canada|UK|United Kingdom|global|worldwide)\b", text, re.I
    )
    if us:
        evidence.append(us[0])
    timezone = None
    tz = re.search(
        (
            "[^.\\n;]{0,65}\\b(?:Eastern|Central|Pacific|Mountain"
            "|EST|EDT|CST|CDT|PST|PDT|MST|MDT)[^.;\\n]{0,65}(?:T"
            "ime|time zones?|timezone)[^.;\\n]{0,40}"
        ),
        text,
    )
    if not tz:
        tz = re.search(r"\bRemote\s*\((?:EST|EDT|CST|CDT|PST|PDT|MST|MDT)\)", raw, re.I)
    if tz:
        timezone = tz[0].strip()[:250]
        evidence.append(timezone)
    return {
        "remote_us_only": True if us and not other_remote else None,
        "remote_states": sorted(set(allowed)),
        "excluded_states": sorted(set(excluded)),
        "timezone_requirement": timezone,
        "remote_restriction_evidence": list(dict.fromkeys(evidence)),
    }
