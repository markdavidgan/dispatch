interface Props {
  body: string | null;
  generatedAt: string | null; // ISO8601
}

export default function FromTheDesk({ body, generatedAt }: Props) {
  if (!body) {
    return (
      <section className="mb-14">
        <h2 className="font-mono text-[11px] uppercase tracking-[0.22em] text-ink pb-3.5 border-b border-ink font-semibold mb-6 flex justify-between">
          From the desk<span className="text-ink-mute font-normal">Weekly · auto</span>
        </h2>
        <p className="font-disp text-base text-ink-soft italic">
          Not yet filed for this project. The weekly auto-summary is filed each Sunday at 23:00.
        </p>
      </section>
    );
  }
  return (
    <section className="mb-14">
      <h2 className="font-mono text-[11px] uppercase tracking-[0.22em] text-ink pb-3.5 border-b border-ink font-semibold mb-6 flex justify-between">
        From the desk<span className="text-ink-mute font-normal">Weekly · auto</span>
      </h2>
      <p className="font-disp text-xl font-medium leading-[1.45] text-ink max-w-[680px] tracking-[-0.01em]">{body}</p>
      <div className="font-mono text-[10.5px] uppercase tracking-[0.22em] text-ink-mute mt-4 font-medium flex items-center gap-2.5">
        <span className="w-1.5 h-1.5 rounded-full bg-signal" />
        Filed {generatedAt ? new Date(generatedAt).toUTCString().slice(0, 22) : "—"} · refreshes weekly
      </div>
    </section>
  );
}
