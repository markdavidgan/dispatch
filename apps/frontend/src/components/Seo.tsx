import { Helmet } from "react-helmet-async";

interface SeoProps {
  title?: string;
  description?: string;
  canonicalPath?: string;
  noindex?: boolean;
  og?: {
    title?: string;
    description?: string;
    type?: string;
    url?: string;
    image?: string;
  };
  jsonLd?: object;
  rss?: { title: string; url: string };
}

const SITE_NAME = "Dispatch";
const DEFAULT_DESCRIPTION =
  "A self-hosted daily editorial brief generator for software projects. AI-synthesized daily reports with audio narration and weekly podcasts.";
const DEFAULT_OG_IMAGE = "https://dispatch-demo.markdavidgan.com/og-image.png";

function origin(): string {
  try {
    return window.location.origin;
  } catch {
    return "https://dispatch-demo.markdavidgan.com";
  }
}

export default function Seo({
  title,
  description = DEFAULT_DESCRIPTION,
  canonicalPath,
  noindex,
  og,
  jsonLd,
  rss,
}: SeoProps) {
  const fullTitle = title ? `${title} · ${SITE_NAME}` : SITE_NAME;
  const ogTitle = og?.title ?? title ?? SITE_NAME;
  const ogDescription = og?.description ?? description;
  const ogType = og?.type ?? "website";
  const ogUrl = og?.url ?? (canonicalPath ? `${origin()}${canonicalPath}` : undefined);
  const ogImage = og?.image ?? DEFAULT_OG_IMAGE;
  const canonical = canonicalPath ? `${origin()}${canonicalPath}` : undefined;

  return (
    <Helmet>
      <title>{fullTitle}</title>
      <meta name="description" content={description} />
      {canonical && <link rel="canonical" href={canonical} />}
      {noindex && <meta name="robots" content="noindex, nofollow" />}
      {rss && <link rel="alternate" type="application/rss+xml" title={rss.title} href={rss.url} />}

      {/* OpenGraph */}
      <meta property="og:site_name" content={SITE_NAME} />
      <meta property="og:title" content={ogTitle} />
      <meta property="og:description" content={ogDescription} />
      <meta property="og:type" content={ogType} />
      {ogUrl && <meta property="og:url" content={ogUrl} />}
      <meta property="og:image" content={ogImage} />

      {/* Twitter Card */}
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content={ogTitle} />
      <meta name="twitter:description" content={ogDescription} />
      <meta name="twitter:image" content={ogImage} />

      {/* JSON-LD */}
      {jsonLd && (
        <script type="application/ld+json">
          {JSON.stringify(jsonLd)}
        </script>
      )}
    </Helmet>
  );
}
