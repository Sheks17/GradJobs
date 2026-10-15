# Frontend architecture

[Guide index](README.md) · [User request walkthrough](flows.md#follow-one-user-search)

The frontend uses Next.js App Router, React, TypeScript, Tailwind's PostCSS
integration, custom CSS and Lucide icons. See [package.json](../../apps/web/package.json)
for actual scripts/ranges and `package-lock.json` for resolved dependencies.
Pages compose a shared header and feature component. Most data interaction is in
client components rather than server-side job fetching.

## Pages and components

| Page file under `apps/web/app/` | URL | Feature component under `components/` |
| --- | --- | --- |
| `page.tsx` | `/` | `dashboard.tsx`: query state, effects, results, summary and retry |
| `jobs/[id]/page.tsx` | `/jobs/<UUID>` | `job-detail.tsx`: full description, evidence, original link, status selector |
| `saved/page.tsx` | `/saved` | `saved-jobs.tsx`: local tracked IDs hydrated through detail API |
| `sources/page.tsx` | `/sources` | `sources.tsx`: source health/history and development administration |
| `admin/ingestion/page.tsx` | `/admin/ingestion` | `ingestion.tsx`: read-only run/source counters |
| `admin/providers/page.tsx` | `/admin/providers` | `provider-capabilities.tsx`: registry support and measured provider health |

[layout.tsx](../../apps/web/app/layout.tsx) owns metadata, global stylesheet,
skip link and footer. The dynamic job page awaits its `params` promise and passes
the ID to the client detail component. [not-found.tsx](../../apps/web/app/not-found.tsx)
handles Next page misses; a missing API job has its own detail error state.

Additional components:

- [filters.tsx](../../apps/web/components/filters.tsx) owns filter defaults, controls
  and metadata fetch. It clears a role group when an explicit role is selected.
- [job-card.tsx](../../apps/web/components/job-card.tsx) renders one API summary,
  fit/experience/skills/date/source evidence, save toggle and application link.
- [provider-badges.tsx](../../apps/web/components/provider-badges.tsx) displays
  provider-specific public metadata such as federal eligibility.
- [saved-searches.tsx](../../apps/web/components/saved-searches.tsx) saves/reloads
  named filter combinations; it does not create a backend subscription.
- [header.tsx](../../apps/web/components/header.tsx) renders main navigation;
  [format.ts](../../apps/web/lib/format.ts) centralizes visible labels and dates.

## Dashboard state and network behavior

`Dashboard` keeps filters, typed query, debounced search, sort and page in React
state. Typing waits 300 ms before replacing the effective search and returning
to page one. Filter changes also reset pagination. A `URLSearchParams` object is
used for the API request; it does **not** update the browser address bar or create
a shareable filter URL. Reloading the dashboard starts from defaults.

The jobs effect sends 12 results per page, aborts obsolete requests and associates
responses with a request key. A slow response from old filters should not replace
the current result. Stats are fetched independently, so a statistics failure can
leave dashes while the jobs request succeeds. Metadata errors leave limited
filter options; these silent catches are useful debugging distinctions.

[fetchApi](../../apps/web/lib/api.ts) uses a 15-second timeout and `cache: no-store`.
It combines timeout and caller abort signals, maps non-OK responses to visible
errors, and returns typed JSON. The generic TypeScript type is a compile-time
assertion, not runtime JSON validation. Keep `types/jobs.ts` aligned with the
Pydantic API response models when adding fields.

The default API base is localhost:8000 in development and `/api` in production.
`NEXT_PUBLIC_API_URL` overrides it at build time. Never put credentials there.
See [search semantics](search.md) for defaults; the seven-day freshness condition
is added by the UI, not automatically imposed on every bare `/jobs` API request.

## Application tracking

[lib/status.ts](../../apps/web/lib/status.ts) stores an ID-to-status map in
`localStorage` key `gradjobs:status:v1`. Allowed statuses are `new`, `viewed`,
`saved`, `applied`, `interviewing`, `offer`, `rejected`, and `archived`.
`parseStatuses` rejects malformed objects/IDs/status values. `useSyncExternalStore`
subscribes to browser `storage` events and the custom `gradjobs-status-change`
event; server snapshots are empty to support rendering before browser storage.

Opening a detail records `viewed` only if no stronger status exists. Saving a card
sets `saved`; toggling a tracked card off resets it to `new`. `/saved` excludes
`new`/`viewed`, fetches each retained ID's detail with `Promise.allSettled`, and
preserves the local statuses if some requests fail. It is not an optimized batch
endpoint: a large personal tracker makes multiple detail requests and transfers
descriptions. This is a known MVP cost, not an account-backed database table.

## Saved searches

Key `gradjobs:searches:v1` contains up to 30 entries: UUID, name, filters, query
and sort. Names are capped at 100 characters, queries at 200; parsing checks
stored field types against defaults. Saving copies filters; loading restores
them and triggers a fresh API request. The saved `days` duration is converted
into a new timestamp on reload, so “last seven days” stays relative to now.
Deletion changes only this browser's list. Storage exceptions produce an alert.

Tracking and searches are scoped to the website origin and browser profile.
They do not transfer from localhost to production, across devices or after
storage clearing. There is no email, push or background saved-search matcher.

## Safe frontend changes

Use existing components/styles before introducing another state system or UI
library. Render employer descriptions as text, preserve unknown labels, retain
the original application destination, and test error/empty/loading/storage states.
For Next.js changes follow the local `AGENTS.md` and bundled framework guides.
