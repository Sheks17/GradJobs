# Security, secrets and known limitations

[Guide index](README.md) · [Deployment](deployment.md)

## Trust boundaries

Employer responses and discovery HTML are untrusted input. Collectors validate
provider payloads, identity, completeness and links before storage. API filters
are Pydantic models and SQLAlchemy predicates use bound values. Employer text
must not be interpreted as instructions, executable HTML or credentials.

Discovery validates HTTP(S), host/port/credentials and public DNS addresses,
revalidates redirects, bounds redirects/page bytes and observes robots rules.
LinkedIn fetching is explicitly disabled. Provider-specific public helpers restrict
links to expected employer hosts/paths. These checks reduce SSRF/unsafe-source
risk; they are not a complete formal security proof for every DNS/network race.
No anti-bot bypass, private recruiter API impersonation, LinkedIn or Indeed
scraping is part of the supported workflow.

`NormalizedJob` rejects unexpected fields and unsafe/credential-bearing URLs,
requires timezone-aware dates, and validates salaries. The text normalizer removes
script/style markup; frontend descriptions are rendered as text. Preserve React's
escaping and original application links when changing the detail view.

## Secret handling

Real database URLs, federal credentials and deployment tokens belong in ignored
local environment files or hosting/repository secret stores. `provider_config`
accepts only reviewed public keys such as Workday tenant/site or bounded USAJOBS
query settings. Its contents are publicly exposed through source metadata, so
storing a credential there would be a disclosure.

`NEXT_PUBLIC_*` variables are browser-visible build configuration. They must never
hold keys, emails used as private credentials, database URLs or tokens. Root and
web `.env.example` files contain placeholders/development defaults only.
`.gitignore` and `.vercelignore` exclude secret files, databases/backups, private
review datasets, deployment state and generated artifacts. An ignore rule does
not remove previously tracked files or secrets from Git history.

Before publication, inspect the diff and perform bounded scans for known secrets
and credential formats across tracked files, history, fixtures/logs and built
frontend assets. Avoid printing secret values while scanning. If exposure is
found, rotate/revoke at its owner and address history deliberately; do not assume
deleting the current line resolves it. The earlier security report records a
bounded scan, not an exhaustive guarantee against all secret formats.

## Administration and public observability

Production forces `APP_ENV=production`, `ENABLE_ADMIN_API=false`, and a hosted
PostgreSQL URL. Source mutations/full sync endpoints require local development
mode plus opt-in administration; there is no production authentication system.
Read-only source, ingestion and provider health data is intentionally public.
The route name `/admin/...` does not make a page private. Inner FastAPI generated
docs are also not an access-control mechanism.

CORS allows expected origins rather than an unnecessary wildcard. CORS is a
browser policy, not authentication or protection against all direct HTTP clients.
Pagination/query/score/salary bounds limit obvious expensive/malformed inputs;
there is no dedicated external rate limiter or general abuse prevention service.
Avoid overstating this MVP's security posture.

## Data integrity and retention

Incomplete snapshots cannot close missing postings. Failed sources retain review
history instead of disappearing. Fingerprints detect source-content changes;
leases and write locks reduce overlap; migrations preserve production records.
These controls are not automatic backups or disaster recovery. There is no
implemented retention policy for accumulated source/run history.

## Product and operational limitations

- Coverage is limited to reviewed public boards and configured federal queries.
  Detection-only ATS entries are not collectors. Custom domains/protected tenants
  may require separate investigation; never guess identifiers to inflate counts.
- Scheduled delivery is best effort and long runs serialize. Workday details can
  lag six hours when summaries stay stable. A latest source timestamp is not a
  real-time market-wide freshness guarantee.
- Missing dates/salary/location stay unknown. Location and English requirement
  heuristics are imperfect, including federal specialized/supervisory wording.
  Scores/confidence are explanatory heuristics, not hiring probabilities.
- SQL substring search has no stemming/semantic model. Offset pagination can shift
  while ingestion changes data. Performance depends on actual row counts/load.
- Tracking/searches are browser-local, not backed up or synced. Saved-job display
  makes one detail request per tracked ID and can add transfer cost at large size.
- Holdout labels/new-provider classification review remain pending. Reviewed
  220-job metrics cannot be generalized to every employer/provider population.
- Code-level transfer estimates do not measure Neon billing. Network costs and
  source-history growth still need operational observation.

Accounts, cross-device sync, email/push, resume matching, more employers and richer
search are optional future work. They are not another required MVP phase.
