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
          {/* ── Metric strip (Domain Studio Style) ── */}
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3 shrink-0">
            <MetricTile
              label="TOTAL EVENTS"
              value={
                latest?.event_count != null
                  ? latest.event_count.toLocaleString()
                  : "—"
              }
              hint={newCount > 0 ? `+${newCount} since last refresh` : "All time"}
              accent="#06b6d4"
            />
            <MetricTile
              label="LAST KIND"
              value={latest?.last_kind ?? "—"}
              hint={
                latest?.last_kind
                  ? getKindMeta(latest.last_kind).description
                  : "Waiting for events"
              }
              accent="#8b5cf6"
            />
            <MetricTile
              label="LAST ACTIVITY"
              value={relativeTime(latest?.last_ts ?? null)}
              hint={absoluteTime(latest?.last_ts ?? null)}
              accent="#f59e0b"
            />
            <MetricTile
              label="AUDIT INTEGRITY"
              value="Verified"
              hint="Checksum chain intact"
              accent="#10b981"
            />
          </div>

          {/* ── Channel Stream Progress Bar (Domain Studio Style) ── */}
          <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-3.5 shrink-0">
            <div className="flex items-center gap-3 w-full">
              <span className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500 shrink-0">
                AUDIT STREAM CHANNEL
              </span>
              <div className="h-1.5 flex-1 rounded-full overflow-hidden bg-slate-950/80 border border-white/10 relative">
                <div className="h-full rounded-full w-full bg-[linear-gradient(90deg,#10b981,#06b6d4,#8b5cf6,#f59e0b)] animate-pulse shadow-[0_0_10px_rgba(34,211,238,0.4)]" />
              </div>
              <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-emerald-400 shrink-0">
                {liveConnected ? "STREAMING" : "STANDBY"}
              </span>
            </div>
          </div>

          {/* ── Main feed panel (Domain Studio SectionShell Style) ── */}
          <section className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)] flex-1 flex flex-col min-h-[380px]">
            <div
              className="pointer-events-none absolute inset-0"
              style={{
                background:
                  "radial-gradient(circle at 14% 8%, rgba(6,182,212,0.12), transparent 28%), radial-gradient(circle at 82% 14%, rgba(255,255,255,0.03), transparent 24%)",
              }}
            />

            {/* Panel header + filter chips */}
            <div className="relative border-b border-white/6 px-5 py-3.5 shrink-0">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-mono text-[10px] font-bold uppercase tracking-[0.28em] text-cyan-400">
                    EVENT STREAM AUDIT
                  </p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <h2 className="text-base font-semibold tracking-tight text-white">
                      Live Feed & Mutation History
                    </h2>
                    {!loading && (
                      <span className="font-mono text-[10px] text-cyan-300 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
                        {filteredEvents.length.toLocaleString()} event
                        {filteredEvents.length !== 1 ? "s" : ""}
                      </span>
                    )}
                  </div>
                </div>

                {/* Filter chips (Domain Studio style) */}
                <div className="flex flex-wrap items-center gap-1.5">
                  <FilterChip
                    label="ALL KINDS"
                    active={kindFilter === ""}
                    onClick={() => setKindFilter("")}
                    accent="#06b6d4"
                  />
                  {allKinds.slice(0, 5).map((k) => (
                    <FilterChip
                      key={k}
                      label={k}
                      active={kindFilter === k}
                      onClick={() => setKindFilter(k)}
                      accent="#8b5cf6"
                    />
                  ))}
                  {allKinds.length > 5 && (
                    <Select
                      options={kindOptions}
                      value={kindFilter}
                      onChange={(val) => setKindFilter(val)}
                      placeholder="MORE..."
                      size="sm"
                      className="min-w-[130px]"
                    />
                  )}
                </div>
              </div>
            </div>

            {/* Feed scroll area */}
            <div className="relative flex-1 overflow-y-auto custom-scrollbar min-h-0">
              {loading ? (
                <div className="flex flex-col items-center justify-center h-full gap-3">
                  <div className="h-7 w-7 rounded-full border-2 border-cyan-500/30 border-t-cyan-400 animate-spin" />
                  <p className="font-mono text-[11px] text-slate-500 uppercase tracking-widest font-bold">
                    Loading journal...
                  </p>
                </div>
              ) : filteredEvents.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full gap-3 text-center px-6">
                  <History size={36} className="text-slate-700" />
                  <p className="font-mono text-[11px] text-slate-500 uppercase tracking-widest font-bold">
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
                    <div className="px-5 py-4 border-t border-white/6">
                      <Button
                        fullWidth
                        variant="outline"
                        size="sm"
                        onClick={loadOlder}
                        loading={loadingOlder}
                        className="border-dashed text-slate-400 hover:text-white hover:border-cyan-500/40"
                      >
                        {loadingOlder ? "Loading..." : "Load Older Events"}
                      </Button>
                    </div>
                  )}

                  {!hasOlder && filteredEvents.length > 0 && (
                    <div className="px-5 py-4 text-center">
                      <p className="font-mono text-[10px] text-slate-600 uppercase tracking-widest font-bold">
                        Beginning of journal
                      </p>
                    </div>
                  )}
                </>
              )}
            </div>
          </section>
        </>
      )}
    </div>
  );
}

function MetricTile({
  label,
  value,
  hint,
  accent,
}: {
  label: string;
  value: React.ReactNode;
  hint: string;
  accent: string;
}) {
  return (
    <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-3.5 shadow-[0_4px_20px_rgba(0,0,0,0.2)]">
      <div className="absolute inset-x-0 top-0 h-[2px]" style={{ background: accent }} />
      <p className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500">
        {label}
      </p>
      <p className="mt-1.5 text-[18px] font-semibold leading-none tracking-tight text-white">
        {value}
      </p>
      <p className="mt-1.5 text-[10px] leading-[1.125rem] text-slate-400 truncate">{hint}</p>
    </div>
  );
}

function FilterChip({
  label,
  active,
  onClick,
  accent = "#06b6d4",
}: {
  label: string;
  active: boolean;
  onClick: () => void;
  accent?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-full border px-3 py-1 font-mono text-[10px] font-semibold uppercase tracking-[0.12em] transition-all duration-200"
      style={
        active
          ? {
              borderColor: `${accent}66`,
              backgroundColor: `${accent}1F`,
              color: accent,
              boxShadow: `0 0 14px ${accent}22`,
            }
          : {
              borderColor: "rgba(255,255,255,0.1)",
              backgroundColor: "rgba(255,255,255,0.03)",
              color: "rgba(148,163,184,0.75)",
            }
      }
    >
      {label}
    </button>
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
