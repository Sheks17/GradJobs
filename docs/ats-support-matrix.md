# ATS support matrix

Researched 14 October 2026. All 22 requested ATS platforms are represented in
`collectors/ats_registry.py`. There are eight ATS collectors plus the existing
USAJOBS collector. Fourteen ATS entries are detection only. A hosted URL signature
is identification evidence, not proof of an active employer or usable feed.
Custom-domain detection requires observed hosted links or exact generator metadata;
ordinary ATS mentions and LinkedIn links do not establish provider identity.

| Provider | Detection | Public job ingestion | Access type | GradJobs support | Notes |
| --- | --- | --- | --- | --- | --- |
| Greenhouse | Hosted URL / exact generator | Yes, verified public path | PUBLIC_API | Full | Anonymous published job board API; Harvest recruiter API is separate. [Evidence](https://developers.greenhouse.io/job-board.html) |
| Lever | Hosted URL / exact generator | Yes, verified public path | PUBLIC_API | Full | Published postings API, not candidate APIs. [Evidence](https://github.com/lever/postings-api) |
| Ashby | Hosted URL / exact generator | Yes, verified public path | PUBLIC_API | Full | Published job-board API only. [Evidence](https://developers.ashbyhq.com/docs/public-job-posting-api) |
| SmartRecruiters | Hosted URL / exact generator | Yes, verified public path | PUBLIC_API | Full | Public posting API, distinct from authenticated recruiting APIs. [Evidence](https://developers.smartrecruiters.com/docs/posting-api) |
| Workday | Hosted URL / exact generator | Yes, verified public path | PUBLIC_CAREERS_ENDPOINT | Full | Verified public CXS tenant sites; custom domains and restricted tenants not assumed. [Evidence](https://workday.wd5.myworkdayjobs.com/en-US/Workday) |
| Workable | Hosted URL / exact generator | Yes, verified public path | PUBLIC_CAREERS_ENDPOINT | Full | Anonymous widget list and hosted-careers detail verified. SPI employer API requires a token; not used. [Evidence](https://help.workable.com/hc/en-us/articles/115012801727-How-to-embed-jobs-on-your-website-job-widget) |
| Recruitee | Hosted URL / exact generator | Yes, verified public path | PUBLIC_CAREERS_ENDPOINT | Full | Published /api/offers feed verified anonymously. New Careers Site API requires employer token; feeds and API must not be conflated. [Evidence](https://support.recruitee.com/en/articles/8213076-faq-api) |
| BreezyHR | Hosted URL / exact generator | Yes, verified public path | PUBLIC_CAREERS_ENDPOINT | Full | Anonymous /json list plus schema.org JobPosting on public pages verified. Private /v3 API is not used. [Evidence](https://adaptic-llc.breezy.hr/) |
| Avature | Hosted URL / exact generator | Not implemented; anonymous feed not established | UNKNOWN | Detection only | Public careers portals and configurable integration framework exist; stable anonymous feed/authentication contract not established. Detection only. [Evidence](https://www.avature.net/blogs/how-to-succeed-hr-technology-integration/) |
| BrassRing | Hosted URL / exact generator | Not implemented; anonymous feed not established | EMPLOYER_API | Detection only | Talent Gateway job-search APIs require employer configuration (ClientID/SiteID). No universal anonymous feed validated. [Evidence](https://media.kenexa.com/Training/TSBR/APIDocs/APIRefCandiTGAPIs.pdf) |
| Darwinbox | Hosted URL / exact generator | Not implemented; anonymous feed not established | UNKNOWN | Detection only | Recruitment integrations and candidate portals exist; no stable anonymous feed verified. Do not use recruitment-account APIs. [Evidence](https://www.postman.com/darwinbox-api/darwinbox-integration-team-s-public-workspace/request/rv0p0r9/fetch-job-detail-v2) |
| Freshteam | Hosted URL / exact generator | Not implemented; anonymous feed not established | AUTHENTICATED_API | Detection only | Documented /api/job_postings requires employer Bearer authorization. Public /jobs pages detectable, collector unavailable. [Evidence](https://developers.freshteam.com/api/) |
| iCIMS | Hosted URL / exact generator | Not implemented; anonymous feed not established | EMPLOYER_API | Detection only | Public job portals visible; documented job-portal API belongs to customer integration. Anonymous stable collection not validated. [Evidence](https://developer-community.icims.com/applications/applicant-tracking/job-portal) |
| JazzHR | Hosted URL / exact generator | Not implemented; anonymous feed not established | AUTHENTICATED_API | Detection only | Public ApplyToJob pages visible; recruiter integration requires account API key. No anonymous feed collector validated. [Evidence](https://marketplace.jazzhr.com/wp-content/uploads/Logi-Serve_JazzHR_Integration.pdf) |
| Jobvite | Hosted URL / exact generator | Not implemented; anonymous feed not established | AUTHENTICATED_API | Detection only | Documented Job Feed API is paid customer access with key/secret; public pages alone are not API authorization. [Evidence](https://careers.jobvite.com/careersite/job_feed_api.html) |
| Kula | Hosted URL / exact generator | Not implemented; anonymous feed not established | DETECTION_ONLY | Detection only | Published career pages observed; stable anonymous API contract not established. No layout scraping added. [Evidence](https://careers.kula.ai/relay) |
| Oracle Recruiting Cloud | Hosted URL / exact generator | Not implemented; anonymous feed not established | DETECTION_ONLY | Detection only | External CandidateExperience pages are public; CE REST category is marked internal-use. No general collector implemented. [Evidence](https://docs.oracle.com/en/cloud/saas/human-resources/farws/op-recruitingcejobapplications-post.html) |
| Rippling | Hosted URL / exact generator | Not implemented; anonymous feed not established | AUTHENTICATED_API | Detection only | Hosted career boards public; documented developer APIs require customer API keys. Public feed contract not validated. [Evidence](https://developer.rippling.com/documentation/developer-portal/reference/api-reference) |
| SAP SuccessFactors | Hosted URL / exact generator | Not implemented; anonymous feed not established | AUTHENTICATED_API | Detection only | OData recruiting API uses OAuth and requisition permissions; public portals do not establish anonymous OData access. [Evidence](https://help.sap.com/docs/SAP_SUCCESSFACTORS_PLATFORM/d599f15995d348a1b45ba5603e2aba9b/5511f05d636f414084a22909bc35f509.html) |
| Teamtailor | Hosted URL / exact generator | Not implemented; anonymous feed not established | AUTHENTICATED_API | Detection only | Even public-scope API keys authenticate a customer account. Anonymous careers pages exist, but generic ingestion not implemented. [Evidence](https://docs.teamtailor.com/) |
| Zoho Recruit | Hosted URL / exact generator | Not implemented; anonymous feed not established | AUTHENTICATED_API | Detection only | Recruit API requires OAuth. Public careers portals detectable; stable anonymous collection not verified. [Evidence](https://www.zoho.com/recruit/developer-guide/apiv2/access-refresh.html) |
| LinkedIn Talent Hub | Limited exact generator only | Not implemented; anonymous feed not established | PARTNER_ONLY | Detection only | No LinkedIn fetching or scraping. Explicit career-page generator metadata can identify Talent Hub; ordinary LinkedIn links cannot. Assessment integrations are not job-feed authorization. [Evidence](https://business.linkedin.com/talent-solutions/talent-hub/integrations) |

## Research questions and boundaries

1. **Anonymous visitor visibility:** published employer careers pages can be
   viewed for implemented providers and the cited public Kula/Oracle portals.
   Visibility of every customer/custom-domain portal is not asserted. Other vendor
   documentation establishes career portals, not successful anonymous access to
   every employer.
2. **Stable public API:** Greenhouse, Lever, Ashby and SmartRecruiters have
   documented public posting APIs. Workday/Workable/Recruitee/BreezyHR collectors
   use verified public careers data, not a guaranteed universal API contract.
3. **Public careers endpoints:** Workable widget and hosted details, Recruitee
   published feed, BreezyHR JSON plus schema.org JobPosting and Workday CXS were
   verified. Other anonymous endpoint contracts remain unverified; UNKNOWN is
   intentional where evidence is insufficient.
4. **Employer credentials:** Freshteam, iCIMS, JazzHR, Jobvite, Rippling,
   SAP SuccessFactors, Teamtailor and Zoho Recruit document authenticated employer
   API access. BrassRing's Talent Gateway API requires employer configuration;
   ClientID/SiteID should not automatically be described as secret credentials.
   Avature and Darwinbox authentication contracts were not independently established.
5. **Partner access:** LinkedIn hiring integrations operate through partner/customer
   arrangements. No private Talent Hub endpoint was accessed. Other partner programs
   are not treated as proof that every job API is partner-only.
6. **Scraping:** public pages exist, but layout scraping is not assumed to be the
   only possible approach. No brittle parser was built for unimplemented providers.
   BreezyHR reads standardized structured JobPosting data rather than page layout.
7. **Detection:** 21 hosted ATS URL signatures plus limited exact Talent Hub
   generator metadata are implemented and fixture tested. Full live employer
   verification is claimed only for runnable providers and documented sources.

The distinction for Recruitee is especially important: its
[Careers Site API now requires a token](https://support.recruitee.com/en/articles/1066282-api-documentation),
while its [published feeds are documented separately](https://support.recruitee.com/en/articles/8213076-faq-api)
and `/api/offers` was verified anonymously on six enabled employer boards. A
protected feed remains unavailable; the collector never supplies an employer token.

Teamtailor's “public” API scope still requires an API key. Public career pages or
possible feeds do not justify a general support claim; Teamtailor remains detection
only. LinkedIn Talent Hub assessment/recruiter integrations, including HackerRank
integrations, provide neither public job-feed authorization nor GradJobs access.
GradJobs refuses LinkedIn fetches, including redirects, and never guesses account IDs.

Candidate records retain provider/access/unsupported reason/last-check metadata.
Normal resumption and `--retry` do not retry unsupported providers. Future review
requires an explicit fresh discovery output after a capability/collector change.
No unsupported source is registered for scheduled ingestion.
