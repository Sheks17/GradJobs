# Final ATS expansion

Measured 14 October 2026. The matching engine and existing 150-posting holdout
remain unchanged. No new required development phase is proposed.

**Restoration update:** the account owner subsequently restored Neon access on
14 October. Production migration and serving checks passed; see the
[production restoration report](production-restoration.md) for recovery ingestion
and current counts. Quota-blocked observations below describe the initial release.

## Coverage and access

All 22 requested ATS platforms were researched and classified in the
[support matrix](ats-support-matrix.md) and central `collectors/ats_registry.py`.
Eight ATS collectors plus USAJOBS are implemented: Greenhouse, Lever, Ashby,
SmartRecruiters, Workday, Workable, Recruitee and BreezyHR; federal API access uses
registered credentials. Twenty-one hosted URL signatures are implemented;
LinkedIn Talent Hub is recognized only from exact generator metadata. Ordinary
LinkedIn links or integration mentions do not identify an ATS.

Fourteen ATS entries remain detection only. Documented authenticated employer
APIs include Freshteam, iCIMS, JazzHR, Jobvite, Rippling, SAP SuccessFactors,
Teamtailor and Zoho Recruit. BrassRing requires employer Talent Gateway
configuration; Avature/Darwinbox anonymous feed contracts remain unknown. Kula
and Oracle public pages do not establish a supported anonymous API contract.
Talent Hub is partner/customer access; no LinkedIn request or private API is used.
The matrix explains uncertainty rather than claiming every other public path
is impossible.

New collectors reuse retries, validation, normalization, source leases, isolated
syncs, matching, deduplication and lifecycle reconciliation. Shared public-feed
helpers reject malformed or unexpectedly paginated/truncated feeds. Current
Workable/Recruitee/BreezyHR feeds supply complete lists rather than page tokens.
Workable and BreezyHR stop after five consecutive detail failures and mark partial
snapshots; missing structured data is not replaced with layout scraping.

Discovery reports provider confidence/access/collector availability and retains
detected-but-unsupported candidates without automatic ingestion retries or source
activation. The read-only `/admin/providers` page reports access, support, employer
counts, jobs, last sync and health; during outages it withholds database counts.

## Verified employers and postings

The previously measured baseline was **87 verified employers**, including four
disabled Workday candidates and 83 enabled employers. Fifteen new employers passed
full posting normalization and live endpoint verification: **102 verified
employers** overall, **98 enabled employer configurations** plus one federal query
source (**99 source configurations**). New configurations are committed but not
yet claimed as production-populated sources because Neon is over quota.

| New provider | Verified employers | Postings imported in isolated database |
| --- | ---: | ---: |
| Workable | 5 | 19 |
| Recruitee | 6 | 87 |
| BreezyHR | 4 | 27 |
| Total | 15 | 133 |

Names, careers URLs and verification timestamps are recorded in
`data/sources/final-ats-verification.json`; the observed 21 candidate URLs are in
`data/sources/final-ats-candidates.csv`. Six candidates were excluded from activation:
unavailable/empty Workable feeds and Topic Software Development's custom-domain
application links, which do not pass the current Recruitee board-host validation.
No identifiers or sources were guessed to meet the count target.

Two live limited imports ran into a separate ignored SQLite database:
first run **15/15 sources successful, 133 created**, 25.483 seconds;
repeat **15/15 successful, zero created/updated, 133 unchanged**, 22.397 seconds.
Stable posting IDs and application links are preserved. Fixture tests separately
verify changed postings and repeated complete missing snapshots before closure
for all three new providers. These are local results, not production row counts.

The new extension `data/evaluation/new_ats_holdout.csv` and companion JSON contain
**69 real postings**: 19 Workable, 25 Recruitee, 25 BreezyHR. Human labels/reviewers
are blank. The provider-balanced sample is drawn from verified public snapshots,
deduplicated by normalized title/description, and is not production prevalence
weighted. The earlier 150-posting holdout is preserved; neither sample tuned rules.
Review files remain ignored local artifacts.

