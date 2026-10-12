import re

from collectors.normalizers.text import normalize_title
from matching.aliases import ROLE_ALIASES
from shared.constants import Seniority

SENIOR_PATTERNS: list[tuple[str, Seniority]] = [
    (r"\b(?:vice president|vp|head|chief|ceo|cto|cio)\b", "executive"),
    (r"\bdirector\b", "director"),
    (r"\bmanager\b", "manager"),
    (r"\bprincipal\b", "principal"),
    (r"\bstaff\b", "staff"),
    (r"\bsenior\b", "senior"),
    (r"\b(?:lead|architect)\b", "lead"),
]


def classify_seniority(title: str) -> Seniority:
    text = normalize_title(title)
    strong_senior = re.search(
        r"\b(?:senior|staff|principal|director|manager|head|vp|chief)\b", text
    )
    # Occupational architect/lead titles can be explicitly trainee or junior roles.
    if not strong_senior:
        if re.search(r"\b(?:intern|internship)\b", text):
            return "internship"
        if re.search(r"\b(?:new grad|recent graduate|graduate)\b", text):
            return "new_grad"
        if re.search(r"\bentry level\b", text):
            return "entry"
        if re.search(r"\bjunior\b", text):
            return "junior"
        if re.search(r"\bassociate\b", text) and ("lead" not in text or "program" in text):
            return "associate"
        if re.search(r"\bearly career\b", text):
            return "early_career"
    for pattern, result in SENIOR_PATTERNS:
        if re.search(pattern, text):
            return result
    # Numerals count only next to a role noun or an explicit Level label.
    if re.search(
        r"\b(?:engineer|analyst|developer|administrator|specialist) (?:i|1)\b|\blevel 1\b", text
    ):
        return "level_1"
    if re.search(
        r"\b(?:engineer|analyst|developer|administrator|specialist) (?:ii|2)\b|\blevel 2\b", text
    ):
        return "level_2"
    if re.search(
        r"\b(?:engineer|analyst|developer|administrator|specialist) (?:iii|3)\b|\blevel 3\b", text
    ):
        return "mid"
    return "unknown"


def classify_role(title: str) -> str:
    text = normalize_title(title)
    return next((role for role, pattern in ROLE_ALIASES if re.search(pattern, text)), "Other")
