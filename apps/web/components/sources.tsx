"use client";

import { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import { timestampLabel } from "@/lib/format";
import type { Source, SourceSync, ProviderHealth } from "@/types/jobs";

function Providers({ refresh }: { refresh: number }) {
  const [providers, setProviders] = useState<ProviderHealth[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    fetchApi<ProviderHealth[]>("/stats/providers", controller.signal)
      .then((data) => {
        setProviders(data);
        setError("");
      })
      .catch((err) => {
        if (!controller.signal.aborted) setError(err.message);
      });
    return () => controller.abort();
  }, [refresh]);
  return (
    <section aria-label="Provider health">
      <h2>Provider health</h2>
      <p className="muted">
        All locations; active counts exclude duplicate aliases. Request metrics
        cover the latest attempt per source.
      </p>
      {error && <p role="alert">{error}</p>}
      <div className="sources-grid">
        {providers.map((provider) => (
          <article className="source-card" key={provider.provider}>
            <h3>{provider.provider}</h3>
            <dl>
              <dt>Sources</dt>
              <dd>
                {provider.sources} ({provider.enabled_sources} enabled)
              </dd>
              <dt>Healthy / Failing</dt>
              <dd>
                {provider.healthy} / {provider.failing}
              </dd>
              <dt>Active Jobs</dt>
              <dd>{provider.active_jobs.toLocaleString()}</dd>
              <dt>Last Sync</dt>
              <dd>{timestampLabel(provider.last_successful_sync)}</dd>
              <dt>Average request</dt>
              <dd>
                {provider.average_request_latency_ms === null
                  ? "Not measured"
                  : `${provider.average_request_latency_ms.toFixed(0)} ms`}
              </dd>
              <dt>Failed requests / Rate limits</dt>
              <dd>
                {provider.failed_requests} / {provider.rate_limit_responses}
              </dd>
            </dl>
            {provider.recent_errors.map((error, index) => (
              <p className="inline-error" key={index}>
                {error.source}: {error.error}
              </p>
            ))}
          </article>
        ))}
      </div>
    </section>
  );
}

function History({ sourceId }: { sourceId: string }) {
  const [history, setHistory] = useState<SourceSync[] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    fetchApi<SourceSync[]>(
      `/sources/${sourceId}/history?limit=10`,
      controller.signal,
    )
      .then(setHistory)
      .catch((err) => {
        if (!controller.signal.aborted) setError(err.message);
      });
    return () => controller.abort();
  }, [sourceId]);
  if (error) return <p role="alert">{error}</p>;
  if (!history) return <p role="status">Loading sync history…</p>;
  if (!history.length) return <p>No sync attempts yet.</p>;
  return (
    <ol className="sync-history">
      {history.map((run) => (
        <li key={run.id}>
          <strong>{run.status}</strong> · {timestampLabel(run.started_at)}
          <p>
            {run.jobs_fetched.toLocaleString()} fetched · {run.jobs_created}{" "}
            created · {run.jobs_updated} updated · {run.jobs_unchanged}{" "}
            unchanged · {run.jobs_closed} closed · {run.jobs_skipped} skipped ·{" "}
            {run.jobs_failed} failed
          </p>
          <small>
            {run.duration_ms === null
              ? "In progress"
              : `${(run.duration_ms / 1000).toFixed(1)} seconds`}
          </small>
          {run.error_message && (
            <p className="inline-error">{run.error_message}</p>
          )}
        </li>
      ))}
    </ol>
  );
}

function SourceCard({ source }: { source: Source }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <article className="source-card">
      <div className="source-status">
        <span className="badge">{source.source_type}</span>
        <span className={`badge ${source.status === "healthy" ? "green" : ""}`}>
          {source.status}
        </span>
      </div>
      <h2>{source.company_name || source.name}</h2>
      <dl>
        <dt>Board</dt>
        <dd>{source.board_identifier}</dd>
        <dt>Collection</dt>
        <dd>{source.enabled ? "Enabled" : "Disabled"}</dd>
        <dt>Active postings</dt>
        <dd>{source.active_jobs.toLocaleString()}</dd>
        <dt>Last attempt</dt>
        <dd>{timestampLabel(source.last_sync_attempt)}</dd>
        <dt>Last complete sync</dt>
        <dd>{timestampLabel(source.last_successful_sync)}</dd>
        <dt>Consecutive failures</dt>
        <dd>{source.failure_count}</dd>
      </dl>
      {source.last_error && <p className="inline-error">{source.last_error}</p>}
      {source.careers_url && (
        <p>
          <a
            className="text-link"
            href={source.careers_url}
            target="_blank"
            rel="noopener noreferrer"
          >
            Employer job board ↗
          </a>
        </p>
      )}
      <button
        className="text-link"
        aria-expanded={expanded}
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? "Hide sync history" : "View sync history"}
      </button>
      {expanded && <History sourceId={source.id} />}
    </article>
  );
}

export function Sources() {
  const [sources, setSources] = useState<Source[] | null>(null);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    fetchApi<Source[]>("/sources?limit=1000", controller.signal)
      .then((data) => {
        setSources(data);
        setError("");
      })
      .catch((err) => {
        if (!controller.signal.aborted) setError(err.message);
      });
    return () => controller.abort();
  }, [retry]);
  return (
    <main className="page-container">
      <section className="page-intro">
        <div>
          <div className="eyebrow">KNOW WHERE YOUR OPPORTUNITIES COME FROM</div>
          <h1>
            Original sources. Clear context<span>.</span>
          </h1>
          <p>
            Live collection health for supported employer boards and official
            federal searches.
          </p>
        </div>
      </section>
      <p className="source-intro">
        Every posting keeps its original source and discovery date. Timestamps
        below show the latest observed collection activity. Active counts
        include all locations and experience levels, before dashboard filters
        and deduplication.
      </p>
      <div className="results-toolbar">
        <p>
          {sources
            ? `${sources.length} sources · ${sources.filter((s) => s.enabled).length} enabled · ${sources.filter((s) => s.status === "healthy").length} healthy`
            : "Source registry"}
        </p>
        <button className="text-link" onClick={() => setRetry(retry + 1)}>
          Refresh status
        </button>
      </div>
      <Providers refresh={retry} />
      {error ? (
        <div className="empty-state" role="alert">
          <p>{error}</p>
          <button
            className="primary-button"
            onClick={() => setRetry(retry + 1)}
          >
            Try again
          </button>
        </div>
      ) : sources === null ? (
        <p role="status">Loading sources…</p>
      ) : sources.length === 0 ? (
        <div className="empty-state">
          <h2>No sources configured yet.</h2>
          <p>Import a source registry to get started.</p>
        </div>
      ) : (
        <div className="sources-grid">
          {sources.map((source) => (
            <SourceCard key={`${source.id}-${retry}`} source={source} />
          ))}
        </div>
      )}
    </main>
  );
}
