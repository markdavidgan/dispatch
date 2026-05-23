interface Props {
  headline: string;
  article: string;
  dek?: string;
}

/**
 * Long-form briefing body rendered on /briefings/[date]. The article
 * arrives as ~500 words of plain prose, paragraphs separated by blank
 * lines. The dek (the short blurb from the home page) sits above the
 * article as an italic deck, mirroring magazine practice — same fact
 * compressed, signposting the read ahead.
 */
export default function LeadArticle({ headline, article, dek }: Props) {
  const paragraphs = article
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter((p) => p.length > 0);

  return (
    <article>
      <h1 className="font-disp text-[42px] leading-[1.06] font-bold tracking-[-0.02em] text-ink max-w-[760px] mb-6">
        {headline}
      </h1>
      {dek && (
        <p className="font-disp italic text-[19px] leading-[1.55] text-ink-soft max-w-[680px] mb-8 pb-6 border-b border-hair">
          {dek}
        </p>
      )}
      <div className="font-disp text-[17px] leading-[1.7] text-ink max-w-[680px] space-y-5">
        {paragraphs.map((p, i) => (
          <p key={i}>{p}</p>
        ))}
      </div>
    </article>
  );
}
