import { Link, useLocation } from "react-router-dom";
import { Gear } from "@phosphor-icons/react";

const NAV = [
  { href: "/", label: "Today" },
  { href: "/briefings", label: "Briefings" },
  { href: "/projects", label: "Projects" },
  { href: "/podcast", label: "Podcast" },
];

export default function Nav() {
  const { pathname } = useLocation();
  return (
    <nav className="flex items-center gap-0 font-mono overflow-x-auto">
      {NAV.map((item) => {
        // Treat /podcasts as an alias of /podcast for the nav-active check.
        const active =
          item.href === "/"
            ? pathname === "/"
            : pathname === item.href
              || pathname.startsWith(item.href + "/")
              || (item.href === "/podcast" && pathname.startsWith("/podcasts"));
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
          pathname.startsWith("/admin") ? "text-ink" : "text-ink-mute hover:text-ink"
        }`}
      >
        <Gear size={16} weight="regular" />
      </Link>
    </nav>
  );
}
