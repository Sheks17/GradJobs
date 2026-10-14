from datetime import timedelta
from math import ceil

from sqlalchemy import case, exists, func, or_, select
from sqlalchemy.orm import Session, load_only

from collectors.normalizers.location import normalize_state
from matching.scoring import SENIOR_LEVELS
from services.api.app.db.session import utcnow
from services.api.app.models.job import Job, JobLocation, JobSkill, JobSource
from services.api.app.schemas.jobs import JobFilters, JobPage, JobSummary, Stats


def visible_conditions(country: str = "US") -> list:
    conditions = [
        Job.is_active.is_(True),
        Job.duplicate_of.is_(None),
        or_(Job.closing_at.is_(None), Job.closing_at > utcnow()),
    ]
    if country != "all":
        conditions.append(
            or_(
                Job.country == country,
                exists(
                    select(1).where(
                        JobLocation.job_id == Job.id,
                        JobLocation.country == country,
                    )
                ),
            )
        )
    return conditions


def list_jobs(db: Session, filters: JobFilters) -> JobPage:
    conditions = visible_conditions(filters.country)
    if filters.provider:
        conditions.append(Job.source == filters.provider)
    relevance = 0
    if not filters.role_family:
        conditions.append(Job.role_family != "Other")
    conditions.append(Job.early_career_score >= filters.min_early_career_score)
    if not filters.include_senior:
        conditions.append(Job.seniority_level.not_in(SENIOR_LEVELS))
    if not filters.include_demo:
        conditions.append(Job.is_demo.is_(False))
    if filters.q:
        from matching.skills import normalize_skill

        for token in filters.q.split()[:12]:
            escaped = token.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            title = Job.title.ilike(pattern, escape="\\")
            company = Job.company_name.ilike(pattern, escape="\\")
            role = Job.role_family.ilike(pattern, escape="\\")
            skill = normalize_skill(token)
            skill_match = (
                Job.id.in_(select(JobSkill.job_id).where(JobSkill.skill == skill))
                if skill
                else False
            )
            conditions.append(
                or_(title, company, role, skill_match, Job.description.ilike(pattern, escape="\\"))
            )
            relevance += case((title, 100), (company, 70), (role, 30), (skill_match, 20), else_=5)
    if filters.skill:
        conditions.append(
            exists(select(1).where(JobSkill.job_id == Job.id, JobSkill.skill == filters.skill))
        )
    if filters.experience_category:
        conditions.append(Job.experience_category == filters.experience_category)
    if filters.role_group:
        groups = {
            "software": ["Software Engineering", "Front-End", "Back-End", "Full-Stack", "Mobile"],
            "support": [
                "Technical Support",
                "Product Support",
                "Application Support",
                "IT Support",
            ],
            "cloud": ["Cloud / Infrastructure", "DevOps / SRE", "Networking"],
        }
        conditions.append(Job.role_family.in_(groups[filters.role_group]))
    for value, column in [
        (filters.role_family, Job.role_family),
        (filters.seniority, Job.seniority_level),
        (filters.remote_type, Job.remote_type),
    ]:
        if value:
            conditions.append(column == value)
    if filters.state:
        state = normalize_state(filters.state)
        loc = select(1).where(JobLocation.job_id == Job.id, JobLocation.state == state)
        if filters.country != "all":
            loc = loc.where(JobLocation.country == filters.country)
        conditions.append(
            or_(
                (Job.state == state) & (Job.country == filters.country)
                if filters.country != "all"
                else Job.state == state,
                exists(loc),
            )
        )
    if filters.company:
        conditions.append(
            or_(
                Job.company_slug == filters.company,
                func.lower(Job.company_name) == filters.company.lower(),
            )
        )
    if filters.min_salary is not None:
        conditions.extend(
            [
                Job.salary_min >= filters.min_salary,
                Job.salary_currency == "USD",
                Job.salary_period == "year",
            ]
        )
    if filters.max_experience is not None:
        # Legacy rows retain their old bounds until safely reprocessed. Preferences
        # on versioned rows never act as a mandatory work-experience minimum.
        required = case(
            (Job.matching_version.is_(None), Job.experience_min_years),
            else_=Job.required_min_years,
        )
        experience = required <= filters.max_experience
        conditions.append(
            or_(experience, required.is_(None))
            if filters.include_unknown_experience
            else experience
        )
    if filters.posted_after:
        conditions.append(Job.posted_at >= filters.posted_after)
    if filters.fresh_after:
        conditions.append(func.coalesce(Job.posted_at, Job.first_seen_at) >= filters.fresh_after)
    freshness = func.coalesce(Job.posted_at, Job.first_seen_at)
    now = utcnow()
    freshness_band = case(
        (freshness >= now - timedelta(days=1), 0),
        (freshness >= now - timedelta(days=3), 1),
        (freshness >= now - timedelta(days=7), 2),
        else_=3,
    )
    quality = [
        freshness_band,
        Job.early_career_score.desc(),
        Job.classification_confidence.desc(),
        freshness.desc(),
    ]
    order = {
        "best_match": ([relevance.desc()] if filters.q else []) + quality,
        "relevance": ([relevance.desc()] if filters.q else []) + quality,
        "newest": [freshness.desc()],
        "newest_posted": [Job.posted_at.desc().nullslast()],
        "recently_discovered": [Job.first_seen_at.desc()],
        "early_career_score": [
            Job.early_career_score.desc(),
            Job.classification_confidence.desc(),
            freshness.desc(),
        ],
        "company": [Job.company_name.asc()],
        "salary": [
            case(
                ((Job.salary_currency == "USD") & (Job.salary_period == "year"), Job.salary_min),
                else_=None,
            )
            .desc()
            .nullslast()
        ],
    }[filters.sort]
    total = db.scalar(select(func.count()).select_from(Job).where(*conditions)) or 0
    items = db.scalars(
        select(Job)
        .options(
            load_only(*(getattr(Job, name) for name in JobSummary.model_fields), raiseload=True)
        )
        .where(*conditions)
        .order_by(*order, Job.id)
        .offset((filters.page - 1) * filters.page_size)
        .limit(filters.page_size)
    ).all()
    return JobPage(
        items=items,
        total=total,
        page=filters.page,
        page_size=filters.page_size,
        total_pages=ceil(total / filters.page_size),
    )


def statistics(db: Session) -> Stats:
    now = utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week = today - timedelta(days=today.weekday())

    def count_when(condition):
        return func.coalesce(func.sum(case((condition, 1), else_=0)), 0)

    row = db.execute(
        select(
            func.count(Job.id),
            count_when(Job.first_seen_at >= today),
            count_when(Job.first_seen_at >= week),
            count_when(Job.remote_type == "remote"),
            count_when(
                Job.seniority_level.in_(
                    ["entry", "new_grad", "level_1", "junior", "associate", "early_career"]
                )
            ),
            func.coalesce(func.avg(Job.early_career_score), 0),
            count_when(Job.is_demo.is_(True)),
        ).where(*visible_conditions())
    ).one()
    return Stats(
        last_successful_sync=db.scalar(select(func.max(JobSource.last_successful_sync))),
        active_jobs=row[0],
        discovered_today=row[1],
        discovered_this_week=row[2],
        remote_jobs=row[3],
        entry_level_jobs=row[4],
        average_early_career_score=round(float(row[5]), 1),
        demo_jobs=row[6],
    )
