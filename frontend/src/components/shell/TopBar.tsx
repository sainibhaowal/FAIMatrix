'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { API_BASE_URL, DEFAULT_GRAPH_ID, fetchHealth, buildFaimHeaders } from '../../lib/api';
import { startFaimStream } from '../../lib/realtime';

type Health = 'ok' | 'degraded' | 'down' | 'unknown';

type GraphSummary = {
  id: string;
  name: string;
  owner?: string;
  created_at?: string;
};

type SearchResult =
  | { type: 'page'; title: string; href: string; subtitle?: string }
  | { type: 'setting'; title: string; actionId: string; subtitle?: string }
  | { type: 'node'; title: string; node_id: string; subtitle?: string }
  | { type: 'session'; title: string; session_id: string; subtitle?: string };

const LS_UI_DENSITY = 'faim.ui.density';
const LS_UI_DEBUG = 'faim.ui.debug';

const LS_UNIVERSE_KEY = 'faim.universe_graph_id';

function getUniverseIdFromStorage(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    const u = window.localStorage.getItem(LS_UNIVERSE_KEY);
    if (!u) return null;
    const v = u.trim();
    return v.startsWith('U:') ? v : null;
  } catch {
    return null;
  }
}
/**
 * Resolve and persist the user's Universe graph id (U:...) once.
 * - Uses SSE /stream contract to learn the Universe id.
 * - Never returns non-U ids (so 'RAVIN_MAIN' cannot leak into the UI).
 */
function resolveUniverseIdOnce(timeoutMs = 2500): Promise<string | null> {
  if (typeof window === 'undefined') return Promise.resolve(null);

  // If already present, fast-path.
  const existing = getUniverseIdFromStorage();
  if (existing) return Promise.resolve(existing);

  return new Promise((resolve) => {
    let settled = false;

    const safeResolve = (v: string | null) => {
      if (settled) return;
      settled = true;
      resolve(v);
    };

    // Start a short-lived SSE stream; stop as soon as we receive the contract.
    const stop = startFaimStream('', {
      onContract: (c: any) => {
        const u = String(c?.universe?.graph_id ?? '').trim();
        if (u.startsWith('U:')) {
          try {
            window.localStorage.setItem(LS_UNIVERSE_KEY, u);
          } catch {}
          safeResolve(u);
        } else {
          safeResolve(null);
        }
        try { stop(); } catch {}
      },
      onError: () => {
        safeResolve(null);
        try { stop(); } catch {}
      },
    });

    window.setTimeout(() => {
      safeResolve(null);
      try { stop(); } catch {}
    }, timeoutMs);
  });
}

function cx(...parts: Array<string | false | null | undefined>) {
  return parts.filter(Boolean).join(' ');
}

function useOutsideClick(
  refs: Array<React.RefObject<HTMLElement | null>>,
  onOutside: () => void,
  enabled: boolean,
) {
  useEffect(() => {
    if (!enabled) return;
    const onDown = (e: MouseEvent) => {
      const t = e.target as Node | null;
      if (!t) return;
      for (const r of refs) {
        const el = r.current;
        if (el && el.contains(t)) return;
      }
      onOutside();
    };
    window.addEventListener('mousedown', onDown);
    return () => window.removeEventListener('mousedown', onDown);
  }, [enabled, onOutside, refs]);
}

function isRemoteApiBase(): boolean {
  const base = (API_BASE_URL || '').trim();
  // Remote means absolute URL like http(s)://... (not "/api/v1")
  return /^https?:\/\//i.test(base);
}

async function fetchGraphsSoft(): Promise<GraphSummary[]> {
  try {
    // ✅ Prevents Next dev server 3000 from receiving /api/v1/graphs (404 spam)
    if (!isRemoteApiBase()) return [];

    const base = (API_BASE_URL || '').trim().replace(/\/+$/, '');
    const res = await fetch(`${base}/graphs`, {
      cache: 'no-store',
      headers: buildFaimHeaders(),
    });

    if (!res.ok) return [];
    const data = (await res.json()) as any;
    const arr = Array.isArray(data) ? data : Array.isArray(data?.graphs) ? data.graphs : [];

    return arr
      .map((g: any) => ({
        id: String(g.id ?? g.graph_id ?? ''),
        name: String(g.name ?? g.display_name ?? g.id ?? g.graph_id ?? ''),
        owner: g.owner ? String(g.owner) : undefined,
        created_at: g.created_at ? String(g.created_at) : undefined,
      }))
      .filter((g: GraphSummary) => !!g.id);
  } catch {
    return [];
  }
}

