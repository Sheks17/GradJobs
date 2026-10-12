# GradJobs MVP completion report

Status: validation in progress, 12 October 2026. This document is not a completion claim.

## Verified baseline

The live deployment is https://gradjobs-drab.vercel.app with API prefix
https://gradjobs-drab.vercel.app/api. Next.js and FastAPI are separate Vercel services;
the API serves requests, while GitHub Actions performs ingestion into managed Neon
PostgreSQL. Ingestion does not depend on the local computer.

Before this sprint's deployment, a public measurement on 12 October found 7,098
active U.S. jobs and 66 registered sources. These are timestamped observations, not
current marketing counts. Use `/api/stats`, `/api/stats/providers`, `/api/sources`
and `/api/ingestion` for current values.

Default search targets active U.S. jobs, the last seven days, cutoff 50, non-senior
roles and freshness/fit ranking. Users can broaden the filters.

## Matching validation

Frozen matching version 3.0.0, cutoff 50. Reviewed 220-posting sample: precision
100%, recall 98.7%, F1 99.4%, four-class accuracy 99.1%, zero false positives,
one false negative. This does not establish universal accuracy or new-provider
accuracy. The final holdout remains unlabeled until human review.

## Baseline performance

Three unauthenticated requests per route, measured from the development machine.
Network latency and serverless cold starts are included; this is not a load test.
Median default jobs: 115.7 ms; text search: 129.0 ms; Python skill filter: 108.2 ms;
freshness: 85.5 ms; Greenhouse provider filter: 103.3 ms. Homepage HTTP response:
51.9 ms. First health request: 2,320.4 ms, subsequent requests about 80 ms.
Browser time to populated results is measured separately where available.

## Remaining completion checks

- Full Workday snapshots and production ingestion, beyond discovery checks.
- PostgreSQL CI and production additive migration.
- Final browser, security and production smoke checks.
- Fresh 150-posting holdout from six providers.
- Final measured provider scale, successful run timestamp and test counts.

No new required phase is planned. Accounts, cross-device tracking, email/push,
personalized matching and additional providers remain optional future work.
