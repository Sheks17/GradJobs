from typing import Literal

from matching.aliases import ROLE_FAMILIES as ROLE_FAMILIES

RemoteType = Literal["remote", "hybrid", "onsite", "unknown"]
CollectorProvider = Literal[
    "greenhouse",
    "lever",
    "ashby",
    "smartrecruiters",
    "usajobs",
    "workday",
    "workable",
    "recruitee",
    "breezyhr",
]
SourceType = Literal[
    "greenhouse",
    "lever",
    "ashby",
    "smartrecruiters",
    "usajobs",
    "workday",
    "workable",
    "recruitee",
    "breezyhr",
    "api",
    "custom",
    "manual",
]
Seniority = Literal[
    "internship",
    "entry",
    "new_grad",
    "level_1",
    "level_2",
    "junior",
    "associate",
    "early_career",
    "mid",
    "senior",
    "staff",
    "principal",
    "lead",
    "manager",
    "director",
    "executive",
    "unknown",
]
SalaryPeriod = Literal["hour", "day", "month", "year"]
