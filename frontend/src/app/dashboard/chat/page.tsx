// src/app/chat/page.tsx
"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { DEFAULT_GRAPH_ID, postChat } from "@/lib/api";
import { ContextSidebar } from "@/components/ContextSidebar";
import type { UsedNodeSummary as ApiUsedNodeSummary } from "@/lib/api";
import type { UsedNodeSummary as RtUsedNodeSummary } from "@/lib/realtime";
import { useChatStore } from "@/state/chatStore";

/* ============================================================================
   Helpers (UI-only)
============================================================================ */

function clamp01(x: number) {
  return Math.max(0, Math.min(1, x));
}

function shortId(s: string) {
  return s.length <= 10 ? s : `${s.slice(0, 6)}…${s.slice(-2)}`;
}

function dayKey(ts: number) {
  const d = new Date(ts);
  return `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}`;
}

function daysAgo(ts: number) {
  const now = Date.now();
  return Math.floor((now - ts) / (24 * 60 * 60 * 1000));
}

/* ============================================================================
   UI atoms
============================================================================ */
const LS_UNIVERSE_KEY = "faim.universe_graph_id";
const SPOT_SIZE = 240;
const SPOT_GAIN = 0.1;
const SPOT_FADE = 64;

function GlowPanel({
  children,
  className = "",
  intensity = 0.26,
}: {
  children: React.ReactNode;
  className?: string;
  intensity?: number;
}) {
  const o = String(clamp01(intensity));

  return (
    <div
      onMouseMove={(e) => {
        const el = e.currentTarget as HTMLDivElement;
        const r = el.getBoundingClientRect();
        const x = ((e.clientX - r.left) / r.width) * 100;
        const y = ((e.clientY - r.top) / r.height) * 100;
        el.style.setProperty("--gx", `${x.toFixed(2)}%`);
        el.style.setProperty("--gy", `${y.toFixed(2)}%`);
      }}
      style={
        {
          ["--gx" as any]: "50%",
          ["--gy" as any]: "50%",
          ["--go" as any]: o,
        } as React.CSSProperties
      }
      className={[
        "relative overflow-hidden rounded-2xl border",
        "border-cyan-300/10 bg-slate-950/55",
        "shadow-[0_0_0_1px_rgba(34,211,238,0.10),0_0_30px_rgba(34,211,238,0.05)]",
        "before:absolute before:inset-0 before:pointer-events-none",
        "before:bg-[linear-gradient(180deg,rgba(34,211,238,0.10),transparent_45%,transparent)]",
        "after:absolute after:inset-0 after:pointer-events-none",
        `after:bg-[radial-gradient(${SPOT_SIZE}px_circle_at_var(--gx)_var(--gy),rgba(34,211,238,calc(var(--go)*${SPOT_GAIN})),transparent_${SPOT_FADE}%)]`,
        className,
      ].join(" ")}
    >
      <div className="pointer-events-none absolute inset-0 rounded-2xl border border-cyan-400/10" />
      <div className="relative h-full min-h-0">{children}</div>
    </div>
  );
}

function IconButton({
  title,
  active,
  onClick,
  children,
  className = "",
}: {
  title: string;
  active?: boolean;
  onClick?: () => void;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <button
      type="button"
      title={title}
      onClick={onClick}
      className={[
        "inline-flex h-9 w-9 items-center justify-center rounded-lg border",
        active
          ? "border-cyan-400/35 bg-cyan-500/10"
          : "border-slate-800/70 bg-slate-950/50",
        "text-slate-200 hover:border-cyan-400/25 hover:bg-cyan-500/5",
        "transition-all duration-150 active:scale-[0.98]",
        className,
      ].join(" ")}
    >
      {children}
    </button>
  );
}

function ModelSelectPlaceholder() {
  return (
    <div className="flex items-center gap-2">
      <div className="text-[11px] font-semibold tracking-widest text-slate-500">
        MODEL
      </div>
      <div
        className="flex h-9 items-center gap-2 rounded-xl border border-slate-800/70 bg-slate-950/40 px-3 text-xs text-slate-500"
        title="No models wired yet"
      >
        <span className="h-2 w-2 rounded-full bg-slate-600/60" />
        <span className="select-none">No model</span>
        <span className="ml-2 select-none text-[10px] text-slate-600">
          (coming soon)
        </span>
      </div>
    </div>
  );
}

/* ============================================================================
   Context Drawer (slide from right)
============================================================================ */

