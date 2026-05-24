import { Link, useLocation } from "react-router-dom";

const NAV = [
  { href: "/", label: "Today" },
  { href: "/briefings", label: "Briefings" },
  { href: "/projects", label: "Projects" },
  { href: "/podcasts", label: "Podcasts" },
];

export default function Nav() {
  const { pathname } = useLocation();
  return (
    <nav className="flex gap-0 font-mono overflow-x-auto">
      {NAV.map((item) => {
        const active =
          item.href === "/"
            ? pathname === "/"
            : pathname === item.href || pathname.startsWith(item.href + "/");
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
    </nav>
  );
}
