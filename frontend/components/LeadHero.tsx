"use client";

interface Props {
  headline: string;
  body: string;
}

export default function LeadHero({ headline, body }: Props) {
  return (
    <article>
      <h1 className="font-disp text-[42px] leading-[1.06] font-bold tracking-[-0.02em] text-ink max-w-[760px] mb-6">
        {headline}
      </h1>
      <p className="font-disp text-base leading-[1.62] text-ink-soft max-w-[680px]">
        {body}
      </p>
    </article>
  );
}
