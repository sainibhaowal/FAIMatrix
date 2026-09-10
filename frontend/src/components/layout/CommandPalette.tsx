"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { API_BASE_URL } from "@/lib/api-client";
import { readJsonSafely } from "@/lib/safeFetch";

function cx(...parts: Array<string | false | null | undefined>) {
  return parts.filter(Boolean).join(" ");
}

export type SearchResult =
  | { type: "page"; title: string; href: string; subtitle?: string }
  | { type: "setting"; title: string; actionId: string; subtitle?: string }
  | { type: "node"; title: string; node_id: string; subtitle?: string }
  | { type: "session"; title: string; session_id: string; subtitle?: string };

async function searchSoft(graphId: string, q: string): Promise<SearchResult[]> {
  const qq = q.trim();
  if (!qq) return [];
  try {
    const res = await fetch(
      `${API_BASE_URL}/search?q=${encodeURIComponent(qq)}&graph_id=${encodeURIComponent(graphId)}`,
      { cache: "no-store" },
    );
    if (!res.ok) return [];
    const data = (await readJsonSafely<any>(res)) ?? {};
    const arr = Array.isArray(data)
      ? data
      : Array.isArray(data?.results)
        ? data.results
        : [];
    return arr.slice(0, 15).map((r: any) => {
      const t = String(r.type ?? "node") as SearchResult["type"];
      if (t === "page") {
        return {
          type: "page",
          title: String(r.title ?? r.label ?? "Page"),
          href: String(r.href ?? "/dashboard"),
          subtitle: r.subtitle ? String(r.subtitle) : undefined,
        };
      }
      if (t === "setting") {
        return {
          type: "setting",
          title: String(r.title ?? r.label ?? "Setting"),
          actionId: String(r.actionId ?? r.action_id ?? "noop"),
          subtitle: r.subtitle ? String(r.subtitle) : undefined,
        };
      }
      if (t === "session") {
        return {
          type: "session",
          title: String(r.title ?? r.label ?? "Session"),
          session_id: String(r.session_id ?? r.id ?? ""),
          subtitle: r.subtitle ? String(r.subtitle) : undefined,
        };
      }
      return {
        type: "node",
        title: String(r.title ?? r.snippet ?? r.label ?? "Node"),
        node_id: String(r.node_id ?? r.id ?? ""),
        subtitle: r.subtitle ? String(r.subtitle) : undefined,
      };
    });
  } catch {
    return [];
  }
}

