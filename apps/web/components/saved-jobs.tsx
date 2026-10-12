"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Bookmark } from "lucide-react";
import { fetchApi } from "@/lib/api";
import { statuses, useStatuses } from "@/lib/status";
import type { Job } from "@/types/jobs";
import { JobCard } from "./job-card";

export function SavedJobs() {
  const saved = useStatuses();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [filter, setFilter] = useState("all");
  const [error, setError] = useState("");
  const [loadedKey, setLoadedKey] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);
  const ids = Object.entries(saved)
    .filter(([, value]) => !["new", "viewed"].includes(value))
    .map(([id]) => id)
    .sort()
    .join(",");
  const requestKey = ids + retry;
  const loading = loadedKey !== requestKey;
  useEffect(() => {
    const controller = new AbortController();
    Promise.allSettled(
      ids
        ? ids
            .split(",")
            .map((id) => fetchApi<Job>(`/jobs/${id}`, controller.signal))
        : [],
    ).then((results) => {
      if (controller.signal.aborted) return;
      setJobs(
        results.flatMap((result) =>
          result.status === "fulfilled" ? [result.value] : [],
        ),
      );
      setError(
        results.some((result) => result.status === "rejected")
          ? "Some tracked jobs could not be loaded. Your saved statuses are still stored in this browser."
          : "",
      );
      setLoadedKey(requestKey);
    });
    return () => controller.abort();
  }, [ids, requestKey]);
  const visible = jobs.filter(
    (job) => filter === "all" || saved[job.id] === filter,
  );
  return (
    <main className="page-container saved-page">
      <section className="page-intro">
        <div>
          <div className="eyebrow">ONE OPPORTUNITY AT A TIME</div>
          <h1>
            My applications<span>.</span>
          </h1>
          <p>Your saved jobs and next steps, together in one place.</p>
        </div>
      </section>
      <div className="demo-banner">
        Application statuses are stored on this browser only. Clearing browser
        data removes them.
      </div>
      <div className="tracker-tabs">
        <button
          className={filter === "all" ? "selected" : ""}
          onClick={() => setFilter("all")}
        >
          All tracked
        </button>
        {statuses
          .filter((status) => !["new", "viewed"].includes(status))
          .map((status) => (
            <button
              className={filter === status ? "selected" : ""}
              key={status}
              onClick={() => setFilter(status)}
            >
              {status}{" "}
              <span>
                {
                  Object.values(saved).filter((value) => value === status)
                    .length
                }
              </span>
            </button>
          ))}
      </div>
      {error && (
        <div className="inline-error" role="alert">
          {error}{" "}
          <button className="text-link" onClick={() => setRetry(retry + 1)}>
            Retry
          </button>
        </div>
      )}
      {loading ? (
        <div className="empty-state" role="status">
          Loading tracked jobs…
        </div>
      ) : visible.length ? (
        <div className="job-list saved-list">
          {visible.map((job) => (
            <JobCard key={job.id} job={job} />
          ))}
        </div>
      ) : (
        <div className="empty-state">
          <Bookmark size={32} />
          <h2>Your next step starts with a save.</h2>
          <p>
            Bookmark an opportunity or update its status on the job details
            page.
          </p>
          <Link className="primary-button" href="/">
            Discover jobs
          </Link>
        </div>
      )}
    </main>
  );
}
