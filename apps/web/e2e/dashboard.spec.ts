import { expect, test } from "@playwright/test";

test("Phase 3 quick filters, skills, freshness, sorting and explanations", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.locator(".job-card").first()).toBeVisible();
  const jobsAfter = async (
    action: () => Promise<unknown>,
    parameter: string,
    value: string,
  ) => {
    const [response] = await Promise.all([
      page.waitForResponse((response) => {
        const url = new URL(response.url());
        return (
          url.pathname.endsWith("/jobs") &&
          url.searchParams.get(parameter) === value &&
          response.status() === 200
        );
      }),
      action(),
    ]);
    return response.json();
  };
  let result = await jobsAfter(
    () => page.getByRole("button", { name: "0–2 Years", exact: true }).click(),
    "max_experience",
    "2",
  );
  expect(
    result.items.every(
      (job: { required_min_years: number | null }) =>
        job.required_min_years !== null && job.required_min_years <= 2,
    ),
  ).toBe(true);
  result = await jobsAfter(
    () => page.getByRole("button", { name: "Remote", exact: true }).click(),
    "remote_type",
    "remote",
  );
  expect(
    result.items.every(
      (job: { remote_type: string }) => job.remote_type === "remote",
    ),
  ).toBe(true);
  result = await jobsAfter(
    () => page.getByLabel("Skill / technology").selectOption("Python"),
    "skill",
    "Python",
  );
  expect(
    result.items.every((job: { detected_skills: string[] }) =>
      job.detected_skills.includes("Python"),
    ),
  ).toBe(true);
  await jobsAfter(
    () => page.getByRole("button", { name: "New Today", exact: true }).click(),
    "skill",
    "Python",
  );
  await expect(page.getByLabel("Freshness", { exact: true })).toHaveValue("1");
  result = await jobsAfter(
    () => page.getByLabel("Sort jobs").selectOption("early_career_score"),
    "sort",
    "early_career_score",
  );
  const scores = result.items.map(
    (job: { early_career_score: number }) => job.early_career_score,
  );
  expect(scores).toEqual([...scores].sort((a, b) => b - a));
  await jobsAfter(
    () => page.getByRole("button", { name: "Reset", exact: true }).click(),
    "sort",
    "best_match",
  );
  const first = page.locator(".job-card").first();
  await expect(first).toContainText("Why it may fit:");
  await expect(first).toContainText("Classification confidence:");
  await first.getByRole("link", { name: "View job", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Why this job?" }),
  ).toBeVisible();
  await expect(page.locator(".reason-box")).toContainText(
    "not a measured probability",
  );
  await page.screenshot({
    path: "../../artifacts/phase3/job-explanation.png",
    fullPage: true,
  });
});

test("live discovery, filters, details, and persistent application tracking", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  const first = page.locator(".job-card").first();
  await expect(first).toBeVisible();
  await expect(page.locator(".demo-banner")).toHaveCount(0);
  await expect(page.locator(".stats-context")).toBeVisible();
  const title = await first.locator("h2 a").innerText();
  const href = await first.locator("h2 a").getAttribute("href");
  await expect(first.getByRole("link", { name: /^Apply/ })).toHaveAttribute(
    "href",
    /^https:\/\//,
  );
  await page.screenshot({
    path: "../../artifacts/dashboard-desktop.png",
    fullPage: true,
  });
  await page.getByLabel("Freshness", { exact: true }).selectOption("0.25");
  await expect(
    page.getByRole("button", { name: "Last 6 hours" }),
  ).toBeVisible();
  await page.getByLabel("Freshness", { exact: true }).selectOption("");
  await page.getByLabel("Sort jobs").selectOption("newest_posted");
  await page.getByLabel("Include senior titles").check();
  await page.getByRole("button", { name: "Reset", exact: true }).click();
  await page.getByRole("searchbox").fill(title);
  await expect(page.locator(`h2 a[href="${href}"]`)).toBeVisible();
  await page.locator(`h2 a[href="${href}"]`).click();
  await expect(
    page.getByRole("heading", { name: title, exact: true, level: 1 }),
  ).toBeVisible();
  await expect(page.locator(".job-description")).not.toBeEmpty();
  await expect(
    page.getByRole("heading", {
      name: "Why this job?",
    }),
  ).toBeVisible();
  await expect(page.locator(".detail-sidebar")).toContainText(
    "Original source",
  );
  await page.getByLabel("Application status").selectOption("applied");
  await page
    .getByRole("link", { name: "My applications", exact: true })
    .click();
  await expect(page.locator(`h2 a[href="${href}"]`)).toBeVisible();
  await page.reload();
  await expect(page.locator(`h2 a[href="${href}"]`)).toBeVisible();
  expect(errors).toEqual([]);
});

test("mobile live dashboard stays within viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.locator(".job-card").first()).toBeVisible();
  await page.getByRole("button", { name: "Filters", exact: true }).click();
  await page.getByLabel("Freshness", { exact: true }).selectOption("30");
  await expect(
    page.getByRole("button", { name: "Last 30 days" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Filters", exact: true }).click();
  await expect(page.locator(".job-card").first()).toBeVisible({
    timeout: 15000,
  });
  await page.screenshot({
    path: "../../artifacts/dashboard-mobile.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth,
    ),
  ).toBe(false);
});

test("source health exposes persisted sync history", async ({ page }) => {
  await page.goto("/sources");
  const source = page
    .locator(".source-card")
    .filter({ has: page.getByRole("button", { name: /sync history/ }) })
    .filter({ has: page.getByText("healthy", { exact: true }) })
    .first();
  await expect(source).toBeVisible();
  await expect(source).toContainText("healthy");
  await source.getByRole("button", { name: "View sync history" }).click();
  await expect(source.locator(".sync-history")).toContainText("success");
  await expect(source.locator(".sync-history")).toContainText("fetched");
  await page.screenshot({
    path: "../../artifacts/sources-desktop.png",
    fullPage: false,
  });
});
