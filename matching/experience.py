"""Experience evidence with independent required/preferred bounds and contextual exclusions."""

import re
from dataclasses import dataclass, field

WORDS = {
    word: str(i)
    for i, word in enumerate(
        [
            "zero",
            "one",
            "two",
            "three",
            "four",
            "five",
            "six",
            "seven",
            "eight",
            "nine",
            "ten",
            "eleven",
            "twelve",
            "thirteen",
            "fourteen",
            "fifteen",
            "sixteen",
            "seventeen",
            "eighteen",
            "nineteen",
            "twenty",
        ]
    )
}
NUMBER = r"(?:\d{1,2}|" + "|".join(WORDS) + r")"
YEAR = re.compile(
    rf"(?<![\w,$])(?P<prefix>at least|minimum of|minimum|up to|less than|fewer than)?[ \t]*"
    rf"(?P<min>{NUMBER})[ \t]*(?:(?P<plus>\+)|(?:-|–|—|to)[ \t]*(?P<max>{NUMBER}))?"
    r"[ \t]*years?\b(?:['’])?",
    re.I,
)
NO_EXPERIENCE = re.compile(
    r"\b(?:no (?:prior )?(?:professional |work )?experience (?:is )?required|"
    r"(?:prior )?(?:professional |work )?experience (?:is )?not required|"
    r"experience (?:is )?preferred but (?:is )?not required)\b",
    re.I,
)
PREFERRED_HEADER = re.compile(
    (
        "^(?:preferred(?: qualifications| skills| experienc"
        "e)?|nice to have|bonus(?: points)?|desired qualifi"
        "cations)\\s*[:\\-]?$"
    ),
    re.I,
)
REQUIRED_HEADER = re.compile(
    (
        "^(?:requirements|required(?: qualifications| skill"
        "s| experience)?|minimum qualifications|what you (?"
        ":bring|need)|qualifications|must have)\\s*[:\\-]?$"
    ),
    re.I,
)
EDUCATION = re.compile(
    (
        "\\b(?:education\\s+(?:and/?or|or|and)\\s+(?:work\\s+)?"
        "experience|combination of education and experience"
        "|equivalent (?:combination|education)|(?:four|4)[ "
        "-]year (?:degree|education))\\b"
    ),
    re.I,
)


@dataclass(frozen=True)
class Experience:
    required_min_years: int | None = None
    required_max_years: int | None = None
    preferred_min_years: int | None = None
    preferred_max_years: int | None = None
    requirement_type: str = "unspecified"
    matched_text: str | None = None
    confidence: float = 0.3
    evidence: list[dict] = field(default_factory=list)

    @property
    def minimum(self):
        return (
            self.required_min_years
            if self.required_min_years is not None
            else self.preferred_min_years
        )

    @property
    def maximum(self):
        return (
            self.required_max_years
            if self.required_min_years is not None
            else self.preferred_max_years
        )

    @property
    def preferred(self):
        return self.required_min_years is None and self.preferred_min_years is not None

    @property
    def text(self):
        return self.matched_text

    @property
    def category(self):
        if self.requirement_type == "none":
            return "no_experience_required"
        if self.requirement_type == "ambiguous":
            return "ambiguous"
        low, high = self.required_min_years, self.required_max_years
        if low is None:
            return "unspecified"
        if low >= 5:
            return "5_plus"
        if low >= 4:
            return "4_plus"
        if low >= 3:
            return "3_plus"
        if (low, high) in {(0, 1), (0, 2), (1, 2), (1, 3), (2, 3)}:
            return f"{low}_{high}"
        if low == 0 and high == 0:
            return "no_experience_required"
        return "0_2" if low <= 2 else "ambiguous"


def _number(value):
    return int(WORDS.get(value.lower(), value))


