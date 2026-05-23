import { test, expect } from "@playwright/test";

const cases: [string, string][] = [
  ["/bureaus",          "/projects"],
  ["/bureaus/archive",  "/projects/archive"],
  ["/bureaus/agos",     "/projects/agos"],
  ["/podcast",          "/podcasts"],
  ["/podcast/agos",     "/podcasts/agos"],
];

for (const [from, to] of cases) {
  test(`${from} 308→ ${to}`, async ({ request }) => {
    const r = await request.fetch(from, { maxRedirects: 0 });
    expect(r.status()).toBe(308);
    expect(r.headers().location).toBe(to);
  });
}
