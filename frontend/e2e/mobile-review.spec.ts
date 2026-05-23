import { test, expect, type Page } from "@playwright/test";

const ROUTES = [
  { path: "/", name: "home" },
  { path: "/briefings", name: "briefings" },
  { path: "/briefings/2026-05-16", name: "briefing-detail" },
  { path: "/projects", name: "projects" },
  { path: "/projects/aether-agent-plugins", name: "project-detail" },
  { path: "/projects/archive", name: "projects-archive" },
  { path: "/podcasts", name: "podcasts" },
  { path: "/podcasts/agos", name: "podcast-detail" },
];

async function captureMobile(page: Page, route: { path: string; name: string }) {
  await page.goto(route.path);
  await page.waitForLoadState("networkidle");
  // Small delay for any layout settling
  await page.waitForTimeout(500);

  // Check for horizontal overflow
  const hasOverflow = await page.evaluate(() => {
    return document.documentElement.scrollWidth > document.documentElement.clientWidth;
  });
  const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
  const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);

  // Capture full-page screenshot — use jpeg to reduce memory/disk pressure
  await page.screenshot({
    path: `e2e/mobile-review/${route.name}.jpg`,
    type: "jpeg",
    quality: 80,
    fullPage: true,
  });

  // Explicitly free renderer memory before next route
  await page.close();

  return { hasOverflow, scrollWidth, clientWidth };
}

// Serial execution: one page at a time to avoid parallel full-page screenshot
// memory spikes that can OOM-kill VS Code: on this 12GB machine.
test.describe.configure({ mode: "serial" });

test.describe("mobile review @mobile", () => {
  test.use({ viewport: { width: 412, height: 915 } }); // Pixel 7

  for (const route of ROUTES) {
    test(`mobile: ${route.name}`, async ({ page }) => {
      const result = await captureMobile(page, route);
      console.log(`${route.name}: overflow=${result.hasOverflow}, scrollWidth=${result.scrollWidth}, clientWidth=${result.clientWidth}`);
      expect(result.hasOverflow).toBe(false);
    });
  }
});
