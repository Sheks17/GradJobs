import { expect, test } from "@playwright/test";

test("saved searches survive reload and restore filters", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator(".job-card").first()).toBeVisible();
  await page.getByText("Saved searches (0)", { exact: true }).click();
  await page.getByRole("button", { name: "Remote", exact: true }).click();
  await page.getByLabel("Saved search name").fill("Remote early career");
  await page.getByRole("button", { name: "Save current search" }).click();
  await page.reload();
  await page.getByText("Saved searches (1)", { exact: true }).click();
  await page
    .getByRole("button", { name: "Remote early career", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Remote", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await page
    .getByRole("button", { name: "Delete saved search Remote early career" })
    .click();
  await expect(
    page.getByText("Saved searches (0)", { exact: true }),
  ).toBeVisible();
});

test("read-only ingestion page and mobile dashboard load", async ({ page }) => {
  await page.goto("/admin/ingestion");
  await expect(
    page.getByRole("heading", { name: "Ingestion health" }),
  ).toBeVisible();
  await expect(page.getByText(/healthy sources/)).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.locator(".job-card").first()).toBeVisible();
  expect(
    await page.locator("body").evaluate((body) => body.scrollWidth),
  ).toBeLessThanOrEqual(390);
});
