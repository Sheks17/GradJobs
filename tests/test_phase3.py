import pytest
from sqlalchemy import select

from collectors.normalizers.location import location_fields, remote_restrictions
from matching.audit import collect_audit
from matching.experience import extract_experience
from matching.reprocess import reprocess
from matching.role_classifier import classify_role, classify_seniority
from matching.scoring import score_job
from matching.skills import extract_skills
from services.api.app.models.job import Job, JobSkill
from services.api.app.repositories.ingestion import upsert_job
from services.api.app.repositories.jobs import list_jobs
from services.api.app.schemas.jobs import JobFilters
from tests.test_deduplication import data


@pytest.mark.parametrize(
    "text,low,high",
    [
        ("0–1 years", 0, 1),
        ("0 to 2 years", 0, 2),
        ("1–2 years", 1, 2),
        ("1 to 3 years", 1, 3),
        ("1+ year", 1, None),
        ("2+ years", 2, None),
        ("2 years", 2, None),
        ("At least two years", 2, None),
        ("minimum 2 years", 2, None),
        ("minimum of two years", 2, None),
        ("up to 2 years", 0, 2),
        ("less than 3 years", 0, 2),
        ("fewer than three years", 0, 2),
        ("No experience required", 0, 0),
        ("No prior professional experience required", 0, 0),
        ("Professional experience not required", 0, 0),
        ("Experience preferred but not required", 0, 0),
        ("At least twelve years of experience", 12, None),
    ],
)
def test_required_experience_forms(text, low, high):
    result = extract_experience(text)
    assert (result.required_min_years, result.required_max_years) == (low, high)
    assert result.confidence >= 0.8 and result.evidence


@pytest.mark.parametrize(
    "text",
    [
        (
            "Fortune 500. 24/7. 401(k). 10,000 customers. 3 day"
            "s onsite. 2 weeks PTO. 5% travel. $80,000 salary."
        ),
        "Certification valid for 3 years.",
        "Our company was founded 5 years ago.",
        "v2.0 software, job ID 12345, 4 years warranty",
        "Bachelor's degree or equivalent experience",
        "Four years of education and/or experience",
        "4 years of education or experience",
        "Experience with AWS preferred",
        "We celebrate our 10 years anniversary",
    ],
)
def test_irrelevant_numbers_and_education_are_not_work_minimums(text):
    assert extract_experience(text).required_min_years is None


def test_required_preferred_evidence_separate_with_headings():
    result = extract_experience(
        "Minimum qualifications:\n2 years of professional ex"
        "perience\nPreferred qualifications:\n5 years of expe"
        "rience\nPython preferred"
    )
    assert result.required_min_years == 2 and result.preferred_min_years == 5
    assert result.requirement_type == "required"
    assert len(result.evidence) == 2
    preferred = extract_experience("2 years preferred")
    assert preferred.required_min_years is None and preferred.preferred_min_years == 2


@pytest.mark.parametrize(
    "text",
    [
        "Recent graduates encouraged",
        "New graduates welcome",
        "Internship experience accepted",
        "Internships count toward experience",
        "Equivalent internship experience",
    ],
)
def test_early_signals_have_evidence_without_inventing_years(text):
    result = score_job("Software Engineer", text)
    assert result.early_career_score > 50 and result.required_min_years is None


@pytest.mark.parametrize(
    "title,level",
    [
        ("Software Engineer I", "level_1"),
        ("Analyst I", "level_1"),
        ("Developer Level 1", "level_1"),
        ("Software Engineer II", "level_2"),
        ("Software Engineer III", "mid"),
        ("Software Engineer Level 2", "level_2"),
        ("Recent Graduate Developer", "new_grad"),
        ("Early Career Engineer", "early_career"),
        ("New Grad Software Engineer", "new_grad"),
        ("Junior Solutions Architect", "junior"),
        ("Cloud Architect Intern", "internship"),
        ("Associate Technical Lead Program", "associate"),
        ("Graduate Leadership Program", "new_grad"),
        ("Junior Project Lead", "junior"),
        ("Entry-Level Security Architect", "entry"),
        ("Senior Software Engineer", "senior"),
        ("Sr. Developer", "senior"),
        ("Staff Engineer", "staff"),
        ("Principal Engineer", "principal"),
        ("Lead Software Engineer", "lead"),
        ("Engineering Manager", "manager"),
        ("Director of Engineering", "director"),
        ("Solutions Architect", "lead"),
        ("World War II Researcher", "unknown"),
    ],
)
def test_complete_title_context(title, level):
    assert classify_seniority(title) == level


