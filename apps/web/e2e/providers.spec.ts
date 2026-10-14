import { expect, test } from "@playwright/test";

test("ATS registry separates detection and collection", async ({ page }) => {
  await page.goto("/admin/providers");
  await expect(
    page.getByRole("heading", { name: "ATS capabilities" }),
  ).toBeVisible();
  const workable = page.getByRole("row").filter({ hasText: "Workable" });
  await expect(workable).toContainText("Supported");
  const teamtailor = page.getByRole("row").filter({ hasText: "Teamtailor" });
  await expect(teamtailor).toContainText("Unavailable");
  await expect(teamtailor).toContainText("AUTHENTICATED API");
  await expect(
    page.getByRole("row").filter({ hasText: "LinkedIn Talent Hub" }),
  ).toContainText("PARTNER ONLY");
});

test("provider health matches persisted API results", async ({
  page,
  request,
}) => {
  const response = await request.get("http://localhost:8000/stats/providers");
  expect(response.ok()).toBe(true);
  const providers = await response.json();
  await page.goto("/sources");
  const summary = page.getByRole("region", { name: "Provider health" });
  for (const provider of providers) {
    const card = summary.locator(".source-card").filter({
      has: page.getByRole("heading", {
        name: provider.provider,
        exact: true,
      }),
    });
    await expect(card).toBeVisible();
    await expect(card).toContainText(
      `${provider.sources} (${provider.enabled_sources} enabled)`,
    );
    await expect(card).toContainText(
      provider.active_jobs.toLocaleString("en-US"),
    );
  }
  await page.screenshot({
    path: "../../artifacts/phase4a/provider-health.png",
    fullPage: false,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth > innerWidth,
    ),
  ).toBe(false);
});

test("advanced provider filter and source-supported federal details", async ({
  page,
  request,
}) => {
  await page.goto("/");
  await expect(page.locator(".job-card").first()).toBeVisible();
  const providerSelect = page.getByLabel("Provider", { exact: true });
  await page.getByText("Source provider", { exact: true }).click();
  await expect(providerSelect).toBeVisible();
  const pending = page.waitForResponse(
    (response) =>
      new URL(response.url()).searchParams.get("provider") === "usajobs" &&
      response.status() === 200,
  );
  await page.getByLabel("Provider", { exact: true }).selectOption("usajobs");
  const response = await pending;
  const results = await response.json();
  expect(
    results.items.every((job: { source: string }) => job.source === "usajobs"),
  ).toBe(true);
  const jobs = await (
    await request.get(
      "http://localhost:8000/jobs?provider=usajobs&country=all&max_experience=40&min_early_career_score=0&include_senior=true&page_size=100",
    )
  ).json();
  expect(jobs.items.length).toBeGreaterThan(0);
  const job = jobs.items.find(
    (job: { closing_at: string | null }) => job.closing_at,
  );
  await page.goto(`/jobs/${job.id}`);
  await expect(page.getByText("Federal", { exact: true })).toBeVisible();
  await expect(page.locator(".detail-tags")).toContainText("Closes");
  await page.screenshot({
    path: "../../artifacts/phase4a/federal-detail.png",
    fullPage: false,
  });
});
