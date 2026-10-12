# Phase 1 verification

Verified locally on October 7, 2026 (America/Chicago), using Python 3.14.2 and Node.js 24.13.0 on Windows.

| Check                           | Result                                                                     |
| ------------------------------- | -------------------------------------------------------------------------- |
| Backend pytest                  | 93 passed                                                                  |
| Python lint and formatting      | Ruff checks passed                                                         |
| Frontend unit/integration tests | 6 passed                                                                   |
| TypeScript                      | Passed with strict configuration                                           |
| ESLint                          | Passed, including React hooks and JSX accessibility rules                  |
| Prettier                        | Passed                                                                     |
| Next.js production build        | Passed                                                                     |
| Desktop/mobile browser tests    | 2 passed in installed Microsoft Edge                                       |
| npm dependency audit            | No known vulnerabilities in installed dependencies                         |
| Migrations                      | SQLite upgrade, drift check, downgrade; PostgreSQL DDL generation verified |
| Local preview                   | API and production frontend served successfully with 21 labeled demo jobs  |

The browser checks exercise actual API data, search, remote/hybrid filters, details and explanations, application status persistence after reload, absence of demo Apply links, browser error collection, and mobile overflow. Desktop and mobile screenshots were visually inspected. The app's built-in browser automation could not initialize in this environment; Playwright with installed Edge provided the verification.

Docker and PostgreSQL are not installed on this machine. A running PostgreSQL migration/integration check was therefore **not executed locally**. The checked-in CI workflow provisions PostgreSQL 17, applies migrations, checks schema drift, and runs backend tests with isolated PostgreSQL schemas. That workflow has not been run remotely in this task. SQLite preview/testing does not validate PostgreSQL locks, JSONB behavior, or PostgreSQL-specific query plans.

Collectors were exercised with offline provider fixtures and mocked network responses, including pagination, retries, partial malformed data, and repeat upserts. No live employer board was synchronized as part of this verification. No automated collector schedule or public deployment was created.

There is one upstream deprecation warning: Starlette's test client currently supports `httpx` but recommends migration to `httpx2`. All tests pass; the production collectors use the separate, pinned `httpx` client intentionally.

Known functional limits and next steps are documented in the root README and the matching/ingestion guides. This record describes observed checks, not a claim of complete production coverage.
