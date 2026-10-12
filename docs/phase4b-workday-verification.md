# Workday live verification

Measured on 12 October 2026 against observed public employer Workday sites. Ten
employers completed reported pagination, detail retrieval and normalization.
Six are enabled in production; four remain verified candidates outside the enabled
registry. Candidate counts are excluded from production job totals.

| Employer | Postings in verified snapshot | Registry state | Observed careers site |
| --- | ---: | --- | --- |
| Adobe | 348 | Enabled in production | [external_experienced](https://adobe.wd5.myworkdayjobs.com/en-US/external_experienced) |
| Autodesk | 398 | Enabled in production | [Ext](https://autodesk.wd1.myworkdayjobs.com/en-US/Ext) |
| Intel | 666 | Enabled in production | [External](https://intel.wd1.myworkdayjobs.com/en-US/External) |
| Leidos | 2,000 | Verified candidate; disabled | [External](https://leidos.wd5.myworkdayjobs.com/en-US/External) |
| Illumina | 162 | Verified candidate; disabled | [illumina-careers](https://illumina.wd1.myworkdayjobs.com/en-US/illumina-careers) |
| MillerKnoll | 228 | Verified candidate; disabled | [MillerKnoll](https://millerknoll.wd1.myworkdayjobs.com/en-US/MillerKnoll) |
| Wells Fargo | 1,370 | Verified candidate; disabled | [WellsFargoJobs](https://wf.wd1.myworkdayjobs.com/en-US/WellsFargoJobs) |
| Guidewire | 112 | Enabled in production | [external](https://guidewire.wd5.myworkdayjobs.com/en-US/external) |
| Zendesk | 138 | Enabled in production | [zendesk](https://zendesk.wd1.myworkdayjobs.com/en-US/zendesk) |
| Workday | 373 | Enabled in production | [Workday](https://workday.wd5.myworkdayjobs.com/en-US/Workday) |

Repeat listing checks used fresh pagination and bounded cached details. All ten
had unique stable IDs and unchanged application URLs for common IDs. Intel had
one new and one missing ID; this demonstrates board changes, not duplicate
creation. Wells Fargo supplied no location for four of its 1,370 postings; unknown
metadata remains unknown. Leidos reported 2,000 postings; verification establishes
coverage of the provider-reported snapshot, not a global employer coverage claim.

Source discovery alone does not establish complete collection. NVIDIA, Cisco,
HPE and Cadence did not pass full snapshot validation; Qualcomm did not pass
discovery. They were not enabled. Failures include malformed postings and changing
or incomplete snapshots. No challenges or automated-access restrictions were
bypassed. Exact provider error messages are not treated as reliable classifications
of access restrictions.

The later production full run encountered an Autodesk listing with no valid
external path. It processed valid postings, reported a partial source and skipped
closure reconciliation. A fresh diagnostic confirmed another invalid-path summary;
the collector does not fabricate an ID or application link to hide provider errors.

Fixture tests cover malformed data, pagination, detail retries/rate limits,
dates/descriptions/locations, bounded detail caching and circuit breaking. Shared
database tests cover duplicate imports, changes and repeated missing snapshots
before closures. Production recovery successfully ingested all six enabled
Workday sources; the later partial run demonstrates operational error isolation.

The four staged configurations are in
`data/sources/phase4b-verified-candidates.json`. Enable only after operational
capacity and current endpoint verification, using the existing registry workflow.
Raw payload caches and human review files remain ignored local artifacts.
