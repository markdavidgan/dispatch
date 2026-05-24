interface Props {
  label: string;
  body: string;
}

export default function Addendum({ label, body }: Props) {
  return (
    <section
      className="mt-10 pt-6 pl-7 relative"
      style={{ animation: "addendum-in 600ms 200ms cubic-bezier(.16,.84,.36,1) both" }}
    >
      <span className="absolute left-0 top-6 bottom-6 w-0.5 bg-signal" aria-hidden />
      <div className="font-mono text-[10.5px] uppercase tracking-[0.22em] text-signal mb-2.5 font-semibold flex items-center gap-2.5">
        {label}
        <span className="inline-block bg-signal text-paper px-1.5 py-0.5 text-[9px] tracking-[0.18em]">
          FILED
        </span>
      </div>
      <p className="font-disp text-base leading-[1.62] text-ink-soft max-w-[680px]">{body}</p>
    </section>
  );
}