function ContextDrawer({
  open,
  onClose,
  children,
}: {
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <>
      <div
        className={[
          "fixed inset-0 z-40 overflow-x-clip",
          open ? "pointer-events-auto" : "pointer-events-none",
        ].join(" ")}
        aria-hidden={!open}
      >
        <div
          className={[
            "absolute inset-0",
            "transition-opacity duration-300 ease-[cubic-bezier(.2,.8,.2,1)]",
            open ? "opacity-100" : "opacity-0",
          ].join(" ")}
          onClick={open ? onClose : undefined}
        >
          <div className="absolute inset-0 bg-black/45" />
        </div>

        <aside
          className={[
            "absolute right-0 top-0 h-full w-[420px] max-w-[92vw]",
            "transform-gpu will-change-transform will-change-opacity",
            "transition-[transform,opacity] duration-300 ease-[cubic-bezier(.2,.8,.2,1)]",
            open ? "translate-x-0 opacity-100" : "translate-x-[110%] opacity-0",
          ].join(" ")}
        >
          <div
            className={[
              "h-full p-4 rounded-2xl overflow-hidden",
              "transition-opacity duration-300 ease-[cubic-bezier(.2,.8,.2,1)]",
              open ? "opacity-100" : "opacity-0",
            ].join(" ")}
          >
            <GlowPanel className="h-full p-0">
              <div className="flex h-full min-h-0 flex-col">
                <div className="flex items-center justify-between border-b border-cyan-300/10 px-4 py-3">
                  <div className="text-sm font-semibold text-slate-100">
                    Context
                  </div>
                  <IconButton title="Close" onClick={onClose}>
                    <svg
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      className="opacity-90"
                    >
                      <path
                        fill="currentColor"
                        d="M18.3 5.71 12 12l6.3 6.29-1.41 1.42L10.59 13.4 4.29 19.71 2.88 18.3 9.17 12 2.88 5.71 4.29 4.29l6.3 6.3 6.29-6.3z"
                      />
                    </svg>
                  </IconButton>
                </div>
                <div className="flex-1 min-h-0 overflow-y-auto">{children}</div>
              </div>
            </GlowPanel>
          </div>
        </aside>
      </div>
    </>
  );
}

/* ============================================================================
   Kebab Menu (3 dots) – minimal popover
============================================================================ */

function MenuItem({
  icon,
  label,
  onClick,
  danger,
}: {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-xs transition-colors",
        danger
          ? "text-red-200 hover:bg-red-500/10"
          : "text-slate-200 hover:bg-cyan-500/10",
      ].join(" ")}
    >
      <span className="opacity-90">{icon}</span>
      <span className="truncate">{label}</span>
    </button>
  );
}

/* ============================================================================
   Main
============================================================================ */

import { useToast } from "@/components/ui/Toast";

