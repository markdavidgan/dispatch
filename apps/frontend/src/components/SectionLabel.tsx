interface Props {
  text: string;
  color?: "signal" | "ink";
}

export default function SectionLabel({ text, color = "signal" }: Props) {
  const dot = color === "signal" ? "bg-signal" : "bg-ink";
  return (
    <div className="font-mono text-[10.5px] uppercase tracking-[0.22em] text-ink mb-4 font-semibold flex items-center gap-2.5">
      <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />
      {text}
    </div>
  );
}
