import { useState } from "react";
import { Check, Copy } from "@phosphor-icons/react";

interface Props {
  feedUrl: string;
  title: string;
  auth?: { username: string; password: string };
}

export function PodcastSubscribeBlock({ feedUrl, title, auth }: Props) {
  const [copied, setCopied] = useState<string | null>(null);

  const copy = async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(label);
      setTimeout(() => setCopied(null), 1800);
    } catch {
      /* clipboard unavailable — ignore */
    }
  };

  const httpsFeed = feedUrl.replace(/^https?:\/\//, "");
  const appleDeepLink = `podcast://${httpsFeed}`;
  const overcastDeepLink = `overcast://x-callback-url/add?url=${encodeURIComponent(feedUrl)}`;

  return (
    <section className="border border-ink mt-6">
      <header className="border-b border-ink px-4 py-2.5 flex items-baseline justify-between bg-paper-deep">
        <h3 className="font-mono text-[10.5px] uppercase tracking-[0.22em] text-ink font-semibold">
          Subscribe — {title}
        </h3>
        <span className="font-mono text-[9.5px] uppercase tracking-[0.18em] text-ink-mute">
          Private feed · Basic Auth
        </span>
      </header>

      <div className="p-4 space-y-4">
        <Field
          label="Feed URL"
          value={feedUrl}
          copied={copied === "feed"}
          onCopy={() => copy(feedUrl, "feed")}
          mono
        />

        {auth?.username && (
          <Field
            label="Username"
            value={auth.username}
            copied={copied === "user"}
            onCopy={() => copy(auth.username, "user")}
            mono
          />
        )}
        {auth?.password && (
          <Field
            label="Password"
            value={auth.password}
            copied={copied === "pass"}
            onCopy={() => copy(auth.password, "pass")}
            mono
            secret
          />
        )}

        <div className="pt-2 border-t border-hair flex flex-wrap gap-2 items-center">
          <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-mute mr-1">
            Open in
          </span>
          <DeepLink href={appleDeepLink}>Apple Podcasts</DeepLink>
          <DeepLink href={overcastDeepLink}>Overcast</DeepLink>
        </div>

        {auth && (
          <p className="font-mono text-[9.5px] uppercase tracking-[0.16em] text-ink-mute leading-relaxed pt-1">
            Most podcast apps prompt for the credentials when adding a feed by URL.
            Apple Podcasts on iOS handles the prompt cleanly; on desktop you may need
            to paste them when the OS dialog appears.
          </p>
        )}
      </div>
    </section>
  );
}

function Field({
  label,
  value,
  copied,
  onCopy,
  mono,
  secret,
}: {
  label: string;
  value: string;
  copied: boolean;
  onCopy: () => void;
  mono?: boolean;
  secret?: boolean;
}) {
  const [revealed, setRevealed] = useState(!secret);
  const display = secret && !revealed ? "•".repeat(Math.max(value.length, 8)) : value;
  return (
    <div className="flex flex-col gap-1 sm:grid sm:grid-cols-[88px_1fr_auto] sm:gap-3 sm:items-center">
      <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-mute">
        {label}
      </span>
      <code
        className={`block w-full px-2.5 py-1.5 bg-paper-deep border border-hair text-ink text-ellipsis overflow-hidden whitespace-nowrap ${
          mono ? "font-mono text-xs" : "text-xs"
        }`}
        title={display}
      >
        {display}
      </code>
      <div className="flex gap-2 items-center">
        {secret && (
          <button
            onClick={() => setRevealed((r) => !r)}
            className="text-ink-mute hover:text-ink px-1 font-mono text-[10px] uppercase tracking-[0.18em] font-medium"
          >
            {revealed ? "Hide" : "Show"}
          </button>
        )}
        <button
          onClick={onCopy}
          className={copied ? "text-signal" : "text-ink hover:text-signal"}
          title={copied ? "Copied" : "Copy"}
          aria-label={copied ? "Copied" : "Copy"}
        >
          {copied ? <Check size={16} weight="bold" /> : <Copy size={16} weight="bold" />}
        </button>
      </div>
    </div>
  );
}

function DeepLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a
      href={href}
      className="font-mono text-[10.5px] uppercase tracking-[0.18em] text-ink border border-ink hover:bg-ink hover:text-paper px-3 py-1.5 font-medium transition-colors"
    >
      {children} ↗
    </a>
  );
}
