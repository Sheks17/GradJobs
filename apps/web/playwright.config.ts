import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  retries: 0,
  workers: 1,
  timeout: 60000,
  expect: { timeout: 15000 },
  reporter: "list",
  outputDir: "../../artifacts/browser-tests",
  use: {
    baseURL: "http://localhost:3000",
    channel:
      process.env.PLAYWRIGHT_CHANNEL ||
      (process.platform === "win32" ? "msedge" : "chromium"),
    viewport: { width: 1440, height: 1000 },
    screenshot: "only-on-failure",
  },
});
