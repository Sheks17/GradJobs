export interface Job {
  id: string;
  title: string;
  company_name: string;
  company_slug: string;
  location_raw: string | null;
  city: string | null;
  state: string | null;
  country: string | null;
  remote_type: string;
  employment_type: string | null;
  salary_min: string | null;
  salary_max: string | null;
  salary_currency: string | null;
  salary_period: string | null;
  experience_min_years: number | null;
  experience_max_years: number | null;
  experience_is_preferred: boolean;
  required_min_years: number | null;
  required_max_years: number | null;
  preferred_min_years: number | null;
  preferred_max_years: number | null;
  requirement_type: string;
  experience_category: string;
  classification_confidence: number;
  classification_conflict: boolean;
  conflict_reasons: string[];
  detected_skills: string[];
  score_evidence: { type: string; reason: string; points: number }[];
  remote_us_only: boolean | null;
  remote_states: string[];
  excluded_states: string[];
  timezone_requirement: string | null;
  role_family: string;
  seniority_level: string;
  early_career_score: number;
  fit_label: string;
  posted_at: string | null;
  closing_at?: string | null;
  provider_metadata?: Record<string, unknown>;
  requires_us_citizenship?: boolean | null;
  requires_security_clearance?: boolean | null;
  first_seen_at: string;
  last_seen_at: string;
  source: string;
  apply_url: string;
  is_active: boolean;
  is_demo: boolean;
  is_new: boolean;
  locations: {
    location_raw: string | null;
    city: string | null;
    state: string | null;
    country: string | null;
  }[];
}
export interface JobDetail extends Job {
  experience_confidence: number;
  experience_evidence: { type: string; text: string; confidence: number }[];
  matching_version: string | null;
  remote_restriction_evidence: string[];
  description: string;
  source_url: string;
  source_job_id: string;
  source_updated_at: string | null;
  company_website: string | null;
  experience_text: string | null;
  score_reasons: string[];
  requires_us_citizenship: boolean | null;
  requires_security_clearance: boolean | null;
  sponsorship_text: string | null;
  work_authorization_text: string | null;
}
export interface JobPage {
  items: Job[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}
export interface Stats {
  active_jobs: number;
  discovered_today: number;
  discovered_this_week: number;
  remote_jobs: number;
  entry_level_jobs: number;
  average_early_career_score: number;
  demo_jobs: number;
}
export interface Source {
  id: string;
  name: string;
  source_type: string;
  company_name: string | null;
  enabled: boolean;
  last_successful_sync: string | null;
  last_sync_attempt: string | null;
  last_error: string | null;
  board_identifier: string;
  careers_url: string | null;
  active_jobs: number;
  failure_count: number;
  status: string;
}

export interface SourceSync {
  id: string;
  started_at: string;
  completed_at: string | null;
  status: string;
  jobs_fetched: number;
  jobs_created: number;
  jobs_updated: number;
  jobs_unchanged: number;
  jobs_skipped: number;
  jobs_failed: number;
  jobs_closed: number;
  error_message: string | null;
  duration_ms: number | null;
}

export interface ProviderHealth {
  provider: string;
  sources: number;
  enabled_sources: number;
  healthy: number;
  failing: number;
  active_jobs: number;
  last_successful_sync: string | null;
  recent_errors: { source: string; error: string }[];
  average_request_latency_ms: number | null;
  failed_requests: number;
  rate_limit_responses: number;
}
