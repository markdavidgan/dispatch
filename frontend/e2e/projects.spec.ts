import { test, expect } from "@playwright/test";

// TODO(post-B9): tighten matchers to `/^AGOS$/` and `/^Made with Aether$/`
// once the backend redeploy syncs the post-953b4f0 display_name renames
// into production R2. The case-insensitive regexes below exist only to
// straddle the A8→Phase-B redeploy window.

test("/projects index lists active projects", async ({ page }) => {
  await page.goto("/projects");
  await expect(page.getByRole("heading", { name: "Projects", exact: true })).toBeVisible();
  // Case-insensitive + includes marklab so the test survives:
  //   (a) the projects.yml AGOS rename (display_name today is "Agos"
  //       on production R2; will be "AGOS" once the backend redeploys),
  //   (b) the Aether-Focus → "Made with Aether" rename in the same redeploy,
  //   (c) environments where marklab is the only currently-active project.
  await expect(
    page.getByRole("link", { name: /Agos|Aether|Marcos|marklab/i }).first()
  ).toBeVisible();
});

test("/projects/agos Section Front renders", async ({ page }) => {
  await page.goto("/projects/agos");
  // Case-insensitive match for "Agos" or "AGOS" depending on whether
  // production R2 has been re-synced from the post-953b4f0 registry.
  await expect(page.getByRole("heading", { name: /^AGOS$/i })).toBeVisible();
  // Empty-state copy until Phase B
  await expect(page.getByText(/From the desk/)).toBeVisible();
  await expect(page.getByText(/Mentioned in briefings/)).toBeVisible();
});
