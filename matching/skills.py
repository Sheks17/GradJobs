"""Deterministic technology vocabulary; punctuation and token boundaries are intentional."""

import re

SKILL_ALIASES = {
    "JavaScript": r"(?i:\bjavascript\b|\bjs\b)",
    "TypeScript": r"(?i:\btypescript\b)",
    "Python": r"(?i:\bpython\b)",
    "Java": r"(?i:\bjava\b)",
    "C#": r"(?i:(?<!\w)c#(?!\w)|\bc sharp\b)",
    "C++": r"(?i:(?<!\w)c\+\+(?![A-Za-z+])|\bc plus plus\b)",
    "React": r"(?i:\breact(?:\.js|js)?\b)",
    "Next.js": r"(?i:\bnext\.js\b|\bnextjs\b)",
    "Angular": r"(?i:\bangular(?:js)?\b)",
    "Vue": r"(?i:\bvue(?:\.js|js)?\b)",
    "Node.js": r"(?i:\bnode\.js\b|\bnodejs\b)",
    "Spring": r"\bSpring(?: Boot)?\b",
    "SQL": r"(?i:\bsql\b)",
    "PostgreSQL": r"(?i:\bpostgres(?:ql)?\b)",
    "MySQL": r"(?i:\bmysql\b)",
    "MongoDB": r"(?i:\bmongodb\b|\bmongo\b)",
    "AWS": r"(?i:\baws\b|\bamazon web services\b)",
    "Azure": r"(?i:\bazure\b)",
    "GCP": r"(?i:\bgcp\b|\bgoogle cloud(?: platform)?\b)",
    "Docker": r"(?i:\bdocker\b)",
    "Kubernetes": r"(?i:\bkubernetes\b|\bk8s\b)",
    "Linux": r"(?i:\blinux\b)",
    "Git": r"(?i:\bgit\b)",
    "REST": r"\bREST\b|(?i:\brestful\b)",
    "GraphQL": r"(?i:\bgraphql\b)",
    "Playwright": r"(?i:\bplaywright\b)",
    "Selenium": r"(?i:\bselenium\b)",
    "Cypress": r"(?i:\bcypress\b)",
    "Postman": r"\bPostman\b",
    "ServiceNow": r"(?i:\bservicenow\b)",
}
PATTERNS = {skill: re.compile(pattern) for skill, pattern in SKILL_ALIASES.items()}


def extract_skills(text: str) -> list[str]:
    return [skill for skill, pattern in PATTERNS.items() if pattern.search(text)]


def normalize_skill(value: str) -> str | None:
    return next(
        (skill for skill, pattern in PATTERNS.items() if pattern.fullmatch(value.strip())), None
    )
