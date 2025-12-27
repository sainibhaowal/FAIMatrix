// ============================================================================
// FAIM LAB — GOLDEN EDITION SHELL
// File: src/components/shell/FaimShell.tsx
//
// Purpose
// - Owns the selected Workspace (graph_id) and persists it to localStorage.
// - Applies global cursor-follow spotlight variables (--cx, --cy) for the UI.
// - Renders the stable App Shell: Sidebar + TopBar + Main content area.
//
// Safety
// - No backend writes here. Only local UI state and CSS vars.
// - Fail-soft localStorage operations.
// - Deterministic event wiring and cleanup.
//
// Dependencies
// - SidebarNav: left navigation
// - TopBar: header control plane (workspace/search/settings/profile/health)
// - FaimHeader + Logo: brand blocks
// ============================================================================

'use client';

import React, { useEffect, useState } from 'react';
import { SidebarNav } from './SidebarNav';
import { TopBar } from './TopBar';
import { FaimHeader } from '../FaimHeader';
import Logo from '../brand/Logo';
import { DEFAULT_GRAPH_ID } from '../../lib/api';

// ----------------------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------------------

function clamp01(v: number): number {
  return Math.max(0, Math.min(1, v));
}

const LS_GRAPH_KEY = 'faim.selected_graph_id';
const LS_UNIVERSE_KEY = 'faim.universe_graph_id'; // must match what you store on SSE contract
const LS_SIDEBAR_KEY = 'faim.ui.sidebar_collapsed';

// ----------------------------------------------------------------------------
// Component: FaimShell
// ----------------------------------------------------------------------------
// Title: App Shell + Workspace persistence + global cursor-follow effect
// ----------------------------------------------------------------------------

export function FaimShell({ children }: { children: React.ReactNode }) {
  // --------------------------------------------------------------------------
  // Section: Workspace (graph_id) state
  // --------------------------------------------------------------------------

  const [graphId, setGraphId] = useState<string>(() => {
    if (typeof window === "undefined") return DEFAULT_GRAPH_ID;

    const universe = window.localStorage.getItem(LS_UNIVERSE_KEY) || "";
    if (universe.startsWith("U:")) return universe;

    const selected = window.localStorage.getItem(LS_GRAPH_KEY) || "";
    if (selected.trim()) return selected.trim();
  
    return DEFAULT_GRAPH_ID;
  });

  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    try {
      return window.localStorage.getItem(LS_SIDEBAR_KEY) === '1';
    } catch {
      return false;
    }
  });

useEffect(() => {
  if (typeof window === "undefined") return;
  if (!graphId) return;

  // Only persist if it's a real Universe graph id
  if (graphId.startsWith("U:")) {
    window.localStorage.setItem(LS_GRAPH_KEY, graphId);
    window.localStorage.setItem(LS_UNIVERSE_KEY, graphId);
  }

}, [graphId]);

  useEffect(() => {
    try {
      window.localStorage.setItem(LS_SIDEBAR_KEY, sidebarCollapsed ? '1' : '0');
    } catch {
      // ignore
    }
  }, [sidebarCollapsed]);

  // --------------------------------------------------------------------------
  // Section: Global cursor-follow effect
  // - Updates CSS vars: --cx, --cy
  // - Used by .faim-bg / .faim-grid or any other global glow layers
  // --------------------------------------------------------------------------

  useEffect(() => {
    const root = document.documentElement;

    const update = (clientX: number, clientY: number) => {
      const w = Math.max(window.innerWidth, 1);
      const h = Math.max(window.innerHeight, 1);
      const x = clamp01(clientX / w);
      const y = clamp01(clientY / h);
      root.style.setProperty('--cx', `${(x * 100).toFixed(2)}%`);
      root.style.setProperty('--cy', `${(y * 100).toFixed(2)}%`);
    };

    const onMouseMove = (e: MouseEvent) => update(e.clientX, e.clientY);
    const onTouchMove = (e: TouchEvent) => {
      if (!e.touches || e.touches.length === 0) return;
      update(e.touches[0]!.clientX, e.touches[0]!.clientY);
    };

    window.addEventListener('mousemove', onMouseMove, { passive: true });
    window.addEventListener('touchmove', onTouchMove, { passive: true });

    // Initial position (pleasant default for first render)
    update(window.innerWidth * 0.55, window.innerHeight * 0.3);

    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('touchmove', onTouchMove);
    };
  }, []);

  // --------------------------------------------------------------------------
  // Render: Shell Layout
  // --------------------------------------------------------------------------
  // Structure:
  //  - Global background (cursor-follow)
  //  - Left sidebar (sticky, scrollable nav)
  //  - Right content (TopBar + page content)
  // --------------------------------------------------------------------------

  return (
    <div className="relative flex h-screen overflow-hidden bg-[#050b14] text-slate-100">
      {/* -------------------------------------------------------------------- */}
      {/* Global Background Layer (cursor-follow)                               */}
      {/* -------------------------------------------------------------------- */}
      <div className="faim-bg" aria-hidden="true">
        <div className="faim-grid" />
      </div>

      {/* -------------------------------------------------------------------- */}
      {/* Left Sidebar                                                         */}
      {/* -------------------------------------------------------------------- */}
      <aside
        className={[
          'relative z-20 hidden h-screen flex-col md:flex faim-divider sticky top-0 overflow-hidden',
          'transition-[width] duration-200',
          sidebarCollapsed ? 'w-0' : 'w-72',
        ].join(' ')}
      >
        <div
          className={[
            'flex h-full flex-col transition-opacity duration-200',
            sidebarCollapsed ? 'opacity-0 pointer-events-none' : 'opacity-100',
          ].join(' ')}
        >
          {/* Branding block: Logo + Header */}
          <div className="px-4 pt-4">
            <div className="faim-surface rounded-2xl p-2">
              <div className="-mt-4 flex items-center justify-center">
                <Logo px={220} className="rounded-2xl" />
              </div>
              <div className="mt-5">
                <FaimHeader />
              </div>
            </div>
          </div>

          {/* Navigation (brand removed to avoid duplication) */}
          <div className="mt-4 overflow-y-auto px-4">
            <SidebarNav showBrand={false} />
          </div>

          {/* Footer note */}
          <div className="mt-auto px-4 pb-6 pt-6 text-[10px] text-slate-400/70">
            <div>Fractal antisymmetric memory engine.</div>
            <div>Built by you; this UI is just the lab window.</div>
          </div>
        </div>
      </aside>

      {/* -------------------------------------------------------------------- */}
      {/* Right Content                                                        */}
      {/* -------------------------------------------------------------------- */}
      <div className="relative z-10 flex min-w-0 flex-1 flex-col">
        {/* Top Bar: workspace/search/settings/user/health */}
        <TopBar
          graphId={graphId}
          setGraphId={setGraphId}
          sidebarCollapsed={sidebarCollapsed}
          onToggleSidebar={() => setSidebarCollapsed((v) => !v)}
        />

        {/* Page body */}
        <main className="flex-1 overflow-y-auto px-4 py-6 md:px-6">
          <div className="faim-panel rounded-2xl p-4 md:p-3">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