@pytest.mark.parametrize(
    "title,role",
    [
        ("Customer Support Engineer", "Technical Support"),
        ("Application Analyst", "Application Support"),
        ("Implementation Consultant", "Implementation"),
        ("Solutions Engineer", "Solutions Engineering"),
        ("Platform Support Engineer", "Product Support"),
        ("DevOps Engineer", "DevOps / SRE"),
        ("Site Reliability Engineer", "DevOps / SRE"),
        ("iOS Engineer", "Mobile"),
        ("Data Analyst", "Data / Analytics"),
        ("Machine Learning Engineer", "Data / Analytics"),
        ("Database Administrator", "Database"),
        ("Network Engineer", "Networking"),
        ("Security Analyst", "Cybersecurity"),
        ("Forward Deployed Engineer", "Software Engineering"),
        ("Associate General Counsel, Commercial – Infrastructure", "Other"),
        ("Marketing Data Analyst", "Other"),
        ("Civil Engineer", "Other"),
    ],
)
def test_role_alias_context(title, role):
    assert classify_role(title) == role


def test_preference_is_less_damaging_than_a_hard_minimum():
    preferred = score_job("Software Engineer", "3 years preferred")
    required = score_job("Software Engineer", "3 years required")
    assert preferred.early_career_score > required.early_career_score
    assert preferred.required_min_years is None and required.required_min_years == 3
    assert (
        score_job("Junior Software Engineer", "5+ years of experience required").early_career_score
        <= 25
    )
    assert (
        score_job(
            "Software Engineer", "No prior professional experience required"
        ).early_career_score
        >= 70
    )


def test_confidence_conflicts_and_explanations():
    clear = score_job(
        "Junior Software Engineer",
        "We require 0–2 years of work experience. Build Python services." * 3,
    )
    ambiguous = score_job("Software Engineer", "Extensive professional experience.")
    conflict = score_job(
        "Junior Software Engineer", "Requires 5+ years of experience and direct reports."
    )
    assert clear.classification_confidence > ambiguous.classification_confidence
    assert conflict.classification_conflict and conflict.conflict_reasons
    assert conflict.classification_confidence < clear.classification_confidence
    assert clear.score_evidence and all(
        set(item) == {"type", "reason", "points"} for item in clear.score_evidence
    )
    assert len(clear.score_reasons) == len(clear.score_evidence)
    assert score_job(
        "Entry-Level Security Architect", "You will manage a team of engineers."
    ).classification_conflict


@pytest.mark.parametrize(
    "location,country,state,remote",
    [
        ("Dallas, TX", "US", "TX", "unknown"),
        ("Dallas, Texas", "US", "TX", "unknown"),
        ("Remote - USA", "US", None, "remote"),
        ("Remote, United States", "US", None, "remote"),
        ("US Remote", "US", None, "remote"),
        ("Anywhere in the US", "US", None, "unknown"),
        ("Hybrid - Austin, TX", "US", "TX", "hybrid"),
        ("Multiple Locations", None, None, "unknown"),
        ("United States - Remote", "US", None, "remote"),
        ("Remote (EST)", None, None, "remote"),
        ("Remote (Central Time)", None, None, "remote"),
        ("Remote except California", None, None, "remote"),
    ],
)
def test_location_examples(location, country, state, remote):
    result = location_fields(location)
    assert (result["country"], result["state"], result["remote_type"]) == (country, state, remote)


def test_multiple_locations_and_remote_restrictions():
    result = location_fields("Austin, TX / Denver, CO")
    assert [loc["state"] for loc in result["locations"]] == ["TX", "CO"]
    assert result["city"] is None and result["state"] is None
    restrictions = remote_restrictions(
        "Remote within the United States",
        (
            "Remote except CA, CO and NY. Must work Eastern Tim"
            "e. Candidates in Central or Eastern time zones pre"
            "ferred."
        ),
    )
    assert restrictions["remote_us_only"] is True
    assert restrictions["excluded_states"] == ["CA", "CO", "NY"]
    assert "Eastern" in restrictions["timezone_requirement"]
    assert remote_restrictions("Remote (EST)")["timezone_requirement"]
    assert remote_restrictions("Remote")["remote_us_only"] is None
    assert remote_restrictions("Remote", "Remote only in TX and CO.")["remote_states"] == [
        "CO",
        "TX",
    ]
    assert location_fields("New York or Remote")["locations"][1]["city"] is None


