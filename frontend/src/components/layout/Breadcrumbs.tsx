"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import React from "react";
import { IconChevron } from "@/components/layout/TopBar/IconChevron";

const NAME_MAP: Record<string, string> = {
  dashboard: "Dashboard",
  monitor: "Monitor",
  graph: "FIG View",

  benchmarks: "Benchmarks",
  settings: "Settings",
  storage: "Storage",
  billing: "Billing",
  admin: "Control Center",
  alerts: "Incidents",
  "control-plane": "Control Center",
  keys: "API Keys",
};

export function Breadcrumbs() {
  const pathname = usePathname();
  // e.g. /dashboard/graph -> ["dashboard", "graph"]
  const parts = pathname.split("/").filter(Boolean);

  if (parts.length === 0) return null;

  return (
    <div className="hidden md:flex items-center gap-2 text-xs text-slate-500 overflow-hidden whitespace-nowrap">
      <Link href="/" className="hover:text-slate-300 transition-colors">
        Home
      </Link>

      {parts.map((p, idx) => {
        // Construct href for this segment
        const href = "/" + parts.slice(0, idx + 1).join("/");
        const isLast = idx === parts.length - 1;
        const name = NAME_MAP[p] || p.charAt(0).toUpperCase() + p.slice(1);

        return (
          <React.Fragment key={href}>
            <IconChevron className="h-3 w-3 -rotate-90 opacity-40" />

            {isLast ? (
              <span className="font-medium text-slate-300">{name}</span>
            ) : (
              <Link
                href={href}
                className="hover:text-slate-300 transition-colors"
              >
                {name}
              </Link>
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}
