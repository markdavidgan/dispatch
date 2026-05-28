/**
 * Demo mode banner — shown on every page when the app is built in demo mode.
 *
 * Self-hosted instances never see this because `vite.demo.config.ts` is the
 * only build path that swaps `@/lib/api` to the demo wrapper.
 */
export function DemoBanner() {
  return (
    <div className="bg-signal/10 border-b border-signal/20 text-center py-2 px-4">
      <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-signal">
        Demo mode — static data.{" "}
        <a
          href="https://github.com/markdavidgan/dispatch"
          target="_blank"
          rel="noreferrer"
          className="underline hover:text-ink transition-colors"
        >
          View on GitHub
        </a>
      </p>
    </div>
  );
}
