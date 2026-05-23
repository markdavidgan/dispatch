import { defineConfig, devices } from "@playwright/test";

// chromium auto-download is broken on this host's Ubuntu 26.04; use system Chrome.
// Override via PLAYWRIGHT_CHROME_EXECUTABLE in CI / other environments.
const executablePath = process.env.PLAYWRIGHT_CHROME_EXECUTABLE || "/usr/bin/google-chrome";

// Cap workers on this 12GB machine to avoid OOM-killing VS Code: when
// multiple Chromes + full-page screenshots run in parallel.
const workers = process.env.PLAYWRIGHT_WORKERS
  ? parseInt(process.env.PLAYWRIGHT_WORKERS, 10)
  : process.env.CI
    ? 4
    : 2;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  workers,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: "list",
  use: {
    baseURL: process.env.E2E_BASE_URL || "http://localhost:3000",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      grepInvert: /@mobile/,
      use: { ...devices["Desktop Chrome"], launchOptions: { executablePath } },
    },
    {
      name: "chromium-mobile",
      grep: /@mobile/,
      use: { ...devices["Pixel 7"], launchOptions: { executablePath } },
    },
  ],
  webServer: process.env.E2E_BASE_URL
    ? undefined
    : {
        command: "pnpm dev",
        url: "http://localhost:3000",
        reuseExistingServer: !process.env.CI,
        timeout: 60_000,
      },
});
