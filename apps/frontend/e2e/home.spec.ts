import { test, expect } from "@playwright/test";

test("home renders Today / Briefings / Projects / Podcasts nav", async ({ page }) => {
  await page.goto("/");
  // Scope to the <nav> element so we don't collide with marginalia links
  // like "All Briefings" (in the right rail) or content-area Numeral links.
  const nav = page.getByRole("navigation");
  for (const label of ["Today", "Briefings", "Projects", "Podcasts"]) {
    await expect(nav.getByRole("link", { name: label })).toBeVisible();
  }
});

test("home renders numeral or empty state", async ({ page }) => {
  await page.goto("/");
  const bodyText = await page.locator("body").textContent();
  expect(bodyText).toMatch(/DISPATCH/);
});
