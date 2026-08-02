"use client";

import React, {
  useEffect,
  useState,
  useCallback,
  useRef,
  useMemo,
} from "react";
import {
  History,
  Filter,
  ChevronDown,
  AlertCircle,
  RefreshCw,
  Layers,
  Clock,
  ShieldCheck,
  Activity,
  ChevronRight,
} from "lucide-react";
import { getSession } from "next-auth/react";
import { GlassHeader } from "@/components/layout/GlassHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { readJsonSafely } from "@/lib/safeFetch";
import { useUser } from "@/contexts/UserContext";

// ─── Types ────────────────────────────────────────────────────────────────────

interface FaimEvent {
  seq: number;
  id: string;
  kind: string;
  ts: string | null;
  payload: Record<string, unknown>;
  checksum: string;
}

interface LatestInfo {
  last_seq: number;
  last_kind: string | null;
  last_ts: string | null;
  event_count: number;
  snapshot_hash: string | null;
}

// ─── Auth helper ──────────────────────────────────────────────────────────────

async function authHeaders(): Promise<Record<string, string>> {
  const session = await getSession();
  const token = (session as { accessToken?: string } | null)?.accessToken;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ─── Time helpers ─────────────────────────────────────────────────────────────

function relativeTime(ts: string | null): string {
  if (!ts) return "—";
  const diff = Date.now() - new Date(ts).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d < 7) return `${d}d ago`;
  return new Date(ts).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

function absoluteTime(ts: string | null): string {
  if (!ts) return "—";
  return new Date(ts).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

// ─── Kind metadata ────────────────────────────────────────────────────────────

interface KindMeta {
  color: string;
  bg: string;
  dot: string;
  description: string;
}

// Exact backend kind → meta mapping (uppercase as emitted by backend)
const KIND_MAP: Record<string, KindMeta> = {
  // Node operations
  NODE_UPSERT: {
    color: "text-emerald-400",
    bg: "bg-emerald-500/10 border-emerald-500/20",
    dot: "bg-emerald-400",
    description: "Node created or updated in graph",
  },
  INVENT_MACRO_NODE: {
    color: "text-violet-400",
    bg: "bg-violet-500/10 border-violet-500/20",
    dot: "bg-violet-400",
    description: "Macro node invented from patterns",
  },
  PRUNE_NODE: {
    color: "text-rose-400",
    bg: "bg-rose-500/10 border-rose-500/20",
    dot: "bg-rose-400",
    description: "Low-value node pruned from graph",
  },
  // Merge
  MERGE: {
    color: "text-violet-400",
    bg: "bg-violet-500/10 border-violet-500/20",
    dot: "bg-violet-400",
    description: "Nodes merged and consolidated",
  },
  EVOLUTION_MERGE: {
    color: "text-violet-400",
    bg: "bg-violet-500/10 border-violet-500/20",
    dot: "bg-violet-400",
    description: "Evolution-driven node merge",
  },
  // Evolution
  EVOLUTION_COMPLETE: {
    color: "text-amber-400",
    bg: "bg-amber-500/10 border-amber-500/20",
    dot: "bg-amber-400",
    description: "Evolution cycle completed",
  },
  EVOLUTION_SKIPPED: {
    color: "text-slate-400",
    bg: "bg-slate-500/10 border-slate-500/20",
    dot: "bg-slate-400",
    description: "Evolution cycle skipped (no changes)",
  },
  EVOLUTION_INVENTION_SUMMARY: {
    color: "text-amber-400",
    bg: "bg-amber-500/10 border-amber-500/20",
    dot: "bg-amber-400",
    description: "Invention summary from evolution",
  },
  EVOLUTION_INVENTION_ERROR: {
    color: "text-rose-400",
    bg: "bg-rose-500/10 border-rose-500/20",
    dot: "bg-rose-400",
    description: "Invention error during evolution",
  },
  // Graph state
  GRAPH_VERSION_BUMP: {
    color: "text-sky-400",
    bg: "bg-sky-500/10 border-sky-500/20",
    dot: "bg-sky-400",
    description: "Graph version incremented",
  },
  INHERITANCE_SET: {
    color: "text-blue-400",
    bg: "bg-blue-500/10 border-blue-500/20",
    dot: "bg-blue-400",
    description: "Inheritance edge established",
  },
  DIAGNOSTICS_SNAPSHOT: {
    color: "text-sky-400",
    bg: "bg-sky-500/10 border-sky-500/20",
    dot: "bg-sky-400",
    description: "Diagnostic snapshot recorded",
  },
  // Query
  QUERY_START: {
    color: "text-cyan-400",
    bg: "bg-cyan-500/10 border-cyan-500/20",
    dot: "bg-cyan-400",
    description: "Memory query initiated",
  },
  QUERY_RERANKED: {
    color: "text-cyan-400",
    bg: "bg-cyan-500/10 border-cyan-500/20",
    dot: "bg-cyan-400",
    description: "Query results re-ranked",
  },
  QUERY_TOUCH: {
    color: "text-cyan-400",
    bg: "bg-cyan-500/10 border-cyan-500/20",
    dot: "bg-cyan-400",
    description: "Memory node touched via query",
  },
  QUERY_COMPLETE: {
    color: "text-cyan-400",
    bg: "bg-cyan-500/10 border-cyan-500/20",
    dot: "bg-cyan-400",
    description: "Query completed successfully",
  },
  // Storage
  STORAGE_RAW_STORED: {
    color: "text-emerald-400",
    bg: "bg-emerald-500/10 border-emerald-500/20",
    dot: "bg-emerald-400",
    description: "Raw file stored to storage",
  },
  STORAGE_ENCRYPT_FAILED: {
    color: "text-rose-400",
    bg: "bg-rose-500/10 border-rose-500/20",
    dot: "bg-rose-400",
    description: "Storage encryption failed",
  },
  storage_upload: {
    color: "text-emerald-400",
    bg: "bg-emerald-500/10 border-emerald-500/20",
    dot: "bg-emerald-400",
    description: "File uploaded to storage",
  },
  // Ingest
  ingest_secondary_index: {
    color: "text-emerald-400",
    bg: "bg-emerald-500/10 border-emerald-500/20",
    dot: "bg-emerald-400",
    description: "Secondary index ingested",
  },
  evolve: {
    color: "text-amber-400",
    bg: "bg-amber-500/10 border-amber-500/20",
    dot: "bg-amber-400",
    description: "Evolution triggered",
  },
};

function getKindMeta(kind: string): KindMeta {
  // Try exact match first (handles both UPPER_CASE and lower_case)
  if (KIND_MAP[kind]) return KIND_MAP[kind];

  // Fallback: substring matching on lowercase for unknown future kinds
  const k = kind.toLowerCase();
  if (
    k.includes("upsert") ||
    k.includes("add") ||
    k.includes("ingest") ||
    k.includes("creat") ||
    k.includes("insert") ||
    k.includes("store") ||
    k.includes("upload")
  )
    return {
      color: "text-emerald-400",
      bg: "bg-emerald-500/10 border-emerald-500/20",
      dot: "bg-emerald-400",
      description: "Creation or ingestion event",
    };
  if (
    k.includes("evolv") ||
    k.includes("updat") ||
    k.includes("modif") ||
    k.includes("bump")
  )
    return {
      color: "text-amber-400",
      bg: "bg-amber-500/10 border-amber-500/20",
      dot: "bg-amber-400",
      description: "Knowledge structure updated",
    };
  if (k.includes("merg") || k.includes("consolid") || k.includes("invent"))
    return {
      color: "text-violet-400",
      bg: "bg-violet-500/10 border-violet-500/20",
      dot: "bg-violet-400",
      description: "Memory consolidation event",
    };
  if (
    k.includes("delet") ||
    k.includes("remov") ||
    k.includes("prun") ||
    k.includes("drop") ||
    k.includes("error") ||
    k.includes("fail")
  )
    return {
      color: "text-rose-400",
      bg: "bg-rose-500/10 border-rose-500/20",
      dot: "bg-rose-400",
      description: "Removal or error event",
    };
  if (
    k.includes("touch") ||
    k.includes("recall") ||
    k.includes("quer") ||
    k.includes("read") ||
    k.includes("access")
  )
    return {
      color: "text-cyan-400",
      bg: "bg-cyan-500/10 border-cyan-500/20",
      dot: "bg-cyan-400",
      description: "Context access event",
    };
  if (
    k.includes("edge") ||
    k.includes("link") ||
    k.includes("inherit") ||
    k.includes("connect")
  )
    return {
      color: "text-blue-400",
      bg: "bg-blue-500/10 border-blue-500/20",
      dot: "bg-blue-400",
      description: "Graph edge operation",
    };
  if (
    k.includes("snapshot") ||
    k.includes("backup") ||
    k.includes("version") ||
    k.includes("checkpoint")
  )
    return {
      color: "text-sky-400",
      bg: "bg-sky-500/10 border-sky-500/20",
      dot: "bg-sky-400",
      description: "State snapshot recorded",
    };
  return {
    color: "text-slate-400",
    bg: "bg-slate-500/10 border-slate-500/20",
    dot: "bg-slate-400",
    description: "System event",
  };
}

// ─── Constants ────────────────────────────────────────────────────────────────

const PAGE_SIZE = 50;
const POLL_INTERVAL_MS = 6000;

// ─── Journal Page ─────────────────────────────────────────────────────────────

export default function JournalPage() {
  const { graphId, isLoading: userLoading } = useUser();

  const [events, setEvents] = useState<FaimEvent[]>([]);
  const [latest, setLatest] = useState<LatestInfo | null>(null);
  const [kindFilter, setKindFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadingOlder, setLoadingOlder] = useState(false);
  const [hasOlder, setHasOlder] = useState(false);
  const [liveConnected, setLiveConnected] = useState(false);
  const [newCount, setNewCount] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const oldestSeqRef = useRef<number>(Infinity);
  const latestSeqRef = useRef<number>(0);
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Fetch latest info ─────────────────────────────────────────────────────

  const fetchLatest = useCallback(
    async (gid: string): Promise<LatestInfo | null> => {
      try {
        const headers = await authHeaders();
        const res = await fetch(
          `/api/v1/events/latest?graph_id=${encodeURIComponent(gid)}`,
          { headers, cache: "no-store" },
        );
        if (res.ok) {
          const data = await readJsonSafely<LatestInfo>(res);
          if (!data) return null;
          setLatest(data);
          return data;
        }
      } catch {
        /* non-fatal */
      }
      return null;
    },
    [],
  );

  // ── Fetch a page of events ────────────────────────────────────────────────

  const fetchEventsPage = useCallback(
    async (
      gid: string,
      afterSeq: number,
      limit = PAGE_SIZE,
    ): Promise<{ events: FaimEvent[]; hasMore: boolean }> => {
      const headers = await authHeaders();
      const res = await fetch(
        `/api/v1/events?graph_id=${encodeURIComponent(gid)}&after_seq=${afterSeq}&limit=${limit}`,
        { headers, cache: "no-store" },
      );
      if (!res.ok) throw new Error(`Events request failed (${res.status})`);
      const data = await readJsonSafely<{
        events?: FaimEvent[];
        has_more?: boolean;
      }>(res);
      if (!data) throw new Error("Invalid events response");
      return {
        events: (data.events ?? []) as FaimEvent[],
        hasMore: !!data.has_more,
      };
    },
    [],
  );

  // ── Initial load ──────────────────────────────────────────────────────────

  const initialLoad = useCallback(
    async (gid: string) => {
      setLoading(true);
      setError(null);
      try {
        const info = await fetchLatest(gid);
        const lastSeq = info?.last_seq ?? 0;

        // Fetch the most recent PAGE_SIZE events by starting near the end
        const startSeq = Math.max(0, lastSeq - PAGE_SIZE);
        const { events: fetched } = await fetchEventsPage(
          gid,
          startSeq,
          PAGE_SIZE,
        );

        // Show newest first
        const sorted = [...fetched].sort((a, b) => b.seq - a.seq);
        setEvents(sorted);
        setNewCount(0);

        if (sorted.length > 0) {
          latestSeqRef.current = sorted[0].seq;
          oldestSeqRef.current = sorted[sorted.length - 1].seq;
        } else {
          latestSeqRef.current = lastSeq;
          oldestSeqRef.current = 0;
        }

        setHasOlder(startSeq > 0);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to load events");
      } finally {
        setLoading(false);
      }
    },
    [fetchLatest, fetchEventsPage],
  );

  // ── Load older ────────────────────────────────────────────────────────────

  const loadOlder = useCallback(async () => {
    if (!graphId || loadingOlder) return;
    const currentOldest = oldestSeqRef.current;
    if (!isFinite(currentOldest) || currentOldest <= 1) {
      setHasOlder(false);
      return;
    }

    setLoadingOlder(true);
    try {
      // Fetch events before currentOldest seq
      const startSeq = Math.max(0, currentOldest - 1 - PAGE_SIZE);
      const { events: fetched } = await fetchEventsPage(
        graphId,
        startSeq,
        PAGE_SIZE,
      );

      // Keep only events strictly older than what we have
      const older = fetched
        .filter((e) => e.seq < currentOldest)
        .sort((a, b) => b.seq - a.seq);

      if (older.length === 0) {
        setHasOlder(false);
        return;
      }

      setEvents((prev) => [...prev, ...older]);
      const newOldest = older[older.length - 1].seq;
      oldestSeqRef.current = newOldest;
      setHasOlder(newOldest > 1);
    } catch {
      /* non-fatal */
    } finally {
      setLoadingOlder(false);
    }
  }, [graphId, loadingOlder, fetchEventsPage]);

  // ── Live polling for new events ───────────────────────────────────────────

  const pollForNew = useCallback(
    async (gid: string) => {
      try {
        const info = await fetchLatest(gid);
        if (!info) return;

        const serverLastSeq = info.last_seq;
        if (serverLastSeq <= latestSeqRef.current) return;

        // There are new events — fetch them
        const { events: fetched } = await fetchEventsPage(
          gid,
          latestSeqRef.current,
          PAGE_SIZE,
        );
        const newer = fetched
          .filter((e) => e.seq > latestSeqRef.current)
          .sort((a, b) => b.seq - a.seq);

        if (newer.length === 0) return;

        setEvents((prev) => {
          const existingIds = new Set(prev.map((e) => e.id));
          const deduped = newer.filter((e) => !existingIds.has(e.id));
          if (deduped.length === 0) return prev;
          setNewCount((c) => c + deduped.length);
          return [...deduped, ...prev];
        });

        latestSeqRef.current = newer[0].seq;
        setLiveConnected(true);
      } catch {
        setLiveConnected(false);
      }
    },
    [fetchLatest, fetchEventsPage],
  );

  // ── Effects ───────────────────────────────────────────────────────────────

  useEffect(() => {
    if (userLoading || !graphId) return;

    initialLoad(graphId);

    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, [graphId, userLoading]); // eslint-disable-line react-hooks/exhaustive-deps

  // Start polling once initial load is done
  useEffect(() => {
    if (!graphId || loading || userLoading) return;

    setLiveConnected(true);
    pollTimerRef.current = setInterval(
      () => pollForNew(graphId),
      POLL_INTERVAL_MS,
    );

    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
      setLiveConnected(false);
    };
  }, [graphId, loading, userLoading, pollForNew]);

  // ── Derived state ─────────────────────────────────────────────────────────

  const allKinds = useMemo(
    () => Array.from(new Set(events.map((e) => e.kind))).sort(),
    [events],
  );

  const kindOptions = useMemo(
    () => [
      { value: "", label: "ALL KINDS" },
      ...allKinds.map((k) => ({ value: k, label: k })),
    ],
    [allKinds],
  );

  const filteredEvents = useMemo(
    () => (kindFilter ? events.filter((e) => e.kind === kindFilter) : events),
    [events, kindFilter],
  );

  // ── Refresh ───────────────────────────────────────────────────────────────

  const handleRefresh = useCallback(() => {
    if (!graphId) return;
    if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    setNewCount(0);
    initialLoad(graphId);
  }, [graphId, initialLoad]);

  const isReady = !userLoading && !!graphId;

  // ─── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col gap-4 h-full" style={{ minHeight: 0 }}>
      <div className="faim-grid" />

      {/* ── Header ── */}
      <GlassHeader
        title="Neural Audit Journal"
        subtitle="Live feed of all memory graph operations, mutations, and system events"
        icon={History}
        actions={
          <div className="flex items-center gap-2">
            <div
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border"
              style={{
                borderColor: liveConnected
                  ? "rgba(52,211,153,0.3)"
                  : "var(--os-stroke)",
                background: liveConnected
                  ? "rgba(52,211,153,0.06)"
                  : "var(--os-surface-2)",
              }}
            >
              <div
                className={`h-1.5 w-1.5 rounded-full ${
                  liveConnected
                    ? "bg-emerald-400 animate-pulse shadow-[0_0_6px_rgba(52,211,153,0.8)]"
                    : "bg-slate-600"
                }`}
              />
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
                {liveConnected ? "Live" : "Paused"}
              </span>
            </div>

            {newCount > 0 && (
              <Badge variant="primary" size="sm">
                +{newCount} new
              </Badge>
            )}

            <Button
              size="sm"
              variant="outline"
              leftIcon={<RefreshCw size={13} />}
              onClick={handleRefresh}
              disabled={loading}
            >
              Refresh
            </Button>
          </div>
        }
      />

      {/* ── Error banner ── */}
      {error && (
        <div
          className="flex items-center gap-3 px-4 py-3 rounded-xl border text-rose-400 text-sm font-medium"
          style={{
            borderColor: "rgba(248,113,113,0.2)",
            background: "rgba(248,113,113,0.05)",
          }}
        >
          <AlertCircle size={16} className="shrink-0" />
          <span className="flex-1 min-w-0">{error}</span>
          <Button
            variant="ghost"
            size="xs"
            onClick={handleRefresh}
            className="text-rose-400 shrink-0"
          >
            Retry
          </Button>
        </div>
      )}

      {/* ── No graph selected ── */}
      {!isReady && !userLoading && (
        <div className="flex flex-col items-center justify-center flex-1 gap-3 py-20 text-center">
          <Activity size={40} className="text-slate-700" />
          <p className="text-sm font-medium text-slate-500">
            No graph connected
          </p>
          <p className="text-xs text-slate-600">
            Connect a memory graph to view its audit journal
          </p>
        </div>
      )}

      {/* ── Loading skeleton ── */}
      {userLoading && (
        <div className="flex flex-col items-center justify-center flex-1 gap-3 py-20">
          <div className="h-8 w-8 rounded-full border-2 border-cyan-500/30 border-t-cyan-400 animate-spin" />
          <p className="text-[11px] text-slate-500 uppercase tracking-widest font-bold">
            Connecting...
          </p>
        </div>
      )}

      {isReady && (
        <>
          {/* ── Metric strip ── */}
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3 shrink-0">
            {[
              {
                label: "Total Events",
                value:
                  latest?.event_count != null
                    ? latest.event_count.toLocaleString()
                    : "—",
                sub:
                  newCount > 0 ? `+${newCount} since last refresh` : "All time",
                icon: <Layers size={15} />,
                color: "text-cyan-300",
                topBorder: "border-t-2 border-t-cyan-400 shadow-[0_-4px_12px_rgba(34,211,238,0.15)]",
                glow: "from-cyan-500/10 to-transparent",
              },
              {
                label: "Last Kind",
                value: latest?.last_kind ?? "—",
                sub: latest?.last_kind
                  ? getKindMeta(latest.last_kind).description
                  : "Waiting for events",
                icon: <Activity size={15} />,
                color: latest?.last_kind
                  ? getKindMeta(latest.last_kind).color
                  : "text-slate-400",
                topBorder: "border-t-2 border-t-violet-400 shadow-[0_-4px_12px_rgba(167,139,250,0.15)]",
                glow: "from-violet-500/10 to-transparent",
              },
              {
                label: "Last Activity",
                value: relativeTime(latest?.last_ts ?? null),
                sub: absoluteTime(latest?.last_ts ?? null),
                icon: <Clock size={15} />,
                color: "text-amber-300",
                topBorder: "border-t-2 border-t-amber-400 shadow-[0_-4px_12px_rgba(251,191,36,0.15)]",
                glow: "from-amber-500/10 to-transparent",
              },
              {
                label: "Audit Integrity",
                value: "Verified",
                sub: "Checksum chain intact",
                icon: <ShieldCheck size={15} />,
                color: "text-emerald-400",
                topBorder: "border-t-2 border-t-emerald-400 shadow-[0_-4px_12px_rgba(52,211,153,0.15)]",
                glow: "from-emerald-500/10 to-transparent",
              },
            ].map((stat) => (
              <div
                key={stat.label}
                className={`relative flex flex-col justify-center px-5 py-4 rounded-xl border backdrop-blur-md bg-gradient-to-b ${stat.glow} ${stat.topBorder}`}
                style={{
                  borderColor: "var(--os-stroke)",
                  backgroundColor: "rgba(9, 14, 26, 0.82)",
                }}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
                    {stat.label}
                  </p>
                  <div className="opacity-40">{stat.icon}</div>
                </div>
                <p
                  className={`text-xl font-bold tabular-nums truncate leading-tight ${stat.color}`}
                >
                  {stat.value}
                </p>
                <p className="text-[10px] text-slate-500 font-medium mt-1 truncate">
                  {stat.sub}
                </p>
              </div>
            ))}
          </div>

          {/* ── Channel Stream Progress Bar ── */}
          <div
            className="flex items-center justify-between px-5 py-2.5 rounded-xl border shrink-0 backdrop-blur-md"
            style={{
              borderColor: "var(--os-stroke)",
              backgroundColor: "rgba(9, 14, 26, 0.82)",
            }}
          >
            <div className="flex items-center gap-3 w-full">
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400 shrink-0">
                AUDIT STREAM CHANNEL
              </span>
              <div className="h-1.5 flex-1 rounded-full overflow-hidden bg-slate-900 border border-white/10 relative">
                <div className="h-full w-full bg-gradient-to-r from-emerald-400 via-cyan-400 via-violet-400 to-amber-400 animate-pulse shadow-[0_0_10px_rgba(34,211,238,0.5)]" />
              </div>
              <span className="text-[10px] font-mono text-emerald-400 font-bold uppercase tracking-wider shrink-0">
                {liveConnected ? "STREAMING" : "STANDBY"}
              </span>
            </div>
          </div>

          {/* ── Main feed panel ── */}
          <div
            className="flex flex-col overflow-hidden rounded-xl border shrink-0 relative backdrop-blur-md"
            style={{
              borderColor: "var(--os-stroke)",
              background: "rgba(9, 14, 26, 0.85)",
              height: "calc(100vh - 350px)",
              minHeight: "380px",
            }}
          >
            {/* Top colorful gradient accent line */}
            <div className="h-[2px] w-full bg-gradient-to-r from-emerald-400 via-cyan-400 via-violet-400 to-amber-400" />

            {/* Panel header + filter */}
            <div
              className="flex flex-wrap items-center justify-between gap-3 border-b px-5 py-3 shrink-0"
              style={{ borderColor: "var(--os-stroke)" }}
            >
              <div className="flex items-center gap-3">
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
                  Event Stream
                </p>
                {!loading && (
                  <span className="text-[10px] font-mono text-cyan-300/80 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
                    {filteredEvents.length.toLocaleString()} event
                    {filteredEvents.length !== 1 ? "s" : ""}
                    {kindFilter ? " filtered" : " loaded"}
                  </span>
                )}
              </div>

              {/* Kind filter */}
              <div className="flex items-center gap-2">
                <Filter size={11} className="text-slate-400 shrink-0" />
                <Select
                  options={kindOptions}
                  value={kindFilter}
                  onChange={(val) => setKindFilter(val)}
                  placeholder="ALL KINDS"
                  size="sm"
                  className="min-w-[170px]"
                />
              </div>
            </div>

            {/* Feed scroll area */}
            <div className="flex-1 overflow-y-auto custom-scrollbar min-h-0">
              {loading ? (
                <div className="flex flex-col items-center justify-center h-full gap-3">
                  <div className="h-7 w-7 rounded-full border-2 border-cyan-500/30 border-t-cyan-400 animate-spin" />
                  <p className="text-[11px] text-slate-500 uppercase tracking-widest font-bold">
                    Loading journal...
                  </p>
                </div>
              ) : filteredEvents.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full gap-3 text-center px-6">
                  <History size={36} className="text-slate-700" />
                  <p className="text-[11px] text-slate-500 uppercase tracking-widest font-bold">
                    {kindFilter
                      ? `No "${kindFilter}" events found`
                      : "No events recorded yet"}
                  </p>
                  {kindFilter && (
                    <Button
                      variant="ghost"
                      size="xs"
                      onClick={() => setKindFilter("")}
                    >
                      Clear filter
                    </Button>
                  )}
                </div>
              ) : (
                <>
                  {filteredEvents.map((event) => (
                    <EventRow key={event.id} event={event} />
                  ))}

                  {/* Load older */}
                  {hasOlder && (
                    <div
                      className="px-5 py-4 border-t"
                      style={{ borderColor: "var(--os-stroke)" }}
                    >
                      <Button
                        fullWidth
                        variant="outline"
                        size="sm"
                        onClick={loadOlder}
                        loading={loadingOlder}
                        className="border-dashed text-slate-400 hover:text-white hover:border-cyan-500/40"
                        style={{ borderColor: "var(--os-stroke)" }}
                      >
                        {loadingOlder ? "Loading..." : "Load Older Events"}
                      </Button>
                    </div>
                  )}

                  {!hasOlder && filteredEvents.length > 0 && (
                    <div className="px-5 py-4 text-center">
                      <p className="text-[10px] text-slate-600 uppercase tracking-widest font-bold">
                        Beginning of journal
                      </p>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ─── Event Row ────────────────────────────────────────────────────────────────

function EventRow({ event }: { event: FaimEvent }) {
  const [expanded, setExpanded] = useState(false);
  const meta = getKindMeta(event.kind);
  const hasPayload = event.payload && Object.keys(event.payload).length > 0;

  // Extract color border for row accent line
  const leftBorderColor = meta.dot.replace("bg-", "border-l-");

  return (
    <div
      className={`group border-b border-l-4 ${leftBorderColor} last:border-b-0 transition-all duration-200 hover:bg-gradient-to-r hover:from-white/[0.04] hover:to-transparent`}
      style={{ borderColor: "var(--os-stroke)" }}
    >
      <div className="flex items-start gap-4 px-5 py-3.5">
        {/* Kind indicator dot */}
        <div className="shrink-0 pt-[5px]">
          <div
            className={`h-2.5 w-2.5 rounded-full ${meta.dot}`}
            style={{ boxShadow: `0 0 8px currentColor` }}
          />
        </div>

        {/* Main content */}
        <div className="flex-1 min-w-0">
          {/* Top row: kind + seq + time */}
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded-md border text-[10px] font-black uppercase tracking-widest ${meta.color} ${meta.bg}`}
            >
              {event.kind}
            </span>
            <span className="text-[10px] font-mono text-slate-400 font-semibold">
              #{event.seq}
            </span>
            <span className="text-[10px] text-slate-400 font-medium ml-auto shrink-0">
              {relativeTime(event.ts)}
            </span>
          </div>

          {/* Description */}
          <p className="text-[13px] text-slate-200 font-medium leading-snug">
            {meta.description}
          </p>

          {/* Absolute time */}
          {event.ts && (
            <p className="text-[10px] text-slate-500 font-mono mt-0.5">
              {absoluteTime(event.ts)}
            </p>
          )}

          {/* Payload toggle */}
          {hasPayload && (
            <div className="mt-2">
              <button
                onClick={() => setExpanded((v) => !v)}
                className="flex items-center gap-1 text-[10px] text-cyan-400/80 hover:text-cyan-300 font-bold uppercase tracking-widest transition-colors"
              >
                <ChevronRight
                  size={10}
                  className={`transition-transform ${expanded ? "rotate-90" : ""}`}
                />
                {expanded ? "Hide" : "View"} payload
              </button>

              {expanded && (
                <div
                  className="mt-2 p-3 rounded-lg overflow-x-auto border border-cyan-500/20"
                  style={{
                    background: "rgba(7, 10, 18, 0.7)",
                  }}
                >
                  <pre className="text-[10px] font-mono text-slate-300 leading-relaxed whitespace-pre-wrap break-all">
                    {JSON.stringify(event.payload, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Checksum (desktop only) */}
        {event.checksum && (
          <div className="shrink-0 hidden md:block pt-0.5">
            <span
              className="text-[9px] font-mono text-slate-500 group-hover:text-slate-300 transition-colors cursor-default select-all bg-white/[0.03] px-2 py-0.5 rounded border border-white/5"
              title={`Checksum: ${event.checksum}`}
            >
              {event.checksum.slice(0, 8)}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
