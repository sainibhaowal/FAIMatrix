'use client';

/* =============================================================================
   FAIM LAB — SidebarNav (Golden Edition)
   -----------------------------------------------------------------------------
   Purpose:
   - Left navigation for FAIM Lab pages.
   - Correct routing (Monitor must be /monitor, not "/").
   - Active route highlighting + premium hover glow.
   - Zero coupling to dashboard/monitor logic (safe).
============================================================================= */

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import React, { useCallback, useMemo } from 'react';
import {
  Activity,
  BarChart3,
  LayoutDashboard,
  MessageSquare,
  Network,
  Shield,
} from 'lucide-react';

import Logo from '../brand/Logo';

type NavItem = {
  href: string;
  label: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
};

const NAV_ITEMS: NavItem[] = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/monitor', label: 'Monitor', icon: Activity }, // ✅ FIXED
  { href: '/graph', label: 'FIG View', icon: Network },
  { href: '/chat', label: 'Chat + Memory', icon: MessageSquare },
  { href: '/benchmarks', label: 'Benchmarks', icon: BarChart3 },
  { href: '/admin', label: 'Admin', icon: Shield },
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
    el.style.setProperty('--mx', `${(x * 100).toFixed(2)}%`);
    el.style.setProperty('--my', `${(y * 100).toFixed(2)}%`);
  }, []);
}

export function SidebarNav({ showBrand = true }: { showBrand?: boolean }) {
  const pathname = usePathname();
  const onMove = useGlowVars();

  const isActive = useCallback(
    (href: string) => {
      return pathname === href || pathname.startsWith(`${href}/`);
    },
    [pathname],
  );

  const activeHref = useMemo(() => {
    const candidates = NAV_ITEMS.filter((i) => isActive(i.href)).sort(
      (a, b) => b.href.length - a.href.length,
    );
    return candidates[0]?.href ?? '';
  }, [isActive]);

  return (
    <div className="w-full">
      {/* BRAND (optional) */}
      {showBrand ? (
        <div className="mb-4 rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-4">
          <div className="flex items-center gap-3">
            <Logo size="small" className="rounded-xl" />
            <div>
              <div className="text-white font-semibold leading-tight">FAIM Lab</div>
              <div className="text-white/60 text-xs leading-tight">
                Fractal Antisymmetric Inheritance Memory
              </div>
            </div>
          </div>

          <div className="mt-3 text-[11px] tracking-wide text-white/40">
            FIG · Antisym · Evolution · CR · R · Drift
          </div>
        </div>
      ) : null}

      {/* NAV */}
      <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-2">
        <nav className="space-y-2 text-sm">
          {NAV_ITEMS.map((item) => {
            const active = item.href === activeHref;
            const Icon = item.icon;

            return (
              <Link
                key={item.href}
                href={item.href}
                onMouseMove={onMove}
                className={[
                  'group relative flex items-center gap-3 rounded-xl px-5 py-2.5',
                  'transition-all duration-300 ease-out',
                  'border border-transparent',
                  active
                    ? 'bg-cyan-500/10 text-cyan-100 border-cyan-400/30 shadow-[0_0_0_1px_rgba(34,211,238,0.18),0_0_18px_rgba(34,211,238,0.10)]'
                    : 'text-slate-300 hover:text-white hover:border-white/10 hover:bg-white/5',
                ].join(' ')}
                style={{
                  backgroundImage: active
                    ? undefined
                    : 'radial-gradient(240px 140px at var(--mx, 50%) var(--my, 50%), rgba(34,211,238,0.16), transparent 60%)',
                }}
              >
                {/* Active rail */}
                <span
                  className={[
                    'absolute left-0 top-1/2 -translate-y-1/2 h-7 w-[3px] rounded-r-full transition-opacity',
                    active
                      ? 'opacity-100 bg-gradient-to-b from-cyan-300/80 to-purple-300/60'
                      : 'opacity-0',
                  ].join(' ')}
                />

                <Icon
                  size={18}
                  className={[
                    'transition-colors',
                    active ? 'text-cyan-200' : 'text-slate-400 group-hover:text-cyan-200',
                  ].join(' ')}
                />

                <span className="flex-1">{item.label}</span>

                {/* Active dot */}
                <span
                  className={[
                    'h-2.5 w-1.5 rounded-full transition-opacity',
                    active ? 'opacity-100 bg-cyan-300' : 'opacity-0 group-hover:opacity-60 bg-white/40',
                  ].join(' ')}
                />
              </Link>
            );
          })}
        </nav>
      </div>
    </div>
  );
}
