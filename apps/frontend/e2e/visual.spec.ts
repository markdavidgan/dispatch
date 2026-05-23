import { test, expect } from "@playwright/test";

const ROUTES_DESKTOP = ["/", "/briefings", "/projects", "/projects/agos", "/podcasts"];

for (const route of ROUTES_DESKTOP) {
  test(`visual · desktop · ${route}`, async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(route);
    await page.waitForLoadState("networkidle");
    await expect(page).toHaveScreenshot(`desktop-${route.replace(/\W/g, "_")}.png`, {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });
}

for (const route of ["/", "/projects/agos"]) {
  test(`visual · mobile · ${route}`, async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(route);
    await page.waitForLoadState("networkidle");
    await expect(page).toHaveScreenshot(`mobile-${route.replace(/\W/g, "_")}.png`, {
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
    });
  });
}
