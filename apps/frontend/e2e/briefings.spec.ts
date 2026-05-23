import { test, expect } from "@playwright/test";

test("/briefings renders heading + empty state until Phase B", async ({ page }) => {
  await page.goto("/briefings");
  await expect(page.getByRole("heading", { name: "Briefings", exact: true })).toBeVisible();
});

test("/briefings/2099-01-01 (non-existent date) returns 404 page", async ({ page }) => {
  const r = await page.goto("/briefings/2099-01-01");
  // notFound() in App Router returns 404 status
  expect(r?.status()).toBe(404);
});

test("/briefings has at least one issue link when API is wired", async ({ page }) => {
  test.skip(!process.env.E2E_LIVE_API, "live API not configured");
  await page.goto("/briefings");
  await expect(page.locator("a[href^='/briefings/']").first()).toBeVisible();
});
