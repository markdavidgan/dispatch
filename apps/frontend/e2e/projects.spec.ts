import { test, expect } from "@playwright/test";

test("/projects index lists active projects", async ({ page }) => {
  await page.goto("/projects");
  await expect(page.getByRole("heading", { name: "Projects", exact: true })).toBeVisible();
  // The shipped example registry includes these active slugs; case-insensitive
  // to tolerate display_name variants between fixture and production data.
  await expect(
    page.getByRole("link", { name: /FastAPI|Tailwind|Astro/i }).first()
  ).toBeVisible();
});

test("/projects/fastapi Section Front renders", async ({ page }) => {
  await page.goto("/projects/fastapi");
  await expect(page.getByRole("heading", { name: /^FastAPI$/i })).toBeVisible();
  // Empty-state copy when no events are present yet
  await expect(page.getByText(/From the desk/)).toBeVisible();
  await expect(page.getByText(/Mentioned in briefings/)).toBeVisible();
});