def test_skills_respect_punctuation_boundaries_and_aliases():
    text = (
        "JavaScript TypeScript Python Java C# C++ React Nex"
        "t.js Angular Vue Node.js Spring SQL Postgres MySQL"
        " MongoDB Amazon Web Services Azure GCP Docker k8s "
        "Linux Git REST GraphQL Playwright Selenium Cypress"
        " Postman ServiceNow"
    )
    skills = extract_skills(text)
    assert len(skills) == 30 and len(skills) == len(set(skills))
    assert extract_skills("JavaScript GitHub NoSQL rest of the spring season") == ["JavaScript"]
    assert "Java" not in extract_skills("JavaScript")


def test_reprocess_is_dry_run_safe_idempotent_and_never_changes_source_fields(db, source):
    job, _ = upsert_job(
        db,
        source.id,
        data(
            description="2 years preferred. Python and React.", location_raw="Hybrid - Austin, TX"
        ),
    )
    job.early_career_score = 0
    immutable = {
        key: getattr(job, key)
        for key in (
            "id",
            "source_id",
            "source_job_id",
            "source_url",
            "apply_url",
            "first_seen_at",
            "last_seen_at",
            "posted_at",
            "raw_data",
            "is_active",
            "missing_since",
            "duplicate_of",
        )
    }
    db.commit()
    report = reprocess(db, dry_run=True)
    assert report["planner_statistics_refreshed"] is False
    assert report["changed"] == 1 and db.get(Job, immutable["id"]).early_career_score == 0
    report = reprocess(db)
    assert report["planner_statistics_refreshed"] is True
    assert report["failed"] == 0
    stored = db.get(Job, immutable["id"])
    assert stored.early_career_score > 0 and stored.preferred_min_years == 2
    for key, value in immutable.items():
        actual = getattr(stored, key)
        if key.endswith("_at") and actual and value:
            assert actual.replace(tzinfo=None) == value.replace(tzinfo=None)
        else:
            assert actual == value
    assert set(db.scalars(select(JobSkill.skill))) == {"Python", "React"}
    assert reprocess(db)["changed"] == 0


def test_skill_filter_and_search_title_rank_above_description(db, source):
    first, _ = upsert_job(
        db,
        source.id,
        data(
            title="Junior React Developer",
            description="0-2 years of experience with React.",
            source_job_id="first",
            apply_url="https://example.com/first",
        ),
    )
    second, _ = upsert_job(
        db,
        source.id,
        data(
            title="Junior Python Developer",
            description="0-2 years of experience. React is also used.",
            source_job_id="second",
            apply_url="https://example.com/second",
        ),
    )
    third, _ = upsert_job(
        db,
        source.id,
        data(
            title="Junior Java Developer",
            description="0-2 years of experience with Java.",
            source_job_id="third",
            apply_url="https://example.com/third",
        ),
    )
    result = list_jobs(db, JobFilters(q="React", sort="best_match"))
    assert result.total == 2 and result.items[0].id == first.id
    assert list_jobs(db, JobFilters(skill="Python")).total == 1
    assert list_jobs(db, JobFilters(skill="Java")).total == 1
    assert list_jobs(db, JobFilters(q="Software Engineering")).total == 3
    assert (
        list_jobs(db, JobFilters(skill="React", max_experience=2, role_group="software")).total == 2
    )
    audit = collect_audit(db)
    assert audit["active_jobs"] == 3


def test_required_and_preferred_in_same_sentence():
    experience = extract_experience("2 years required and 5 years preferred.")
    assert experience.required_min_years == 2
    assert experience.preferred_min_years == 5


def test_contradictory_no_experience_language_keeps_hard_requirement():
    result = score_job("Junior Developer", "No experience required. Requires 5 years experience.")
    assert result.required_min_years == 5
    assert result.early_career_score <= 25
    assert "No-experience wording conflicts with a numeric requirement" in result.conflict_reasons


