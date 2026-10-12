"use client";

import { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";

type Run = {
  id: string;
  started_at: string;
  completed_at: string | null;
  status: string;
  summary: {
    duration_seconds?: number;
    sources_successful?: number;
    sources_failed?: number;
    jobs_fetched?: number;
    jobs_created?: number;
    jobs_updated?: number;
    provider_filter?: string | null;
    providers?: { provider: string; successful: number; sources: number }[];
  };
};
type Overview = {
  history: Run[];
  healthy_sources: number;
  failing_sources: number;
  jobs_created_today: number;
  jobs_updated_today: number;
};

export function Ingestion() {
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    fetchApi<Overview>("/ingestion", controller.signal)
      .then(setData)
      .catch((err) => {
        if (!controller.signal.aborted) setError(err.message);
      });
    return () => controller.abort();
  }, []);
  return (
    <main className="page-container">
      <section className="page-intro">
        <div>
          <h1>Ingestion health</h1>
          <p>
            Read-only operational history. Source changes and sync controls
            remain disabled publicly.
          </p>
        </div>
      </section>
      {error && <p role="alert">{error}</p>}
      {!data && !error && <p role="status">Loading ingestion history…</p>}
      {data && (
        <>
          <p>
            {data.healthy_sources} healthy sources · {data.failing_sources}{" "}
            failing sources · {data.jobs_created_today} jobs created today ·{" "}
            {data.jobs_updated_today} jobs updated today (UTC)
          </p>
          {data.history.length === 0 && (
            <p>
              No full runs have been recorded since run history was introduced.
            </p>
          )}
          {data.history.map((run) => (
            <article className="stat-card" key={run.id}>
              <h2>
                {run.summary.provider_filter || "All providers"} · {run.status}
              </h2>
              <p>
                Started {new Date(run.started_at).toLocaleString()} ·{" "}
                {run.completed_at
                  ? `Completed ${new Date(run.completed_at).toLocaleString()}`
                  : "Completion pending; consult GitHub Actions if the worker stopped."}
              </p>
              <p>
                Duration: {run.summary.duration_seconds ?? "—"} seconds · Jobs
                fetched: {run.summary.jobs_fetched ?? "—"} · Created:{" "}
                {run.summary.jobs_created ?? "—"} · Updated:{" "}
                {run.summary.jobs_updated ?? "—"}
              </p>
              <p>
                Successful sources: {run.summary.sources_successful ?? "—"} ·
                Failed: {run.summary.sources_failed ?? "—"}
              </p>
              <p>
                {run.summary.providers
                  ?.map(
                    (provider) =>
                      `${provider.provider}: ${provider.successful}/${provider.sources} successful`,
                  )
                  .join(" · ")}
              </p>
            </article>
          ))}
        </>
      )}
    </main>
  );
}
