# Source index

[Guide index](README.md)

Generated from tracked application source at inspected commit `62ecfa6`.
Python entries include top-level classes/functions and class methods; frontend
entries identify exported declarations. Line anchors refer to that inspected
source, which this documentation change does not modify. Empty package markers
are listed separately. This is a navigation inventory, not a security audit.

## Collector modules

| File | Definitions / exports |
| --- | --- |
| [collectors/__main__.py](../../collectors/__main__.py) | [`main`](../../collectors/__main__.py#L12) |
| [collectors/ashby.py](../../collectors/ashby.py) | [`AshbyCollector`](../../collectors/ashby.py#L9), [`AshbyCollector.fetch`](../../collectors/ashby.py#L13), [`AshbyCollector.normalize`](../../collectors/ashby.py#L19) |
| [collectors/ats_registry.py](../../collectors/ats_registry.py) | [`record`](../../collectors/ats_registry.py#L11), [`detect_url`](../../collectors/ats_registry.py#L253), [`capability`](../../collectors/ats_registry.py#L267) |
| [collectors/audit_production.py](../../collectors/audit_production.py) | [`audit`](../../collectors/audit_production.py#L13) |
| [collectors/base.py](../../collectors/base.py) | [`Collector`](../../collectors/base.py#L16), [`Collector.__init__`](../../collectors/base.py#L30), [`Collector.close`](../../collectors/base.py#L55), [`Collector.get_json`](../../collectors/base.py#L59), [`Collector.request_text`](../../collectors/base.py#L64), [`Collector.request_json`](../../collectors/base.py#L67), [`Collector.fetch`](../../collectors/base.py#L115), [`Collector.normalize`](../../collectors/base.py#L119) |
| [collectors/benchmark_production.py](../../collectors/benchmark_production.py) | [`benchmark`](../../collectors/benchmark_production.py#L15) |
| [collectors/breezyhr.py](../../collectors/breezyhr.py) | [`job_posting`](../../collectors/breezyhr.py#L14), [`BreezyHRCollector`](../../collectors/breezyhr.py#L34), [`BreezyHRCollector.fetch`](../../collectors/breezyhr.py#L45), [`BreezyHRCollector.normalize`](../../collectors/breezyhr.py#L70) |
| [collectors/discover.py](../../collectors/discover.py) | [`ats_from_url`](../../collectors/discover.py#L19), [`public_url`](../../collectors/discover.py#L49), [`fetch_page`](../../collectors/discover.py#L67), [`check_allowed`](../../collectors/discover.py#L86), [`allowed_page`](../../collectors/discover.py#L100), [`page_candidates`](../../collectors/discover.py#L104), [`_discover`](../../collectors/discover.py#L121), [`detected_page`](../../collectors/discover.py#L264), [`discover`](../../collectors/discover.py#L300) |
| [collectors/discover_batch.py](../../collectors/discover_batch.py) | [`discover_batch`](../../collectors/discover_batch.py#L12) |
| [collectors/greenhouse.py](../../collectors/greenhouse.py) | [`GreenhouseCollector`](../../collectors/greenhouse.py#L7), [`GreenhouseCollector.fetch`](../../collectors/greenhouse.py#L11), [`GreenhouseCollector.normalize`](../../collectors/greenhouse.py#L20) |
| [collectors/ingestion_state.py](../../collectors/ingestion_state.py) | [`source_fields`](../../collectors/ingestion_state.py#L36), [`content_fingerprint`](../../collectors/ingestion_state.py#L40), [`source_state`](../../collectors/ingestion_state.py#L59), [`unchanged`](../../collectors/ingestion_state.py#L66) |
| [collectors/lever.py](../../collectors/lever.py) | [`LeverCollector`](../../collectors/lever.py#L9), [`LeverCollector.fetch`](../../collectors/lever.py#L13), [`LeverCollector.normalize`](../../collectors/lever.py#L24) |
| [collectors/lifecycle.py](../../collectors/lifecycle.py) | [`utc`](../../collectors/lifecycle.py#L10), [`expire_deadlines`](../../collectors/lifecycle.py#L14), [`reconcile_missing`](../../collectors/lifecycle.py#L30), [`promote_active_aliases`](../../collectors/lifecycle.py#L66) |
| [collectors/locking.py](../../collectors/locking.py) | [`release_sqlite_writer`](../../collectors/locking.py#L12), [`write_lock`](../../collectors/locking.py#L17) |
| [collectors/measure_egress.py](../../collectors/measure_egress.py) | [`wire_size`](../../collectors/measure_egress.py#L12), [`measure`](../../collectors/measure_egress.py#L21) |
| [collectors/normalizers/location.py](../../collectors/normalizers/location.py) | [`normalize_state`](../../collectors/normalizers/location.py#L18), [`_single_location`](../../collectors/normalizers/location.py#L31), [`location_fields`](../../collectors/normalizers/location.py#L104), [`states_in`](../../collectors/normalizers/location.py#L152), [`remote_restrictions`](../../collectors/normalizers/location.py#L160) |
| [collectors/normalizers/text.py](../../collectors/normalizers/text.py) | [`plain_text`](../../collectors/normalizers/text.py#L10), [`normalize_text`](../../collectors/normalizers/text.py#L21), [`normalize_company`](../../collectors/normalizers/text.py#L26), [`normalize_title`](../../collectors/normalizers/text.py#L31), [`normalize_url`](../../collectors/normalizers/text.py#L37), [`description_fingerprint`](../../collectors/normalizers/text.py#L56) |
| [collectors/production_check.py](../../collectors/production_check.py) | [`require_postgres`](../../collectors/production_check.py#L6) |
| [collectors/providers.py](../../collectors/providers.py) | [`make_collector`](../../collectors/providers.py#L38) |
| [collectors/public_cache.py](../../collectors/public_cache.py) | [`cache_path`](../../collectors/public_cache.py#L10), [`load_detail_cache`](../../collectors/public_cache.py#L17), [`save_detail_cache`](../../collectors/public_cache.py#L32) |
| [collectors/public_feeds.py](../../collectors/public_feeds.py) | [`source_date`](../../collectors/public_feeds.py#L7), [`complete_rows`](../../collectors/public_feeds.py#L15), [`public_link`](../../collectors/public_feeds.py#L28), [`salary_fields`](../../collectors/public_feeds.py#L42) |
| [collectors/recover_failed.py](../../collectors/recover_failed.py) | [`main`](../../collectors/recover_failed.py#L15) |
| [collectors/recruitee.py](../../collectors/recruitee.py) | [`RecruiteeCollector`](../../collectors/recruitee.py#L10), [`RecruiteeCollector.fetch`](../../collectors/recruitee.py#L20), [`RecruiteeCollector.normalize`](../../collectors/recruitee.py#L23) |
| [collectors/registry.py](../../collectors/registry.py) | Module constants, imports or CLI entrypoint; open file |
| [collectors/runner.py](../../collectors/runner.py) | [`observe_unchanged`](../../collectors/runner.py#L25), [`upsert_with_retry`](../../collectors/runner.py#L42), [`SyncResult`](../../collectors/runner.py#L57), [`sync_source`](../../collectors/runner.py#L75) |
| [collectors/scheduler.py](../../collectors/scheduler.py) | [`main`](../../collectors/scheduler.py#L13) |
| [collectors/seed_sources.py](../../collectors/seed_sources.py) | [`seed`](../../collectors/seed_sources.py#L13) |
| [collectors/smartrecruiters.py](../../collectors/smartrecruiters.py) | [`SmartRecruitersCollector`](../../collectors/smartrecruiters.py#L11), [`SmartRecruitersCollector.fetch_detail`](../../collectors/smartrecruiters.py#L21), [`SmartRecruitersCollector.fetch`](../../collectors/smartrecruiters.py#L26), [`SmartRecruitersCollector.normalize`](../../collectors/smartrecruiters.py#L65) |
| [collectors/sync_all.py](../../collectors/sync_all.py) | [`dry_run_source`](../../collectors/sync_all.py#L26), [`sync_one`](../../collectors/sync_all.py#L54), [`_sync_all`](../../collectors/sync_all.py#L73), [`sync_all`](../../collectors/sync_all.py#L218), [`main`](../../collectors/sync_all.py#L249) |
| [collectors/sync_source.py](../../collectors/sync_source.py) | Module constants, imports or CLI entrypoint; open file |
| [collectors/usajobs.py](../../collectors/usajobs.py) | [`source_date`](../../collectors/usajobs.py#L22), [`USAJobsCollector`](../../collectors/usajobs.py#L34), [`USAJobsCollector.fetch`](../../collectors/usajobs.py#L46), [`USAJobsCollector.normalize`](../../collectors/usajobs.py#L94) |
| [collectors/verify_sources.py](../../collectors/verify_sources.py) | [`verify_file`](../../collectors/verify_sources.py#L15), [`verify_registered`](../../collectors/verify_sources.py#L78) |
| [collectors/workable.py](../../collectors/workable.py) | [`WorkableCollector`](../../collectors/workable.py#L12), [`WorkableCollector.fetch`](../../collectors/workable.py#L17), [`WorkableCollector.normalize`](../../collectors/workable.py#L50) |
| [collectors/workday.py](../../collectors/workday.py) | [`workday_config`](../../collectors/workday.py#L16), [`source_token`](../../collectors/workday.py#L36), [`WorkdayCollector`](../../collectors/workday.py#L41), [`WorkdayCollector.__init__`](../../collectors/workday.py#L53), [`WorkdayCollector.fetch`](../../collectors/workday.py#L72), [`WorkdayCollector.fetch_detail`](../../collectors/workday.py#L131), [`WorkdayCollector.normalize`](../../collectors/workday.py#L174) |

## Matching modules

| File | Definitions / exports |
| --- | --- |
| [matching/aliases.py](../../matching/aliases.py) | Module constants, imports or CLI entrypoint; open file |
| [matching/audit.py](../../matching/audit.py) | [`indicators`](../../matching/audit.py#L19), [`collect_audit`](../../matching/audit.py#L56), [`markdown_report`](../../matching/audit.py#L122), [`main`](../../matching/audit.py#L189) |
| [matching/benchmark.py](../../matching/benchmark.py) | [`benchmark`](../../matching/benchmark.py#L21), [`main`](../../matching/benchmark.py#L154) |
| [matching/evaluate.py](../../matching/evaluate.py) | [`prediction`](../../matching/evaluate.py#L15), [`ratio`](../../matching/evaluate.py#L30), [`binary_metrics`](../../matching/evaluate.py#L34), [`grouped_accuracy`](../../matching/evaluate.py#L50), [`confidence_band`](../../matching/evaluate.py#L68), [`confidence_comparison`](../../matching/evaluate.py#L80), [`evaluate`](../../matching/evaluate.py#L100), [`main`](../../matching/evaluate.py#L246) |
| [matching/experience.py](../../matching/experience.py) | [`Experience`](../../matching/experience.py#L75), [`Experience.minimum`](../../matching/experience.py#L86), [`Experience.maximum`](../../matching/experience.py#L94), [`Experience.preferred`](../../matching/experience.py#L102), [`Experience.text`](../../matching/experience.py#L106), [`Experience.category`](../../matching/experience.py#L110), [`_number`](../../matching/experience.py#L131), [`extract_experience`](../../matching/experience.py#L135), [`early_career_signals`](../../matching/experience.py#L278) |
| [matching/reprocess.py](../../matching/reprocess.py) | [`derived_fields`](../../matching/reprocess.py#L26), [`apply_fields`](../../matching/reprocess.py#L46), [`reprocess`](../../matching/reprocess.py#L57), [`main`](../../matching/reprocess.py#L142) |
| [matching/review.py](../../matching/review.py) | [`fingerprint`](../../matching/review.py#L28), [`safe_cell`](../../matching/review.py#L33), [`excerpt`](../../matching/review.py#L38), [`export_review`](../../matching/review.py#L52), [`load_reviews`](../../matching/review.py#L103), [`main`](../../matching/review.py#L152) |
| [matching/role_classifier.py](../../matching/role_classifier.py) | [`classify_seniority`](../../matching/role_classifier.py#L18), [`classify_role`](../../matching/role_classifier.py#L56) |
| [matching/sample_evaluation.py](../../matching/sample_evaluation.py) | [`sample_jobs`](../../matching/sample_evaluation.py#L21), [`main`](../../matching/sample_evaluation.py#L96) |
| [matching/sample_holdout.py](../../matching/sample_holdout.py) | [`sample`](../../matching/sample_holdout.py#L19) |
| [matching/sample_pilot.py](../../matching/sample_pilot.py) | [`sample_pilot`](../../matching/sample_pilot.py#L17), [`main`](../../matching/sample_pilot.py#L86) |
| [matching/scoring.py](../../matching/scoring.py) | [`MatchResult`](../../matching/scoring.py#L28), [`MatchResult.to_dict`](../../matching/scoring.py#L53), [`score_job`](../../matching/scoring.py#L57) |
| [matching/skills.py](../../matching/skills.py) | [`extract_skills`](../../matching/skills.py#L40), [`normalize_skill`](../../matching/skills.py#L44) |
| [matching/validation_report.py](../../matching/validation_report.py) | [`display`](../../matching/validation_report.py#L4), [`render_report`](../../matching/validation_report.py#L8) |

## API application and migrations

| File | Definitions / exports |
| --- | --- |
| [services/api/app/api/routes.py](../../services/api/app/api/routes.py) | [`health`](../../services/api/app/api/routes.py#L19), [`jobs`](../../services/api/app/api/routes.py#L28), [`job_detail`](../../services/api/app/api/routes.py#L33), [`companies`](../../services/api/app/api/routes.py#L47), [`sources`](../../services/api/app/api/routes.py#L58), [`stats`](../../services/api/app/api/routes.py#L73), [`provider_stats`](../../services/api/app/api/routes.py#L78), [`ats_capabilities`](../../services/api/app/api/routes.py#L85), [`metadata`](../../services/api/app/api/routes.py#L92), [`ingestion`](../../services/api/app/api/routes.py#L100) |
| [services/api/app/api/sources.py](../../services/api/app/api/sources.py) | [`development_admin`](../../services/api/app/api/sources.py#L22), [`require_source`](../../services/api/app/api/sources.py#L33), [`source_detail`](../../services/api/app/api/sources.py#L41), [`source_history`](../../services/api/app/api/sources.py#L46), [`create_source`](../../services/api/app/api/sources.py#L63), [`patch_source`](../../services/api/app/api/sources.py#L89), [`sync_registered_source`](../../services/api/app/api/sources.py#L102), [`sync_every_source`](../../services/api/app/api/sources.py#L122) |
| [services/api/app/core/config.py](../../services/api/app/core/config.py) | [`Settings`](../../services/api/app/core/config.py#L7), [`Settings.normalize_postgres_url`](../../services/api/app/core/config.py#L35), [`get_settings`](../../services/api/app/core/config.py#L43) |
| [services/api/app/core/logging.py](../../services/api/app/core/logging.py) | [`configure_logging`](../../services/api/app/core/logging.py#L6) |
| [services/api/app/db/maintenance.py](../../services/api/app/db/maintenance.py) | [`refresh_sqlite_statistics`](../../services/api/app/db/maintenance.py#L8) |
| [services/api/app/db/session.py](../../services/api/app/db/session.py) | [`utcnow`](../../services/api/app/db/session.py#L10), [`Base`](../../services/api/app/db/session.py#L14), [`get_db`](../../services/api/app/db/session.py#L40) |
| [services/api/app/main.py](../../services/api/app/main.py) | Module constants, imports or CLI entrypoint; open file |
| [services/api/app/models/job.py](../../services/api/app/models/job.py) | [`Timestamps`](../../services/api/app/models/job.py#L30), [`JobSource`](../../services/api/app/models/job.py#L37), [`IngestionRun`](../../services/api/app/models/job.py#L61), [`Job`](../../services/api/app/models/job.py#L71), [`JobLocation`](../../services/api/app/models/job.py#L173), [`JobSkill`](../../services/api/app/models/job.py#L184), [`SourceSync`](../../services/api/app/models/job.py#L193) |
| [services/api/app/repositories/ingestion.py](../../services/api/app/repositories/ingestion.py) | [`duplicate_candidate`](../../services/api/app/repositories/ingestion.py#L21), [`upsert_job`](../../services/api/app/repositories/ingestion.py#L66), [`replace_skills`](../../services/api/app/repositories/ingestion.py#L151) |
| [services/api/app/repositories/jobs.py](../../services/api/app/repositories/jobs.py) | [`visible_conditions`](../../services/api/app/repositories/jobs.py#L14), [`list_jobs`](../../services/api/app/repositories/jobs.py#L35), [`statistics`](../../services/api/app/repositories/jobs.py#L191) |
| [services/api/app/repositories/providers.py](../../services/api/app/repositories/providers.py) | [`provider_statistics`](../../services/api/app/repositories/providers.py#L13), [`ats_statistics`](../../services/api/app/repositories/providers.py#L126) |
| [services/api/app/schemas/jobs.py](../../services/api/app/schemas/jobs.py) | [`ensure_utc`](../../services/api/app/schemas/jobs.py#L21), [`JobFilters`](../../services/api/app/schemas/jobs.py#L29), [`JobFilters.valid_skill`](../../services/api/app/schemas/jobs.py#L79), [`JobSummary`](../../services/api/app/schemas/jobs.py#L90), [`JobSummary.is_new`](../../services/api/app/schemas/jobs.py#L143), [`JobDetail`](../../services/api/app/schemas/jobs.py#L148), [`JobPage`](../../services/api/app/schemas/jobs.py#L166), [`Stats`](../../services/api/app/schemas/jobs.py#L174), [`SourceOut`](../../services/api/app/schemas/jobs.py#L185), [`SourceOut.status`](../../services/api/app/schemas/jobs.py#L208) |
| [services/api/app/schemas/sources.py](../../services/api/app/schemas/sources.py) | [`SourceCreate`](../../services/api/app/schemas/sources.py#L10), [`SourceCreate.workday_required`](../../services/api/app/schemas/sources.py#L20), [`SourceCreate.public_configuration`](../../services/api/app/schemas/sources.py#L31), [`SourceCreate.validate_url`](../../services/api/app/schemas/sources.py#L78), [`SourcePatch`](../../services/api/app/schemas/sources.py#L86), [`SyncOut`](../../services/api/app/schemas/sources.py#L98) |
| [services/api/app/seed.py](../../services/api/app/seed.py) | [`main`](../../services/api/app/seed.py#L37) |
| [services/api/app/services/sources.py](../../services/api/app/services/sources.py) | [`register_source`](../../services/api/app/services/sources.py#L9) |
| [services/api/migrations/env.py](../../services/api/migrations/env.py) | Module constants, imports or CLI entrypoint; open file |
| [services/api/migrations/versions/1a4b0c4e2026_provider_expansion.py](../../services/api/migrations/versions/1a4b0c4e2026_provider_expansion.py) | [`upgrade`](../../services/api/migrations/versions/1a4b0c4e2026_provider_expansion.py#L13), [`downgrade`](../../services/api/migrations/versions/1a4b0c4e2026_provider_expansion.py#L35) |
| [services/api/migrations/versions/4d3b3cd86b1c_matching_evidence_skills_and_remote_.py](../../services/api/migrations/versions/4d3b3cd86b1c_matching_evidence_skills_and_remote_.py) | [`upgrade`](../../services/api/migrations/versions/4d3b3cd86b1c_matching_evidence_skills_and_remote_.py#L17), [`downgrade`](../../services/api/migrations/versions/4d3b3cd86b1c_matching_evidence_skills_and_remote_.py#L137) |
| [services/api/migrations/versions/6ed2ad4faacd_initial_jobs_and_sources_schema.py](../../services/api/migrations/versions/6ed2ad4faacd_initial_jobs_and_sources_schema.py) | [`upgrade`](../../services/api/migrations/versions/6ed2ad4faacd_initial_jobs_and_sources_schema.py#L17), [`downgrade`](../../services/api/migrations/versions/6ed2ad4faacd_initial_jobs_and_sources_schema.py#L139) |
| [services/api/migrations/versions/7bf8b519f9b4_source_history_lifecycle_and_multiple_.py](../../services/api/migrations/versions/7bf8b519f9b4_source_history_lifecycle_and_multiple_.py) | [`upgrade`](../../services/api/migrations/versions/7bf8b519f9b4_source_history_lifecycle_and_multiple_.py#L17), [`downgrade`](../../services/api/migrations/versions/7bf8b519f9b4_source_history_lifecycle_and_multiple_.py#L86) |
| [services/api/migrations/versions/9f83a21cb4d0_freshness_index_and_boolean_storage.py](../../services/api/migrations/versions/9f83a21cb4d0_freshness_index_and_boolean_storage.py) | [`upgrade`](../../services/api/migrations/versions/9f83a21cb4d0_freshness_index_and_boolean_storage.py#L16), [`downgrade`](../../services/api/migrations/versions/9f83a21cb4d0_freshness_index_and_boolean_storage.py#L59) |
| [services/api/migrations/versions/a12de0c2026_employment_description_text.py](../../services/api/migrations/versions/a12de0c2026_employment_description_text.py) | [`upgrade`](../../services/api/migrations/versions/a12de0c2026_employment_description_text.py#L12), [`downgrade`](../../services/api/migrations/versions/a12de0c2026_employment_description_text.py#L18) |
| [services/api/migrations/versions/b42f0c2026_ingestion_operations.py](../../services/api/migrations/versions/b42f0c2026_ingestion_operations.py) | [`upgrade`](../../services/api/migrations/versions/b42f0c2026_ingestion_operations.py#L13), [`downgrade`](../../services/api/migrations/versions/b42f0c2026_ingestion_operations.py#L32) |
| [services/api/migrations/versions/c53e0a2026_ingestion_fingerprint.py](../../services/api/migrations/versions/c53e0a2026_ingestion_fingerprint.py) | [`upgrade`](../../services/api/migrations/versions/c53e0a2026_ingestion_fingerprint.py#L12), [`downgrade`](../../services/api/migrations/versions/c53e0a2026_ingestion_fingerprint.py#L16) |

## Shared contracts

| File | Definitions / exports |
| --- | --- |
| [shared/constants.py](../../shared/constants.py) | Module constants, imports or CLI entrypoint; open file |
| [shared/schemas.py](../../shared/schemas.py) | [`NormalizedJob`](../../shared/schemas.py#L10), [`NormalizedJob.safe_url`](../../shared/schemas.py#L51), [`NormalizedJob.timezone_required`](../../shared/schemas.py#L60), [`NormalizedJob.valid_salary`](../../shared/schemas.py#L66) |

## Frontend source

| File | Definitions / exports |
| --- | --- |
| [apps/web/app/admin/ingestion/page.tsx](../../apps/web/app/admin/ingestion/page.tsx) | [`IngestionPage`](../../apps/web/app/admin/ingestion/page.tsx#L4) |
| [apps/web/app/admin/providers/page.tsx](../../apps/web/app/admin/providers/page.tsx) | [`ProvidersPage`](../../apps/web/app/admin/providers/page.tsx#L4) |
| [apps/web/app/jobs/[id]/page.tsx](../../apps/web/app/jobs/[id]/page.tsx) | [`JobPage`](../../apps/web/app/jobs/[id]/page.tsx#L3) |
| [apps/web/app/layout.tsx](../../apps/web/app/layout.tsx) | [`metadata`](../../apps/web/app/layout.tsx#L4), [`RootLayout`](../../apps/web/app/layout.tsx#L9) |
| [apps/web/app/not-found.tsx](../../apps/web/app/not-found.tsx) | [`NotFound`](../../apps/web/app/not-found.tsx#L2) |
| [apps/web/app/page.tsx](../../apps/web/app/page.tsx) | [`Home`](../../apps/web/app/page.tsx#L3) |
| [apps/web/app/saved/page.tsx](../../apps/web/app/saved/page.tsx) | [`SavedPage`](../../apps/web/app/saved/page.tsx#L3) |
| [apps/web/app/sources/page.tsx](../../apps/web/app/sources/page.tsx) | [`SourcesPage`](../../apps/web/app/sources/page.tsx#L3) |
| [apps/web/components/dashboard.tsx](../../apps/web/components/dashboard.tsx) | [`Dashboard`](../../apps/web/components/dashboard.tsx#L22) |
| [apps/web/components/filters.tsx](../../apps/web/components/filters.tsx) | [`defaults`](../../apps/web/components/filters.tsx#L5), [`Filters`](../../apps/web/components/filters.tsx#L21), [`FiltersPanel`](../../apps/web/components/filters.tsx#L23) |
| [apps/web/components/header.tsx](../../apps/web/components/header.tsx) | [`Header`](../../apps/web/components/header.tsx#L4) |
| [apps/web/components/ingestion.tsx](../../apps/web/components/ingestion.tsx) | [`Ingestion`](../../apps/web/components/ingestion.tsx#L31) |
| [apps/web/components/job-card.tsx](../../apps/web/components/job-card.tsx) | [`JobCard`](../../apps/web/components/job-card.tsx#L23) |
| [apps/web/components/job-detail.tsx](../../apps/web/components/job-detail.tsx) | [`JobDetail`](../../apps/web/components/job-detail.tsx#L22) |
| [apps/web/components/provider-badges.tsx](../../apps/web/components/provider-badges.tsx) | [`closingLabel`](../../apps/web/components/provider-badges.tsx#L4), [`ProviderBadges`](../../apps/web/components/provider-badges.tsx#L13) |
| [apps/web/components/provider-capabilities.tsx](../../apps/web/components/provider-capabilities.tsx) | [`ProviderCapabilities`](../../apps/web/components/provider-capabilities.tsx#L22) |
| [apps/web/components/saved-jobs.tsx](../../apps/web/components/saved-jobs.tsx) | [`SavedJobs`](../../apps/web/components/saved-jobs.tsx#L11) |
| [apps/web/components/saved-searches.tsx](../../apps/web/components/saved-searches.tsx) | [`parseSearches`](../../apps/web/components/saved-searches.tsx#L16), [`SavedSearches`](../../apps/web/components/saved-searches.tsx#L56) |
| [apps/web/components/sources.tsx](../../apps/web/components/sources.tsx) | [`Sources`](../../apps/web/components/sources.tsx#L169) |
| [apps/web/lib/api.ts](../../apps/web/lib/api.ts) | [`fetchApi`](../../apps/web/lib/api.ts#L6) |
| [apps/web/lib/format.ts](../../apps/web/lib/format.ts) | [`experienceLabel`](../../apps/web/lib/format.ts#L3), [`salaryLabel`](../../apps/web/lib/format.ts#L31), [`dateLabel`](../../apps/web/lib/format.ts#L54), [`relativeDate`](../../apps/web/lib/format.ts#L64), [`postedLabel`](../../apps/web/lib/format.ts#L82), [`timestampLabel`](../../apps/web/lib/format.ts#L105), [`remoteLabels`](../../apps/web/lib/format.ts#L115) |
| [apps/web/lib/status.ts](../../apps/web/lib/status.ts) | [`statuses`](../../apps/web/lib/status.ts#L5), [`JobStatus`](../../apps/web/lib/status.ts#L15), [`parseStatuses`](../../apps/web/lib/status.ts#L19), [`useStatuses`](../../apps/web/lib/status.ts#L49), [`setJobStatus`](../../apps/web/lib/status.ts#L53) |
| [apps/web/types/jobs.ts](../../apps/web/types/jobs.ts) | [`Job`](../../apps/web/types/jobs.ts#L1), [`JobDetail`](../../apps/web/types/jobs.ts#L57), [`JobPage`](../../apps/web/types/jobs.ts#L74), [`Stats`](../../apps/web/types/jobs.ts#L81), [`Source`](../../apps/web/types/jobs.ts#L91), [`SourceSync`](../../apps/web/types/jobs.ts#L109), [`ProviderHealth`](../../apps/web/types/jobs.ts#L125) |

## Root and operational configuration

| File | Responsibility |
| --- | --- |
| [vercel_app.py](../../vercel_app.py) | Production ASGI guard and API mount |
| [vercel.json](../../vercel.json) | Services and request rewrites |
| [pyproject.toml](../../pyproject.toml) | Python package, dependency ranges, pytest and Ruff settings |
| [requirements.txt](../../requirements.txt) | Pinned deployment runtime |
| [requirements-dev.lock](../../requirements-dev.lock) | Tested development dependency lock |
| [alembic.ini](../../alembic.ini) | Migration environment location and logging |
| [docker-compose.yml](../../docker-compose.yml) | Local PostgreSQL 17 and persistent volume |
| [.env.example](../../.env.example) | Public development placeholders; never real secret values |
| [.gitignore](../../.gitignore) | Repository exclusions |
| [.vercelignore](../../.vercelignore) | Deployment upload exclusions |
| [.github/workflows/ci.yml](../../.github/workflows/ci.yml) | Backend, frontend and browser validation |
| [.github/workflows/ingestion.yml](../../.github/workflows/ingestion.yml) | Cloud sync and public-detail cache persistence |
| [.github/workflows/database.yml](../../.github/workflows/database.yml) | Schema maintenance, audit and targeted recovery |
| [data/sources.json](../../data/sources.json) | Reviewed source configurations imported idempotently |
| [apps/web/package.json](../../apps/web/package.json) | Frontend dependency ranges and npm scripts |
| [apps/web/package-lock.json](../../apps/web/package-lock.json) | Resolved npm dependencies |
| [apps/web/next.config.ts](../../apps/web/next.config.ts) | Next.js build configuration |
| [apps/web/playwright.config.ts](../../apps/web/playwright.config.ts) | Browser regression configuration |
| [apps/web/vitest.config.ts](../../apps/web/vitest.config.ts) | Component/unit test configuration |
| [apps/web/AGENTS.md](../../apps/web/AGENTS.md) | Frontend coding-agent framework guidance |

## Empty Python package markers

- [collectors/__init__.py](../../collectors/__init__.py)
- [collectors/normalizers/__init__.py](../../collectors/normalizers/__init__.py)
- [matching/__init__.py](../../matching/__init__.py)
- [services/api/__init__.py](../../services/api/__init__.py)
- [services/api/app/__init__.py](../../services/api/app/__init__.py)
- [services/api/app/api/__init__.py](../../services/api/app/api/__init__.py)
- [services/api/app/core/__init__.py](../../services/api/app/core/__init__.py)
- [services/api/app/db/__init__.py](../../services/api/app/db/__init__.py)
- [services/api/app/models/__init__.py](../../services/api/app/models/__init__.py)
- [services/api/app/repositories/__init__.py](../../services/api/app/repositories/__init__.py)
- [services/api/app/schemas/__init__.py](../../services/api/app/schemas/__init__.py)
- [services/api/app/services/__init__.py](../../services/api/app/services/__init__.py)
- [shared/__init__.py](../../shared/__init__.py)

For test responsibilities and commands see [testing](testing.md).
