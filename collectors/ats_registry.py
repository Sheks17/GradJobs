"""Evidence-backed access classification, separate from runnable collectors.

Detection never grants permission to call an employer or partner API. Public
career-page visibility does not establish a stable anonymous job feed.
"""

import re
from urllib.parse import urlsplit


def record(
    name, hosts, access, notes, evidence, *, supported=False, aliases=(), paths=(), endpoints=()
):
    return dict(
        canonical_name=name,
        aliases=list(aliases),
        career_url_patterns=list(hosts),
        path_patterns=list(paths),
        public_endpoint_patterns=list(endpoints),
        detection_signatures=[name],
        ingestion_status=access,
        authentication_type="none"
        if supported
        else "partner"
        if access == "PARTNER_ONLY"
        else "employer"
        if access in {"AUTHENTICATED_API", "EMPLOYER_API"}
        else "unknown",
        public_job_discovery_supported=True if supported else None,
        source_discovery_supported=bool(hosts),
        implementation_status="supported" if supported else "detection_only",
        notes=notes,
        evidence_urls=[evidence],
        researched_at="2026-10-14",
    )


ATS_REGISTRY = {
    "greenhouse": record(
        "Greenhouse",
        [r"(?:boards|job-boards)\.greenhouse\.io"],
        "PUBLIC_API",
        "Anonymous published job board API; Harvest recruiter API is separate.",
        "https://developers.greenhouse.io/job-board.html",
        supported=True,
        endpoints=["https://boards-api.greenhouse.io/v1/boards/{account}/jobs"],
    ),
    "lever": record(
        "Lever",
        [r"jobs\.lever\.co"],
        "PUBLIC_API",
        "Published postings API, not candidate APIs.",
        "https://github.com/lever/postings-api",
        supported=True,
    ),
    "ashby": record(
        "Ashby",
        [r"jobs\.ashbyhq\.com"],
        "PUBLIC_API",
        "Published job-board API only.",
        "https://developers.ashbyhq.com/docs/public-job-posting-api",
        supported=True,
    ),
    "smartrecruiters": record(
        "SmartRecruiters",
        [r"(?:careers|jobs|www)\.smartrecruiters\.com"],
        "PUBLIC_API",
        "Public posting API, distinct from authenticated recruiting APIs.",
        "https://developers.smartrecruiters.com/docs/posting-api",
        supported=True,
    ),
    "workday": record(
        "Workday",
        [r"[a-z0-9-]+\.wd\d+\.myworkdayjobs\.com"],
        "PUBLIC_CAREERS_ENDPOINT",
        "Verified public CXS tenant sites; custom domains and restricted tenants not assumed.",
        "https://workday.wd5.myworkdayjobs.com/en-US/Workday",
        supported=True,
    ),
    "workable": record(
        "Workable",
        [r"apply\.workable\.com"],
        "PUBLIC_CAREERS_ENDPOINT",
        "Anonymous widget list and hosted-careers detail verified. SPI employer API "
        "requires a token; not used.",
        "https://help.workable.com/hc/en-us/articles/115012801727-How-to-embed-jobs-on-your-website-job-widget",
        supported=True,
        endpoints=[
            "https://apply.workable.com/api/v1/widget/accounts/{account}",
            "https://apply.workable.com/api/v2/accounts/{account}/jobs/{shortcode}",
        ],
    ),
    "recruitee": record(
        "Recruitee",
        [r"(?!app\.|api\.|support\.)[a-z0-9-]+\.recruitee\.com"],
        "PUBLIC_CAREERS_ENDPOINT",
        "Published /api/offers feed verified anonymously. New Careers Site API "
        "requires employer token; feeds and API must not be conflated.",
        "https://support.recruitee.com/en/articles/8213076-faq-api",
        supported=True,
        aliases=["Tellent Recruitee"],
        endpoints=["https://{account}.recruitee.com/api/offers"],
    ),
    "breezyhr": record(
        "BreezyHR",
        [r"(?!api\.|help\.|developer\.|www\.)[a-z0-9-]+\.breezy\.hr"],
        "PUBLIC_CAREERS_ENDPOINT",
        "Anonymous /json list plus schema.org JobPosting on public pages verified. "
        "Private /v3 API is not used.",
        "https://adaptic-llc.breezy.hr/",
        supported=True,
        aliases=["Breezy HR"],
        endpoints=["https://{account}.breezy.hr/json"],
    ),
    "avature": record(
        "Avature",
        [r"[a-z0-9-]+\.avature\.net"],
        "UNKNOWN",
        "Public careers portals and configurable integration framework exist; "
        "stable anonymous feed/authentication contract not established. Detection "
        "only.",
        "https://www.avature.net/blogs/how-to-succeed-hr-technology-integration/",
        paths=[r"/(?:careers|jobs|talent).*"],
    ),
    "brassring": record(
        "BrassRing",
        [r"[a-z0-9-]+\.brassring\.com"],
        "EMPLOYER_API",
        "Talent Gateway job-search APIs require employer configuration "
        "(ClientID/SiteID). No universal anonymous feed validated.",
        "https://media.kenexa.com/Training/TSBR/APIDocs/APIRefCandiTGAPIs.pdf",
        aliases=["Kenexa BrassRing"],
        paths=[r"/TG(?:new)?UI/.*"],
    ),
    "darwinbox": record(
        "Darwinbox",
        [r"[a-z0-9-]+\.darwinbox\.(?:in|com)"],
        "UNKNOWN",
        "Recruitment integrations and candidate portals exist; no stable anonymous "
        "feed verified. Do not use recruitment-account APIs.",
        "https://www.postman.com/darwinbox-api/darwinbox-integration-team-s-public-workspace/request/rv0p0r9/fetch-job-detail-v2",
        paths=[r"/(?:jobs|careers|ms/candidate).*"],
    ),
    "freshteam": record(
        "Freshteam",
        [r"(?!developers\.|support\.)[a-z0-9-]+\.freshteam\.com"],
        "AUTHENTICATED_API",
        "Documented /api/job_postings requires employer Bearer authorization. "
        "Public /jobs pages detectable, collector unavailable.",
        "https://developers.freshteam.com/api/",
        paths=[r"/jobs.*"],
    ),
    "icims": record(
        "iCIMS",
        [r"[a-z0-9-]+\.icims\.com"],
        "EMPLOYER_API",
        "Public job portals visible; documented job-portal API belongs to customer "
        "integration. Anonymous stable collection not validated.",
        "https://developer-community.icims.com/applications/applicant-tracking/job-portal",
        paths=[r"/jobs.*"],
    ),
    "jazzhr": record(
        "JazzHR",
        [r"[a-z0-9-]+\.applytojob\.com"],
        "AUTHENTICATED_API",
        "Public ApplyToJob pages visible; recruiter integration requires account "
        "API key. No anonymous feed collector validated.",
        "https://marketplace.jazzhr.com/wp-content/uploads/Logi-Serve_JazzHR_Integration.pdf",
        paths=[r"/apply.*"],
    ),
    "jobvite": record(
        "Jobvite",
        [r"(?:jobs|careers)\.jobvite\.com"],
        "AUTHENTICATED_API",
        "Documented Job Feed API is paid customer access with key/secret; public "
        "pages alone are not API authorization.",
        "https://careers.jobvite.com/careersite/job_feed_api.html",
    ),
    "kula": record(
        "Kula",
        [r"careers\.kula\.ai"],
        "DETECTION_ONLY",
        "Published career pages observed; stable anonymous API contract not "
        "established. No layout scraping added.",
        "https://careers.kula.ai/relay",
    ),
    "oracle_recruiting_cloud": record(
        "Oracle Recruiting Cloud",
        [r"[a-z0-9.-]+\.oraclecloud\.com"],
        "DETECTION_ONLY",
        "External CandidateExperience pages are public; CE REST category is marked "
        "internal-use. No general collector implemented.",
        "https://docs.oracle.com/en/cloud/saas/human-resources/farws/op-recruitingcejobapplications-post.html",
        aliases=["Oracle Cloud Recruiting", "ORC"],
        paths=[r"/hcmUI/CandidateExperience/.*"],
    ),
    "rippling": record(
        "Rippling",
        [r"ats\.rippling\.com"],
        "AUTHENTICATED_API",
        "Hosted career boards public; documented developer APIs require customer "
        "API keys. Public feed contract not validated.",
        "https://developer.rippling.com/documentation/developer-portal/reference/api-reference",
    ),
    "sap_successfactors": record(
        "SAP SuccessFactors",
        [r"[a-z0-9.-]+\.successfactors\.(?:com|eu)"],
        "AUTHENTICATED_API",
        "OData recruiting API uses OAuth and requisition permissions; public "
        "portals do not establish anonymous OData access.",
        "https://help.sap.com/docs/SAP_SUCCESSFACTORS_PLATFORM/d599f15995d348a1b45ba5603e2aba9b/5511f05d636f414084a22909bc35f509.html",
        aliases=["SuccessFactors"],
        paths=[r"/career.*"],
    ),
    "teamtailor": record(
        "Teamtailor",
        [r"(?!api\.|support\.|partner\.|www\.)[a-z0-9-]+\.(?:na\.|au\.)?teamtailor\.com"],
        "AUTHENTICATED_API",
        "Even public-scope API keys authenticate a customer account. Anonymous "
        "careers pages exist, but generic ingestion not implemented.",
        "https://docs.teamtailor.com/",
    ),
    "zoho_recruit": record(
        "Zoho Recruit",
        [r"[a-z0-9.-]+\.zohorecruit\.(?:com|eu|in)"],
        "AUTHENTICATED_API",
        "Recruit API requires OAuth. Public careers portals detectable; stable "
        "anonymous collection not verified.",
        "https://www.zoho.com/recruit/developer-guide/apiv2/access-refresh.html",
        paths=[r"/jobs.*"],
    ),
    "linkedin_talent_hub": record(
        "LinkedIn Talent Hub",
        [],
        "PARTNER_ONLY",
        "No LinkedIn fetching or scraping. Explicit career-page generator metadata "
        "can identify Talent Hub; ordinary LinkedIn links cannot. Assessment "
        "integrations are not job-feed authorization.",
        "https://business.linkedin.com/talent-solutions/talent-hub/integrations",
    ),
    "usajobs": record(
        "USAJOBS",
        [r"(?:www\.)?usajobs\.gov"],
        "AUTHENTICATED_API",
        "Official job discovery uses registered API key/User-Agent; already supported. Not an ATS.",
        "https://developer.usajobs.gov/",
        supported=True,
    ),
}
ATS_REGISTRY["usajobs"]["authentication_type"] = "registered_api_key"


def detect_url(url):
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password:
        return None
    host = (parsed.hostname or "").lower()
    for provider, item in ATS_REGISTRY.items():
        if any(re.fullmatch(pattern, host) for pattern in item["career_url_patterns"]) and (
            not item["path_patterns"]
            or any(re.fullmatch(pattern, parsed.path, re.I) for pattern in item["path_patterns"])
        ):
            return provider
    return None


def capability(provider):
    item = ATS_REGISTRY[provider]
    return dict(
        provider=provider,
        access_classification=item["ingestion_status"],
        detection_confidence="high",
        verified_ats=True,
        public_ingestion=item["implementation_status"],
        authentication_type=item["authentication_type"],
        source_discovery_supported=item["source_discovery_supported"],
        unsupported_reason=None if item["implementation_status"] == "supported" else item["notes"],
    )
