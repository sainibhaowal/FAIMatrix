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
import {
  Activity,
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
      { href: "/dashboard/monitor", label: "Monitor", icon: Activity },
      { href: "/dashboard/graph", label: "FIG View", icon: Network },
    ],
  },
  {
    title: "Operations",
    items: [
      { href: "/dashboard/journal", label: "Journal", icon: MessageSquare },
      { href: "/dashboard/benchmarks", label: "Benchmarks", icon: BarChart3 },
      { href: "/dashboard/evolution", label: "Evolution", icon: Dna },
      { href: "/dashboard/api-keys", label: "API Keys", icon: Shield },
      { href: "/dashboard/storage", label: "Storage", icon: HardDrive },
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

  const isActive = useCallback(
    (href: string) => {
      return pathname === href || pathname.startsWith(`${href}/`);
    },
    [pathname],
  );

  const activeHref = useMemo(() => {
    const allItems = NAV_GROUPS.flatMap((g) => g.items);
    const candidates = allItems.filter((i) => isActive(i.href)).sort(
      (a, b) => b.href.length - a.href.length,
    );
    return candidates[0]?.href ?? "";
  }, [isActive]);

  // Collapsed mode: Show only icons with tooltips
  if (collapsed) {
    return (
      <div className="w-full">
        {/* NAV - Icons only */}
        <nav className="space-y-1.5" role="navigation" aria-label="Main navigation">
          {NAV_GROUPS.flatMap((group) => group.items).map((item) => {
            const active = item.href === activeHref;
            const Icon = item.icon;

            return (
              <Link
                key={item.href}
                href={item.href}
                title={item.label}
                aria-label={item.label}
                className={[
                  "group relative flex items-center justify-center w-10 h-10 rounded-lg mx-auto",
                  "transition-all duration-200",
                  active
                    ? "bg-primary-500/15 text-primary-300 shadow-[0_0_12px_rgba(34,211,238,0.15)]"
                    : "text-slate-400 hover:text-white hover:bg-white/5",
                ].join(" ")}
              >
                {/* Active indicator */}
                {active && (
                  <span className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-[2px] rounded-r-full bg-gradient-to-b from-primary-400 to-secondary-400" />
                )}
                <Icon size={18} />
              </Link>
            );
          })}
        </nav>
      </div>
    );
  }

  return (
    <div className="w-full px-2">
      <div className="os-surface rounded-xl p-1.5">
        <nav className="space-y-4" role="navigation" aria-label="Main navigation">
          {NAV_GROUPS.map((group, gIdx) => (
            <CollapsibleGroup key={gIdx} group={group} isActive={isActive} activeHref={activeHref} onMove={onMove} />
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
  onMove 
}: { 
  group: NavGroup; 
  isActive: (href: string) => boolean; 
  activeHref: string;
  onMove: (e: React.MouseEvent<HTMLElement>) => void;
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
            className={`transition-transform duration-200 ${open ? 'rotate-90 text-primary-400/70' : 'text-slate-600'}`} 
            aria-hidden="true" 
          />
          {group.title}
        </button>
      )}
      
      <div className={`space-y-0.5 overflow-hidden transition-all duration-300 ${open ? 'max-h-[500px] opacity-100' : 'max-h-0 opacity-0'}`}>
        {group.items.map((item) => {
          const active = item.href === activeHref;
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              onMouseMove={onMove}
              className={[
                "group relative flex items-center gap-2.5 rounded-lg px-3 py-1.5",
                "transition-all duration-200",
                active
                  ? "bg-primary-500/10 text-primary-200 border border-primary-500/20 shadow-[0_0_8px_rgba(34,211,238,0.05)]"
                  : "text-slate-400 hover:text-white hover:bg-white/5 border border-transparent",
              ].join(" ")}
              style={{
                backgroundImage: active
                  ? undefined
                  : "radial-gradient(120px 80px at var(--mx, 50%) var(--my, 50%), rgba(34,211,238,0.08), transparent 80%)",
              }}
            >
              <Icon
                size={16}
                className={[
                  "transition-colors",
                  active ? "text-primary-300" : "text-slate-500 group-hover:text-primary-300",
                ].join(" ")}
              />

              <span className="flex-1 text-sm font-medium tracking-tight">{item.label}</span>

              {active && (
                <div className="h-1 w-1 rounded-full bg-primary-400 shadow-[0_0_4px_rgba(34,211,238,0.5)]" />
              )}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
