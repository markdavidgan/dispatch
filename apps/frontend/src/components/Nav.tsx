import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Gear, List, X } from "@phosphor-icons/react";

const NAV = [
  { href: "/", label: "Today" },
  { href: "/briefings", label: "Briefings" },
  { href: "/projects", label: "Projects" },
  { href: "/podcast", label: "Podcast" },
];

function isActive(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  return (
    pathname === href ||
    pathname.startsWith(href + "/") ||
    (href === "/podcast" && pathname.startsWith("/podcasts"))
  );
}

export default function Nav() {
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  const activeAdmin = pathname.startsWith("/admin");

  // Close on route change.
  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  // Close on Escape.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    if (open) {
      window.addEventListener("keydown", onKey);
      return () => window.removeEventListener("keydown", onKey);
    }
  }, [open]);

  // Close on click outside.
  useEffect(() => {
    function onClick(e: MouseEvent) {
      const target = e.target as Node;
      if (
        panelRef.current &&
        !panelRef.current.contains(target) &&
        buttonRef.current &&
        !buttonRef.current.contains(target)
      ) {
        setOpen(false);
      }
    }
    if (open) {
      document.addEventListener("mousedown", onClick);
      return () => document.removeEventListener("mousedown", onClick);
    }
  }, [open]);

  return (
    <div className="relative">
      {/* Desktop tabs */}
      <nav className="hidden sm:flex items-center gap-0 font-mono overflow-x-auto">
        {NAV.map((item) => {
          const active = isActive(pathname, item.href);
          return (
            <Link
              key={item.href}
              to={item.href}
              aria-current={active ? "page" : undefined}
              className={`text-[11px] uppercase tracking-[var(--tracking-nav)] px-2 sm:px-3.5 py-2 font-medium transition-colors whitespace-nowrap ${
                active ? "text-ink" : "text-ink-mute hover:text-ink"
              }`}
            >
              {item.label}
            </Link>
          );
        })}
        <Link
          to="/admin"
          aria-label="Admin"
          title="Admin"
          className={`ml-1 sm:ml-2 px-2 py-2 transition-colors ${
            activeAdmin ? "text-ink" : "text-ink-mute hover:text-ink"
          }`}
        >
          <Gear size={16} weight="regular" />
        </Link>
      </nav>

      {/* Mobile toggle */}
      <button
        ref={buttonRef}
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls="nav-mobile-panel"
        aria-label={open ? "Close menu" : "Open menu"}
        className="sm:hidden flex items-center justify-center p-2 -mr-2 text-ink-mute hover:text-ink transition-colors"
      >
        {open ? <X size={20} weight="regular" /> : <List size={20} weight="regular" />}
      </button>

      {/* Mobile dropdown */}
      <div
        ref={panelRef}
        id="nav-mobile-panel"
        className={`sm:hidden absolute right-0 top-full mt-2 w-48 bg-paper border border-ink shadow-sm z-30 transition-all duration-200 origin-top-right ${
          open
            ? "opacity-100 scale-100 translate-y-0 pointer-events-auto"
            : "opacity-0 scale-95 -translate-y-1 pointer-events-none"
        }`}
      >
        <nav className="flex flex-col font-mono py-1">
          {NAV.map((item) => {
            const active = isActive(pathname, item.href);
            return (
              <Link
                key={item.href}
                to={item.href}
                aria-current={active ? "page" : undefined}
                onClick={() => setOpen(false)}
                className={`text-[11px] uppercase tracking-[var(--tracking-nav)] px-4 py-2.5 font-medium transition-colors ${
                  active ? "text-ink" : "text-ink-mute hover:text-ink"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
          <div className="border-t border-hair mx-4 my-1" />
          <Link
            to="/admin"
            aria-label="Admin"
            onClick={() => setOpen(false)}
            className={`flex items-center gap-2 text-[11px] uppercase tracking-[var(--tracking-nav)] px-4 py-2.5 font-medium transition-colors ${
              activeAdmin ? "text-ink" : "text-ink-mute hover:text-ink"
            }`}
          >
            <Gear size={16} weight="regular" />
            Admin
          </Link>
        </nav>
      </div>
    </div>
  );
}