async function searchSoft(graphId: string, q: string): Promise<SearchResult[]> {
  const qq = q.trim();
  if (!qq) return [];
  try {
    const res = await fetch(
      `${API_BASE_URL}/search?q=${encodeURIComponent(qq)}&graph_id=${encodeURIComponent(graphId)}`,
      { cache: 'no-store' },
    );
    if (!res.ok) return [];
    const data = (await res.json()) as any;
    const arr = Array.isArray(data) ? data : Array.isArray(data?.results) ? data.results : [];
    return arr.slice(0, 15).map((r: any) => {
      const t = String(r.type ?? 'node') as SearchResult['type'];
      if (t === 'page') {
        return {
          type: 'page',
          title: String(r.title ?? r.label ?? 'Page'),
          href: String(r.href ?? '/dashboard'),
          subtitle: r.subtitle ? String(r.subtitle) : undefined,
        };
      }
      if (t === 'setting') {
        return {
          type: 'setting',
          title: String(r.title ?? r.label ?? 'Setting'),
          actionId: String(r.actionId ?? r.action_id ?? 'noop'),
          subtitle: r.subtitle ? String(r.subtitle) : undefined,
        };
      }
      if (t === 'session') {
        return {
          type: 'session',
          title: String(r.title ?? r.label ?? 'Session'),
          session_id: String(r.session_id ?? r.id ?? ''),
          subtitle: r.subtitle ? String(r.subtitle) : undefined,
        };
      }
      return {
        type: 'node',
        title: String(r.title ?? r.snippet ?? r.label ?? 'Node'),
        node_id: String(r.node_id ?? r.id ?? ''),
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
      <path d="M10.5 18a7.5 7.5 0 1 1 0-15 7.5 7.5 0 0 1 0 15Z" stroke="currentColor" strokeWidth="1.5" />
      <path d="M16.5 16.5 21 21" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}
function IconGear(props: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={props.className} fill="none">
      <path d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z" stroke="currentColor" strokeWidth="1.5" />
      <path
        d="M19.4 15a7.94 7.94 0 0 0 .1-1l2-1.2-2-3.5-2.3.6a7.6 7.6 0 0 0-.8-.8l.6-2.3-3.5-2-1.2 2a7.94 7.94 0 0 0-1 0l-1.2-2-3.5 2 .6 2.3c-.28.25-.55.52-.8.8l-2.3-.6-2 3.5 2 1.2a7.94 7.94 0 0 0 0 1l-2 1.2 2 3.5 2.3-.6c.25.28.52.55.8.8l-.6 2.3 3.5 2 1.2-2a7.94 7.94 0 0 0 1 0l1.2 2 3.5-2-.6-2.3c.28-.25.55-.52.8-.8l2.3.6 2-3.5-2-1.2Z"
        stroke="currentColor"
        strokeWidth="1.1"
        strokeLinejoin="round"
        opacity="0.7"
      />
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
function IconSidebar(props: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={props.className} fill="none">
      <rect x="3" y="4" width="18" height="16" rx="2" stroke="currentColor" strokeWidth="1.5" />
      <path d="M9 4v16" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}
function IconChevron(props: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={props.className} fill="none">
      <path d="M7 10l5 5 5-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Dropdown({
  open,
  anchorRef,
  onClose,
  children,
  className,
}: {
  open: boolean;
  anchorRef: React.RefObject<HTMLElement | null>;
  onClose: () => void;
  children: React.ReactNode;
  className?: string;
}) {
  const panelRef = useRef<HTMLDivElement>(null);
  useOutsideClick([anchorRef as any, panelRef as any], onClose, open);
  if (!open) return null;
  return (
    <div
      ref={panelRef}
      className={cx(
        'absolute right-0 mt-2 w-[320px] rounded-2xl border border-white/10 bg-slate-950/70 backdrop-blur-xl shadow-[0_20px_60px_-28px_rgba(0,0,0,0.9)]',
        className,
      )}
    >
      {children}
    </div>
  );
}

function CommandPalette({
  open,
  onClose,
  graphId,
}: {
  open: boolean;
  onClose: () => void;
  graphId: string;
}) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [q, setQ] = useState('');
  const [remote, setRemote] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);

  const localActions: SearchResult[] = useMemo(
    () => [
      { type: 'page', title: 'Dashboard', href: '/dashboard', subtitle: 'Health + metrics + timeline' },
      { type: 'page', title: 'FIG View', href: '/fig', subtitle: '3D graph inspector' },
      { type: 'page', title: 'Chat', href: '/chat', subtitle: 'Memory-grounded chat (if enabled)' },
      { type: 'setting', title: 'Open Settings', actionId: 'open_settings', subtitle: 'Quick toggles and preferences' },
      { type: 'setting', title: 'Open Admin', actionId: 'open_admin', subtitle: 'Account & governance (future)' },
    ],
    [],
  );

  const results = useMemo(() => {
    const qq = q.trim().toLowerCase();
    const local = !qq
      ? localActions
      : localActions.filter((a) => a.title.toLowerCase().includes(qq) || (a.subtitle ?? '').toLowerCase().includes(qq));
    return [...local.slice(0, 8), ...remote].slice(0, 15);
  }, [localActions, q, remote]);

  useEffect(() => {
    if (!open) return;
    setQ('');
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

  if (!open) return null;

  const onPick = (r: SearchResult) => {
    if (r.type === 'page') {
      router.push(r.href);
      onClose();
      return;
    }
    if (r.type === 'setting') {
      if (r.actionId === 'open_settings') router.push('/admin');
      if (r.actionId === 'open_admin') router.push('/admin');
      onClose();
      return;
    }
    if (r.type === 'node') {
      router.push(`/node/${encodeURIComponent(r.node_id || 'unknown')}`);
      onClose();
      return;
    }
    if (r.type === 'session') {
      router.push(`/session/${encodeURIComponent(r.session_id || 'unknown')}`);
      onClose();
      return;
    }
  };

  return (
    <div className="fixed inset-0 z-[70] flex items-start justify-center p-4 pt-20">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative w-full max-w-[720px] overflow-hidden rounded-2xl border border-white/10 bg-slate-950/70 backdrop-blur-xl shadow-[0_30px_90px_-50px_rgba(0,0,0,0.95)]">
        <div className="flex items-center gap-2 border-b border-white/10 px-4 py-3">
          <IconSearch className="h-4 w-4 text-slate-300" />
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search nodes, sessions, pages, settings…"
            className="w-full bg-transparent text-sm text-slate-100 outline-none placeholder:text-slate-500"
          />
          <div className="text-[10px] text-slate-500">ESC</div>
        </div>

        <div className="max-h-[420px] overflow-y-auto p-2">
          {loading && <div className="px-3 py-2 text-[11px] text-slate-500">Searching…</div>}

          {results.length === 0 ? (
            <div className="px-3 py-8 text-center text-[11px] text-slate-500">No results.</div>
          ) : (
            <ul className="space-y-1">
              {results.map((r, idx) => (
                <li key={`${r.type}-${idx}`}>
                  <button
                    onClick={() => onPick(r)}
                    className="w-full rounded-xl border border-transparent px-3 py-2 text-left hover:border-white/10 hover:bg-white/5"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="text-[12px] font-medium text-slate-100">{r.title}</div>
                      <div className="text-[10px] text-slate-500">{r.type}</div>
                    </div>
                    {r.subtitle && <div className="mt-0.5 text-[11px] text-slate-500">{r.subtitle}</div>}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="flex items-center justify-between border-t border-white/10 px-4 py-2 text-[10px] text-slate-500">
          <div>Scope: graph_id={graphId}</div>
          <div>Ctrl/Cmd+K</div>
        </div>
      </div>
    </div>
  );
}

export function TopBar({
  graphId,
  setGraphId,
  sidebarCollapsed = false,
  onToggleSidebar,
}: {
  graphId: string;
  setGraphId: (v: string) => void;
  sidebarCollapsed?: boolean;
  onToggleSidebar?: () => void;
}) {
  const router = useRouter();

  const goAdmin = (tab?: string) => {
    const t = (tab ?? '').trim();
    router.push(!t ? '/admin' : `/admin?tab=${encodeURIComponent(t)}`);
  };

  const [health, setHealth] = useState<Health>('unknown');
  const [version, setVersion] = useState<string | null>(null);
  const [healthAt, setHealthAt] = useState<string | null>(null);
  const [gpu, setGpu] = useState<{
    enabled?: boolean;
    available?: boolean;
    device?: string;
    mem_free_bytes?: number | null;
    mem_total_bytes?: number | null;
  } | null>(null);

  const [graphs, setGraphs] = useState<GraphSummary[]>([]);
  const [graphsLoaded, setGraphsLoaded] = useState(false);

  const [openWorkspace, setOpenWorkspace] = useState(false);
  const [openSettings, setOpenSettings] = useState(false);
  const [openUser, setOpenUser] = useState(false);
  const [openHealth, setOpenHealth] = useState(false);
  const [openCmdk, setOpenCmdk] = useState(false);

  const wsRef = useRef<HTMLButtonElement>(null);
  const settingsRef = useRef<HTMLButtonElement>(null);
  const userRef = useRef<HTMLButtonElement>(null);
  const healthRef = useRef<HTMLButtonElement>(null);

  // ✅ Universe preference without hydration mismatch
  const [mounted, setMounted] = useState(false);
  const [universeGraphId, setUniverseGraphId] = useState<string>('');

  useEffect(() => {
    setMounted(true);

    const read = () => {
      const u = getUniverseIdFromStorage();
      setUniverseGraphId(u ?? '');
    };

    read();

    const onStorage = (e: StorageEvent) => {
      if (e.key === LS_UNIVERSE_KEY) read();
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, []);

  const effectiveGraphId = mounted && universeGraphId ? universeGraphId : graphId;

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
          setHealth('down');
          setHealthAt(new Date().toISOString());
        }
      }
    };

    void tick();
    const id = window.setInterval(() => void tick(), 15000);

    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  // ✅ If Universe exists, keep app state aligned
  useEffect(() => {
    const u = getUniverseIdFromStorage();
    if (u) setGraphId(u);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ✅ Only fetch remote graphs when API_BASE_URL is absolute (prevents 404 spam)
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

      // local-only fallback: show Universe (if known) else current effective id
      // local-only fallback: resolve Universe id (U:...) and NEVER show non-U ids (e.g. 'RAVIN_MAIN')
      const universe = getUniverseIdFromStorage() ?? (await resolveUniverseIdOnce());
      if (!cancelled && universe) setUniverseGraphId(universe);

      const idToShow =
        universe ?? (effectiveGraphId.startsWith('U:') ? effectiveGraphId : 'U:(resolving)');
 
      setGraphs([{ id: idToShow, name: 'Universe' }]);
      setGraphsLoaded(true);

    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const isK = e.key.toLowerCase() === 'k';
      const mod = e.metaKey || e.ctrlKey;
      if (mod && isK) {
        e.preventDefault();
        setOpenCmdk(true);
        setOpenWorkspace(false);
        setOpenSettings(false);
        setOpenUser(false);
        setOpenHealth(false);
      }
      if (e.key === 'Escape') {
        setOpenCmdk(false);
        setOpenWorkspace(false);
        setOpenSettings(false);
        setOpenUser(false);
        setOpenHealth(false);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const currentGraph = useMemo(() => {
    const found = graphs.find((g) => g.id === effectiveGraphId);
    if (found) return found;
    return { id: effectiveGraphId, name: 'Workspace' };
  }, [graphs, effectiveGraphId]);

  const healthLabel =
    health === 'ok'
      ? 'FAIM Core: OK'
      : health === 'degraded'
        ? 'FAIM Core: Degraded'
        : health === 'down'
          ? 'FAIM Core: DOWN'
          : 'FAIM Core: …';

  const healthClass =
    health === 'ok'
      ? 'bg-emerald-500/12 text-emerald-300 border-emerald-500/30'
      : health === 'degraded'
        ? 'bg-amber-500/12 text-amber-300 border-amber-500/30'
        : health === 'down'
          ? 'bg-rose-500/12 text-rose-300 border-rose-500/30'
          : 'bg-slate-700/25 text-slate-200 border-slate-500/25';

  const gpuActive = !!(gpu?.enabled && gpu?.available);
  const gpuLabel = gpuActive ? 'GPU active' : gpu?.enabled ? 'GPU enabled (no CUDA)' : 'GPU off';

  const formatBytes = (value?: number | null) => {
    if (!value || value <= 0) return '—';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let idx = 0;
    let v = value;
    while (v >= 1024 && idx < units.length - 1) {
      v /= 1024;
      idx += 1;
    }
    return `${v.toFixed(v >= 10 ? 1 : 2)} ${units[idx]}`;
  };

  const [density, setDensity] = useState<'comfortable' | 'compact'>(() => {
    if (typeof window === 'undefined') return 'comfortable';
    return (window.localStorage.getItem(LS_UI_DENSITY) as any) || 'comfortable';
  });
  const [debugUi, setDebugUi] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    return window.localStorage.getItem(LS_UI_DEBUG) === '1';
  });
  useEffect(() => {
    try {
      window.localStorage.setItem(LS_UI_DENSITY, density);
      window.localStorage.setItem(LS_UI_DEBUG, debugUi ? '1' : '0');
    } catch {
      // ignore
    }
  }, [density, debugUi]);

  const createWorkspace = async () => {
    const name = window.prompt('New workspace name:', 'New Workspace');
    if (!name) return;

    const tmpId = `local-${Date.now()}`;
    const next = { id: tmpId, name };
    setGraphs((prev) => [next, ...prev]);
    setGraphId(tmpId);
    setOpenWorkspace(false);

    try {
      if (!isRemoteApiBase()) return;
      const base = (API_BASE_URL || '').trim().replace(/\/+$/, '');
      await fetch(`${base}/graphs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...buildFaimHeaders() },
        body: JSON.stringify({ name }),
      });
    } catch {
      // keep local-only until backend exists
    }
  };

  const renameWorkspace = async (g: GraphSummary) => {
    const name = window.prompt('Rename workspace:', g.name);
    if (!name || name.trim() === g.name) return;

    setGraphs((prev) => prev.map((x) => (x.id === g.id ? { ...x, name: name.trim() } : x)));
    setOpenWorkspace(false);

    try {
      if (!isRemoteApiBase()) return;
      const base = (API_BASE_URL || '').trim().replace(/\/+$/, '');
      await fetch(`${base}/graphs/${encodeURIComponent(g.id)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', ...buildFaimHeaders() },
        body: JSON.stringify({ name: name.trim() }),
      });
    } catch {}
  };

  const duplicateWorkspace = async (g: GraphSummary) => {
    const name = window.prompt('Duplicate workspace as:', `${g.name} Copy`);
    if (!name) return;

    const tmpId = `local-${Date.now()}`;
    setGraphs((prev) => [{ id: tmpId, name }, ...prev]);
    setGraphId(tmpId);
    setOpenWorkspace(false);

    try {
      if (!isRemoteApiBase()) return;
      const base = (API_BASE_URL || '').trim().replace(/\/+$/, '');
      await fetch(`${base}/graphs/${encodeURIComponent(g.id)}/duplicate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...buildFaimHeaders() },
        body: JSON.stringify({ name }),
      });
    } catch {}
  };

  const deleteWorkspace = async (g: GraphSummary) => {
    const ok = window.confirm(
      `Delete workspace "${g.name}"?\n\nThis should be irreversible in production.\n(If backend does not support this yet, UI will just remove locally.)`,
    );
    if (!ok) return;

    setGraphs((prev) => prev.filter((x) => x.id !== g.id));
    if (graphId === g.id) setGraphId(DEFAULT_GRAPH_ID);
    setOpenWorkspace(false);

    try {
      if (!isRemoteApiBase()) return;
      const base = (API_BASE_URL || '').trim().replace(/\/+$/, '');
      await fetch(`${base}/graphs/${encodeURIComponent(g.id)}`, { method: 'DELETE', headers: buildFaimHeaders() });
    } catch {}
  };

  return (
    <>
      <header className="relative z-20 border-b border-white/10 bg-white/5 px-6 py-3 backdrop-blur">
        <div className="flex items-center justify-between gap-3">
          {/* LEFT: Workspace selector */}
          <div className="relative flex min-w-0 items-center gap-3">
            {onToggleSidebar && (
              <button
                onClick={onToggleSidebar}
                className="rounded-xl border border-white/10 bg-black/20 p-2 hover:border-white/15 hover:bg-white/5"
                title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
                aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              >
                <IconSidebar className="h-4 w-4 text-slate-300" />
              </button>
            )}
            <button
              ref={wsRef}
              onClick={() => {
                setOpenWorkspace((v) => !v);
                setOpenSettings(false);
                setOpenUser(false);
                setOpenHealth(false);
              }}
              className={cx(
                'flex min-w-0 items-center gap-2 rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-xs',
                'hover:border-white/15 hover:bg-white/5',
              )}
              title="Workspace (graph context)"
            >
              <span className="text-slate-300/70">Workspace</span>
              <span className="mx-1 h-3 w-px bg-white/10" />
              <span className="truncate text-slate-100">{currentGraph.name}</span>
              <IconChevron className="h-4 w-4 text-slate-300/70" />
            </button>

            <Dropdown
              open={openWorkspace}
              anchorRef={wsRef}
              onClose={() => setOpenWorkspace(false)}
              className="left-0 right-auto w-[360px]"
            >
              <div className="p-3">
                <div className="mb-2 flex items-center justify-between">
                  <div className="text-[11px] font-semibold text-slate-200">Workspaces</div>
                  <button
                    onClick={createWorkspace}
                    className="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-[10px] text-slate-200 hover:bg-white/10"
                  >
                    + New
                  </button>
                </div>

                <div className="mb-2 text-[10px] text-slate-500">
                  Scope for memory, metrics, FIG, and retrieval. (graph_id stays internal)
                </div>

                <div className="max-h-[280px] overflow-y-auto rounded-xl border border-white/10">
                  {graphsLoaded && graphs.length === 0 ? (
                    <div className="px-3 py-6 text-center text-[11px] text-slate-500">No workspaces found.</div>
                  ) : (
                    <ul className="divide-y divide-white/10">
                      {graphs.map((g) => {
                        const active = g.id === effectiveGraphId;
                        return (
                          <li key={g.id} className={cx('px-3 py-2', active && 'bg-white/5')}>
                            <div className="flex items-center justify-between gap-2">
                              <button
                                className="min-w-0 flex-1 text-left"
                                onClick={() => {
                                  setGraphId(g.id);
                                  setOpenWorkspace(false);
                                }}
                                title={'id: ${g.id}'}
                              >
                                <div className="truncate text-[12px] font-medium text-slate-100">{g.name}</div>
                                <div className="truncate text-[10px] text-slate-500">id: {g.id}</div>
                              </button>

                              <div className="flex items-center gap-1">
                                <button
                                  className="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-[10px] text-slate-200 hover:bg-white/10"
                                  onClick={() => renameWorkspace(g)}
                                >
                                  Rename
                                </button>
                                <button
                                  className="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-[10px] text-slate-200 hover:bg-white/10"
                                  onClick={() => duplicateWorkspace(g)}
                                >
                                  Copy
                                </button>
                                <button
                                  className="rounded-lg border border-rose-500/20 bg-rose-500/10 px-2 py-1 text-[10px] text-rose-200 hover:bg-rose-500/15"
                                  onClick={() => deleteWorkspace(g)}
                                >
                                  Delete
                                </button>
                              </div>
                            </div>
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </div>

                <div className="mt-2 text-[10px] text-slate-500">
                  Tip: In production, show only display name; id stays internal (uuid/slug).
                </div>
              </div>
            </Dropdown>
          </div>

          {/* CENTER: Search (Cmd/Ctrl+K) */}
          <button
            onClick={() => setOpenCmdk(true)}
            className={cx(
              'hidden w-[520px] max-w-[45vw] items-center gap-2 rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-xs md:flex',
              'hover:border-white/15 hover:bg-white/5',
            )}
            title="Search (Cmd/Ctrl+K)"
          >
            <IconSearch className="h-4 w-4 text-slate-300/70" />
            <span className="truncate text-slate-300/70">Search nodes, sessions, settings…</span>
            <span className="ml-auto rounded-md border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] text-slate-300/80">
              Ctrl / ⌘ K
            </span>
          </button>

          {/* RIGHT: Settings + User + Health */}
          <div className="relative flex items-center gap-2">
            {/* Settings */}
            <div className="relative">
              <button
                ref={settingsRef}
                onClick={() => {
                  setOpenSettings((v) => !v);
                  setOpenWorkspace(false);
                  setOpenUser(false);
                  setOpenHealth(false);
                }}
                className="rounded-xl border border-white/10 bg-black/20 p-2 hover:border-white/15 hover:bg-white/5"
                title="Settings"
              >
                <IconGear className="h-4 w-4 text-slate-300" />
              </button>

              <Dropdown open={openSettings} anchorRef={settingsRef} onClose={() => setOpenSettings(false)}>
                <div className="p-3">
                  <div className="mb-2 text-[11px] font-semibold text-slate-200">Quick settings</div>

                  <div className="space-y-2 rounded-xl border border-white/10 p-3">
                    <div className="flex items-center justify-between">
                      <div className="text-[11px] text-slate-300">UI density</div>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => setDensity('comfortable')}
                          className={cx(
                            'rounded-lg border px-2 py-1 text-[10px]',
                            density === 'comfortable'
                              ? 'border-cyan-500/30 bg-cyan-500/10 text-cyan-200'
                              : 'border-white/10 bg-white/5 text-slate-200 hover:bg-white/10',
                          )}
                        >
                          Comfortable
                        </button>
                        <button
                          onClick={() => setDensity('compact')}
                          className={cx(
                            'rounded-lg border px-2 py-1 text-[10px]',
                            density === 'compact'
                              ? 'border-cyan-500/30 bg-cyan-500/10 text-cyan-200'
                              : 'border-white/10 bg-white/5 text-slate-200 hover:bg-white/10',
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
                          'rounded-lg border px-2 py-1 text-[10px]',
                          debugUi
                            ? 'border-violet-500/30 bg-violet-500/10 text-violet-200'
                            : 'border-white/10 bg-white/5 text-slate-200 hover:bg-white/10',
                        )}
                      >
                        {debugUi ? 'ON' : 'OFF'}
                      </button>
                    </div>

                    <div className="text-[10px] text-slate-500">Cmd/Ctrl+K: Search · ESC: close menus</div>
                  </div>

                  <div className="mt-2 grid grid-cols-2 gap-2">
                    <button
                      onClick={() => {
                        setOpenSettings(false);
                        goAdmin('account');
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

            {/* User */}
            <div className="relative">
              <button
                ref={userRef}
                onClick={() => {
                  setOpenUser((v) => !v);
                  setOpenWorkspace(false);
                  setOpenSettings(false);
                  setOpenHealth(false);
                }}
                className="rounded-xl border border-white/10 bg-black/20 p-2 hover:border-white/15 hover:bg-white/5"
                title="Profile"
              >
                <IconUser className="h-4 w-4 text-slate-300" />
              </button>

              <Dropdown open={openUser} anchorRef={userRef} onClose={() => setOpenUser(false)}>
                <div className="p-3">
                  <div className="mb-2 flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/5 text-[12px] text-slate-200">
                      U
                    </div>
                    <div className="min-w-0">
                      <div className="truncate text-[12px] font-semibold text-slate-100">Local User</div>
                      <div className="truncate text-[10px] text-slate-500">(auth not wired yet)</div>
                    </div>
                  </div>

                  <div className="space-y-1 rounded-xl border border-white/10 p-2">
                    <button
                      onClick={() => {
                        setOpenUser(false);
                        goAdmin('profile');
                      }}
                      className="w-full rounded-lg px-3 py-2 text-left text-[11px] text-slate-200 hover:bg-white/5"
                    >
                      Profile
                    </button>
                    <button
                      onClick={() => {
                        setOpenUser(false);
                        goAdmin('account');
                      }}
                      className="w-full rounded-lg px-3 py-2 text-left text-[11px] text-slate-200 hover:bg-white/5"
                    >
                      Account (delete / clear data)
                    </button>
                    <button
                      onClick={() => {
                        setOpenUser(false);
                        goAdmin('apikeys');
                      }}
                      className="w-full rounded-lg px-3 py-2 text-left text-[11px] text-slate-200 hover:bg-white/5"
                    >
                    API Keys (FAIM)
                    </button>
                    <button
                      onClick={() => {
                        setOpenUser(false);
                        goAdmin('billing');
                      }}
                      className="w-full rounded-lg px-3 py-2 text-left text-[11px] text-slate-200 hover:bg-white/5"
                    >
                      Billing / receipts (future)
                    </button>
                    <button
                      onClick={() => {
                        setOpenUser(false);
                        goAdmin();
                      }}
                      className="w-full rounded-lg px-3 py-2 text-left text-[11px] text-slate-200 hover:bg-white/5"
                    >
                      Admin console (block / freeze / terminate)
                    </button>
                  </div>

                  <div className="mt-2 rounded-xl border border-rose-500/20 bg-rose-500/10 p-2">
                    <button
                      onClick={() => {
                        setOpenUser(false);
                        alert('Logout requires auth wiring (future).');
                      }}
                      className="w-full rounded-lg px-3 py-2 text-left text-[11px] text-rose-200 hover:bg-rose-500/10"
                    >
                      Log out
                    </button>
                  </div>

                  <div className="mt-2 text-[10px] text-slate-500">
                    Admin actions must be audited + consented in production (privacy + refunds + records).
                  </div>
                </div>
              </Dropdown>
            </div>

            {/* Health */}
            <div className="relative">
              <button
                ref={healthRef}
                onClick={() => {
                  setOpenHealth((v) => !v);
                  setOpenWorkspace(false);
                  setOpenSettings(false);
                  setOpenUser(false);
                }}
                className={cx('flex items-center gap-2 rounded-full border px-3 py-2 text-xs', healthClass)}
                title="FAIM backend health"
              >
                <span className="h-2 w-2 rounded-full bg-current" />
                <span>{healthLabel}</span>
                {version && <span className="hidden text-[10px] text-slate-300/60 sm:inline">v{version}</span>}
                {gpuActive && (
                  <span className="rounded-full border border-sky-400/30 bg-sky-500/10 px-2 py-0.5 text-[10px] text-sky-100">
                    GPU active
                  </span>
                )}
              </button>

              <Dropdown open={openHealth} anchorRef={healthRef} onClose={() => setOpenHealth(false)} className="w-[340px]">
                <div className="p-3">
                  <div className="text-[11px] font-semibold text-slate-200">System status</div>
                  <div className="mt-2 rounded-xl border border-white/10 p-3 text-[11px] text-slate-300">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400">Status</span>
                      <span className="font-medium text-slate-100">{health}</span>
                    </div>
                    <div className="mt-1 flex items-center justify-between">
                      <span className="text-slate-400">Version</span>
                      <span className="font-medium text-slate-100">{version ?? '—'}</span>
                    </div>
                    <div className="mt-1 flex items-center justify-between">
                      <span className="text-slate-400">Last check</span>
                      <span className="font-medium text-slate-100">
                        {healthAt ? new Date(healthAt).toLocaleTimeString() : '—'}
                      </span>
                    </div>
                    <div className="mt-1 flex items-center justify-between">
                      <span className="text-slate-400">GPU</span>
                      <span className="font-medium text-slate-100">{gpuLabel}</span>
                    </div>
                    {gpu?.device && (
                      <div className="mt-1 flex items-center justify-between">
                        <span className="text-slate-400">GPU device</span>
                        <span className="font-medium text-slate-100">{gpu.device}</span>
                      </div>
                    )}
                    {gpu?.mem_total_bytes ? (
                      <div className="mt-1 flex items-center justify-between">
                        <span className="text-slate-400">GPU memory</span>
                        <span className="font-medium text-slate-100">
                          {formatBytes(gpu.mem_free_bytes)} free / {formatBytes(gpu.mem_total_bytes)}
                        </span>
                      </div>
                    ) : null}
                  </div>

                  <div className="mt-2 grid grid-cols-2 gap-2">
                    <button
                      onClick={() => {
                        setOpenHealth(false);
                        router.push('/dashboard');
                      }}
                      className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-[11px] text-slate-200 hover:bg-white/10"
                    >
                      Open Dashboard
                    </button>
                    <button
                      onClick={() => {
                        setOpenHealth(false);
                        router.push('/dashboard');
                      }}
                      className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-[11px] text-slate-200 hover:bg-white/10"
                    >
                      Runtime panel
                    </button>
                  </div>
                </div>
              </Dropdown>
            </div>
          </div>
        </div>
      </header>

      <CommandPalette open={openCmdk} onClose={() => setOpenCmdk(false)} graphId={effectiveGraphId} />
    </>
  );
}
