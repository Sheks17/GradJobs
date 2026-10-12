"use client";

import { useMemo, useState, useSyncExternalStore } from "react";
import { defaults, type Filters } from "./filters";

type SavedSearch = {
  id: string;
  name: string;
  filters: Filters;
  query: string;
  sort: string;
};
const KEY = "gradjobs:searches:v1";
const EVENT = "gradjobs-searches-change";

export function parseSearches(raw: string): SavedSearch[] {
  try {
    const value: unknown = JSON.parse(raw);
    if (!Array.isArray(value)) return [];
    return value
      .filter(
        (item): item is SavedSearch =>
          item &&
          typeof item.id === "string" &&
          typeof item.name === "string" &&
          item.name.length <= 100 &&
          typeof item.query === "string" &&
          item.query.length <= 200 &&
          typeof item.sort === "string" &&
          item.filters &&
          Object.entries(defaults).every(
            ([key, val]) => typeof item.filters[key] === typeof val,
          ),
      )
      .slice(0, 30);
  } catch {
    return [];
  }
}
function snapshot() {
  try {
    return window.localStorage.getItem(KEY) || "[]";
  } catch {
    return "[]";
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

export function SavedSearches({
  filters,
  query,
  sort,
  onLoad,
}: {
  filters: Filters;
  query: string;
  sort: string;
  onLoad: (search: SavedSearch) => void;
}) {
  const raw = useSyncExternalStore(subscribe, snapshot, () => "[]");
  const searches = useMemo(() => parseSearches(raw), [raw]);
  const [name, setName] = useState("");
  const [message, setMessage] = useState("");
  function write(next: SavedSearch[]) {
    try {
      window.localStorage.setItem(KEY, JSON.stringify(next));
      window.dispatchEvent(new Event(EVENT));
      setMessage("");
      return true;
    } catch {
      setMessage(
        "This browser couldn’t save the search. Check storage permissions.",
      );
      return false;
    }
  }
  return (
    <details className="saved-searches">
      <summary>Saved searches ({searches.length})</summary>
      <p>
        Keep your filters in this browser. Searches refresh when you open them.
      </p>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          if (!name.trim()) return;
          if (searches.length >= 30) {
            setMessage("Delete a search before adding another (limit 30).");
            return;
          }
          if (
            write([
              ...searches,
              {
                id: crypto.randomUUID(),
                name: name.trim(),
                filters: { ...filters },
                query,
                sort,
              },
            ])
          )
            setName("");
        }}
      >
        <input
          aria-label="Saved search name"
          maxLength={100}
          required
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Name this search"
        />
        <button className="filter-chip" type="submit">
          Save current search
        </button>
      </form>
      {message && <p role="alert">{message}</p>}
      {searches.map((search) => (
        <div key={search.id} className="quick-filters">
          <button className="filter-chip" onClick={() => onLoad(search)}>
            {search.name}
          </button>
          <button
            className="text-link"
            aria-label={`Delete saved search ${search.name}`}
            onClick={() =>
              write(searches.filter((item) => item.id !== search.id))
            }
          >
            Delete
          </button>
        </div>
      ))}
    </details>
  );
}
