import { test, expect } from "@playwright/test";

test("home renders without errors", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(page.locator("body")).toBeVisible();
  expect(errors, errors.join("\n")).toEqual([]);
});
