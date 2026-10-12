"use client";

import Link from "next/link";
import {
  ArrowUpRight,
  Bookmark,
  BriefcaseBusiness,
  MapPin,
} from "lucide-react";
import {
  dateLabel,
  experienceLabel,
  relativeDate,
  postedLabel,
  remoteLabels,
  salaryLabel,
} from "@/lib/format";
import { setJobStatus, useStatuses } from "@/lib/status";
import type { Job } from "@/types/jobs";
import { useState } from "react";
import { ProviderBadges } from "./provider-badges";

export function JobCard({ job }: { job: Job }) {
  const statuses = useStatuses();
  const status = statuses[job.id] || "new";
  const [error, setError] = useState("");
  const tracked = !["new", "viewed"].includes(status);
  function save() {
    try {
      setJobStatus(job.id, tracked ? "new" : "saved");
      setError("");
    } catch {
      setError(
        "Your browser could not save this job. Check storage permissions.",
      );
    }
  }
  return (
    <article className="job-card">
      <div className="job-top">
        <div
          className={`company-mark mark-${job.company_name.length % 4}`}
          aria-hidden="true"
        >
          {job.company_name
            .replace("Demo Company ", "D")
            .slice(0, 2)
            .toUpperCase()}
        </div>
        <div className="job-heading">
          <div className="company-name">
            {job.company_name}
            {job.is_new && (
              <span
                className="badge green"
                title="Recently discovered by GradJobs"
              >
                NEW
              </span>
            )}
            {job.is_demo && <span className="demo-tag">Demo</span>}
            <ProviderBadges job={job} />
          </div>
          <h2>
            <Link href={`/jobs/${job.id}`}>{job.title}</Link>
          </h2>
          <div className="location-line">
            <MapPin size={14} />
            {job.locations?.length > 1
              ? job.locations
                  .map(
                    (loc) =>
                      loc.location_raw ||
                      [loc.city, loc.state, loc.country]
                        .filter(Boolean)
                        .join(", "),
                  )
                  .join(" · ")
              : job.location_raw || "Location not provided"}
            <span className="dot">·</span>
            {remoteLabels[job.remote_type]}
          </div>
        </div>
        <button
          className={`icon-button save-button ${tracked ? "is-saved" : ""}`}
          onClick={save}
          aria-label={
            tracked
              ? `Remove ${job.title} from tracked jobs`
              : `Save ${job.title}`
          }
          aria-pressed={tracked}
        >
          <Bookmark size={19} fill={tracked ? "currentColor" : "none"} />
        </button>
      </div>
      <div className="job-body">
        <div className="job-meta">
          <div className="salary">{salaryLabel(job)}</div>
          <div className="job-tags">
            <span>
              <BriefcaseBusiness size={13} />
              {experienceLabel(job)}
            </span>
            <span>{job.role_family}</span>
            {job.seniority_level !== "unknown" && (
              <span className="badge green">
                {job.seniority_level.replace("_", " ")}
              </span>
            )}
          </div>
        </div>
        <div
          className={`score ${job.early_career_score < 70 ? "neutral" : ""}`}
          title={job.fit_label}
        >
          <strong>
            {job.early_career_score}
            <small>/100</small>
          </strong>
          <span>Early-career fit</span>
        </div>
      </div>
      <div className="matching-preview">
        <div className="skill-tags" aria-label="Detected skills">
          {job.detected_skills.slice(0, 5).map((skill) => (
            <span key={skill}>{skill}</span>
          ))}
        </div>
        <p>
          <strong>Why it may fit:</strong>{" "}
          {job.score_evidence
            .filter((item) => item.type === "positive")
            .slice(0, 2)
            .map((item) => item.reason)
            .join(" · ") || "Review the employer’s requirements."}
        </p>
        <small>
          Classification confidence: {job.classification_confidence}/100
          {job.classification_conflict && " · Requirements need review"}
        </small>
      </div>
      <div className="job-footer">
        <div className="freshness">
          <span className="fresh-dot" />
          {job.posted_at
            ? `Posted ${postedLabel(job.posted_at)}`
            : `Discovered ${relativeDate(job.first_seen_at)}`}
          <span className="muted source-label">via {job.source}</span>
          <span className="discovery-date">
            Discovered {dateLabel(job.first_seen_at)}
          </span>
        </div>
        <div className="card-actions">
          {tracked && <span className="badge status-badge">{status}</span>}
          <Link className="text-link" href={`/jobs/${job.id}`}>
            View job
          </Link>
          {job.is_demo ? (
            <span
              className="demo-apply"
              title="Demo listings are not open positions"
            >
              Demo listing
            </span>
          ) : (
            <a
              className="apply-button"
              href={job.apply_url}
              target="_blank"
              rel="noopener noreferrer"
            >
              Apply <ArrowUpRight size={14} />
            </a>
          )}
        </div>
      </div>
      {error && (
        <p role="alert" className="inline-error">
          {error}
        </p>
      )}
    </article>
  );
}
