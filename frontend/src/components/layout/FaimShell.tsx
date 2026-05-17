// ============================================================================
// FAIMATRIX — GOLDEN EDITION SHELL
// File: src/components/shell/FaimShell.tsx
//
// Purpose
// - Owns the selected Universe (graph_id) and persists it to localStorage.
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
// - TopBar: header control plane (universe/search/settings/profile/health)
// - Logo: branding identity
// ============================================================================

"use client";

import React, { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { SidebarNav } from "@/components/layout/Sidebar/SidebarNav";
import { TopBar } from "./TopBar/TopBar";
import Logo from "@/components/brand/Logo";
import { DEFAULT_GRAPH_ID } from "@/lib/api-client";

// ----------------------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------------------

function clamp01(v: number): number {
  return Math.max(0, Math.min(1, v));
}

const LS_GRAPH_KEY = "faim.selected_graph_id";
const LS_UNIVERSE_KEY = "faim.universe_graph_id"; // must match what you store on SSE contract
const LS_SIDEBAR_KEY = "faim.ui.sidebar_collapsed";

// ----------------------------------------------------------------------------
// Component: FaimShell
// ----------------------------------------------------------------------------
// Title: App Shell + Universe persistence + global cursor-follow effect
// ----------------------------------------------------------------------------

export function FaimShell({ children }: { children: React.ReactNode }) {
  // --------------------------------------------------------------------------
  // Section: Universe (graph_id) state
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
    if (typeof window === "undefined") return false;
    try {
      return window.localStorage.getItem(LS_SIDEBAR_KEY) === "1";
    } catch {
      return false;
    }
  });

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const pathname = usePathname();
  const isControlPlane = pathname.startsWith("/dashboard/control-plane");

  // Close mobile menu on route change
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [pathname]);

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
      window.localStorage.setItem(LS_SIDEBAR_KEY, sidebarCollapsed ? "1" : "0");
    } catch {
      // ignore
    }
  }, [sidebarCollapsed]);

  // Keyboard shortcuts
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      // Cmd+B or Cmd+\ to toggle sidebar
      if (
        (e.metaKey || e.ctrlKey) &&
        (e.key.toLowerCase() === "b" || e.key === "\\")
      ) {
        e.preventDefault();
        setSidebarCollapsed((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

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
      root.style.setProperty("--cx", `${(x * 100).toFixed(2)}%`);
      root.style.setProperty("--cy", `${(y * 100).toFixed(2)}%`);
    };

    const onMouseMove = (e: MouseEvent) => update(e.clientX, e.clientY);
    const onTouchMove = (e: TouchEvent) => {
      if (!e.touches || e.touches.length === 0) return;
      update(e.touches[0]!.clientX, e.touches[0]!.clientY);
    };

    window.addEventListener("mousemove", onMouseMove, { passive: true });
    window.addEventListener("touchmove", onTouchMove, { passive: true });

    // Initial position (pleasant default for first render)
    update(window.innerWidth * 0.55, window.innerHeight * 0.3);

    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("touchmove", onTouchMove);
    };
  }, []);

  // --------------------------------------------------------------------------
  // Render: Shell Layout (OmniSync Theme)
  // --------------------------------------------------------------------------

  return (
    <div className="relative flex h-screen overflow-hidden bg-[var(--os-bg)] text-[var(--foreground)]">
      {/* -------------------------------------------------------------------- */}
      {/* Global Background Layer (OmniGlow)                                    */}
      {/* -------------------------------------------------------------------- */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        {/* Grid Overlay */}
        <div className="faim-grid opacity-20" />
      </div>

      {/* -------------------------------------------------------------------- */}
      {/* Left Sidebar                                                         */}
      {/* -------------------------------------------------------------------- */}
      <aside
        className={[
          "relative z-20 hidden h-screen flex-col md:flex border-r border-white/10 sticky top-0 overflow-hidden",
          "transition-[width] duration-300 ease-out",
          sidebarCollapsed ? "w-[70px]" : "w-[270px]",
        ].join(" ")}
      >
        <div
          className={[
            "flex h-full flex-col bg-[var(--os-surface-1)] backdrop-blur-sm",
            sidebarCollapsed ? "items-center" : "",
          ].join(" ")}
        >
          {/* Unified Branding Header */}
          <div
            className={[
              "px-4 pt-6 pb-4 transition-all duration-300",
              sidebarCollapsed
                ? "flex flex-col items-center"
                : "flex items-center gap-3",
            ].join(" ")}
          >
            <Logo
              px={sidebarCollapsed ? 44 : 38}
              className="transition-all duration-500"
            />
            {!sidebarCollapsed && (
              <div className="animate-in fade-in slide-in-from-left-2 duration-700 flex flex-col">
                {/* FAIMATRIX Title - Split Color */}
                <div className="text-lg uppercase tracking-[0.3em] font-black leading-none mb-1.5">
                  <span className="text-primary-300">FAIM</span>
                  <span className="text-secondary-400">ATRIX</span>
                </div>

                {/* Tagline */}
                <div className="text-[10px] uppercase tracking-[0.15em] text-slate-500 font-semibold leading-tight">
                  Fractal Intelligence Core
                </div>
              </div>
            )}
          </div>

          {/* Navigation */}
          <div
            className={[
              "mt-4 overflow-y-auto flex-1",
              sidebarCollapsed ? "px-2" : "px-4",
            ].join(" ")}
          >
            <SidebarNav showBrand={false} collapsed={sidebarCollapsed} />
          </div>

          {/* Footer note */}
          {!sidebarCollapsed && (
            <div className="mt-auto px-4 pb-6 pt-6 text-[10px] text-white/40">
              <div>Fractal antisymmetric memory engine.</div>
              <div>Exclusively powered by FAIMATRIX.</div>
            </div>
          )}
        </div>
      </aside>

      {/* -------------------------------------------------------------------- */}
      {/* Right Content                                                        */}
      {/* -------------------------------------------------------------------- */}
      <div className="relative z-10 flex min-w-0 flex-1 flex-col">
        {/* Top Bar: universe/search/settings/user/health */}
        <TopBar
          graphId={graphId}
          setGraphId={setGraphId}
          sidebarCollapsed={sidebarCollapsed}
          onToggleSidebar={() => setSidebarCollapsed((v) => !v)}
          onMobileMenuOpen={() => setMobileMenuOpen(true)}
        />

        {/* Page body */}
        <main
          className={[
            "flex-1",
            pathname === "/dashboard/graph" ||
            pathname === "/dashboard/memory-query"
              ? "overflow-hidden p-0"
              : isControlPlane
                ? "overflow-y-auto px-2 py-4 md:px-4 lg:px-6"
                : "overflow-y-auto px-4 py-6 md:px-6",
          ].join(" ")}
        >
          <div
            className={
              pathname === "/dashboard/graph" ||
              pathname === "/dashboard/memory-query"
                ? "h-full"
                : isControlPlane
                  ? "w-full max-w-none"
                  : "mx-auto max-w-[1400px]"
            }
          >
            {children}
          </div>
        </main>
      </div>

      {/* -------------------------------------------------------------------- */}
      {/* Mobile Drawer                                                        */}
      {/* -------------------------------------------------------------------- */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 flex md:hidden">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-[fadeIn_0.2s_ease-out]"
            onClick={() => setMobileMenuOpen(false)}
          />

          {/* Drawer Panel */}
          <div className="relative w-[280px] h-full bg-[var(--os-surface-1)] border-r border-white/10 shadow-2xl animate-[slideIn_0.3s_cubic-bezier(0.16,1,0.3,1)]">
            <div className="flex h-full flex-col">
              {/* Header */}
              <div className="px-4 pt-4 pb-2 border-b border-white/5">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <Logo px={32} />
                    <span className="text-[13px] uppercase tracking-[0.3em] font-black">
                      <span className="text-cyan-300">FAIM</span>
                      <span className="text-violet-400">ATRIX</span>
                    </span>
                  </div>
                  <button
                    onClick={() => setMobileMenuOpen(false)}
                    className="p-2 text-slate-400 hover:text-white"
                  >
                    <svg
                      width="20"
                      height="20"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      <path d="M18 6L6 18M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>

              {/* Nav */}
              <div className="flex-1 overflow-y-auto py-4">
                <SidebarNav showBrand={false} />
              </div>

              {/* Footer */}
              <div className="px-4 py-4 border-t border-white/5 text-[10px] text-zinc-500">
                FAIMATRIX Mobile
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