## Automatic ingestion and production status

Three real automatic `schedule` events completed successfully on 13 October.
The latest [successful scheduled run](https://github.com/Sheks17/GradJobs/actions/runs/38439471093)
started **17:32:23 UTC** and completed **17:56:49 UTC**. Its production-only
environment validation rejects SQLite; it uses the existing Neon database secret.
All **84/84 sources** succeeded: **16,626 fetched, 182 created, 2,568 updated,
57 closed**, 1,438.619 seconds. The result artifact records persisted writes and
run ID `120a6192-4bd2-432e-9918-d26c3fd98407`. Secret values are masked and are not
copied into documentation. This clears Phase 4B's unobserved timer-event blocker.

Today the [latest scheduled attempt](https://github.com/Sheks17/GradJobs/actions/runs/38641392444)
fails before ingestion because Neon reports **account/project quota exceeded**.
The database is not reset or migrated to another provider. Restore quota/access in
the connected Neon project's Usage/Billing controls, then run Production database
maintenance and a cloud ingestion dispatch to verify new provider writes. Any paid
plan decision must be made by the account owner.

The configured cadence remains minutes 7 and 37 UTC; observed GitHub event delivery
was much less frequent and is not a freshness SLA. Resource consumption and
cadence should be reviewed against the actual Neon quota after access is restored.
No paid plan or billing change has been made automatically.

[Production](https://gradjobs-drab.vercel.app) and
[API health](https://gradjobs-drab.vercel.app/api/health) retain their existing
URLs. Current active production counts are unavailable while the database rejects
connections. The last measured 12 October baseline was **16,578 global / 9,286
U.S. active jobs**; these are historical numbers, not current counts. New provider
counts above are local verification results. No before/after production growth is
fabricated by adding fetched rows to historical active totals.

## Validation and limitations

Final PostgreSQL CI backend tests: **338 passed, 12 skipped**, with three existing warnings. The
separate existing-provider network regression passed **12 live checks** across
Greenhouse, Lever, Ashby, SmartRecruiters, USAJOBS and Workday. New-provider live
verification covers 15 complete boards and repeat ingestion. **13 frontend tests
and nine browser tests passed**. Ruff/formatting, ESLint/Prettier, TypeScript,
production frontend builds and PostgreSQL Alembic upgrade/check passed. No new
migration was needed. [Final CI evidence](https://github.com/Sheks17/GradJobs/actions/runs/38646373489).

The bounded credential audit found no findings in **210 publication files, 282
Git-history text objects and 27 built JavaScript bundles**. Local secrets and
review datasets remain ignored. Public production API health returned **503**
on 14 October; Neon quota rejection prevents current counts and new cloud writes.
The provider registry intentionally reports unavailable counts during that outage.

Vercel release `dpl_CHhRVBXftrHc5r8UjuKxrdGuR9re` reached READY on 14 October.
The public `/admin/providers` page loaded all 23 registry entries (22 ATS plus
USAJOBS), displayed supported/detection-only access accurately and withheld
operational counts during the quota outage. This verifies release serving and
outage behavior, not job-search availability. Production database-dependent
search, details, health and new provider ingestion still require restored access.

Supported career-host families do not guarantee every custom domain or protected
board. Unknown dates/locations/salaries stay unknown; unstructured salary text is
retained rather than invented as a numeric range. Workable public data lacks
structured salary on the verified sample. Missing JSON-LD makes a Breezy source
partial. Public undocumented endpoint schemas can change; failures remain visible.
Matching version 3.0.0/cutoff 50 are frozen, and previous 220-posting accuracy
figures do not establish accuracy on the new providers.

The only production completion dependency is restored Neon access and subsequent
cloud ingestion/smoke verification. Employer-only or partner APIs remain documented
limitations, not another required phase.
