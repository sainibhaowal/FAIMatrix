"use client";

/* =============================================================================
   FAIMATRIX — SidebarNav (Golden Edition)
   -----------------------------------------------------------------------------
   Purpose:
   - Left navigation for FAIMATRIX pages.
   - Correct routing (Monitor must be /monitor, not "/").
   - Active route highlighting + premium hover glow.
   - Collapsed mode shows icons only with tooltips.
============================================================================= */

import Link from "next/link";
import { usePathname } from "next/navigation";
import React, { useCallback, useMemo, useState } from "react";
import { useSession } from "next-auth/react";
import {
  BarChart3,
  LayoutDashboard,
  MessageSquare,
  Network,
  Shield,
  HardDrive,
  CreditCard,
  Dna,
  User,
  ChevronRight,
  Search,
  Cpu,
  ServerCog,
  Brain,
  AlertTriangle,
} from "lucide-react";

import Logo from "@/components/brand/Logo";

type NavItem = {
  href: string;
  label: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
};

type NavGroup = {
  title?: string;
  items: NavItem[];
};

const NAV_GROUPS: NavGroup[] = [
  {
    title: "Core",
    items: [
      { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
      { href: "/dashboard/memory-query", label: "FAIM Cortex", icon: Search },
      { href: "/dashboard/graph", label: "FIG View", icon: Network },
      { href: "/dashboard/domain", label: "Domain Studio", icon: ServerCog },
    ],
  },
  {
    title: "Operations",
    items: [
      { href: "/dashboard/journal", label: "Journal", icon: MessageSquare },
      { href: "/dashboard/benchmarks", label: "Benchmarks", icon: BarChart3 },
      { href: "/dashboard/evolution", label: "Evolution", icon: Dna },
      { href: "/dashboard/providers", label: "Providers", icon: Cpu },
      { href: "/dashboard/api-keys", label: "API Keys", icon: Shield },
      { href: "/dashboard/storage", label: "Storage", icon: HardDrive },
      { href: "/dashboard/approval-queue", label: "Approval Queue", icon: AlertTriangle },
    ],
  },
  {
    title: "Account",
    items: [
      { href: "/dashboard/billing", label: "Billing", icon: CreditCard },
      { href: "/dashboard/profile", label: "Profile", icon: User },
    ],
  },
];

function clamp(n: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, n));
}

function useGlowVars() {
  return useCallback((e: React.MouseEvent<HTMLElement>) => {
    const el = e.currentTarget as HTMLElement;
    const r = el.getBoundingClientRect();
    const x = clamp((e.clientX - r.left) / Math.max(r.width, 1), 0, 1);
    const y = clamp((e.clientY - r.top) / Math.max(r.height, 1), 0, 1);
    el.style.setProperty("--mx", `${(x * 100).toFixed(2)}%`);
    el.style.setProperty("--my", `${(y * 100).toFixed(2)}%`);
  }, []);
}

