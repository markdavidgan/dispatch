"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/", label: "Today" },
  { href: "/briefings", label: "Briefings" },
  { href: "/projects", label: "Projects" },
  { href: "/podcasts", label: "Podcasts" },
];

export default function Nav() {
  const pathname = usePathname();
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
            href={item.href}
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