export default function ChatPage() {
  const { toast } = useToast();
  const [graphId, setGraphId] = useState(DEFAULT_GRAPH_ID);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const u = window.localStorage.getItem(LS_UNIVERSE_KEY) || "";
    if (u.startsWith("U:")) setGraphId(u);

    const onStorage = (e: StorageEvent) => {
      if (e.key === LS_UNIVERSE_KEY && (e.newValue || "").startsWith("U:")) {
        setGraphId(e.newValue!);
      }
    };

    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  // Zustand persistence (prevents reset on navigation)
  const ensureInitialized = useChatStore((s) => s.ensureInitialized);
  const sessions = useChatStore((s) => s.sessions);
  const activeSessionId = useChatStore((s) => s.activeSessionId);

  const setActive = useChatStore((s) => s.setActive);
  const newSession = useChatStore((s) => s.newSession);
  const updateActive = useChatStore((s) => s.updateActive);

  const archiveSession = useChatStore((s) => s.archiveSession);
  const deleteForever = useChatStore((s) => s.deleteForever);
  const restoreSession = useChatStore((s) => s.restoreSession);
  const renameSession = useChatStore((s) => s.renameSession);

  // UI-only state
  const [contextOpen, setContextOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [showArchived, setShowArchived] = useState(false);

  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [webEnabled, setWebEnabled] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // kebab menu state
  const [menuSessionId, setMenuSessionId] = useState<string>("");
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    ensureInitialized();
  }, [ensureInitialized]);

  // close menu on outside click / resize / scroll
  useEffect(() => {
    if (!menuSessionId) return;

    const onDown = (e: MouseEvent) => {
      const t = e.target as Node | null;
      if (!t) return;
      if (menuRef.current && menuRef.current.contains(t)) return;
      setMenuSessionId("");
    };
    const onAny = () => setMenuSessionId("");

    window.addEventListener("mousedown", onDown);
    window.addEventListener("resize", onAny);
    window.addEventListener("scroll", onAny, true);

    return () => {
      window.removeEventListener("mousedown", onDown);
      window.removeEventListener("resize", onAny);
      window.removeEventListener("scroll", onAny, true);
    };
  }, [menuSessionId]);

  const active = useMemo(() => {
    if (!sessions.length || !activeSessionId) return null;
    const s = sessions.find((x: any) => x.id === activeSessionId) ?? null;
    // never render trashed/archived chat as the main panel
    if (!s || s.status !== "active") return null;
    return s;
  }, [sessions, activeSessionId]);

  const groups = useMemo(() => {
    const todayKeyStr = dayKey(Date.now());
    const today: any[] = [];
    const prev7: any[] = [];
    const older: any[] = [];

    for (const s of [...sessions].sort(
      (a: any, b: any) => b.updatedAt - a.updatedAt,
    )) {
      if (s.status !== "active") continue;
      const k = dayKey(s.updatedAt);
      if (k === todayKeyStr) today.push(s);
      else if (daysAgo(s.updatedAt) <= 7) prev7.push(s);
      else older.push(s);
    }

    return { today, prev7, older };
  }, [sessions]);

  const archived = useMemo(() => {
    return [...sessions]
      .filter((s: any) => s.status === "archived")
      .sort((a: any, b: any) => b.updatedAt - a.updatedAt);
  }, [sessions]);

  async function onSend() {
    const msg = input.trim();
    if (!msg || sending || !active) return;

    setSending(true);

    updateActive((s: any) => ({
      ...s,
      title: s.title === "New Session" ? msg.slice(0, 34) : s.title,
      updatedAt: Date.now(),
      turns: [...s.turns, { role: "user", content: msg }],
    }));

    setInput("");

    try {
      const gid = graphId?.startsWith("U:") ? graphId : undefined;
      const res = await postChat(msg, gid);

      const mapped: RtUsedNodeSummary[] = (res.used_nodes ?? []).map(
        (n: ApiUsedNodeSummary) => ({
          id: (n as any).id ?? (n as any).node_id ?? "unknown",
          label: (n as any).label ?? (n as any).node_id ?? "node",
          score: (n as any).score ?? 0,
          kind: (n as any).kind,
          region: (n as any).region,
          preview: (n as any).preview ?? (n as any).snippet,
        }),
      );

      updateActive((s: any) => ({
        ...s,
        updatedAt: Date.now(),
        turns: [...s.turns, { role: "assistant", content: res.reply ?? "—" }],
        usedNodes: mapped,
      }));
    } catch (e: any) {
      updateActive((s: any) => ({
        ...s,
        updatedAt: Date.now(),
        turns: [
          ...s.turns,
          {
            role: "assistant",
            content: `Error: ${e?.message ?? "Failed to fetch"}`,
          },
        ],
      }));
    } finally {
      setSending(false);
    }
  }

  // Sidebar width (smooth) — chat expands to fill remaining space
  const sidebarWidth = sidebarOpen ? 300 : 0;

  return (
    <div className="w-full max-w-none h-[calc(86vh-24px)] min-h-0 overflow-hidden overflow-x-hidden">
      <div
        className="grid h-full min-h-0 grid-cols-1 gap-3 lg:grid-cols-[auto_1fr]"
        style={{
          gridTemplateColumns: `minmax(${sidebarWidth}px, ${sidebarWidth}px) minmax(0, 1fr)`,
        }}
      >
        {/* LEFT: sessions */}
        <div
          className={[
            "min-h-0 transition-all duration-200 ease-out",
            sidebarOpen ? "opacity-100" : "opacity-0 pointer-events-none",
          ].join(" ")}
          style={{ width: sidebarWidth }}
        >
          <GlowPanel className="h-full min-h-0 p-3">
            <div className="flex h-full min-h-0 flex-col">
              <button
                type="button"
                onClick={() => {
                  newSession();
                  setFiles([]);
                  setWebEnabled(false);
                  setInput("");
                  setMenuSessionId("");
                }}
                className="flex items-center justify-center gap-2 rounded-xl border border-cyan-300/15 bg-cyan-500/5 px-3 py-3
                           text-sm font-medium text-cyan-100 hover:bg-cyan-500/10 hover:border-cyan-300/25
                           transition-all duration-150 active:scale-[0.99]"
              >
                <span className="text-cyan-300">＋</span> New Session
              </button>

              <div className="mt-4 flex-1 min-h-0 overflow-y-auto pr-1">
                <div className="mb-2 text-[10px] font-semibold tracking-widest text-slate-500">
                  TODAY
                </div>

                <div className="space-y-2">
                  {groups.today.map((s: any) => {
                    const activeRow = s.id === activeSessionId;

                    return (
                      <div
                        key={s.id}
                        className={[
                          "group relative rounded-xl border",
                          activeRow
                            ? "border-cyan-400/25 bg-cyan-500/10"
                            : "border-slate-800/70 bg-slate-950/40 hover:bg-cyan-500/5 hover:border-cyan-400/15",
                          "transition-all duration-150",
                        ].join(" ")}
                      >
                        <div
                          role="button"
                          tabIndex={0}
                          onClick={() => setActive(s.id)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" || e.key === " ") {
                              e.preventDefault();
                              setActive(s.id);
                            }
                          }}
                          className="w-full cursor-pointer rounded-xl px-3 py-2 text-left"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="min-w-0">
                              <div className="truncate text-sm text-slate-100">
                                {s.title}
                              </div>
                              <div className="mt-1 text-[11px] text-slate-500">
                                id:{" "}
                                <span className="font-mono text-slate-400">
                                  {shortId(s.id)}
                                </span>
                              </div>
                            </div>

                            {/* kebab: appears only on hover */}
                            <button
                              type="button"
                              title="Session menu"
                              onClick={(e) => {
                                e.stopPropagation();
                                setMenuSessionId((cur) =>
                                  cur === s.id ? "" : s.id,
                                );
                              }}
                              className={[
                                "mt-0.5 inline-flex h-8 w-8 items-center justify-center rounded-lg border",
                                "border-slate-800/70 bg-slate-950/40 text-slate-300",
                                "opacity-0 group-hover:opacity-100",
                                "transition-opacity duration-150",
                                activeRow ? "opacity-100" : "",
                              ].join(" ")}
                            >
                              <svg
                                width="16"
                                height="16"
                                viewBox="0 0 24 24"
                                className="opacity-90"
                              >
                                <path
                                  fill="currentColor"
                                  d="M12 7a2 2 0 1 0 .001-4.001A2 2 0 0 0 12 7Zm0 7a2 2 0 1 0 .001-4.001A2 2 0 0 0 12 14Zm0 7a2 2 0 1 0 .001-4.001A2 2 0 0 0 12 21Z"
                                />
                              </svg>
                            </button>
                          </div>
                        </div>

                        {/* popover */}
                        {menuSessionId === s.id && (
                          <div
                            ref={menuRef}
                            className="absolute right-2 top-10 z-20 w-48 origin-top-right animate-[fadeIn_120ms_ease-out]"
                          >
                            <div className="rounded-xl border border-cyan-300/10 bg-slate-950/90 p-2 shadow-[0_10px_30px_rgba(0,0,0,0.40)] backdrop-blur">
                              <MenuItem
                                icon={
                                  <svg
                                    width="14"
                                    height="14"
                                    viewBox="0 0 24 24"
                                  >
                                    <path
                                      fill="currentColor"
                                      d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25Zm18-11.5a1 1 0 0 0 0-1.41l-1.59-1.59a1 1 0 0 0-1.41 0l-1.13 1.13l3.75 3.75L21 5.75Z"
                                    />
                                  </svg>
                                }
                                label="Rename"
                                onClick={() => {
                                  setMenuSessionId("");
                                  const next = window.prompt(
                                    "Rename session",
                                    s.title,
                                  );
                                  if (next) renameSession(s.id, next);
                                }}
                              />

                              <MenuItem
                                icon={
                                  <svg
                                    width="14"
                                    height="14"
                                    viewBox="0 0 24 24"
                                  >
                                    <path
                                      fill="currentColor"
                                      d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7a2.5 2.5 0 0 0 0-1.39l7.02-4.11A2.99 2.99 0 1 0 14 5a3 3 0 0 0 .04.49L7.02 9.6a3 3 0 1 0 0 4.8l7.02 4.11A3 3 0 1 0 18 16.08Z"
                                    />
                                  </svg>
                                }
                                label="Share (soon)"
                                onClick={() => {
                                  setMenuSessionId("");
                                  toast.info("Share is not wired yet.");
                                }}
                              />

                              <div className="my-1 h-px bg-slate-800/70" />

                              <MenuItem
                                icon={
                                  <svg
                                    width="14"
                                    height="14"
                                    viewBox="0 0 24 24"
                                  >
                                    <path
                                      fill="currentColor"
                                      d="M20 8h-3V4H7v4H4v2h16V8Zm-2 12H6V10h12v10Z"
                                    />
                                  </svg>
                                }
                                label="Archive"
                                onClick={() => {
                                  setMenuSessionId("");
                                  archiveSession(s.id);
                                }}
                              />

                              <MenuItem
                                danger
                                icon={
                                  <svg
                                    width="14"
                                    height="14"
                                    viewBox="0 0 24 24"
                                  >
                                    <path
                                      fill="currentColor"
                                      d="M9 3h6l1 2h4v2H4V5h4l1-2Zm1 7h2v9h-2v-9Zm4 0h2v9h-2v-9Z"
                                    />
                                  </svg>
                                }
                                label="Delete"
                                onClick={() => {
                                  setMenuSessionId("");
                                  const ok = window.confirm(
                                    "Delete this session? This cannot be undone.",
                                  );
                                  if (!ok) return;
                                  deleteForever(s.id);
                                }}
                              />
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}

                  {!groups.today.length && (
                    <div className="rounded-xl border border-slate-800/60 bg-slate-950/30 p-3 text-xs text-slate-400">
                      No sessions today.
                    </div>
                  )}
                </div>

                <div className="mt-5 mb-2 text-[10px] font-semibold tracking-widest text-slate-500">
                  PREVIOUS 7 DAYS
                </div>

                <div className="space-y-2">
                  {groups.prev7.map((s: any) => {
                    const activeRow = s.id === activeSessionId;

                    return (
                      <div
                        key={s.id}
                        className={[
                          "group relative rounded-xl border",
                          activeRow
                            ? "border-cyan-400/25 bg-cyan-500/10"
                            : "border-slate-800/70 bg-slate-950/40 hover:bg-cyan-500/5 hover:border-cyan-400/15",
                          "transition-all duration-150",
                        ].join(" ")}
                      >
                        <div
                          role="button"
                          tabIndex={0}
                          onClick={() => setActive(s.id)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" || e.key === " ") {
                              e.preventDefault();
                              setActive(s.id);
                            }
                          }}
                          className="w-full cursor-pointer rounded-xl px-3 py-2 text-left"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="min-w-0">
                              <div className="truncate text-sm text-slate-100">
                                {s.title}
                              </div>
                              <div className="mt-1 text-[11px] text-slate-500">
                                {daysAgo(s.updatedAt)}d ago
                              </div>
                            </div>

                            <button
                              type="button"
                              title="Session menu"
                              onClick={(e) => {
                                e.stopPropagation();
                                setMenuSessionId((cur) =>
                                  cur === s.id ? "" : s.id,
                                );
                              }}
                              className={[
                                "mt-0.5 inline-flex h-8 w-8 items-center justify-center rounded-lg border",
                                "border-slate-800/70 bg-slate-950/40 text-slate-300",
                                "opacity-0 group-hover:opacity-100",
                                "transition-opacity duration-150",
                                activeRow ? "opacity-100" : "",
                              ].join(" ")}
                            >
                              <svg
                                width="16"
                                height="16"
                                viewBox="0 0 24 24"
                                className="opacity-90"
                              >
                                <path
                                  fill="currentColor"
                                  d="M12 7a2 2 0 1 0 .001-4.001A2 2 0 0 0 12 7Zm0 7a2 2 0 1 0 .001-4.001A2 2 0 0 0 12 14Zm0 7a2 2 0 1 0 .001-4.001A2 2 0 0 0 12 21Z"
                                />
                              </svg>
                            </button>
                          </div>
                        </div>

                        {menuSessionId === s.id && (
                          <div
                            ref={menuRef}
                            className="absolute right-2 top-10 z-20 w-48 origin-top-right animate-[fadeIn_120ms_ease-out]"
                          >
                            <div className="rounded-xl border border-cyan-300/10 bg-slate-950/90 p-2 shadow-[0_10px_30px_rgba(0,0,0,0.40)] backdrop-blur">
                              <MenuItem
                                icon={
                                  <svg
                                    width="14"
                                    height="14"
                                    viewBox="0 0 24 24"
                                  >
                                    <path
                                      fill="currentColor"
                                      d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25Zm18-11.5a1 1 0 0 0 0-1.41l-1.59-1.59a1 1 0 0 0-1.41 0l-1.13 1.13l3.75 3.75L21 5.75Z"
                                    />
                                  </svg>
                                }
                                label="Rename"
                                onClick={() => {
                                  setMenuSessionId("");
                                  const next = window.prompt(
                                    "Rename session",
                                    s.title,
                                  );
                                  if (next) renameSession(s.id, next);
                                }}
                              />

                              <MenuItem
                                icon={
                                  <svg
                                    width="14"
                                    height="14"
                                    viewBox="0 0 24 24"
                                  >
                                    <path
                                      fill="currentColor"
                                      d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7a2.5 2.5 0 0 0 0-1.39l7.02-4.11A2.99 2.99 0 1 0 14 5a3 3 0 0 0 .04.49L7.02 9.6a3 3 0 1 0 0 4.8l7.02 4.11A3 3 0 1 0 18 16.08Z"
                                    />
                                  </svg>
                                }
                                label="Share (soon)"
                                onClick={() => {
                                  setMenuSessionId("");
                                  toast.info("Share is not wired yet.");
                                }}
                              />

                              <div className="my-1 h-px bg-slate-800/70" />

                              <MenuItem
                                icon={
                                  <svg
                                    width="14"
                                    height="14"
                                    viewBox="0 0 24 24"
                                  >
                                    <path
                                      fill="currentColor"
                                      d="M20 8h-3V4H7v4H4v2h16V8Zm-2 12H6V10h12v10Z"
                                    />
                                  </svg>
                                }
                                label="Archive"
                                onClick={() => {
                                  setMenuSessionId("");
                                  archiveSession(s.id);
                                }}
                              />

                              <MenuItem
                                danger
                                icon={
                                  <svg
                                    width="14"
                                    height="14"
                                    viewBox="0 0 24 24"
                                  >
                                    <path
                                      fill="currentColor"
                                      d="M9 3h6l1 2h4v2H4V5h4l1-2Zm1 7h2v9h-2v-9Zm4 0h2v9h-2v-9Z"
                                    />
                                  </svg>
                                }
                                label="Delete"
                                onClick={() => {
                                  setMenuSessionId("");
                                  const ok = window.confirm(
                                    "Delete this session? This cannot be undone.",
                                  );
                                  if (!ok) return;
                                  deleteForever(s.id);
                                }}
                              />
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>

                {groups.older.length > 0 && (
                  <>
                    <div className="mt-5 mb-2 text-[10px] font-semibold tracking-widest text-slate-500">
                      OLDER
                    </div>

                    <div className="space-y-2">
                      {groups.older.map((s: any) => {
                        const activeRow = s.id === activeSessionId;

                        return (
                          <div
                            key={s.id}
                            className={[
                              "group relative rounded-xl border",
                              activeRow
                                ? "border-cyan-400/25 bg-cyan-500/10"
                                : "border-slate-800/70 bg-slate-950/40 hover:bg-cyan-500/5 hover:border-cyan-400/15",
                              "transition-all duration-150",
                            ].join(" ")}
                          >
                            <div
                              role="button"
                              tabIndex={0}
                              onClick={() => setActive(s.id)}
                              onKeyDown={(e) => {
                                if (e.key === "Enter" || e.key === " ") {
                                  e.preventDefault();
                                  setActive(s.id);
                                }
                              }}
                              className="w-full cursor-pointer rounded-xl px-3 py-2 text-left"
                            >
                              <div className="flex items-start justify-between gap-2">
                                <div className="min-w-0">
                                  <div className="truncate text-sm text-slate-100">
                                    {s.title}
                                  </div>
                                  <div className="mt-1 text-[11px] text-slate-500">
                                    {daysAgo(s.updatedAt)}d ago
                                  </div>
                                </div>

                                <button
                                  type="button"
                                  title="Session menu"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setMenuSessionId((cur) =>
                                      cur === s.id ? "" : s.id,
                                    );
                                  }}
                                  className={[
                                    "mt-0.5 inline-flex h-8 w-8 items-center justify-center rounded-lg border",
                                    "border-slate-800/70 bg-slate-950/40 text-slate-300",
                                    "opacity-0 group-hover:opacity-100",
                                    "transition-opacity duration-150",
                                    activeRow ? "opacity-100" : "",
                                  ].join(" ")}
                                >
                                  <svg
                                    width="16"
                                    height="16"
                                    viewBox="0 0 24 24"
                                    className="opacity-90"
                                  >
                                    <path
                                      fill="currentColor"
                                      d="M12 7a2 2 0 1 0 .001-4.001A2 2 0 0 0 12 7Zm0 7a2 2 0 1 0 .001-4.001A2 2 0 0 0 12 14Zm0 7a2 2 0 1 0 .001-4.001A2 2 0 0 0 12 21Z"
                                    />
                                  </svg>
                                </button>
                              </div>
                            </div>

                            {menuSessionId === s.id && (
                              <div
                                ref={menuRef}
                                className="absolute right-2 top-10 z-20 w-48 origin-top-right animate-[fadeIn_120ms_ease-out]"
                              >
                                <div className="rounded-xl border border-cyan-300/10 bg-slate-950/90 p-2 shadow-[0_10px_30px_rgba(0,0,0,0.40)] backdrop-blur">
                                  <MenuItem
                                    icon={
                                      <svg
                                        width="14"
                                        height="14"
                                        viewBox="0 0 24 24"
                                      >
                                        <path
                                          fill="currentColor"
                                          d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25Zm18-11.5a1 1 0 0 0 0-1.41l-1.59-1.59a1 1 0 0 0-1.41 0l-1.13 1.13l3.75 3.75L21 5.75Z"
                                        />
                                      </svg>
                                    }
                                    label="Rename"
                                    onClick={() => {
                                      setMenuSessionId("");
                                      const next = window.prompt(
                                        "Rename session",
                                        s.title,
                                      );
                                      if (next) renameSession(s.id, next);
                                    }}
                                  />

                                  <MenuItem
                                    icon={
                                      <svg
                                        width="14"
                                        height="14"
                                        viewBox="0 0 24 24"
                                      >
                                        <path
                                          fill="currentColor"
                                          d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7a2.5 2.5 0 0 0 0-1.39l7.02-4.11A2.99 2.99 0 1 0 14 5a3 3 0 0 0 .04.49L7.02 9.6a3 3 0 1 0 0 4.8l7.02 4.11A3 3 0 1 0 18 16.08Z"
                                        />
                                      </svg>
                                    }
                                    label="Share (soon)"
                                    onClick={() => {
                                      setMenuSessionId("");
                                      toast.info("Share is not wired yet.");
                                    }}
                                  />

                                  <div className="my-1 h-px bg-slate-800/70" />

                                  <MenuItem
                                    icon={
                                      <svg
                                        width="14"
                                        height="14"
                                        viewBox="0 0 24 24"
                                      >
                                        <path
                                          fill="currentColor"
                                          d="M20 8h-3V4H7v4H4v2h16V8Zm-2 12H6V10h12v10Z"
                                        />
                                      </svg>
                                    }
                                    label="Archive"
                                    onClick={() => {
                                      setMenuSessionId("");
                                      archiveSession(s.id);
                                    }}
                                  />

                                  <MenuItem
                                    danger
                                    icon={
                                      <svg
                                        width="14"
                                        height="14"
                                        viewBox="0 0 24 24"
                                      >
                                        <path
                                          fill="currentColor"
                                          d="M9 3h6l1 2h4v2H4V5h4l1-2Zm1 7h2v9h-2v-9Zm4 0h2v9h-2v-9Z"
                                        />
                                      </svg>
                                    }
                                    label="Delete"
                                    onClick={() => {
                                      setMenuSessionId("");
                                      const ok = window.confirm(
                                        "Delete this session? This cannot be undone.",
                                      );
                                      if (!ok) return;
                                      deleteForever(s.id);
                                    }}
                                  />
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </>
                )}

                <div className="mt-5 flex items-center justify-between">
                  <div className="text-[10px] font-semibold tracking-widest text-slate-500">
                    ARCHIVED
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowArchived((v) => !v)}
                    className="rounded-lg border border-slate-800/70 bg-slate-950/50 px-2 py-1 text-[10px] text-slate-300 hover:bg-slate-900/50"
                  >
                    {showArchived ? "Hide" : "Show"}
                  </button>
                </div>

                {showArchived && (
                  <div className="mt-2 space-y-2">
                    {archived.map((s: any) => (
                      <div
                        key={s.id}
                        className={[
                          "group relative rounded-xl border",
                          "border-slate-800/60 bg-slate-950/30",
                        ].join(" ")}
                      >
                        <div className="w-full rounded-xl px-3 py-2 text-left">
                          <div className="flex items-start justify-between gap-2">
                            <div className="min-w-0">
                              <div className="truncate text-sm text-slate-300">
                                {s.title}
                              </div>
                              <div className="mt-1 text-[11px] text-slate-500">
                                Archived • {daysAgo(s.updatedAt)}d ago
                              </div>
                            </div>

                            <button
                              type="button"
                              title="Session menu"
                              onClick={(e) => {
                                e.stopPropagation();
                                setMenuSessionId((cur) =>
                                  cur === s.id ? "" : s.id,
                                );
                              }}
                              className={[
                                "mt-0.5 inline-flex h-8 w-8 items-center justify-center rounded-lg border",
                                "border-slate-800/70 bg-slate-950/40 text-slate-300",
                                "opacity-0 group-hover:opacity-100",
                                "transition-opacity duration-150",
                              ].join(" ")}
                            >
                              <svg
                                width="16"
                                height="16"
                                viewBox="0 0 24 24"
                                className="opacity-90"
                              >
                                <path
                                  fill="currentColor"
                                  d="M12 7a2 2 0 1 0 .001-4.001A2 2 0 0 0 12 7Zm0 7a2 2 0 1 0 .001-4.001A2 2 0 0 0 12 14Zm0 7a2 2 0 1 0 .001-4.001A2 2 0 0 0 12 21Z"
                                />
                              </svg>
                            </button>
                          </div>
                        </div>

                        {menuSessionId === s.id && (
                          <div
                            ref={menuRef}
                            className="absolute right-2 top-10 z-20 w-48 origin-top-right animate-[fadeIn_120ms_ease-out]"
                          >
                            <div className="rounded-xl border border-cyan-300/10 bg-slate-950/90 p-2 shadow-[0_10px_30px_rgba(0,0,0,0.40)] backdrop-blur">
                              <MenuItem
                                icon={
                                  <svg
                                    width="14"
                                    height="14"
                                    viewBox="0 0 24 24"
                                  >
                                    <path
                                      fill="currentColor"
                                      d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25Zm18-11.5a1 1 0 0 0 0-1.41l-1.59-1.59a1 1 0 0 0-1.41 0l-1.13 1.13l3.75 3.75L21 5.75Z"
                                    />
                                  </svg>
                                }
                                label="Rename"
                                onClick={() => {
                                  setMenuSessionId("");
                                  const next = window.prompt(
                                    "Rename session",
                                    s.title,
                                  );
                                  if (next) renameSession(s.id, next);
                                }}
                              />

                              <MenuItem
                                icon={
                                  <svg
                                    width="14"
                                    height="14"
                                    viewBox="0 0 24 24"
                                  >
                                    <path
                                      fill="currentColor"
                                      d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7a2.5 2.5 0 0 0 0-1.39l7.02-4.11A2.99 2.99 0 1 0 14 5a3 3 0 0 0 .04.49L7.02 9.6a3 3 0 1 0 0 4.8l7.02 4.11A3 3 0 1 0 18 16.08Z"
                                    />
                                  </svg>
                                }
                                label="Share (soon)"
                                onClick={() => {
                                  setMenuSessionId("");
                                  toast.info("Share is not wired yet.");
                                }}
                              />

                              <div className="my-1 h-px bg-slate-800/70" />

                              <MenuItem
                                icon={
                                  <svg
                                    width="14"
                                    height="14"
                                    viewBox="0 0 24 24"
                                  >
                                    <path
                                      fill="currentColor"
                                      d="M12 5v14m7-7H5"
                                      stroke="currentColor"
                                      strokeWidth="2"
                                      strokeLinecap="round"
                                    />
                                  </svg>
                                }
                                label="Restore"
                                onClick={() => {
                                  setMenuSessionId("");
                                  restoreSession(s.id);
                                }}
                              />

                              <MenuItem
                                danger
                                icon={
                                  <svg
                                    width="14"
                                    height="14"
                                    viewBox="0 0 24 24"
                                  >
                                    <path
                                      fill="currentColor"
                                      d="M9 3h6l1 2h4v2H4V5h4l1-2Zm1 7h2v9h-2v-9Zm4 0h2v9h-2v-9Z"
                                    />
                                  </svg>
                                }
                                label="Delete"
                                onClick={() => {
                                  setMenuSessionId("");
                                  const ok = window.confirm(
                                    "Delete this session? This cannot be undone.",
                                  );
                                  if (!ok) return;
                                  deleteForever(s.id);
                                }}
                              />
                            </div>
                          </div>
                        )}
                      </div>
                    ))}

                    {archived.length === 0 && (
                      <div className="rounded-xl border border-slate-800/60 bg-slate-950/30 p-3 text-xs text-slate-400">
                        No archived sessions.
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div className="mt-3 text-[11px] text-slate-600">
                Persistent sessions (no reset).
              </div>
            </div>
          </GlowPanel>
        </div>

        {/* CENTER: chat */}
        <div className="relative min-h-0">
          {/* collapse button sits on boundary */}
          <button
            type="button"
            onClick={() => setSidebarOpen((v) => !v)}
            title={sidebarOpen ? "Collapse sessions" : "Expand sessions"}
            className={[
              "absolute left-[-10px] top-1/2 z-30 hidden -translate-y-1/2 lg:flex",
              "h-10 w-5 items-center justify-center rounded-full border",
              "border-cyan-300/10 bg-slate-950/60 text-slate-200",
              "hover:border-cyan-400/25 hover:bg-cyan-500/10",
              "transition-all duration-150",
            ].join(" ")}
          >
            <svg
              width="12"
              height="12"
              viewBox="0 0 24 24"
              className="opacity-90"
            >
              <path
                fill="currentColor"
                d={
                  sidebarOpen
                    ? "M15.41 7.41 14 6l-6 6 6 6 1.41-1.41L10.83 12z"
                    : "M8.59 16.59 10 18l6-6-6-6-1.41 1.41L13.17 12z"
                }
              />
            </svg>
          </button>

          <GlowPanel className="h-full min-h-0 p-0">
            <div className="flex h-full min-h-0 flex-col">
              {/* header */}
              <div className="shrink-0 flex items-center justify-between gap-3 border-b border-cyan-300/10 px-4 py-3">
                <ModelSelectPlaceholder />

                <div className="flex items-center gap-2">
                  <div className="rounded-full border border-emerald-300/15 bg-emerald-500/10 px-3 py-1 text-[11px] text-emerald-100">
                    MEMORY ACTIVE
                  </div>

                  <IconButton
                    title="Open Context"
                    active={contextOpen}
                    onClick={() => setContextOpen(true)}
                  >
                    <svg
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      className="opacity-90"
                    >
                      <path
                        fill="currentColor"
                        d="M4 4h16v16H4V4Zm14 2H8v12h10V6Zm-12 0v12h1V6H6Z"
                      />
                    </svg>
                  </IconButton>
                </div>
              </div>

              {/* messages (scrollable) */}
              <div className="flex-1 min-h-0 overflow-y-auto px-2 py-3">
                {active?.turns?.map((t: any, i: number) => {
                  const isUser = t.role === "user";
                  const isSystem = t.role === "system";

                  return (
                    <div
                      key={i}
                      className={[
                        "mb-3 flex",
                        isUser ? "justify-end" : "justify-start",
                      ].join(" ")}
                    >
                      <div
                        className={[
                          "max-w-[860px] rounded-2xl border px-4 py-3 text-sm leading-relaxed",
                          isSystem
                            ? "border-slate-800/60 bg-slate-950/30 text-slate-400"
                            : isUser
                              ? "border-cyan-400/20 bg-cyan-500/10 text-cyan-50"
                              : "border-slate-800/70 bg-slate-950/45 text-slate-100",
                        ].join(" ")}
                      >
                        {t.content}
                      </div>
                    </div>
                  );
                })}

                {!active && (
                  <div className="rounded-2xl border border-slate-800/60 bg-slate-950/30 p-4 text-sm text-slate-400">
                    No active session selected. Create a new session to start
                    chatting.
                  </div>
                )}
              </div>

              {/* composer (fixed inside panel) */}
              <div className="shrink-0 border-t border-cyan-300/10 bg-slate-950/55 backdrop-blur-xl">
                <div className="px-2 py-3">
                  <GlowPanel intensity={0.18} className="p-3">
                    {files.length > 0 && (
                      <div className="mb-2 flex flex-wrap gap-2">
                        {files.map((f) => (
                          <div
                            key={f.name}
                            className="flex items-center gap-2 rounded-lg border border-cyan-300/10 bg-slate-950/50 px-2 py-1 text-xs text-slate-200"
                          >
                            <span className="max-w-[220px] truncate">
                              {f.name}
                            </span>
                            <button
                              type="button"
                              className="text-slate-400 hover:text-slate-100"
                              onClick={() =>
                                setFiles((prev) => prev.filter((x) => x !== f))
                              }
                              title="Remove"
                            >
                              ×
                            </button>
                          </div>
                        ))}
                      </div>
                    )}

                    <div className="flex items-center gap-2">
                      <input
                        ref={fileInputRef}
                        type="file"
                        className="hidden"
                        multiple
                        onChange={(e) => {
                          const next = Array.from(e.target.files ?? []);
                          if (next.length)
                            setFiles((prev) => [...prev, ...next]);
                          e.currentTarget.value = "";
                        }}
                      />

                      <IconButton
                        title="Attach files"
                        onClick={() => fileInputRef.current?.click()}
                      >
                        <svg
                          width="16"
                          height="16"
                          viewBox="0 0 24 24"
                          className="opacity-90"
                        >
                          <path
                            fill="currentColor"
                            d="M16.5 6.5l-7.78 7.78a3 3 0 1 0 4.24 4.24l7.07-7.07a5 5 0 0 0-7.07-7.07L5.64 11.7"
                          />
                        </svg>
                      </IconButton>

                      <IconButton
                        title="Web search (UI toggle)"
                        active={webEnabled}
                        onClick={() => setWebEnabled((v) => !v)}
                      >
                        <svg
                          width="16"
                          height="16"
                          viewBox="0 0 24 24"
                          className="opacity-90"
                        >
                          <path
                            fill="currentColor"
                            d="M12 2a10 10 0 1 0 0 20a10 10 0 0 0 0-20Zm7.93 9h-3.18a15.3 15.3 0 0 0-1.15-5.02A8.02 8.02 0 0 1 19.93 11ZM12 4c.9 1.2 1.67 3.1 2.07 7H9.93C10.33 7.1 11.1 5.2 12 4ZM4.07 13h3.18c.23 1.78.7 3.57 1.15 5.02A8.02 8.02 0 0 1 4.07 13Zm3.18-2H4.07a8.02 8.02 0 0 1 4.33-5.02A15.3 15.3 0 0 0 7.25 11Zm2.68 2h4.14c-.4 3.9-1.17 5.8-2.07 7c-.9-1.2-1.67-3.1-2.07-7Zm6.82 5.02c.45-1.45.92-3.24 1.15-5.02h3.18a8.02 8.02 0 0 1-4.33 5.02Z"
                          />
                        </svg>
                      </IconButton>

                      <input
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" && !e.shiftKey) {
                            e.preventDefault();
                            onSend();
                          }
                        }}
                        className="h-11 flex-1 rounded-xl border border-slate-800/70 bg-slate-950/40 px-4 text-sm text-slate-100 outline-none placeholder:text-slate-500
                                   focus:ring-1 focus:ring-cyan-500/60"
                        placeholder="Ask FAIM anything…"
                      />

                      <button
                        type="button"
                        disabled={sending || !input.trim() || !active}
                        onClick={onSend}
                        className={[
                          "h-11 rounded-xl border px-4 text-sm font-semibold",
                          sending || !input.trim() || !active
                            ? "border-slate-800/70 bg-slate-950/30 text-slate-500"
                            : "border-cyan-400/25 bg-cyan-500/10 text-cyan-100 hover:bg-cyan-500/15 hover:border-cyan-300/35",
                          "transition-all duration-150 active:scale-[0.98]",
                        ].join(" ")}
                      >
                        Send
                      </button>
                    </div>

                    <div className="mt-2 text-[10px] text-slate-600">
                      {webEnabled ? "Web: ON (UI toggle)" : "Web: OFF"} • Files:{" "}
                      {files.length}
                    </div>
                  </GlowPanel>
                </div>
              </div>
            </div>
          </GlowPanel>
        </div>
      </div>

      {/* Slide-in Context Drawer */}
      <ContextDrawer open={contextOpen} onClose={() => setContextOpen(false)}>
        <ContextSidebar nodes={(active as any)?.usedNodes ?? []} />
      </ContextDrawer>

      {/* minimal keyframes for popover */}
      <style jsx global>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(-4px) scale(0.98);
          }
          to {
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }
      `}</style>
    </div>
  );
}
