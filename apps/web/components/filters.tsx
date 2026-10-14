import { SlidersHorizontal } from "lucide-react";
import { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";

export const defaults = {
  provider: "",
  role: "",
  group: "",
  skill: "",
  category: "",
  experience: "3",
  remote: "",
  state: "",
  days: "7",
  salary: "",
  score: "50",
  unknown: true,
  senior: false,
  demo: false,
};
export type Filters = typeof defaults;

export function FiltersPanel({
  value,
  onChange,
  onReset,
}: {
  value: Filters;
  onChange: (next: Filters) => void;
  onReset: () => void;
}) {
  const [metadata, setMetadata] = useState<{
    role_families: string[];
    skills: string[];
  }>({ role_families: [], skills: [] });
  useEffect(() => {
    const controller = new AbortController();
    fetchApi<typeof metadata>("/metadata", controller.signal)
      .then(setMetadata)
      .catch(() => {});
    return () => controller.abort();
  }, []);
  const set = (key: keyof Filters, next: string | boolean) =>
    onChange({
      ...value,
      ...(key === "role" ? { group: "" } : {}),
      [key]: next,
    });
  return (
    <aside className="filter-panel" aria-label="Job filters">
      <div className="filter-heading">
        <h2>
          <SlidersHorizontal size={16} /> Filters
        </h2>
        <button className="text-link" onClick={onReset}>
          Reset
        </button>
      </div>
      <details>
        <summary>Source provider</summary>
        <label className="field-label">
          Provider
          <select
            aria-label="Provider"
            value={value.provider}
            onChange={(e) => set("provider", e.target.value)}
          >
            <option value="">All providers</option>
            {[
              "greenhouse",
              "lever",
              "ashby",
              "smartrecruiters",
              "usajobs",
              "workday",
              "workable",
              "recruitee",
              "breezyhr",
            ].map((provider) => (
              <option key={provider} value={provider}>
                {provider}
              </option>
            ))}
          </select>
        </label>
      </details>
      <label className="field-label">
        Role family
        <select
          value={value.role}
          onChange={(e) => set("role", e.target.value)}
        >
          <option value="">All technology roles</option>
          {metadata.role_families?.map((role) => (
            <option key={role}>{role}</option>
          ))}
        </select>
      </label>
      <label className="field-label">
        Skill / technology
        <select
          value={value.skill}
          onChange={(e) => set("skill", e.target.value)}
        >
          <option value="">All skills</option>
          {metadata.skills?.map((skill) => (
            <option key={skill}>{skill}</option>
          ))}
        </select>
      </label>
      <label className="field-label">
        Experience category
        <select
          value={value.category}
          onChange={(e) => set("category", e.target.value)}
        >
          <option value="">All categories</option>
          {[
            ["no_experience_required", "No experience required"],
            ["0_1", "0–1 years"],
            ["0_2", "0–2 years"],
            ["1_2", "1–2 years"],
            ["1_3", "1–3 years"],
            ["2_3", "2–3 years"],
            ["3_plus", "3+ years"],
            ["4_plus", "4+ years"],
            ["5_plus", "5+ years"],
            ["unspecified", "Unspecified"],
            ["ambiguous", "Needs review"],
          ].map(([id, label]) => (
            <option value={id} key={id}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <label className="field-label">
        Experience
        <select
          value={value.experience}
          onChange={(e) => set("experience", e.target.value)}
        >
          <option value="0">No experience required</option>
          <option value="1">Up to 1 year</option>
          <option value="2">Up to 2 years</option>
          <option value="3">Up to 3 years</option>
          <option value="40">Any experience</option>
        </select>
      </label>
      <label className="checkbox-label">
        <input
          type="checkbox"
          checked={value.unknown}
          onChange={(e) => set("unknown", e.target.checked)}
        />
        Include unspecified experience
      </label>
      <fieldset className="workplace-field">
        <legend>Workplace</legend>
        {[
          ["", "All workplaces"],
          ["remote", "Remote"],
          ["hybrid", "Hybrid"],
          ["onsite", "On-site"],
          ["unknown", "Unspecified"],
        ].map(([id, label]) => (
          <label key={id} className="radio-label">
            <input
              type="radio"
              name="remote"
              checked={value.remote === id}
              onChange={() => set("remote", id)}
            />
            {label}
          </label>
        ))}
      </fieldset>
      <label className="field-label">
        State
        <input
          placeholder="All states · e.g. TX"
          value={value.state}
          onChange={(e) => set("state", e.target.value)}
          maxLength={100}
        />
      </label>
      <label className="field-label">
        Freshness
        <select
          aria-label="Freshness"
          value={value.days}
          onChange={(e) => set("days", e.target.value)}
        >
          <option value="0.25">Last 6 hours</option>
          <option value="1">Last 24 hours</option>
          <option value="3">Last 3 days</option>
          <option value="7">Last 7 days</option>
          <option value="14">Last 14 days</option>
          <option value="30">Last 30 days</option>
          <option value="">Any time</option>
        </select>
      </label>
      <p className="field-help">
        Posting date, or discovery date when the employer hasn’t provided one.
      </p>
      <label className="field-label">
        Minimum annual salary
        <select
          value={value.salary}
          onChange={(e) => set("salary", e.target.value)}
        >
          <option value="">Any salary</option>
          <option value="50000">$50,000 USD</option>
          <option value="70000">$70,000 USD</option>
          <option value="90000">$90,000 USD</option>
          <option value="110000">$110,000 USD</option>
        </select>
      </label>
      <label className="field-label">
        Early-career score
        <select
          value={value.score}
          onChange={(e) => set("score", e.target.value)}
        >
          <option value="50">Possible fit & above · 50+</option>
          <option value="70">Strong fit & above · 70+</option>
          <option value="85">Excellent fit · 85+</option>
          <option value="0">All scores</option>
        </select>
      </label>
      <label className="checkbox-label">
        <input
          type="checkbox"
          checked={value.senior}
          onChange={(e) => set("senior", e.target.checked)}
        />
        Include senior titles
      </label>
      <label className="checkbox-label">
        <input
          type="checkbox"
          checked={value.demo}
          onChange={(e) => set("demo", e.target.checked)}
        />
        Include demo listings
      </label>
      <div className="filter-note">
        <strong>A better starting point.</strong>
        <p>
          We look at titles and experience requirements to help you find roles
          within reach.
        </p>
      </div>
    </aside>
  );
}
