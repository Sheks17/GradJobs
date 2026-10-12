import pytest

from matching.experience import extract_experience
from matching.role_classifier import classify_role, classify_seniority
from matching.scoring import score_job


@pytest.mark.parametrize(
    "text,minimum,maximum",
    [
        ("0-2 years of software development experience", 0, 2),
        ("At least 1 year of professional experience", 1, None),
        ("3+ years of experience", 3, None),
        ("5-7 years of experience", 5, 7),
        ("minimum of two years of experience", 2, None),
        ("1–3 years of hands-on experience", 1, 3),
        ("Up to 2 years of experience", 0, 2),
        ("No prior experience required", 0, 0),
        ("We support customers 24/7 and serve Fortune 500 companies.", None, None),
        ("$70,000 salary, 3 days per week, serving 500 customers.", None, None),
        ("Founded 5 years ago. Experience with Python is helpful.", None, None),
        ("2 years of experience required. 5 years of experience preferred.", 2, None),
        ("3 years of production experience and 1 year of Python experience.", 3, None),
    ],
)
def test_experience(text, minimum, maximum):
    result = extract_experience(text)
    assert (result.minimum, result.maximum) == (minimum, maximum)


@pytest.mark.parametrize(
    "title,level",
    [
        ("Associate Software Engineer", "associate"),
        ("Senior Software Engineer", "senior"),
        ("Sr. Developer", "senior"),
        ("QA Analyst I", "level_1"),
        ("Software Engineer II", "level_2"),
        ("Junior Systems Administrator", "junior"),
        ("Staff Engineer", "staff"),
        ("Principal Developer", "principal"),
        ("Software Engineering Manager", "manager"),
        ("Head of Technology", "executive"),
        ("Technical Lead", "lead"),
        ("Software Architect", "lead"),
        ("Technical Support Engineer", "unknown"),
        ("Leadership Program Analyst", "unknown"),
    ],
)
def test_seniority(title, level):
    assert classify_seniority(title) == level


@pytest.mark.parametrize(
    "title,role",
    [
        ("QA Analyst I", "QA / Testing"),
        ("Junior SDET", "QA / Testing"),
        ("Associate Software Engineer", "Software Engineering"),
        ("Front-End Developer", "Front-End"),
        ("Full Stack Developer", "Full-Stack"),
        ("Backend Developer", "Back-End"),
        ("Cloud Support Associate", "Cloud / Infrastructure"),
        ("Business Systems Analyst", "Systems / Business Systems"),
        ("Application Support Engineer", "Application Support"),
        ("Application Analyst", "Application Support"),
        ("Implementation Specialist", "Implementation"),
        ("IT Analyst", "IT Support"),
        ("Product Support Engineer", "Product Support"),
        ("Customer Support Engineer", "Technical Support"),
        ("Data Analyst", "Data / Analytics"),
        ("Security Analyst", "Cybersecurity"),
        ("Nurse", "Other"),
    ],
)
def test_roles(title, role):
    assert classify_role(title) == role


def test_transparent_scoring():
    associate = score_job("Associate Software Engineer", "0-2 years of experience preferred")
    senior = score_job("Senior Software Engineer", "5+ years of production experience")
    qa = score_job("QA Analyst I", "Bachelor's degree in IT. Experience with testing preferred.")
    assert associate.early_career_score >= 85
    assert associate.experience_is_preferred
    assert senior.early_career_score < 30
    assert qa.early_career_score >= 85
    assert score_job("Developer", "You will lead projects.").seniority_level == "unknown"
    assert all(result.score_reasons for result in [associate, senior, qa])
