"use client";

import { useEffect, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  BriefcaseBusiness,
  CalendarDays,
  Globe2,
  Search,
  Sparkles,
  X,
} from "lucide-react";
import { fetchApi } from "@/lib/api";
import type { JobPage, Stats } from "@/types/jobs";
import { FiltersPanel, defaults, type Filters } from "./filters";
import { JobCard } from "./job-card";

export function Dashboard() {
  const [filters, setFilters] = useState<Filters>(defaults);
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("best_match");
  const [page, setPage] = useState(1);
  const requestKey = JSON.stringify({ filters, search, sort, page });
  const [response, setResponse] = useState<{
    key: string;
    result: JobPage | null;
    error: string;
  } | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [retry, setRetry] = useState(0);
  const responseKey = requestKey + retry;
  const loading = response?.key !== responseKey;
  const result = response?.result;
  const error = !loading ? response?.error : "";
  const [showFilters, setShowFilters] = useState(false);
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(query);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);
  useEffect(() => {
    const controller = new AbortController();
    fetchApi<Stats>("/stats", controller.signal)
      .then(setStats)
      .catch(() => {});
    return () => controller.abort();
  }, [retry]);
  useEffect(() => {
    const controller = new AbortController();
    const params = new URLSearchParams({
      page: String(page),
      page_size: "12",
      sort,
      q: search,
      max_experience: filters.experience,
      min_early_career_score: filters.score,
      include_unknown_experience: String(filters.unknown),
      include_senior: String(filters.senior),
      include_demo: String(filters.demo),
    });
    if (filters.role) params.set("role_family", filters.role);
    if (filters.provider) params.set("provider", filters.provider);
    if (filters.group) params.set("role_group", filters.group);
    if (filters.skill) params.set("skill", filters.skill);
    if (filters.category) params.set("experience_category", filters.category);
    if (filters.remote) params.set("remote_type", filters.remote);
    if (filters.state.trim()) params.set("state", filters.state.trim());
    if (filters.salary) params.set("min_salary", filters.salary);
    if (filters.days)
      params.set(
        "fresh_after",
        new Date(Date.now() - Number(filters.days) * 86400000).toISOString(),
      );
    fetchApi<JobPage>(`/jobs?${params}`, controller.signal)
      .then((data) => {
        if (!controller.signal.aborted)
          setResponse({ key: responseKey, result: data, error: "" });
      })
      .catch((err) => {
        if (!controller.signal.aborted)
          setResponse({
            key: responseKey,
            result: null,
            error:
              err instanceof TypeError
                ? "We couldn’t reach the job service. Check that the API is running, then try again."
                : err.message,
          });
      });
    return () => controller.abort();
  }, [filters, search, sort, page, responseKey]);
  function reset() {
    setFilters(defaults);
    setQuery("");
    setSort("best_match");
    setPage(1);
  }
  const quickFilters: { label: string; values: Partial<Filters> }[] = [
    { label: "New Today", values: { days: "1" } },
    {
      label: "0–2 Years",
      values: { experience: "2", unknown: false, category: "" },
    },
    {
      label: "No Experience Required",
      values: {
        experience: "0",
        unknown: false,
        category: "no_experience_required",
      },
    },
    { label: "Remote", values: { remote: "remote" } },
    { label: "Software", values: { group: "software", role: "" } },
    { label: "QA", values: { group: "", role: "QA / Testing" } },
    { label: "Support", values: { group: "support", role: "" } },
    { label: "Cloud", values: { group: "cloud", role: "" } },
    { label: "Implementation", values: { group: "", role: "Implementation" } },
  ];
  const cards = [
    {
      label: "Discovered today",
      value: stats?.discovered_today,
      icon: Sparkles,
      note: "A fresh start",
    },
    {
      label: "New this week",
      value: stats?.discovered_this_week,
      icon: CalendarDays,
      note: "Since Monday · UTC",
    },
    {
      label: "Entry-level roles",
      value: stats?.entry_level_jobs,
      icon: BriefcaseBusiness,
      note: "Your experience, valued",
    },
    {
      label: "Remote opportunities",
      value: stats?.remote_jobs,
      icon: Globe2,
      note: "Based in the U.S.",
    },
  ];
  return (
    <main className="page-container">
      <section className="page-intro">
        <div>
          <div className="eyebrow">SMALL STEPS. BIG POSSIBILITIES.</div>
          <h1>
            Find your next beginning<span>.</span>
          </h1>
          <p>Find the opportunities built for the start of your career.</p>
        </div>
        <div className="intro-note">
          <span className="live-dot" />
          Built for early careers
          <small>Fresh opportunities. Clear requirements.</small>
        </div>
      </section>
      {filters.demo && stats && stats.demo_jobs > 0 && (
        <div className="demo-banner">
          <span className="badge">DEMO DATA INCLUDED</span> Sample roles are
          clearly labeled. Demo listings aren’t open positions.
        </div>
      )}
      <section
        className="stats-grid"
        aria-label="All active U.S. job statistics"
      >
        {cards.map(({ label, value, icon: Icon, note }) => (
          <div className="stat-card" key={label}>
            <div className="stat-label">
              {label}
              <Icon size={17} />
            </div>
            <strong>{value?.toLocaleString() ?? "—"}</strong>
            <span>{note}</span>
          </div>
        ))}
      </section>
      {stats && (
        <p className="stats-context">
          {stats.active_jobs.toLocaleString()} active U.S. jobs · Average
          early-career score: {stats.average_early_career_score}/100 ·
          Statistics include all active U.S. roles; day and week use UTC.
        </p>
      )}
      <div className="workspace-grid">
        <div className={`filters-wrapper ${showFilters ? "filters-open" : ""}`}>
          <FiltersPanel
            value={filters}
            onChange={(next) => {
              setFilters(next);
              setPage(1);
            }}
            onReset={reset}
          />
        </div>
        <section className="results-section" aria-label="Job results">
          <div className="search-box">
            <Search size={20} />
            <input
              type="search"
              aria-label="Search jobs, companies, or technologies"
              placeholder="Search jobs, companies, or technologies…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <span className="search-hint">
              Find your fit <ArrowUpRight size={14} />
            </span>
          </div>
          <div className="quick-filters" aria-label="Quick filters">
            {quickFilters.map(({ label, values }) => (
              <button
                key={label}
                className="filter-chip"
                aria-pressed={Object.entries(values).every(
                  ([key, value]) => filters[key as keyof Filters] === value,
                )}
                onClick={() => {
                  setFilters({ ...filters, ...values });
                  setPage(1);
                }}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="results-toolbar">
            <div>
              <h2>
                Opportunities for you{" "}
                <span>{loading ? "…" : (result?.total ?? 0)}</span>
              </h2>
              <p>U.S. roles, with early-career relevance in focus.</p>
            </div>
            <label className="sort-label">
              Sort by
              <select
                aria-label="Sort jobs"
                value={sort}
                onChange={(e) => {
                  setSort(e.target.value);
                  setPage(1);
                }}
              >
                <option value="best_match">Freshness, fit & confidence</option>
                <option value="relevance">Search relevance</option>
                <option value="newest">Newest first</option>
                <option value="newest_posted">Newest posted</option>
                <option value="recently_discovered">Recently discovered</option>
                <option value="early_career_score">
                  Best early-career fit
                </option>
                <option value="company">Company A–Z</option>
                <option value="salary">Highest annual USD salary</option>
              </select>
            </label>
          </div>
          <p className="ranking-help">
            Title and company matches first when searching, then freshness,
            early-career fit, and confidence.
          </p>
          <div className="active-filters">
            <button
              className="mobile-filter-toggle"
              onClick={() => setShowFilters(!showFilters)}
            >
              Filters
            </button>
            <span className="filter-chip">United States</span>
            {(["skill", "group", "category"] as const).map(
              (key) =>
                filters[key] && (
                  <button
                    className="filter-chip"
                    key={key}
                    onClick={() => {
                      setFilters({ ...filters, [key]: "" });
                      setPage(1);
                    }}
                  >
                    {key === "category"
                      ? filters[key].replaceAll("_", " ")
                      : filters[key]}
                    <X size={12} />
                  </button>
                ),
            )}
            {filters.days && (
              <button
                className="filter-chip"
                onClick={() => setFilters({ ...filters, days: "" })}
              >
                Last{" "}
                {filters.days === "0.25"
                  ? "6 hours"
                  : filters.days === "1"
                    ? "24 hours"
                    : `${filters.days} days`}
                <X size={12} />
              </button>
            )}
            <span className="filter-chip">
              {filters.experience === "40"
                ? "Any experience"
                : `Up to ${filters.experience} years`}
            </span>
            {filters.role && (
              <button
                className="filter-chip"
                onClick={() => setFilters({ ...filters, role: "" })}
              >
                {filters.role}
                <X size={12} />
              </button>
            )}
          </div>
          {error ? (
            <div className="empty-state" role="alert">
              <h3>Let’s reconnect.</h3>
              <p>{error}</p>
              <button
                className="primary-button"
                onClick={() => setRetry(retry + 1)}
              >
                Try again
              </button>
            </div>
          ) : loading ? (
            <div
              className="loading-state"
              role="status"
              aria-label="Loading jobs"
            >
              {[0, 1, 2].map((i) => (
                <div key={i} className="skeleton-card">
                  <div />
                  <div />
                  <div />
                </div>
              ))}
            </div>
          ) : result?.items.length ? (
            <div className="job-list">
              {result.items.map((job) => (
                <JobCard key={job.id} job={job} />
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <Search size={30} />
              <h3>No matches just yet.</h3>
              <p>Try another role, a wider date range, or fewer filters.</p>
              <button className="primary-button" onClick={reset}>
                Reset filters
              </button>
            </div>
          )}
          {!loading && !error && result && result.total_pages > 0 && (
            <div className="pagination">
              <span>
                Showing {(page - 1) * result.page_size + 1}–
                {Math.min(page * result.page_size, result.total)} of{" "}
                {result.total} jobs
              </span>
              <div>
                <button
                  className="icon-button"
                  aria-label="Previous page"
                  disabled={page <= 1}
                  onClick={() => setPage(page - 1)}
                >
                  <ArrowLeft size={17} />
                </button>
                <span>
                  Page {page} of {result.total_pages}
                </span>
                <button
                  className="icon-button"
                  aria-label="Next page"
                  disabled={page >= result.total_pages}
                  onClick={() => setPage(page + 1)}
                >
                  <ArrowRight size={17} />
                </button>
              </div>
            </div>
          )}
          <p className="results-note">
            A score is a guide, not a guarantee. Always check the employer’s
            full requirements.
          </p>
        </section>
      </div>
    </main>
  );
}