export function SidebarNav({
  showBrand = true,
  collapsed = false,
}: {
  showBrand?: boolean;
  collapsed?: boolean;
}) {
  const pathname = usePathname();
  const onMove = useGlowVars();
  const { data: session } = useSession();

  const isActive = useCallback(
    (href: string) => {
      const normalized = href.split(/[?#]/)[0];
      return pathname === normalized || pathname.startsWith(`${normalized}/`);
    },
    [pathname],
  );

  const navGroups = useMemo(() => {
    return NAV_GROUPS;
  }, []);

  const activeHref = useMemo(() => {
    const allItems = navGroups.flatMap((g) => g.items);
    const candidates = allItems
      .filter((i) => isActive(i.href))
      .sort((a, b) => b.href.length - a.href.length);
    return candidates[0]?.href ?? "";
  }, [isActive, navGroups]);

  // Collapsed mode: Show only icons with tooltips
  if (collapsed) {
    return (
      <div className="w-full">
        {/* NAV - Icons only */}
        <nav
          className="space-y-1.5"
          role="navigation"
          aria-label="Main navigation"
        >
          {navGroups
            .flatMap((group) => group.items)
            .map((item) => {
              const active = item.href === activeHref;
              const Icon = item.icon;

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  title={item.label}
                  aria-label={item.label}
                  className={[
                    "group relative flex items-center justify-center w-11 h-11 rounded-xl mx-auto overflow-hidden",
                    "transition-all duration-300",
                    active
                      ? "bg-primary-500/15 text-primary-300"
                      : "text-slate-400 hover:text-white hover:bg-white/5",
                  ].join(" ")}
                >
                  {/* Light Sweep Effect (Collapsed Mode) */}
                  <span className="absolute inset-0 z-0 -translate-x-full group-hover:translate-x-full transition-transform duration-700 ease-in-out bg-gradient-to-r from-transparent via-white/5 to-transparent pointer-events-none" />

                  {/* Active indicator */}
                  {active && (
                    <span className="absolute left-0 top-1/2 -translate-y-1/2 h-6 w-[2px] rounded-r-full bg-gradient-to-b from-primary-400 to-secondary-400" />
                  )}
                  <Icon size={20} className="relative z-10" />
                </Link>
              );
            })}
        </nav>
      </div>
    );
  }

  return (
    <div className="w-full px-3">
      <div
        className="rounded-[24px] p-2 border shadow-[0_20px_50px_rgba(0,0,0,0.7)] backdrop-blur-3xl overflow-hidden"
        style={{
          borderColor: "rgba(255,255,254,0.1)",
          background: "rgba(10, 15, 25, 0.78)",
          boxShadow:
            "0 25px 80px -20px rgba(0,0,0,0.9), inset 0 1px 1px rgba(255,255,255,0.08)",
        }}
      >
        <nav
          className="space-y-5"
          role="navigation"
          aria-label="Main navigation"
        >
          {navGroups.map((group, gIdx) => (
            <CollapsibleGroup
              key={gIdx}
              group={group}
              isActive={isActive}
              activeHref={activeHref}
            />
          ))}
        </nav>
      </div>
    </div>
  );
}

function CollapsibleGroup({
  group,
  isActive,
  activeHref,
}: {
  group: NavGroup;
  isActive: (href: string) => boolean;
  activeHref: string;
}) {
  const [open, setOpen] = useState(true);

  return (
    <div className="flex flex-col gap-1">
      {group.title && (
        <button
          onClick={() => setOpen(!open)}
          aria-expanded={open}
          className="group/btn flex items-center gap-2 w-full px-3 py-1.5 text-[10px] uppercase tracking-[0.2em] text-slate-500 font-bold hover:text-slate-300 transition-colors"
        >
          <ChevronRight
            size={10}
            className={`transition-transform duration-200 ${open ? "rotate-90 text-primary-400/70" : "text-slate-600"}`}
            aria-hidden="true"
          />
          {group.title}
        </button>
      )}

      <div
        className={`space-y-0.5 mt-1 overflow-hidden transition-all duration-500 ${open ? "max-h-[500px] opacity-100" : "max-h-0 opacity-0"}`}
      >
        {group.items.map((item) => {
          const active = item.href === activeHref;
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={[
                "group relative flex items-center gap-2.5 rounded-2xl px-4 py-2 overflow-hidden",
                "transition-all duration-300",
                active
                  ? "bg-primary-500/10 text-primary-200 border border-primary-500/20"
                  : "text-slate-400 hover:text-white hover:bg-white/5 border border-transparent",
              ].join(" ")}
            >
              {/* Light Sweep Effect */}
              <span className="absolute inset-0 z-0 -translate-x-[110%] group-hover:translate-x-[110%] transition-transform duration-700 ease-in-out bg-gradient-to-r from-transparent via-white/5 to-transparent pointer-events-none" />

              <Icon
                size={17}
                className={[
                  "relative z-10 transition-colors duration-300",
                  active
                    ? "text-primary-300"
                    : "text-slate-500 group-hover:text-primary-300",
                ].join(" ")}
              />

              <span className="relative z-10 flex-1 text-sm font-semibold tracking-tight">
                {item.label}
              </span>

              {active && (
                <div className="relative z-10 h-1.5 w-1.5 rounded-full bg-primary-400 animate-pulse" />
              )}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
