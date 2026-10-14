"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchApi } from "@/lib/api";

type Capability = {
  provider: string;
  canonical_name: string;
  ingestion_status: string;
  detection_supported: boolean;
  ingestion_supported: boolean;
  database_available: boolean;
  verified_employers: number | null;
  active_jobs: number | null;
  last_successful_sync: string | null;
  healthy: number | null;
  failing: number | null;
  notes: string;
};

export function ProviderCapabilities() {
  const [rows, setRows] = useState<Capability[]>([]);
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    fetchApi<Capability[]>("/stats/ats", controller.signal)
      .then((value) => {
        setRows(value);
        setLoaded(true);
      })
      .catch((err) => {
        if (!controller.signal.aborted) setError(err.message);
      });
    return () => controller.abort();
  }, []);
  return (
    <main className="page-container">
      <section className="page-intro">
        <div>
          <h1>ATS capabilities</h1>
          <p>
            Read-only provider access and operational health. Detection does not
            imply ingestion support.
          </p>
          <Link href="/admin/ingestion">Ingestion history</Link>
        </div>
      </section>
      {error && <p role="alert">{error}</p>}
      {!loaded && !error && <p role="status">Loading provider capabilities…</p>}
      {loaded && (
        <>
          {rows.some((row) => !row.database_available) && (
            <p role="status">
              Database unavailable. Operational counts are withheld; ATS access
              classifications remain available.
            </p>
          )}
          <p>
            Employer counts reflect sources with a successful database sync;
            disabled candidates and the federal query are excluded from employer
            counts.
          </p>
          <div style={{ overflowX: "auto" }}>
            <table className="w-full text-left text-sm [&_td]:p-3 [&_th]:p-3 [&_td]:align-top [&_th]:align-top [&_tr]:border-b">
              <caption>Provider access and current health</caption>
              <thead>
                <tr>
                  {[
                    "Provider",
                    "Access",
                    "Detection",
                    "Ingestion",
                    "Verified employers",
                    "Active jobs",
                    "Last success",
                    "Health",
                  ].map((label) => (
                    <th scope="col" key={label}>
                      {label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.provider}>
                    <th scope="row">
                      <details>
                        <summary>{row.canonical_name}</summary>
                        <p>{row.notes}</p>
                      </details>
                    </th>
                    <td>{row.ingestion_status.replaceAll("_", " ")}</td>
                    <td>
                      {row.detection_supported
                        ? "Yes"
                        : "Limited explicit evidence"}
                    </td>
                    <td>
                      {row.ingestion_supported ? "Supported" : "Unavailable"}
                    </td>
                    <td>{row.verified_employers ?? "Unavailable"}</td>
                    <td>
                      {row.active_jobs?.toLocaleString() ?? "Unavailable"}
                    </td>
                    <td>
                      {row.last_successful_sync
                        ? new Date(row.last_successful_sync).toLocaleString()
                        : "—"}
                    </td>
                    <td>
                      {!row.database_available
                        ? "Database unavailable"
                        : row.ingestion_supported
                          ? `${row.healthy} healthy / ${row.failing} failing`
                          : "Detection only"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </main>
  );
}
