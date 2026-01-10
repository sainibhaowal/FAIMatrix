"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import {
  API_BASE_URL,
  DEFAULT_GRAPH_ID,
  fetchHealth,
  buildFaimHeaders,
  GraphSummary,
  fetchGraphsSoft,
  getUniverseIdFromStorage,
  resolveUniverseIdOnce
} from "../../lib/api";
import { CommandPalette } from "./CommandPalette";
import { Breadcrumbs } from "./Breadcrumbs";
import { WorkspaceSelector } from "./topbar/WorkspaceSelector";
import { IconChevron } from "./topbar/IconChevron";
import { Dropdown } from "./topbar/Dropdown";
import { UserDropdownContent } from "./UserDropdownContent";

import { NotificationCenter } from "./NotificationCenter";

// ----------------------------------------------------------------------------
// Local Helpers
// ----------------------------------------------------------------------------

function IconSearch(props: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={props.className} fill="none">
      <path d="M10.5 18a7.5 7.5 0 1 1 0-15 7.5 7.5 0 0 1 0 15Z" stroke="currentColor" strokeWidth="1.5" />
      <path d="M16.5 16.5 21 21" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function IconMenu(props: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={props.className} fill="none">
      <path d="M3 12h18M3 6h18M3 18h18" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function IconSidebar(props: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={props.className} fill="none">
      <rect x="3" y="4" width="18" height="16" rx="2" stroke="currentColor" strokeWidth="1.5" />
      <path d="M9 4v16" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}

function IconGear(props: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={props.className} fill="none">
      <path d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z" stroke="currentColor" strokeWidth="1.5" />
      <path d="M19.4 15a7.94 7.94 0 0 0 .1-1l2-1.2-2-3.5-2.3.6a7.6 7.6 0 0 0-.8-.8l.6-2.3-3.5-2-1.2 2a7.94 7.94 0 0 0-1 0l-1.2-2-3.5 2 .6 2.3c-.28.25-.55.52-.8.8l-2.3-.6-2 3.5 2 1.2a7.94 7.94 0 0 0 0 1l-2 1.2 2 3.5 2.3-.6c.25.28.52.55.8.8l-.6 2.3 3.5 2 1.2-2a7.94 7.94 0 0 0 1 0l1.2 2 3.5-2-.6-2.3c.28-.25.55-.52.8-.8l2.3.6 2-3.5-2-1.2Z" stroke="currentColor" strokeWidth="1.1" strokeLinejoin="round" opacity="0.7" />
    </svg>
  );
}

function IconUser(props: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={props.className} fill="none">
      <path d="M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4Z" stroke="currentColor" strokeWidth="1.5" />
      <path d="M4 21a8 8 0 0 1 16 0" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function cx(...parts: Array<string | false | null | undefined>) {
  return parts.filter(Boolean).join(" ");
}

// Beautiful avatar collection using DiceBear API (same as admin profile page)
const AVATARS = [
  { id: "avatar_01", style: "adventurer", seed: "Felix", bg: "b6e3f4" },
  { id: "avatar_02", style: "adventurer", seed: "Aneka", bg: "c0aede" },
  { id: "avatar_03", style: "adventurer", seed: "Leo", bg: "d1fae5" },
  { id: "avatar_04", style: "adventurer", seed: "Mia", bg: "fde68a" },
  { id: "avatar_05", style: "adventurer-neutral", seed: "Alex", bg: "fecaca" },
  { id: "avatar_06", style: "adventurer-neutral", seed: "Sam", bg: "bfdbfe" },
  { id: "avatar_07", style: "avataaars", seed: "Charlie", bg: "c7d2fe" },
  { id: "avatar_08", style: "avataaars", seed: "Jordan", bg: "fbcfe8" },
  { id: "avatar_09", style: "big-ears", seed: "Riley", bg: "d9f99d" },
  { id: "avatar_10", style: "big-ears", seed: "Casey", bg: "fed7aa" },
  { id: "avatar_11", style: "bottts", seed: "Robot1", bg: "0ea5e9" },
  { id: "avatar_12", style: "bottts", seed: "Robot2", bg: "8b5cf6" },
  { id: "avatar_13", style: "fun-emoji", seed: "Happy", bg: "fbbf24" },
  { id: "avatar_14", style: "fun-emoji", seed: "Cool", bg: "34d399" },
  { id: "avatar_15", style: "lorelei", seed: "Luna", bg: "f9a8d4" },
  { id: "avatar_16", style: "lorelei", seed: "Nova", bg: "a5b4fc" },
  { id: "avatar_17", style: "micah", seed: "Kai", bg: "86efac" },
  { id: "avatar_18", style: "micah", seed: "Sage", bg: "fca5a5" },
  { id: "avatar_19", style: "notionists", seed: "Pro", bg: "e5e7eb" },
  { id: "avatar_20", style: "notionists", seed: "Dev", bg: "fef3c7" },
  { id: "avatar_21", style: "open-peeps", seed: "Tech", bg: "cffafe" },
  { id: "avatar_22", style: "open-peeps", seed: "Art", bg: "fce7f3" },
  { id: "avatar_23", style: "personas", seed: "Zen", bg: "ddd6fe" },
  { id: "avatar_24", style: "personas", seed: "Max", bg: "ccfbf1" },
];

function getAvatarUrl(avatarId: string): string {
  const avatar = AVATARS.find((a) => a.id === avatarId) || AVATARS[0];
  return `https://api.dicebear.com/7.x/${avatar.style}/svg?seed=${avatar.seed}&backgroundColor=${avatar.bg}&size=128`;
}

const LS_UI_DENSITY = "faim.ui.density";
const LS_UI_DEBUG = "faim.ui.debug";
const LS_UNIVERSE_KEY = "faim.universe_graph_id";

export type Health = "ok" | "degraded" | "down" | "unknown";

// ----------------------------------------------------------------------------
// TopBar Component
// ----------------------------------------------------------------------------

export function TopBar({
  graphId,
  setGraphId,
  sidebarCollapsed = false,
  onToggleSidebar,
  onMobileMenuOpen,
}: {
  graphId: string;
  setGraphId: (v: string) => void;
  sidebarCollapsed?: boolean;
  onToggleSidebar?: () => void;
  onMobileMenuOpen?: () => void;
}) {
  const router = useRouter();
  const { data: session } = useSession();

  const goAdmin = (tab?: string) => {
    const t = (tab ?? "").trim();
    router.push(
      !t ? "/dashboard/admin" : `/dashboard/admin?tab=${encodeURIComponent(t)}`,
    );
  };

  // --- Search / CMDK State ---
  const [openCmdk, setOpenCmdk] = useState(false);

  // --- Graph / Workspace State ---
  const [graphs, setGraphs] = useState<GraphSummary[]>([]);
  const [graphsLoaded, setGraphsLoaded] = useState(false);

  // --- Health State ---
  const [health, setHealth] = useState<Health>("unknown");
  const [version, setVersion] = useState<string | null>(null);
  const [healthAt, setHealthAt] = useState<string | null>(null);
  const [gpu, setGpu] = useState<{
    enabled?: boolean;
    available?: boolean;
    device?: string;
    mem_free_bytes?: number | null;
    mem_total_bytes?: number | null;
  } | null>(null);

  // --- UI State ---
  const [openSettings, setOpenSettings] = useState(false);
  const [openUser, setOpenUser] = useState(false);
  const [openHealth, setOpenHealth] = useState(false);
  
  // --- Avatar State ---
  const [avatarId, setAvatarId] = useState<string | null>(null);

  const [density, setDensity] = useState<"comfortable" | "compact">(() => {
    if (typeof window === "undefined") return "comfortable";
    return (window.localStorage.getItem(LS_UI_DENSITY) as any) || "comfortable";
  });
  const [debugUi, setDebugUi] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    return window.localStorage.getItem(LS_UI_DEBUG) === "1";
  });

  // --- Refs ---
  const settingsRef = useRef<HTMLButtonElement>(null);
  const userRef = useRef<HTMLButtonElement>(null);
  const healthRef = useRef<HTMLButtonElement>(null);

  // --- Fetch Avatar (DiceBear) ---
  useEffect(() => {
    if (!session) return;
    const loadProfile = async () => {
      try {
        const token = (session as any)?.accessToken;
        if (!token) return;
        const res = await fetch("/api/v1/me", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          if (data.avatar_id) setAvatarId(data.avatar_id);
        }
      } catch {}
    };
    loadProfile();
  }, [session]);

  // --- Universe Preference ---
  const [mounted, setMounted] = useState(false);
  const [universeGraphId, setUniverseGraphId] = useState<string>("");

  useEffect(() => {
    setMounted(true);
    const read = () => {
      const u = getUniverseIdFromStorage();
      setUniverseGraphId(u ?? "");
    };
    read();
    const onStorage = (e: StorageEvent) => {
      if (e.key === LS_UNIVERSE_KEY) read();
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const effectiveGraphId = mounted && universeGraphId ? universeGraphId : graphId;

  // Poll Health
  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const h = await fetchHealth();
        if (cancelled) return;
        setHealth(h.status);
        setVersion(h.version ?? null);
        setGpu(h.gpu ?? null);
        setHealthAt(new Date().toISOString());
      } catch {
        if (!cancelled) {
          setHealth("down");
          setHealthAt(new Date().toISOString());
        }
      }
    };
    void tick();
    const id = window.setInterval(tick, 15000);
    return () => {
        cancelled = true;
        clearInterval(id);
    };
  }, []);

  // UI Prefs persistence
  useEffect(() => {
    try {
      window.localStorage.setItem(LS_UI_DENSITY, density);
      window.localStorage.setItem(LS_UI_DEBUG, debugUi ? "1" : "0");
    } catch {}
  }, [density, debugUi]);


  // Load Graphs
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const remote = await fetchGraphsSoft();
      if (cancelled) return;

      if (remote.length > 0) {
        setGraphs(remote);
        setGraphsLoaded(true);
        return;
      }

      // Fallback
      const universe = getUniverseIdFromStorage() ?? (await resolveUniverseIdOnce());
      if (!cancelled && universe) setUniverseGraphId(universe);

      const idToShow = universe ?? (effectiveGraphId.startsWith("U:") ? effectiveGraphId : "U:(resolving)");
      setGraphs([{ id: idToShow, name: "Universe" }]);
      setGraphsLoaded(true);
    })();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Keyboard Shortcuts (Cmd+K)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpenCmdk(true);
        setOpenSettings(false);
        setOpenUser(false);
        setOpenHealth(false);
      }
      if (e.key === "Escape") {
         setOpenCmdk(false);
         setOpenSettings(false);
         setOpenUser(false);
         setOpenHealth(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const currentGraph = useMemo(() => {
    return graphs.find((g) => g.id === effectiveGraphId) ?? { id: effectiveGraphId, name: "Workspace" };
  }, [graphs, effectiveGraphId]);

  const healthLabel = health === "ok" ? "FAIM Core: OK" : health === "degraded" ? "FAIM Core: Degraded" : health === "down" ? "FAIM Core: DOWN" : "FAIM Core: …";
  const healthClass = health === "ok" ? "bg-emerald-500/12 text-emerald-300 border-emerald-500/30" : health === "degraded" ? "bg-amber-500/12 text-amber-300 border-amber-500/30" : health === "down" ? "bg-rose-500/12 text-rose-300 border-rose-500/30" : "bg-slate-700/25 text-slate-200 border-slate-500/25";
  
  const gpuActive = !!(gpu?.enabled && gpu?.available);
  const gpuLabel = gpuActive ? "GPU active" : gpu?.enabled ? "GPU enabled (no CUDA)" : "GPU off";

  const formatBytes = (value?: number | null) => {
    if (!value || value <= 0) return "—";
    const units = ["B", "KB", "MB", "GB", "TB"];
    let idx = 0;
    let v = value;
    while (v >= 1024 && idx < units.length - 1) {
      v /= 1024;
      idx += 1;
    }
    return `${v.toFixed(v >= 10 ? 1 : 2)} ${units[idx]}`;
  };

  return (
    <>
      <header className="relative z-20 border-b border-white/10 bg-white/5 px-6 py-3 backdrop-blur">
        <div className="flex items-center justify-between gap-3">
          {/* LEFT: Sidebar Toggle & Workspace & Breadcrumbs */}
          <div className="relative flex min-w-0 items-center gap-3 flex-1">
            {/* Collapse Button (Desktop) */}
            {onToggleSidebar && (
              <button
                onClick={onToggleSidebar}
                className="hidden md:flex rounded-xl border border-white/10 bg-black/20 p-2 hover:border-white/15 hover:bg-white/5 transition-colors"
                title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
              >
                <IconSidebar className="h-4 w-4 text-slate-300" />
              </button>
            )}
            
            {/* Mobile Menu Trigger */}
            <button
              onClick={onMobileMenuOpen}
              className="md:hidden rounded-xl border border-white/10 bg-black/20 p-2 hover:border-white/15 hover:bg-white/5"
              title="Open menu"
            >
              <IconMenu className="h-4 w-4 text-slate-300" />
            </button>

            {/* Workspace Selector */}
            <WorkspaceSelector 
              graphId={graphId}
              setGraphId={setGraphId}
              graphs={graphs}
              graphsLoaded={graphsLoaded}
              setGraphs={setGraphs}
              currentGraphName={currentGraph.name}
            />

            {/* Separator */}
            <div className="hidden md:block h-4 w-px bg-white/10 mx-1" />

            {/* Breadcrumbs */}
            <Breadcrumbs />
          </div>

          {/* RIGHT: Search, Health, Profile */}
          <div className="flex items-center gap-3">
            {/* Search Trigger */}
            <button
              onClick={() => setOpenCmdk(true)}
              className="hidden md:flex items-center gap-2 rounded-xl border border-white/10 bg-black/20 py-1.5 pl-2.5 pr-1.5 hover:border-white/20 hover:bg-white/5 transition-colors group"
            >
              <IconSearch className="h-3.5 w-3.5 text-slate-400 group-hover:text-slate-300" />
              <span className="text-xs text-slate-500 group-hover:text-slate-400">Search...</span>
              <kbd className="hidden lg:inline-flex items-center gap-1 rounded border border-white/10 bg-white/5 px-1.5 font-mono text-[10px] text-slate-500">
                <span className="text-xs">⌘</span>K
              </kbd>
            </button>
            <button
               onClick={() => setOpenCmdk(true)}
               className="md:hidden p-2 text-slate-400 hover:text-white"
            >
               <IconSearch className="h-5 w-5" />
            </button>

             {/* Settings */}
             <div className="relative">
              <button
                ref={settingsRef}
                onClick={() => {
                  setOpenSettings((v) => !v);
                  setOpenUser(false);
                  setOpenHealth(false);
                }}
                className="hidden md:flex rounded-xl border border-white/10 bg-black/20 p-2 hover:border-white/15 hover:bg-white/5"
                title="Settings"
              >
                <IconGear className="h-4 w-4 text-slate-300" />
              </button>

              <Dropdown
                open={openSettings}
                anchorRef={settingsRef}
                onClose={() => setOpenSettings(false)}
              >
                <div className="p-3">
                  <div className="mb-2 text-[11px] font-semibold text-slate-200">
                    Quick settings
                  </div>

                  <div className="space-y-2 rounded-xl border border-white/10 p-3">
                    <div className="flex items-center justify-between">
                      <div className="text-[11px] text-slate-300">
                        UI density
                      </div>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => setDensity("comfortable")}
                          className={cx(
                            "rounded-lg border px-2 py-1 text-[10px]",
                            density === "comfortable"
                              ? "border-cyan-500/30 bg-cyan-500/10 text-cyan-200"
                              : "border-white/10 bg-white/5 text-slate-200 hover:bg-white/10",
                          )}
                        >
                          Comfortable
                        </button>
                        <button
                          onClick={() => setDensity("compact")}
                          className={cx(
                            "rounded-lg border px-2 py-1 text-[10px]",
                            density === "compact"
                              ? "border-cyan-500/30 bg-cyan-500/10 text-cyan-200"
                              : "border-white/10 bg-white/5 text-slate-200 hover:bg-white/10",
                          )}
                        >
                          Compact
                        </button>
                      </div>
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="text-[11px] text-slate-300">Debug UI</div>
                      <button
                        onClick={() => setDebugUi((v) => !v)}
                        className={cx(
                          "rounded-lg border px-2 py-1 text-[10px]",
                          debugUi
                            ? "border-violet-500/30 bg-violet-500/10 text-violet-200"
                            : "border-white/10 bg-white/5 text-slate-200 hover:bg-white/10",
                        )}
                      >
                        {debugUi ? "ON" : "OFF"}
                      </button>
                    </div>

                    <div className="text-[10px] text-slate-500">
                      Cmd/Ctrl+K: Search · ESC: close menus
                    </div>
                  </div>

                  <div className="mt-2 grid grid-cols-2 gap-2">
                    <button
                      onClick={() => {
                        setOpenSettings(false);
                        goAdmin("account");
                      }}
                      className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-[11px] text-slate-200 hover:bg-white/10"
                    >
                      Open Settings
                    </button>
                    <button
                      onClick={() => {
                        setOpenSettings(false);
                        goAdmin();
                      }}
                      className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-[11px] text-slate-200 hover:bg-white/10"
                    >
                      Admin
                    </button>
                  </div>
                </div>
              </Dropdown>
            </div>

            {/* Health Status */}
            <div className="relative">
              <button
                ref={healthRef}
                 onClick={() => {
                  setOpenHealth((v) => !v);
                  setOpenSettings(false);
                  setOpenUser(false);
                }}
                className={cx(
                  "hidden md:flex items-center gap-2 rounded-full border px-3 py-2 text-xs",
                  healthClass,
                )}
                title="FAIM backend health"
              >
                  <span className="h-2 w-2 rounded-full bg-current" />
                  <span>{healthLabel}</span>
                  {version && (
                    <span className="hidden text-[10px] text-slate-300/60 sm:inline">
                      v{version}
                    </span>
                  )}
                  {gpuActive && (
                    <span className="rounded-full border border-sky-400/30 bg-sky-500/10 px-2 py-0.5 text-[10px] text-sky-100">
                      GPU active
                    </span>
                  )}
              </button>

               <Dropdown
                open={openHealth}
                anchorRef={healthRef}
                onClose={() => setOpenHealth(false)}
                className="w-[340px]"
              >
                <div className="p-3">
                  <div className="text-[11px] font-semibold text-slate-200">
                    System status
                  </div>
                  <div className="mt-2 rounded-xl border border-white/10 p-3 text-[11px] text-slate-300">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400">Status</span>
                      <span className="font-medium text-slate-100">
                        {health}
                      </span>
                    </div>
                    <div className="mt-1 flex items-center justify-between">
                      <span className="text-slate-400">Version</span>
                      <span className="font-medium text-slate-100">
                        {version ?? "—"}
                      </span>
                    </div>
                    <div className="mt-1 flex items-center justify-between">
                      <span className="text-slate-400">Last check</span>
                      <span className="font-medium text-slate-100">
                        {healthAt
                          ? new Date(healthAt).toLocaleTimeString()
                          : "—"}
                      </span>
                    </div>
                    <div className="mt-1 flex items-center justify-between">
                      <span className="text-slate-400">GPU</span>
                      <span className="font-medium text-slate-100">
                        {gpuLabel}
                      </span>
                    </div>
                    {gpu?.device && (
                      <div className="mt-1 flex items-center justify-between">
                        <span className="text-slate-400">GPU device</span>
                        <span className="font-medium text-slate-100">
                          {gpu.device}
                        </span>
                      </div>
                    )}
                    {gpu?.mem_total_bytes ? (
                       <div className="mt-1 flex items-center justify-between">
                        <span className="text-slate-400">GPU memory</span>
                        <span className="font-medium text-slate-100">
                          {formatBytes(gpu.mem_free_bytes)} free /{" "}
                          {formatBytes(gpu.mem_total_bytes)}
                        </span>
                      </div>
                    ) : null}
                  </div>
                  
                  <div className="mt-2 grid grid-cols-2 gap-2">
                    <button
                      onClick={() => {
                        setOpenHealth(false);
                        router.push("/dashboard");
                      }}
                      className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-[11px] text-slate-200 hover:bg-white/10"
                    >
                      Open Dashboard
                    </button>
                    <button
                      onClick={() => {
                        setOpenHealth(false);
                        router.push("/dashboard");
                      }}
                      className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-[11px] text-slate-200 hover:bg-white/10"
                    >
                      Runtime panel
                    </button>
                  </div>
                </div>
              </Dropdown>
            </div>

            {/* Notification Bell */}
             <NotificationCenter />

            {/* User Profile (Simplified) */}
             <div className="relative">
               <button
                 ref={userRef}
                 onClick={() => {
                    setOpenUser((v) => !v);
                    setOpenSettings(false);
                    setOpenHealth(false);
                 }}
                 className="h-8 w-8 rounded-full bg-gradient-to-br from-cyan-500/20 to-purple-500/20 border border-white/10 flex items-center justify-center text-xs font-medium text-white/80 hover:border-white/20 transition-colors overflow-hidden"
               >
                  {avatarId || session?.user?.image ? (
                    <img 
                      src={avatarId ? getAvatarUrl(avatarId) : session!.user!.image!} 
                      alt={session?.user?.name || "User"} 
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    session?.user?.name?.[0] ?? "U"
                  )}
               </button>
               
               <Dropdown
                 open={openUser}
                 anchorRef={userRef}
                 onClose={() => setOpenUser(false)}
               >
                 <UserDropdownContent
                   goAdmin={goAdmin}
                   onClose={() => setOpenUser(false)}
                 />
               </Dropdown>
             </div>
          </div>
        </div>
      </header>

      {/* Command Palette Modal */}
      <CommandPalette
        open={openCmdk}
        onClose={() => setOpenCmdk(false)}
        graphId={effectiveGraphId}
      />
    </>
  );
}
