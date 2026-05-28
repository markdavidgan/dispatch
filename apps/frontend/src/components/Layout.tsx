import { Link, Outlet } from "react-router-dom";
import Nav from "./Nav";
import { DemoBanner } from "./DemoBanner";
import { IS_DEMO } from "@/lib/api";

export default function Layout() {
  return (
    <div className="min-h-screen">
      {IS_DEMO && <DemoBanner />}
      <header className="border-b border-ink sticky top-0 bg-paper z-20">
        <div className="max-w-[1400px] mx-auto px-4 sm:px-8 py-4 flex items-center justify-between gap-6">
          <Link
            to="/"
            className="font-disp font-extrabold text-lg tracking-tight flex items-center gap-2.5"
          >
            <span
              className="w-2 h-2 rounded-full bg-signal"
              style={{ animation: "on-air 3.6s ease-in-out infinite" }}
              aria-hidden
              title="Dispatch is on the air"
            />
            DISPATCH
          </Link>
          <Nav />
        </div>
      </header>
      <Outlet />
    </div>
  );
}