def test_reprocess_row_failure_isolated_and_source_filter_respected(db, source, monkeypatch):
    import matching.reprocess as module

    first, _ = upsert_job(
        db, source.id, data(source_job_id="first", apply_url="https://example.com/first")
    )
    second, _ = upsert_job(
        db, source.id, data(source_job_id="second", apply_url="https://example.com/second")
    )
    first_id, second_id = first.id, second.id
    first.early_career_score = second.early_career_score = 0
    db.commit()
    original = module.derived_fields

    def fail_one(job, collector=None):
        if job.id == first_id:
            raise ValueError("Bad retained payload")
        return original(job, collector)

    monkeypatch.setattr(module, "derived_fields", fail_one)
    assert reprocess(db, source="ashby")["processed"] == 0
    report = reprocess(db, batch_size=1)
    assert report["failed"] == 1 and report["processed"] == 2
    assert db.get(Job, first_id).early_career_score == 0
    assert db.get(Job, second_id).early_career_score > 0


def test_evaluation_never_invents_ground_truth():
    from matching.evaluate import evaluate

    dataset = {
        "jobs": [
            {
                "job_id": "test",
                "title": "Junior Developer",
                "description": "0-2 years",
                "label": None,
            }
        ]
    }
    report = evaluate(dataset)
    assert report["human_labeled"] == 0 and report["accuracy"] is None
    assert report["early_career_precision"] is None and report["confusion_matrix"] == []
    dataset["jobs"][0]["label"] = "strong_fit"
    assert evaluate(dataset)["accuracy"] == 1
    dataset["jobs"][0]["label"] = "generated_guess"
    with pytest.raises(ValueError):
        evaluate(dataset)


def test_preferred_only_is_not_a_hard_experience_filter(db, source):
    upsert_job(db, source.id, data(title="Associate Developer", description="5 years preferred."))
    assert list_jobs(db, JobFilters(max_experience=2, include_unknown_experience=True)).total == 1
    assert list_jobs(db, JobFilters(max_experience=2, include_unknown_experience=False)).total == 0


def test_conflict_boolean_sql_filter_matches_evidence(db, source):
    upsert_job(
        db, source.id, data(title="Junior Developer", description="Requires 5 years experience.")
    )
    upsert_job(
        db,
        source.id,
        data(
            title="Junior Developer",
            description="No experience required.",
            source_job_id="second",
            apply_url="https://example.com/second",
        ),
    )
    db.commit()
    conflicts = db.scalars(select(Job).where(Job.classification_conflict.is_(True))).all()
    assert len(conflicts) == 1 and conflicts[0].conflict_reasons


@pytest.mark.parametrize(
    "title,family",
    [
        ("Software Engineer, Revenue and Financial Automation", "Software Engineering"),
        ("Backend Software Engineer - Codex for Finance", "Back-End"),
        ("Software Engineer, Hardware Health", "Software Engineering"),
        ("Staff Machine Learning Engineer, Financial Connections", "Data / Analytics"),
        ("Technical Support Engineer (Finance)", "Technical Support"),
        ("Implementation Consultant - Marketing & Medical Software", "Implementation"),
        ("Founding Full Stack Software Engineer, Legal", "Full-Stack"),
        ("Privacy and Civil Liberties Software Engineer, Internship", "Software Engineering"),
        ("Developer Marketing Lead, APAC", "Other"),
        ("Associate General Counsel, Commercial Infrastructure", "Other"),
    ],
)
def test_technical_occupation_wins_over_business_domain(title, family):
    assert classify_role(title) == family


def test_reprocess_changed_roles_only_updates_affected_rows(db, source):
    changed, _ = upsert_job(db, source.id, data(title="Software Engineer, Financial Automation"))
    changed.role_family = "Other"
    upsert_job(db, source.id, data(source_job_id="second", apply_url="https://example.com/second"))
    db.commit()
    result = reprocess(db, changed_roles_only=True)
    assert result["processed"] == 2 and result["changed"] == 1
    assert result["skipped_unchanged_roles"] == 1
    assert reprocess(db, changed_roles_only=True)["skipped_unchanged_roles"] == 2
