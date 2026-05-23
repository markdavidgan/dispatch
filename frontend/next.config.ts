import type { NextConfig } from "next";

const config: NextConfig = {
  output: "standalone",
  images: { unoptimized: true },
  async redirects() {
    return [
      // Bureau → project rename (phase 3, post-7fb2698 backend merge).
      // Permanent (308) so old links and bookmarks resolve to the new URLs.
      { source: "/bureaus",          destination: "/projects",         permanent: true },
      { source: "/bureaus/archive",  destination: "/projects/archive", permanent: true },
      { source: "/bureaus/:slug",    destination: "/projects/:slug",   permanent: true },
      { source: "/podcast",          destination: "/podcasts",         permanent: true },
      { source: "/podcast/:slug",    destination: "/podcasts/:slug",   permanent: true },
    ];
  },
};

export default config;