def extract_experience(description: str) -> Experience:
    evidence = []
    section = "required"
    education_ambiguous = False
    offset = 0
    for line in description.splitlines() or [description]:
        clean = line.strip(" \t-*•")
        if PREFERRED_HEADER.fullmatch(clean):
            section = "preferred"
        elif REQUIRED_HEADER.fullmatch(clean):
            section = "required"
        for match in YEAR.finditer(line):
            before = re.split(r"[.!?;]", line[max(0, match.start() - 90) : match.start()])[-1]
            after = line[match.end() : match.end() + 100]
            tail = re.split(r"[.!?;\n]", after, maxsplit=1)[0]
            next_year = YEAR.search(tail)
            if next_year:
                tail = tail[: next_year.start()]
            context = before + match[0] + tail
            if re.search(
                (
                    "\\b(?:founded|established|company history|certifica"
                    "tion valid|valid for|validity|expires?|warranty|an"
                    "niversary)\\b"
                ),
                context,
                re.I,
            ):
                continue
            educational = bool(EDUCATION.search(context))
            if educational:
                education_ambiguous = True
                evidence.append(
                    {
                        "type": "education_equivalency",
                        "text": context.strip(),
                        "start": offset + match.start(),
                        "confidence": 0.45,
                    }
                )
                continue
            explicit = bool(
                match["prefix"]
                or re.search(r"\b(?:required|preferred|desired|experience)\b", tail, re.I)
            )
            experience_tail = re.match(
                r"[ \t]*(?:of[ \t]+)?(?:[A-Za-z/+\-]+[ \t]+){0,10}experience\b", tail, re.I
            )
            standalone = bool(
                re.fullmatch(
                    r"\s*(?:requires?\s+)?" + re.escape(match[0]) + r"\s*[.!]?\s*", clean, re.I
                )
            )
            heading_context = section == "preferred" or bool(
                re.search(r"experience|require|qualification", before, re.I)
            )
            if not (experience_tail or explicit or standalone or heading_context):
                continue
            low = _number(match["min"])
            high = _number(match["max"]) if match["max"] else None
            prefix = (match["prefix"] or "").lower()
            if high is not None and high < low:
                continue
            if prefix == "up to":
                low, high = 0, low
            elif prefix in {"less than", "fewer than"}:
                low, high = 0, max(0, low - 1)
            kind = section
            suffix_preferred = re.search(
                r"\b(?:preferred|desired|nice to have|a plus)\b", tail[:75], re.I
            )
            suffix_required = re.search(r"\b(?:required|mandatory|must have)\b", tail[:50], re.I)
            if suffix_required and (
                not suffix_preferred or suffix_required.start() < suffix_preferred.start()
            ):
                kind = "required"
            elif suffix_preferred:
                kind = "preferred"
            elif suffix_required or prefix.startswith(("minimum", "at least")):
                kind = "required"
            elif re.search(r"(?:preferred|desired|ideally|nice to have)[^.;]*$", before, re.I):
                kind = "preferred"
            text = match[0] + (experience_tail[0] if experience_tail else "")
            evidence.append(
                {
                    "type": kind,
                    "min_years": low,
                    "max_years": high,
                    "text": text.strip(),
                    "start": offset + match.start(),
                    "confidence": 0.95 if explicit else 0.8,
                }
            )
        offset += len(line) + 1
    no_exp = NO_EXPERIENCE.search(description)
    if no_exp:
        evidence.append(
            {
                "type": "none",
                "min_years": 0,
                "max_years": 0,
                "text": no_exp[0],
                "start": no_exp.start(),
                "confidence": 0.98,
            }
        )
    required = [item for item in evidence if item["type"] == "required"]
    preferred = [item for item in evidence if item["type"] == "preferred"]
    req = max(required, key=lambda item: item["min_years"], default=None)
    pref = max(preferred, key=lambda item: item["min_years"], default=None)
    if no_exp and not req:
        req = next(item for item in evidence if item["type"] == "none")
    uncertain = education_ambiguous or bool(
        re.search(
            r"\b(?:extensive|significant|substantial)\s+(?:professional\s+)?experience\b",
            description,
            re.I,
        )
    )
    kind = (
        "required"
        if required
        else "none"
        if no_exp
        else "ambiguous"
        if uncertain
        else "preferred"
        if pref
        else "unspecified"
    )
    chosen = req or pref
    return Experience(
        req["min_years"] if req else None,
        req["max_years"] if req else None,
        pref["min_years"] if pref else None,
        pref["max_years"] if pref else None,
        kind,
        chosen["text"] if chosen else next((item["text"] for item in evidence), None),
        chosen["confidence"] if chosen else 0.45 if uncertain else 0.3,
        evidence,
    )


def early_career_signals(description: str) -> list[str]:
    patterns = [
        (
            r"(?:recent|new) graduates? (?:are )?(?:welcome|encouraged)",
            "Recent graduates explicitly welcomed",
        ),
        (
            (
                "internship experience (?:is )?accepted|internships"
                "? count toward experience|equivalent internship ex"
                "perience"
            ),
            "Internship experience accepted",
        ),
        (
            r"(?:training (?:is )?provided|(?:graduate|rotational) program)",
            "Training or rotational program offered",
        ),
        (
            r"equivalent combination of education and experience",
            "Employer allows an education/experience combination; required years remain uncertain",
        ),
    ]
    return [label for pattern, label in patterns if re.search(pattern, description, re.I)]