function IconSearch(props: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={props.className} fill="none">
      <path
        d="M10.5 18a7.5 7.5 0 1 1 0-15 7.5 7.5 0 0 1 0 15Z"
        stroke="currentColor"
        strokeWidth="1.5"
      />
      <path
        d="M16.5 16.5 21 21"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function CommandPalette({
  open,
  onClose,
  graphId,
}: {
  open: boolean;
  onClose: () => void;
  graphId: string;
}) {
  const router = useRouter();
  const { data: session } = useSession();
  const inputRef = useRef<HTMLInputElement>(null);
  const [q, setQ] = useState("");
  const [remote, setRemote] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);

  const localActions: SearchResult[] = useMemo(
    () => [
      {
        type: "page",
        title: "Dashboard",
        href: "/dashboard",
        subtitle: "Health + metrics + timeline",
      },
      {
        type: "page",
        title: "FIG View",
        href: "/dashboard/graph",
        subtitle: "3D graph inspector",
      },

      {
        type: "setting",
        title: "Open Settings",
        actionId: "open_settings",
        subtitle: "Quick toggles and preferences",
      },

    ],
    [],
  );

  const results = useMemo(() => {
    const qq = q.trim().toLowerCase();
    const local = !qq
      ? localActions
      : localActions.filter(
          (a) =>
            a.title.toLowerCase().includes(qq) ||
            (a.subtitle ?? "").toLowerCase().includes(qq),
        );
    return [...local.slice(0, 8), ...remote].slice(0, 15);
  }, [localActions, q, remote]);

  useEffect(() => {
    if (!open) return;
    setQ("");
    setRemote([]);
    setLoading(false);
    const t = window.setTimeout(() => inputRef.current?.focus(), 0);
    return () => window.clearTimeout(t);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const qq = q.trim();
    if (!qq) {
      setRemote([]);
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    const id = window.setTimeout(async () => {
      const r = await searchSoft(graphId, qq);
      if (!cancelled) {
        setRemote(r);
        setLoading(false);
      }
    }, 180);
    return () => {
      cancelled = true;
      window.clearTimeout(id);
    };
  }, [open, q, graphId]);

  // Use portal to render at document root level - MUST be before any early returns!
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Early returns AFTER all hooks
  if (!open) return null;
  if (!mounted) return null;

  const onPick = (r: SearchResult) => {
    if (r.type === "page") {
      router.push(r.href);
      onClose();
      return;
    }
    if (r.type === "setting") {
      if (r.actionId === "open_settings") router.push("/dashboard/profile");

      onClose();
      return;
    }
    if (r.type === "node") {
      router.push(`/node/${encodeURIComponent(r.node_id || "unknown")}`);
      onClose();
      return;
    }
    if (r.type === "session") {
      router.push(`/session/${encodeURIComponent(r.session_id || "unknown")}`);
      onClose();
      return;
    }
  };

  return createPortal(
    <div
      className="fixed inset-0 z-[9999] flex items-start justify-center p-4 pt-20"
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
    >
      {/* Backdrop with frosted glass effect - can see through */}
      <div
        className="absolute inset-0 bg-slate-950/10 backdrop-blur-xl"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal - matches FAIM dark slate theme */}
      <div className="relative w-full max-w-[600px] overflow-hidden rounded-2xl border border-white/10 bg-slate-900/95 backdrop-blur-xl shadow-[0_25px_80px_-20px_rgba(0,0,0,0.9)]">
        {/* Search input - subtle styling */}
        <div className="relative flex items-center gap-3 border-b border-white/5 px-5 py-4">
          <IconSearch className="h-5 w-5 text-slate-400" />
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search nodes, sessions, pages, settings…"
            className="w-full bg-transparent text-base text-slate-100 outline-none placeholder:text-slate-500 caret-cyan-400"
            aria-label="Search command palette"
            role="combobox"
            aria-expanded="true"
            aria-controls="command-results"
          />
          <kbd className="hidden sm:inline-flex h-6 items-center rounded border border-white/10 bg-white/5 px-2 text-[10px] font-medium text-slate-500">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div className="max-h-[380px] overflow-y-auto p-2">
          {loading && (
            <div className="px-3 py-4 text-center text-sm text-slate-500">
              <span className="inline-block animate-pulse">Searching…</span>
            </div>
          )}

          {!loading && results.length === 0 ? (
            <div className="px-3 py-10 text-center text-sm text-slate-500">
              No results found.
            </div>
          ) : (
            <ul className="space-y-0.5" id="command-results" role="listbox">
              {results.map((r, idx) => (
                <li key={`${r.type}-${idx}`}>
                  <button
                    onClick={() => onPick(r)}
                    className={[
                      "w-full rounded-xl px-4 py-3 text-left",
                      "transition-all duration-150",
                      "hover:bg-white/5",
                      "focus:outline-none focus:bg-white/10",
                    ].join(" ")}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="text-sm font-medium text-slate-200">
                        {r.title}
                      </div>
                      <span
                        className={[
                          "rounded px-2 py-0.5 text-[10px] font-medium",
                          r.type === "page"
                            ? "bg-white/5 text-slate-400"
                            : r.type === "setting"
                              ? "bg-white/5 text-slate-400"
                              : r.type === "node"
                                ? "bg-white/5 text-slate-400"
                                : "bg-white/5 text-slate-500",
                        ].join(" ")}
                      >
                        {r.type}
                      </span>
                    </div>
                    {r.subtitle && (
                      <div className="mt-1 text-xs text-slate-500">
                        {r.subtitle}
                      </div>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-white/5 px-5 py-2.5 text-[10px] text-slate-500">
          <div className="truncate max-w-[180px]">
            {graphId.slice(0, 24)}...
          </div>
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <kbd className="rounded border border-white/10 bg-white/5 px-1.5 py-0.5">
                ↑↓
              </kbd>
              navigate
            </span>
            <span className="flex items-center gap-1">
              <kbd className="rounded border border-white/10 bg-white/5 px-1.5 py-0.5">
                ⏎
              </kbd>
              select
            </span>
          </div>
        </div>
      </div>
    </div>,
    document.body,
  );
}
