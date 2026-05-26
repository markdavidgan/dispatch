const BANNED_PHRASES = [
  "excited to announce",
  "in today's fast-paced",
  "leverage",
  "leveraging",
  "best-in-class",
  "robust",
  "game-changing",
  "synergize",
  "synergy",
  "delighted to share",
  "stay tuned",
];

export function lintLead(result: Record<string, any>): string[] {
  const warnings: string[] = [];
  const blob = ((result.lead_headline || "") + " " + (result.lead_body || "")).toLowerCase();
  for (const phrase of BANNED_PHRASES) {
    if (blob.includes(phrase)) warnings.push(`banned phrase: '${phrase}'`);
  }
  if ((result.lead_headline || "").includes("!")) warnings.push("exclamation in headline");
  if ((result.lead_headline || "").length > 100) warnings.push(`headline too long: ${result.lead_headline.length} chars`);
  return warnings;
}

export function lintAddendum(body: string): string[] {
  const warnings: string[] = [];
  const blob = body.toLowerCase();
  for (const phrase of BANNED_PHRASES) {
    if (blob.includes(phrase)) warnings.push(`banned phrase: '${phrase}'`);
  }
  if (body.includes("!")) warnings.push("exclamation in addendum");
  return warnings;
}
