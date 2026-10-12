"""Explainable deterministic fit and evidence-confidence heuristics, versioned for reprocessing."""

import re
from dataclasses import asdict, dataclass

from matching.aliases import EARLY_LEVELS, SENIOR_LEVELS
from matching.experience import early_career_signals, extract_experience
from matching.role_classifier import classify_role, classify_seniority
from matching.skills import extract_skills

MATCHING_VERSION = "3.0.0"
MANAGEMENT = re.compile(
    (
        "\\b(?:manage|supervise|lead|build)\\s+(?:and\\s+\\w+\\s"
        "+)?(?:a |the |our |an? )?team of (?:\\w+\\s+){0,3}(?"
        ":engineers|employees|analysts)|\\b(?:direct reports"
        "|people management (?:experience|required)|hiring "
        "and performance (?:reviews|management))\\b"
    ),
    re.I,
)
EXTENSIVE = re.compile(
    r"\b(?:extensive|substantial|significant)\s+(?:professional\s+)?experience\b", re.I
)


@dataclass(frozen=True)
class MatchResult:
    seniority_level: str
    role_family: str
    experience_min_years: int | None
    experience_max_years: int | None
    experience_text: str | None
    experience_is_preferred: bool
    required_min_years: int | None
    required_max_years: int | None
    preferred_min_years: int | None
    preferred_max_years: int | None
    requirement_type: str
    experience_category: str
    experience_confidence: float
    experience_evidence: list[dict]
    early_career_score: int
    fit_label: str
    score_reasons: list[str]
    score_evidence: list[dict]
    classification_confidence: int
    classification_conflict: bool
    conflict_reasons: list[str]
    detected_skills: list[str]
    matching_version: str = MATCHING_VERSION

    def to_dict(self) -> dict:
        return asdict(self)


def score_job(title: str, description: str) -> MatchResult:
    level, role = classify_seniority(title), classify_role(title)
    exp = extract_experience(description)
    score = 50
    confidence = 40
    evidence = []
    conflicts = []

    def add(reason, points=0):
        nonlocal score
        score += points
        evidence.append(
            {
                "type": "positive" if points > 0 else "negative" if points < 0 else "neutral",
                "reason": reason,
                "points": points,
            }
        )

    if level in SENIOR_LEVELS:
        add(f"Title indicates {level} responsibility", -60)
        confidence += 25
    elif level in EARLY_LEVELS:
        add(
            f"Title indicates {level.replace('_', ' ')} opportunity",
            28 if level != "internship" else 20,
        )
        confidence += 20
    elif level == "level_2":
        add("Level II title; experience requirements decide suitability", 4)
        confidence += 8
    elif level == "mid":
        add("Level III or mid-level title", -12)
        confidence += 12
    else:
        add("Title has no explicit seniority; suitability depends on requirements")
    if role != "Other":
        confidence += 10
    minimum = exp.required_min_years
    if minimum is not None:
        if exp.requirement_type == "none":
            points = 35
            label = "Employer explicitly says work experience is not required"
        else:
            points = (
                25
                if minimum <= 1
                else 18
                if minimum == 2
                else -20
                if minimum == 3
                else -35
                if minimum == 4
                else -55
            )
            if exp.required_max_years == 3 and minimum < 3:
                points = 18
            label = f"Required experience: {exp.matched_text}"
        add(label, points)
        confidence += 25
    elif exp.preferred_min_years is not None:
        points = 8 if exp.preferred_min_years <= 2 else -4 if exp.preferred_min_years == 3 else -8
        add(
            f"Preferred experience: {exp.preferred_min_years}+ years; "
            "no numeric required minimum detected",
            points,
        )
        confidence += 12
    else:
        add("No explicit required years detected; this does not establish zero experience")
    for signal in early_career_signals(description):
        if "uncertain" in signal:
            add(signal)
        else:
            add(signal, 8 if "Internship" in signal else 10)
    if re.search(r"\bbachelor(?:['’]s|s)?\b", description, re.I) and (
        minimum is None or minimum <= 2
    ):
        add("Bachelor's degree mentioned without a high required work-experience minimum", 7)
    if exp.requirement_type == "ambiguous":
        confidence -= 15
        add("Experience wording is ambiguous; review the employer's alternatives")
    extensive = bool(EXTENSIVE.search(description))
    management = bool(MANAGEMENT.search(description))
    if extensive:
        add("Employer asks for substantial experience beyond a clear numeric minimum", -18)
    if management:
        add("Description includes people-management responsibilities", -25)
    if level in EARLY_LEVELS and minimum is not None and minimum >= 4:
        conflicts.append("Early-career title conflicts with a high required experience minimum")
    if level in SENIOR_LEVELS and minimum is not None and minimum <= 2:
        conflicts.append("Senior title conflicts with a low required experience minimum")
    if level in EARLY_LEVELS and management:
        conflicts.append("Early-career title includes people-management responsibilities")
    if minimum is None and extensive:
        conflicts.append(
            "Substantial experience is requested without an explicit required year count"
        )
    if any(item["type"] == "none" for item in exp.evidence) and any(
        item.get("min_years", 0) > 0 and item["type"] == "required" for item in exp.evidence
    ):
        conflicts.append("No-experience wording conflicts with a numeric requirement")
    cap = 100
    if minimum is not None and minimum >= 5:
        cap = 25
    elif minimum is not None and minimum >= 4:
        cap = 40
    elif minimum is not None and minimum >= 3:
        cap = 49
    if level in SENIOR_LEVELS:
        cap = min(cap, 29)
    if management:
        cap = min(cap, 40)
    if extensive:
        cap = min(cap, 49)
    if score > cap:
        add("Hard requirements limit early-career suitability", cap - score)
    if conflicts:
        confidence -= 25
    if len(description.strip()) < 100:
        confidence -= 10
    score = max(0, min(100, score))
    confidence = max(15, min(98, confidence))
    label = (
        "Excellent Early-Career Fit"
        if score >= 85
        else "Strong Early-Career Fit"
        if score >= 70
        else "Possible Fit"
        if score >= 50
        else "Stretch"
        if score >= 30
        else "Experienced Role"
    )
    return MatchResult(
        level,
        role,
        minimum,
        exp.required_max_years,
        exp.text,
        exp.preferred,
        minimum,
        exp.required_max_years,
        exp.preferred_min_years,
        exp.preferred_max_years,
        exp.requirement_type,
        exp.category,
        exp.confidence,
        exp.evidence,
        score,
        label,
        [item["reason"] for item in evidence],
        evidence,
        confidence,
        bool(conflicts),
        conflicts,
        extract_skills(title + "\n" + description),
    )
