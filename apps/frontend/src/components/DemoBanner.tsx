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
        Demo Mode — Data is static. Admin and audio generation are disabled.
      </p>
    </div>
  );
}
