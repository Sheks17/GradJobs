"use client";
import { ProviderBadges } from "./provider-badges";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft, ArrowUpRight, Check, MapPin } from "lucide-react";
import { fetchApi } from "@/lib/api";
import {
  dateLabel,
  experienceLabel,
  remoteLabels,
  salaryLabel,
} from "@/lib/format";
import {
  setJobStatus,
  statuses,
  useStatuses,
  type JobStatus,
} from "@/lib/status";
import type { JobDetail as Detail } from "@/types/jobs";

export function JobDetail({ id }: { id: string }) {
  const [job, setJob] = useState<Detail | null>(null);
  const [error, setError] = useState("");
  const [storageError, setStorageError] = useState("");
  const [retry, setRetry] = useState(0);
  const saved = useStatuses();
  useEffect(() => {
    const controller = new AbortController();
    fetchApi<Detail>(`/jobs/${id}`, controller.signal)
      .then((data) => {
        setJob(data);
        setError("");
      })
      .catch((err) => {
        if (!controller.signal.aborted)
          setError(err.message || "Unable to load this job.");
      });
    return () => controller.abort();
  }, [id, retry]);
  useEffect(() => {
    if (job && (!saved[id] || saved[id] === "new")) {
      try {
        setJobStatus(id, "viewed");
      } catch {
        /* Explicit saves surface storage errors below. */
      }
    }
  }, [job, id, saved]);
  function changeStatus(value: JobStatus) {
    try {
      setJobStatus(id, value);
      setStorageError("");
    } catch {
      setStorageError(
        "Could not save your status. Browser storage may be disabled or full.",
      );
    }
  }
  return (
    <main className="page-container detail-page">
      <Link className="back-link" href="/">
        <ArrowLeft size={16} />
        Back to opportunities
      </Link>
      {error ? (
        <div className="empty-state" role="alert">
          <h1>Job unavailable</h1>
          <p>{error}</p>
          <button
            className="primary-button"
            onClick={() => setRetry(retry + 1)}
          >
            Try again
          </button>
        </div>
      ) : !job ? (
        <div className="empty-state" role="status">
          Loading job details…
        </div>
      ) : (
        <>
          {job.is_demo && (
            <div className="demo-banner">
              <span className="badge">DEMO DATA</span>This is a sample listing,
              not an open position.
            </div>
          )}
          {!job.is_active && (
            <div className="demo-banner">
              This job is no longer active. Your application status is still
              available.
            </div>
          )}
          <div className="detail-grid">
            <article className="detail-content">
              <div className="company-name">{job.company_name}</div>
              <h1>{job.title}</h1>
              <p className="location-line">
                <MapPin size={16} />
                {job.location_raw || "Location not provided"} ·{" "}
                {remoteLabels[job.remote_type]}
              </p>
              <div className="detail-tags">
                {job.is_new && <span className="badge green">NEW</span>}
                <ProviderBadges job={job} />
                <span className="badge green">{job.role_family}</span>
                <span className="badge">{experienceLabel(job)}</span>
                <span className="badge">
                  {job.employment_type || "Employment type not provided"}
                </span>
              </div>
              {job.locations?.length > 1 && (
                <section>
                  <h2>Available locations</h2>
                  <ul>
                    {job.locations.map((loc, index) => (
                      <li key={index}>
                        {loc.location_raw ||
                          [loc.city, loc.state, loc.country]
                            .filter(Boolean)
                            .join(", ")}
                      </li>
                    ))}
                  </ul>
                </section>
              )}
              <section>
                <h2>Skills mentioned</h2>
                <div className="skill-tags">
                  {job.detected_skills.map((skill) => (
                    <span key={skill}>{skill}</span>
                  ))}
                </div>
                {!job.detected_skills.length && (
                  <p>No supported technology terms detected.</p>
                )}
              </section>
              {job.experience_evidence.length > 0 && (
                <section>
                  <h2>Experience evidence</h2>
                  <ul>
                    {job.experience_evidence.map((item, index) => (
                      <li key={index}>
                        <strong>{item.type.replaceAll("_", " ")}:</strong>{" "}
                        {item.text}
                      </li>
                    ))}
                  </ul>
                </section>
              )}
              {(job.remote_us_only !== null ||
                job.remote_states.length > 0 ||
                job.excluded_states.length > 0 ||
                job.timezone_requirement) && (
                <section>
                  <h2>Remote eligibility</h2>
                  {job.remote_us_only === true && (
                    <p>Explicit U.S. remote location language detected.</p>
                  )}
                  {job.remote_states.length > 0 && (
                    <p>Named allowed states: {job.remote_states.join(", ")}</p>
                  )}
                  {job.excluded_states.length > 0 && (
                    <p>Excluded states: {job.excluded_states.join(", ")}</p>
                  )}
                  {job.timezone_requirement && (
                    <p>Time zone wording: {job.timezone_requirement}</p>
                  )}
                  <p className="field-help">
                    Check the original posting for eligibility and any preferred
                    versus required restrictions.
                  </p>
                </section>
              )}
              <section>
                <h2>About the opportunity</h2>
                <div className="job-description">
                  {job.description ||
                    "The employer did not provide a description. See the original posting for details."}
                </div>
              </section>
              <section className="reason-box">
                <div className="eyebrow">TRANSPARENT BY DESIGN</div>
                <h2>Why this job?</h2>
                <p>
                  {job.fit_label}. This rule-based assessment can also flag
                  reasons a role may be a stretch.
                </p>
                <ul>
                  {job.score_reasons.map((reason) => (
                    <li key={reason}>
                      <Check size={16} />
                      {reason}
                    </li>
                  ))}
                </ul>
                <p>
                  Classification confidence: {job.classification_confidence}
                  /100. This reflects how clear the title and requirements are;
                  it is a heuristic, not a measured probability.
                </p>
                {job.classification_conflict && (
                  <div className="conflict-note">
                    <strong>Requirements need review</strong>
                    <ul>
                      {job.conflict_reasons.map((reason) => (
                        <li key={reason}>{reason}</li>
                      ))}
                    </ul>
                  </div>
                )}
                <p className="field-help">
                  This is an early-career relevance score, not a personal resume
                  match. The employer’s requirements take priority.
                </p>
              </section>
              {(job.sponsorship_text || job.work_authorization_text) && (
                <section>
                  <h2>Employer’s work authorization language</h2>
                  <p>{job.sponsorship_text}</p>
                  <p>{job.work_authorization_text}</p>
                </section>
              )}
            </article>
            <aside className="detail-sidebar">
              <div className="detail-side-card">
                <div className="score detail-score">
                  <strong>
                    {job.early_career_score}
                    <small>/100</small>
                  </strong>
                  <span>{job.fit_label}</span>
                </div>
                <dl>
                  <dt>Compensation</dt>
                  <dd>{salaryLabel(job)}</dd>
                  <dt>Posted by employer</dt>
                  <dd>{dateLabel(job.posted_at)}</dd>
                  <dt>First discovered</dt>
                  <dd>{dateLabel(job.first_seen_at)}</dd>
                  <dt>Last confirmed</dt>
                  <dd>{dateLabel(job.last_seen_at)}</dd>
                  <dt>Original source</dt>
                  <dd className="capitalize">{job.source}</dd>
                </dl>
                {job.is_demo ? (
                  <div className="demo-apply">
                    Demo listing · applications unavailable
                  </div>
                ) : (
                  job.is_active && (
                    <a
                      className="primary-button"
                      href={job.apply_url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Apply on employer site
                      <ArrowUpRight size={16} />
                    </a>
                  )
                )}
                {!job.is_demo && (
                  <a
                    className="text-link original-link"
                    href={job.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    View original posting
                    <ArrowUpRight size={14} />
                  </a>
                )}
                <hr />
                <label className="field-label">
                  Application status
                  <select
                    value={saved[id] || "new"}
                    onChange={(e) => changeStatus(e.target.value as JobStatus)}
                  >
                    {statuses.map((status) => (
                      <option key={status} value={status}>
                        {status.charAt(0).toUpperCase() + status.slice(1)}
                      </option>
                    ))}
                  </select>
                </label>
                <p className="field-help">
                  Saved on this browser. No account required.
                </p>
                {storageError && (
                  <p className="inline-error" role="alert">
                    {storageError}
                  </p>
                )}
              </div>
            </aside>
          </div>
        </>
      )}
    </main>
  );
}
