"use client";

import { useMemo, useSyncExternalStore } from "react";

export const statuses = [
  "new",
  "viewed",
  "saved",
  "applied",
  "interviewing",
  "offer",
  "rejected",
  "archived",
] as const;
export type JobStatus = (typeof statuses)[number];
const KEY = "gradjobs:status:v1";
const EVENT = "gradjobs-status-change";

export function parseStatuses(raw: string | null): Record<string, JobStatus> {
  try {
    const data: unknown = JSON.parse(raw || "{}");
    if (!data || typeof data !== "object" || Array.isArray(data)) return {};
    return Object.fromEntries(
      Object.entries(data).filter(
        ([id, value]) =>
          /^[a-f0-9-]{36}$/i.test(id) && statuses.includes(value as JobStatus),
      ),
    );
  } catch {
    return {};
  }
}

function snapshot() {
  try {
    return window.localStorage.getItem(KEY) || "{}";
  } catch {
    return "{}";
  }
}
function subscribe(callback: () => void) {
  window.addEventListener("storage", callback);
  window.addEventListener(EVENT, callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener(EVENT, callback);
  };
}
export function useStatuses() {
  const raw = useSyncExternalStore(subscribe, snapshot, () => "{}");
  return useMemo(() => parseStatuses(raw), [raw]);
}
export function setJobStatus(id: string, status: JobStatus) {
  const data = parseStatuses(snapshot());
  data[id] = status;
  window.localStorage.setItem(KEY, JSON.stringify(data));
  window.dispatchEvent(new Event(EVENT));
}
