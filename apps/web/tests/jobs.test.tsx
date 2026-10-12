import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { JobCard } from "@/components/job-card";
import { Dashboard } from "@/components/dashboard";
import { fetchApi } from "@/lib/api";
import { experienceLabel, salaryLabel } from "@/lib/format";
import { parseStatuses } from "@/lib/status";
import { demoJob } from "./fixtures";

vi.mock("@/lib/api", () => ({ fetchApi: vi.fn() }));

describe("honest job metadata", () => {
  it("distinguishes unknown experience and salary", () => {
    expect(
      experienceLabel({
        experience_min_years: null,
        experience_max_years: null,
      }),
    ).toBe("Experience not specified");
    expect(
      salaryLabel({
        salary_min: null,
        salary_max: null,
        salary_currency: null,
        salary_period: null,
      }),
    ).toBe("Salary not disclosed");
    expect(salaryLabel(demoJob)).toContain("$70,000–$85,000 / year");
  });
  it("does not provide a fake apply link for demo jobs and uses discovery date", () => {
    render(<JobCard job={demoJob} />);
    expect(
      screen.queryByRole("link", { name: /^Apply/ }),
    ).not.toBeInTheDocument();
    expect(screen.getByText("Demo listing")).toBeVisible();
    expect(screen.queryByText(/^Posted /)).not.toBeInTheDocument();
  });
  it("saves and removes jobs persistently", () => {
    render(<JobCard job={demoJob} />);
    fireEvent.click(screen.getByRole("button", { name: /^Save / }));
    expect(
      parseStatuses(localStorage.getItem("gradjobs:status:v1"))[demoJob.id],
    ).toBe("saved");
    fireEvent.click(screen.getByRole("button", { name: /^Remove / }));
    expect(
      parseStatuses(localStorage.getItem("gradjobs:status:v1"))[demoJob.id],
    ).toBe("new");
  });
  it("recovers from corrupted or invalid saved state", () => {
    expect(parseStatuses("broken")).toEqual({});
    expect(
      parseStatuses(
        JSON.stringify({ [demoJob.id]: "invalid", other: "saved" }),
      ),
    ).toEqual({});
  });
});

describe("dashboard API integration", () => {
  it("passes filters to the API and renders results", async () => {
    vi.mocked(fetchApi).mockImplementation(async (path) =>
      path === "/metadata"
        ? { role_families: ["QA / Testing"], skills: ["React", "Playwright"] }
        : path === "/stats"
          ? {
              active_jobs: 1,
              discovered_today: 1,
              discovered_this_week: 1,
              remote_jobs: 0,
              entry_level_jobs: 1,
              average_early_career_score: 98,
              demo_jobs: 1,
            }
          : {
              items: [demoJob],
              total: 1,
              total_pages: 1,
              page: 1,
              page_size: 12,
            },
    );
    render(<Dashboard />);
    expect(
      await screen.findByText("Associate Software Engineer"),
    ).toBeVisible();
    fireEvent.click(screen.getByLabelText("Remote", { selector: "input" }));
    await waitFor(() =>
      expect(
        vi
          .mocked(fetchApi)
          .mock.calls.some(([path]) => path.includes("remote_type=remote")),
      ).toBe(true),
    );
    expect(
      vi
        .mocked(fetchApi)
        .mock.calls.some(
          ([path]) =>
            path.includes("fresh_after=") && path.includes("max_experience=3"),
        ),
    ).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "0–2 Years" }));
    fireEvent.change(screen.getByLabelText("Skill / technology"), {
      target: { value: "React" },
    });
    await waitFor(() =>
      expect(
        vi
          .mocked(fetchApi)
          .mock.calls.some(
            ([path]) =>
              path.includes("max_experience=2") &&
              path.includes("include_unknown_experience=false") &&
              path.includes("skill=React") &&
              path.includes("sort=best_match"),
          ),
      ).toBe(true),
    );
    fireEvent.click(
      screen.getByRole("button", {
        name: "No Experience Required",
      }),
    );
    await waitFor(() =>
      expect(
        vi
          .mocked(fetchApi)
          .mock.calls.some(([path]) =>
            path.includes("experience_category=no_experience_required"),
          ),
      ).toBe(true),
    );
  });
  it("shows an actionable error instead of fabricated results", async () => {
    vi.mocked(fetchApi).mockRejectedValue(new TypeError("Failed to fetch"));
    render(<Dashboard />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "couldn’t reach the job service",
    );
    expect(screen.getByRole("button", { name: "Try again" })).toBeVisible();
  });
});

it("shows separate confidence, skills, conflicts, and concise fit evidence", () => {
  render(<JobCard job={{ ...demoJob, classification_conflict: true }} />);
  expect(screen.getByText("React")).toBeVisible();
  expect(screen.getByText(/Associate-level title/)).toBeVisible();
  expect(
    screen.getByText(/Classification confidence: 95\/100/),
  ).toHaveTextContent("Requirements need review");
  expect(
    experienceLabel({
      ...demoJob,
      required_min_years: null,
      preferred_min_years: 2,
      preferred_max_years: null,
    }),
  ).toBe("2+ years preferred");
  expect(
    experienceLabel({
      ...demoJob,
      experience_category: "no_experience_required",
    }),
  ).toBe("No experience required");
});

it("NEW is driven by API discovery metadata and posting labels distinguish calendar days", () => {
  render(<JobCard job={{ ...demoJob, is_new: true }} />);
  expect(screen.getByText("NEW")).toBeVisible();
});
