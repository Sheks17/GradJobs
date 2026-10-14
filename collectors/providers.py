from collectors.ashby import AshbyCollector
from collectors.breezyhr import BreezyHRCollector
from collectors.greenhouse import GreenhouseCollector
from collectors.lever import LeverCollector
from collectors.recruitee import RecruiteeCollector
from collectors.smartrecruiters import SmartRecruitersCollector
from collectors.usajobs import USAJobsCollector
from collectors.workable import WorkableCollector
from collectors.workday import WorkdayCollector

PROVIDERS = {"greenhouse": GreenhouseCollector, "lever": LeverCollector, "ashby": AshbyCollector}
PROVIDERS.update(smartrecruiters=SmartRecruitersCollector, usajobs=USAJobsCollector)
PROVIDERS["workday"] = WorkdayCollector
PROVIDERS.update(
    workable=WorkableCollector, recruitee=RecruiteeCollector, breezyhr=BreezyHRCollector
)
GreenhouseCollector.capabilities = {**GreenhouseCollector.capabilities, "posted_date": False}
LeverCollector.capabilities = {
    **LeverCollector.capabilities,
    "pagination": True,
    "salary": True,
    "posted_date": True,
}
AshbyCollector.capabilities = {**AshbyCollector.capabilities, "salary": True, "posted_date": True}
CAREERS = {
    "workable": "https://apply.workable.com/{board}/",
    "recruitee": "https://{board}.recruitee.com/",
    "breezyhr": "https://{board}.breezy.hr/",
    "workday": "https://{board}",
    "greenhouse": "https://boards.greenhouse.io/{board}",
    "lever": "https://jobs.lever.co/{board}",
    "ashby": "https://jobs.ashbyhq.com/{board}",
    "smartrecruiters": "https://careers.smartrecruiters.com/{board}",
    "usajobs": "https://www.usajobs.gov/",
}


def make_collector(provider, board, company, config=None, **kwargs):
    return PROVIDERS[provider](board, company, config=config or {}, **kwargs)
