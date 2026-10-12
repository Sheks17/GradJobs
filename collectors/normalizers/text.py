import hashlib
import html
import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from bs4 import BeautifulSoup


def plain_text(value: str | None) -> str:
    text = value or ""
    # Greenhouse can encode the HTML twice.
    for _ in range(2):
        text = html.unescape(text)
    soup = BeautifulSoup(text, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())


def normalize_text(value: str | None) -> str:
    value = unicodedata.normalize("NFKC", value or "").casefold()
    return re.sub(r"[^\w+#]+", " ", value).strip()


def normalize_company(value: str) -> str:
    text = normalize_text(value)
    return re.sub(r"(?:\s+(?:inc|incorporated|llc|ltd|limited|corp|corporation))+$", "", text)


def normalize_title(value: str) -> str:
    text = normalize_text(value)
    text = re.sub(r"\bsr\b", "senior", text)
    return re.sub(r"\bjr\b", "junior", text)


def normalize_url(value: str) -> str:
    parts = urlsplit(value)
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in {"source", "ref", "referrer"}
    ]
    # Keep requisition query parameters (e.g. gh_jid); they identify distinct jobs.
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path.rstrip("/"),
            urlencode(sorted(query)),
            "",
        )
    )


def description_fingerprint(value: str) -> str:
    return hashlib.sha256(normalize_text(value).encode()).hexdigest()
