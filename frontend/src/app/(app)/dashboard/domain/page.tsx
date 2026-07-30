"use client";

import { AnimatePresence, motion } from "framer-motion";
import { getSession, useSession } from "next-auth/react";
import {
  Activity,
  ArrowRight,
  BookOpenText,
  BrainCircuit,
  Network,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Target,
} from "lucide-react";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { DomainInfoTip } from "@/components/domain/DomainInfoTip";
import { DomainKnowledgeGraph } from "@/components/domain/DomainKnowledgeGraph";
import { GlassHeader } from "@/components/layout/GlassHeader";
import { Badge, Button, Input, useToast } from "@/components/ui";

type DomainKindCount = {
  kind: string;
  count: number;
};

type DomainPackStrength = {
  domain_pack: string;
  term_count: number;
  support_total: number;
  avg_score: number;
};

type DomainSourceKindCount = {
  source_kind: string;
  count: number;
};

type DomainTerm = {
  surface_form: string;
  canonical_form: string;
  kind: string;
  domain_pack?: string | null;
  support_count: number;
  score: number;
  has_node: boolean;
  node_id?: string | null;
  meta: Record<string, unknown>;
  updated_at?: string | null;
};

type DomainOverviewResponse = {
  graph_id: string;
  graph_version: number;
  jobs_enabled: boolean;
  domain_autonomy_enabled: boolean;
  lexicon_total: number;
  source_total: number;
  linked_total: number;
  maturity_score: number;
  detected_packs: string[];
  kind_breakdown: DomainKindCount[];
  pack_strengths: DomainPackStrength[];
  source_kinds: DomainSourceKindCount[];
  top_terms: DomainTerm[];
  top_sources: Array<{
    source_id: string;
    source_kind: string;
    source_hash: string;
    meta: Record<string, unknown>;
    updated_at?: string | null;
  }>;
  last_updated_at?: string | null;
};

type DomainTermsResponse = {
  graph_id: string;
  total: number;
  limit: number;
  offset: number;
  items: DomainTerm[];
};

type DomainGraphNode = {
  id: string;
  label: string;
  type: string;
  pack?: string | null;
  kind?: string | null;
  score?: number | null;
  support_count?: number | null;
  canonical_form?: string | null;
  cognitive_type?: string | null;
  cluster_id?: number | null;
};

type DomainGraphEdge = {
  id: string;
  source: string;
  target: string;
  kind: string;
  weight: number;
};

type DomainGraphResponse = {
  graph_id: string;
  graph_version: number;
  nodes: DomainGraphNode[];
  edges: DomainGraphEdge[];
  terms_sampled: number;
  packs_sampled: number;
  linked_nodes_sampled: number;
  generated_at: string;
};

type StudioPane = "overview" | "graph" | "signal" | "matrix";

const INK = {
  amber: "#F5B461",
  violet: "#A78BFA",
  teal: "#5EEAD4",
  rose: "#FB7185",
  slate: "#94A3B8",
} as const;

class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function normalizeApiError(payload: unknown, fallback: string): string {
  if (!payload) return fallback;
  if (typeof payload === "string") return payload;
  if (typeof payload === "object") {
    const data = payload as {
      detail?: unknown;
      error?: unknown;
      message?: unknown;
    };
    if (typeof data.detail === "string" && data.detail.trim()) return data.detail;
    if (typeof data.error === "string" && data.error.trim()) return data.error;
    if (typeof data.message === "string" && data.message.trim()) return data.message;
  }
  return fallback;
}

function mergeHeaders(
  base: Record<string, string>,
  extra?: HeadersInit,
): Record<string, string> {
  if (!extra) return base;
  if (extra instanceof Headers) {
    extra.forEach((value, key) => {
      base[key] = value;
    });
    return base;
  }
  if (Array.isArray(extra)) {
    for (const [key, value] of extra) base[key] = value;
    return base;
  }
  return { ...base, ...(extra as Record<string, string>) };
}

function formatTime(value?: string | null): string {
  if (!value) return "No update yet";
  return new Date(value).toLocaleString();
}

function maturityLabel(score?: number | null): string {
  if (!score || score <= 0) return "Bootstrapping";
  if (score >= 85) return "High-coverage";
  if (score >= 65) return "Production-learning";
  if (score >= 40) return "Growing";
  return "Early formation";
}

function SectionShell({
  eyebrow,
  title,
  subtitle,
  info,
  action,
  children,
  accent = INK.amber,
}: {
  eyebrow: string;
  title: string;
  subtitle?: string;
  info?: React.ReactNode;
  action?: React.ReactNode;
  children: React.ReactNode;
  accent?: string;
}) {
  return (
    <section className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)]">
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background: `radial-gradient(circle at 14% 8%, ${accent}16, transparent 28%), radial-gradient(circle at 82% 14%, rgba(255,255,255,0.03), transparent 24%)`,
        }}
      />
      <div className="relative border-b border-white/6 px-4 py-2.5 sm:px-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="max-w-3xl">
            <div className="flex items-center gap-2">
              <p
                className="font-mono text-[10px] font-bold uppercase tracking-[0.28em]"
                style={{ color: `${accent}D9` }}
              >
                {eyebrow}
              </p>
              {info ? <DomainInfoTip label={title} content={info} /> : null}
            </div>
            <h2 className="mt-1 text-base font-semibold tracking-tight text-white sm:text-[1.12rem]">
              {title}
            </h2>
            {subtitle ? (
              <p className="mt-1 max-w-2xl text-[12px] leading-5 text-slate-400">
                {subtitle}
              </p>
            ) : null}
          </div>
          {action ? <div className="flex items-center gap-2">{action}</div> : null}
        </div>
      </div>
      <div className="relative">{children}</div>
    </section>
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
    <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-3">
      <div className="absolute inset-x-0 top-0 h-[2px]" style={{ background: accent }} />
      <p className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500">
        {label}
      </p>
      <p className="mt-1.5 text-[18px] font-semibold leading-none tracking-tight text-white">
        {value}
      </p>
      <p className="mt-1.5 text-[10px] leading-[1.125rem] text-slate-400">{hint}</p>
    </div>
  );
}

function CompactStat({
  label,
  value,
  accent = INK.slate,
}: {
  label: string;
  value: React.ReactNode;
  accent?: string;
}) {
  return (
    <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-slate-950/45 px-3 py-2.5">
      <span
        className="pointer-events-none absolute left-0 top-0 h-full w-[2px]"
        style={{ background: `${accent}88` }}
      />
      <p className="font-mono text-[10px] font-bold uppercase tracking-[0.18em] text-slate-500">
        {label}
      </p>
      <p className="mt-1.5 text-[13px] font-semibold text-white">{value}</p>
    </div>
  );
}

function FilterChip({
  label,
  active,
  onClick,
  accent = INK.amber,
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
      className="rounded-full border px-2.5 py-1.5 font-mono text-[10px] font-semibold uppercase tracking-[0.12em] transition-all duration-200"
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

function StrengthRail({ packs }: { packs: DomainPackStrength[] }) {
  if (!packs.length) {
    return (
      <div className="rounded-[14px] border border-dashed border-white/10 px-4 py-5 text-center text-sm text-slate-400">
        No strong domain packs have formed yet for this graph.
      </div>
    );
  }

  return (
    <div className="space-y-2.5">
      {packs.map((pack, index) => {
        const width = Math.max(8, Math.min(100, pack.avg_score * 100));
        return (
          <motion.div
            key={pack.domain_pack}
            initial={{ opacity: 0, x: 12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.22, delay: index * 0.03 }}
            className="rounded-[14px] border border-white/8 bg-white/[0.03] p-3"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold capitalize text-white">
                  {pack.domain_pack}
                </p>
                <p className="mt-1 text-[11px] text-slate-400">
                  {pack.term_count} terms · {pack.support_total} support
                </p>
              </div>
              <Badge size="xs" variant="info">
                {pack.avg_score.toFixed(2)}
              </Badge>
            </div>
            <div className="mt-3 h-1.5 rounded-full bg-slate-900/80">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${width}%` }}
                transition={{ duration: 0.35, delay: 0.04 + index * 0.03 }}
                className="h-1.5 rounded-full"
                style={{
                  background: `linear-gradient(90deg, ${INK.amber}, ${INK.violet}, ${INK.teal})`,
                }}
              />
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}

function TopTermCard({
  term,
  index,
}: {
  term: DomainTerm;
  index: number;
}) {
  const accent = term.has_node ? INK.teal : INK.slate;
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, delay: index * 0.025 }}
      className="relative overflow-hidden rounded-[14px] border border-white/8 bg-[linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0.02))] p-3"
    >
      <span
        className="pointer-events-none absolute left-0 top-0 h-full w-[2px]"
        style={{ background: `${accent}80` }}
      />
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-white">
            {term.surface_form}
          </p>
          <p className="mt-1 truncate text-[11px] text-slate-400">
            {term.canonical_form}
          </p>
        </div>
        <Badge size="xs" variant={term.has_node ? "success" : "warning"}>
          {term.has_node ? "linked" : "learned"}
        </Badge>
      </div>
      <div className="mt-3 flex flex-wrap gap-1.5">
        <Badge size="xs" variant="info">
          {term.kind}
        </Badge>
        {term.domain_pack ? (
          <Badge size="xs" variant="default">
            {term.domain_pack}
          </Badge>
        ) : null}
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 font-mono text-[11px] text-slate-400">
        <div>
          <span className="block text-slate-500">Support</span>
          <span className="font-medium text-slate-200">{term.support_count}</span>
        </div>
        <div>
          <span className="block text-slate-500">Score</span>
          <span className="font-medium text-slate-200">{term.score.toFixed(2)}</span>
        </div>
      </div>
    </motion.div>
  );
}

export default function DomainPage() {
  const { data: session, status: sessionStatus } = useSession();
  const { toast } = useToast();
  const accessToken = (session as { accessToken?: string } | null)?.accessToken;
  const isAuthenticated =
    sessionStatus === "authenticated" && Boolean(accessToken);
  const sessionGraphId =
    (session as { graphId?: string } | null)?.graphId || "default";

  const [graphScopeInput, setGraphScopeInput] = useState(sessionGraphId);
  const [graphScope, setGraphScope] = useState(sessionGraphId);
  const [overview, setOverview] = useState<DomainOverviewResponse | null>(null);
  const [graphView, setGraphView] = useState<DomainGraphResponse | null>(null);
  const [terms, setTerms] = useState<DomainTermsResponse | null>(null);
  const [query, setQuery] = useState("");
  const [kindFilter, setKindFilter] = useState("");
  const [packFilter, setPackFilter] = useState("");
  const [loadingOverview, setLoadingOverview] = useState(false);
  const [loadingTerms, setLoadingTerms] = useState(false);
  const [liveEventSeq, setLiveEventSeq] = useState(0);
  const liveEventSeqRef = useRef(0);
  const [activePane, setActivePane] = useState<StudioPane>("graph");

  const activeGraphId = useMemo(
    () => graphScope.trim() || sessionGraphId,
    [graphScope, sessionGraphId],
  );

  useEffect(() => {
    setGraphScopeInput(sessionGraphId);
    setGraphScope(sessionGraphId);
  }, [sessionGraphId]);

  const authHeaders = useCallback(
    async (headers?: HeadersInit): Promise<Record<string, string>> => {
      const currentSession = await getSession();
      const token =
        (currentSession as { accessToken?: string } | null)?.accessToken || "";
      const resolvedGraphId =
        ((currentSession as { graphId?: string } | null)?.graphId || "").trim() ||
        activeGraphId;
      return mergeHeaders(
        {
          Authorization: `Bearer ${token}`,
          "X-Graph-Id": resolvedGraphId,
        },
        headers,
      );
    },
    [activeGraphId],
  );

  const fetchJson = useCallback(
    async <T,>(url: string, init?: RequestInit): Promise<T> => {
      const headers = await authHeaders(init?.headers);
      const response = await fetch(url, {
        ...init,
        headers,
        cache: "no-store",
      });

      const text = await response.text();
      let payload: unknown = null;
      if (text) {
        try {
          payload = JSON.parse(text);
        } catch {
          payload = text;
        }
      }

      if (!response.ok) {
        throw new ApiError(
          response.status,
          normalizeApiError(payload, `Request failed (${response.status})`),
        );
      }

      return (payload as T) || ({} as T);
    },
    [authHeaders],
  );

  const fetchOverview = useCallback(async () => {
    setLoadingOverview(true);
    try {
      const data = await fetchJson<DomainOverviewResponse>(
        `/api/v1/domain/overview?graph_id=${encodeURIComponent(activeGraphId)}&limit=12`,
      );
      setOverview(data);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      toast.error("Domain overview unavailable", message);
    } finally {
      setLoadingOverview(false);
    }
  }, [activeGraphId, fetchJson, toast]);

  const fetchGraphView = useCallback(async () => {
    try {
      const data = await fetchJson<DomainGraphResponse>(
        `/api/v1/domain/graph?graph_id=${encodeURIComponent(activeGraphId)}&limit=48`,
      );
      setGraphView(data);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      toast.error("Domain graph unavailable", message);
    }
  }, [activeGraphId, fetchJson, toast]);

  const fetchTerms = useCallback(async () => {
    setLoadingTerms(true);
    try {
      const params = new URLSearchParams({
        graph_id: activeGraphId,
        limit: "80",
        offset: "0",
      });
      if (query.trim()) params.set("q", query.trim());
      if (kindFilter.trim()) params.set("kind", kindFilter.trim());
      if (packFilter.trim()) params.set("domain_pack", packFilter.trim());
      const data = await fetchJson<DomainTermsResponse>(
        `/api/v1/domain/terms?${params.toString()}`,
      );
      setTerms(data);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      toast.error("Domain term view unavailable", message);
    } finally {
      setLoadingTerms(false);
    }
  }, [activeGraphId, fetchJson, kindFilter, packFilter, query, toast]);

  const refreshAll = useCallback(() => {
    void Promise.all([fetchOverview(), fetchGraphView(), fetchTerms()]);
  }, [fetchGraphView, fetchOverview, fetchTerms]);

  useEffect(() => {
    if (!isAuthenticated) return;
    refreshAll();
  }, [isAuthenticated, refreshAll]);

  const availableKinds = useMemo(
    () => overview?.kind_breakdown.map((item) => item.kind) || [],
    [overview],
  );
  const availablePacks = useMemo(
    () => overview?.pack_strengths.map((item) => item.domain_pack) || [],
    [overview],
  );

  const heroState = useMemo(
    () => maturityLabel(overview?.maturity_score),
    [overview],
  );

  useEffect(() => {
    if (!isAuthenticated) return;

    let cancelled = false;
    let retryTimer: number | null = null;
    let controller: AbortController | null = null;
    let afterSeq = liveEventSeqRef.current;

    const connect = async () => {
      try {
        while (!cancelled) {
          controller = new AbortController();
          const headers = await authHeaders({
            Accept: "text/event-stream",
          });
          const response = await fetch(
            `/api/v1/events/stream?graph_id=${encodeURIComponent(activeGraphId)}&after_seq=${afterSeq}`,
            {
              method: "GET",
              headers,
              cache: "no-store",
              signal: controller.signal,
            },
          );

          if (!response.ok || !response.body) {
            throw new Error(`Event stream unavailable (${response.status})`);
          }

          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = "";
          let eventName = "";
          let eventData = "";

          const flush = () => {
            if (!eventName && !eventData) return;
            try {
              const payload = eventData ? JSON.parse(eventData) : null;
              const seq = typeof payload?.seq === "number" ? payload.seq : null;
              if (seq != null) {
                afterSeq = Math.max(afterSeq, seq);
                liveEventSeqRef.current = afterSeq;
                setLiveEventSeq(afterSeq);
              }
              if (eventName && !["ping", "timeout", "disconnect"].includes(eventName)) {
                void refreshAll();
                window.dispatchEvent(
                  new CustomEvent("faim:domain-live-refresh", {
                    detail: { graphId: activeGraphId, seq: afterSeq, kind: eventName },
                  }),
                );
              }
            } catch {
              // ignore malformed event frames
            } finally {
              eventName = "";
              eventData = "";
            }
          };

          while (!cancelled) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            let newlineIndex = buffer.indexOf("\n");
            while (newlineIndex >= 0) {
              const line = buffer.slice(0, newlineIndex).replace(/\r$/, "");
              buffer = buffer.slice(newlineIndex + 1);
              if (line === "") {
                flush();
              } else if (line.startsWith("event:")) {
                eventName = line.slice(6).trim();
              } else if (line.startsWith("data:")) {
                eventData = eventData
                  ? `${eventData}\n${line.slice(5).trimStart()}`
                  : line.slice(5).trimStart();
              }
              newlineIndex = buffer.indexOf("\n");
            }
          }
        }
      } catch {
        if (!cancelled) {
          retryTimer = window.setTimeout(() => {
            void connect();
          }, 3000);
        }
      }
    };

    void connect();
    return () => {
      cancelled = true;
      controller?.abort();
      if (retryTimer) window.clearTimeout(retryTimer);
    };
  }, [activeGraphId, authHeaders, isAuthenticated, refreshAll]);

  const paneMeta = useMemo(
    () =>
      ({
        overview: {
          label: "Knowledge cartography",
          hint: "Overview",
          accent: INK.amber,
        },
        graph: {
          label: "Graph chamber",
          hint: "Topology",
          accent: INK.violet,
        },
        signal: {
          label: "Signal feed",
          hint: "Strongest terms",
          accent: INK.teal,
        },
        matrix: {
          label: "Term matrix",
          hint: "Lexical memory",
          accent: INK.rose,
        },
      }) as const,
    [],
  );

  return (
    <div
      className="mx-auto max-w-[1480px] space-y-4 px-2 pb-6"
      style={{
        background:
          "radial-gradient(circle at 20% 0%, rgba(245,180,97,0.03), transparent 28%), radial-gradient(circle at 85% 10%, rgba(167,139,250,0.03), transparent 28%)",
      }}
    >
      <GlassHeader
        title="Domain Studio"
        subtitle={`Graph-Native Knowledge Control Surface · Graph Scope: ${activeGraphId}`}
        icon={BrainCircuit}
        accentColor={INK.amber}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Badge size="xs" variant="info">
              {heroState}
            </Badge>
            <Button
              size="sm"
              variant="ghost"
              leftIcon={<RefreshCw size={12} />}
              onClick={() => refreshAll()}
            >
              Refresh domain layer
            </Button>
          </div>
        }
      />

      <div className="sticky top-3 z-20 mx-auto flex max-w-[1480px] justify-center px-2">
        <div className="flex flex-wrap items-center gap-2 rounded-none border-0 bg-transparent px-0 py-0 shadow-none backdrop-blur-0">
          {(Object.entries(paneMeta) as Array<[StudioPane, (typeof paneMeta)[StudioPane]]>).map(
            ([key, meta]) => {
              const active = activePane === key;
              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => setActivePane(key)}
                  className="inline-flex items-center gap-2 rounded-[12px] border px-2.5 py-2 text-left transition-all duration-200 shadow-[0_10px_24px_rgba(0,0,0,0.22)]"
                  style={{
                    borderColor: active ? `${meta.accent}55` : "rgba(255,255,255,0.08)",
                    backgroundColor: active ? `${meta.accent}1E` : "rgba(255,255,255,0.02)",
                    boxShadow: active ? `0 0 0 1px ${meta.accent}33` : "none",
                  }}
                >
                  <span
                    className="flex h-7 w-7 items-center justify-center rounded-[10px]"
                    style={{ backgroundColor: `${meta.accent}18`, color: meta.accent }}
                  >
                    {key === "overview" ? (
                      <BrainCircuit size={13} />
                    ) : key === "graph" ? (
                      <Network size={13} />
                    ) : key === "signal" ? (
                      <Sparkles size={13} />
                    ) : (
                      <Search size={13} />
                    )}
                  </span>
                  <span className="flex flex-col">
                    <span
                      className="font-mono text-[9px] font-semibold uppercase tracking-[0.14em]"
                      style={{ color: active ? meta.accent : "rgba(148,163,184,0.8)" }}
                    >
                      {meta.hint}
                    </span>
                    <span className="text-[11px] font-medium text-white">{meta.label}</span>
                  </span>
                </button>
              );
            },
          )}
        </div>
      </div>

      {activePane === "overview" ? (
        <SectionShell
          eyebrow="Domain Command Deck"
          title="Inspect the graph-local domain structures FAIM is forming"
          subtitle="A compact control surface for graph scope, maturity, pack formation, learned terms, and retrieval-facing domain memory."
          info="This surface is for product-grade inspection, not presentation. It shows the real learning layer FAIM builds from uploads and memory writes."
          accent={INK.amber}
          action={
            <div className="flex flex-wrap items-center gap-2">
              <Badge size="xs" variant={overview?.domain_autonomy_enabled ? "success" : "warning"}>
                autonomy {overview?.domain_autonomy_enabled ? "on" : "off"}
              </Badge>
              <Badge size="xs" variant={overview?.jobs_enabled ? "success" : "warning"}>
                jobs {overview?.jobs_enabled ? "ready" : "off"}
              </Badge>
            </div>
          }
        >
          <div className="grid gap-3 px-4 py-4 sm:px-4 xl:grid-cols-[1.12fr_0.88fr]">
          <div className="space-y-3">
            <div className="rounded-[16px] border border-white/8 bg-[linear-gradient(135deg,rgba(9,13,21,0.92),rgba(3,5,10,0.97))] p-3.5">
              <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_252px]">
                <div>
                  <div className="flex items-center gap-2">
                    <p
                      className="font-mono text-[10px] font-bold uppercase tracking-[0.28em]"
                      style={{ color: `${INK.amber}D9` }}
                    >
                      Knowledge cartography
                    </p>
                    <DomainInfoTip
                      label="Graph overview"
                      content="This header gives the fastest read on what FAIM has learned for the active graph and whether that knowledge is becoming structurally useful."
                    />
                  </div>
                  <p className="mt-2 max-w-lg text-[clamp(1rem,1.4vw,1.42rem)] font-semibold leading-[1.06] tracking-[-0.028em] text-white">
                    Domain memory, distilled into one operating surface.
                  </p>
                  <p className="mt-2.5 max-w-lg text-[12px] leading-5 text-slate-400">
                    Track lexical growth, pack formation, and graph-linked evidence without leaving the runtime.
                  </p>
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {(overview?.detected_packs?.length
                      ? overview.detected_packs
                      : ["general"]
                    ).map((pack) => (
                      <Badge key={pack} size="xs" variant="info">
                        {pack}
                      </Badge>
                    ))}
                    <Badge size="xs" variant="default">
                      version {overview?.graph_version ?? "—"}
                    </Badge>
                    <Badge size="xs" variant="default">
                      updated {formatTime(overview?.last_updated_at)}
                    </Badge>
                  </div>
                </div>

                <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-3">
                  <span
                    className="pointer-events-none absolute left-0 top-0 h-full w-[2px]"
                    style={{ background: `${INK.amber}80` }}
                  />
                  <p className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500">
                    Active graph scope
                  </p>
                  <p className="mt-1.5 break-all text-[14px] font-semibold tracking-tight text-white">
                    {activeGraphId}
                  </p>
                  <div className="mt-2.5 flex items-end gap-2">
                    <div className="flex-1">
                      <Input
                        value={graphScopeInput}
                        onChange={(event) => setGraphScopeInput(event.target.value)}
                        placeholder="Enter graph id"
                      />
                    </div>
                    <Button
                      size="sm"
                      onClick={() =>
                        setGraphScope(graphScopeInput.trim() || sessionGraphId)
                      }
                    >
                      Apply
                    </Button>
                  </div>
                  <p className="mt-1.5 text-[10px] leading-[1.125rem] text-slate-400">
                    Switch the studio to another graph id.
                  </p>
                </div>
              </div>

              <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
                <MetricTile
                  label="Maturity"
                  value={overview?.maturity_score ?? "—"}
                  hint="How far the domain layer has progressed."
                  accent={`linear-gradient(90deg, ${INK.violet}, ${INK.amber})`}
                />
                <MetricTile
                  label="Lexicon rows"
                  value={overview?.lexicon_total ?? "—"}
                  hint="Learned terms, aliases, and extracted rows."
                  accent={`linear-gradient(90deg, ${INK.teal}, ${INK.violet})`}
                />
                <MetricTile
                  label="Sources"
                  value={overview?.source_total ?? "—"}
                  hint="Source rows backing long-tail knowledge."
                  accent={`linear-gradient(90deg, ${INK.amber}, ${INK.rose})`}
                />
                <MetricTile
                  label="Graph-linked"
                  value={overview?.linked_total ?? "—"}
                  hint="Terms already anchored to live nodes."
                  accent={`linear-gradient(90deg, ${INK.teal}, ${INK.amber})`}
                />
              </div>

              <div className="mt-3 rounded-[14px] border border-white/8 bg-slate-950/45 p-3">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <Activity size={14} className="text-amber-300" />
                    <p className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500">
                      Maturity channel
                    </p>
                  </div>
                  <p className="text-sm font-semibold text-white">{heroState}</p>
                </div>
                <div className="mt-2.5 h-1.5 rounded-full bg-slate-900/80">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{
                      width: `${Math.max(4, Math.min(100, overview?.maturity_score ?? 0))}%`,
                    }}
                    transition={{ duration: 0.4 }}
                    className="h-1.5 rounded-full bg-[linear-gradient(90deg,#A78BFA,#F5B461,#5EEAD4)]"
                  />
                </div>
              </div>
            </div>

            <div className="grid gap-2.5 lg:grid-cols-[0.88fr_1.12fr]">
              <div className="rounded-[14px] border border-white/8 bg-white/[0.03] p-3">
                <div className="flex items-center gap-2">
                  <Target size={14} className="text-amber-300" />
                  <p className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500">
                    Detected domains
                  </p>
                </div>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {(overview?.detected_packs?.length
                    ? overview.detected_packs
                    : ["general"]
                  ).map((pack) => (
                    <Badge key={pack} size="xs" variant="info">
                      {pack}
                    </Badge>
                  ))}
                </div>
                <div className="mt-2.5 grid gap-2 sm:grid-cols-2">
                  <CompactStat
                    label="Retrieval mode"
                    value="Domain-aware rerank"
                    accent={INK.amber}
                  />
                  <CompactStat
                    label="State"
                    value={heroState}
                    accent={INK.violet}
                  />
                </div>
              </div>

              <div className="rounded-[14px] border border-white/8 bg-white/[0.03] p-3">
                <div className="flex items-center gap-2">
                  <ShieldCheck size={14} className="text-teal-300" />
                  <p className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500">
                    Runtime effect
                  </p>
                  <DomainInfoTip
                    label="Runtime effect"
                    content="The learned domain layer helps later retrieval by improving canonical matching, aliasing, graph linking, and domain-aware reranking."
                  />
                </div>
                <div className="mt-2.5 grid gap-2 sm:grid-cols-2">
                  <CompactStat
                    label="Automation"
                    value={overview?.domain_autonomy_enabled ? "Enabled" : "Disabled"}
                    accent={INK.teal}
                  />
                  <CompactStat
                    label="Worker path"
                    value={overview?.jobs_enabled ? "Available" : "Unavailable"}
                    accent={INK.amber}
                  />
                  <CompactStat
                    label="Graph version"
                    value={overview?.graph_version ?? "—"}
                    accent={INK.violet}
                  />
                  <CompactStat
                    label="Learned packs"
                    value={overview?.detected_packs?.length ?? 0}
                    accent={INK.rose}
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-2.5">
            <div className="rounded-[14px] border border-white/8 bg-white/[0.03] p-3">
              <div className="flex items-center gap-2">
                <Sparkles size={14} className="text-violet-300" />
                <p className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500">
                  Domain strength ladder
                </p>
              </div>
              <div className="mt-2.5">
                <StrengthRail packs={overview?.pack_strengths || []} />
              </div>
            </div>

            <div className="rounded-[14px] border border-white/8 bg-white/[0.03] p-3">
              <div className="flex items-center gap-2">
                <Activity size={14} className="text-teal-300" />
                <p className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500">
                  Ingestion signatures
                </p>
              </div>
              <div className="mt-2.5 grid gap-2 sm:grid-cols-2">
                {(overview?.source_kinds?.length ? overview.source_kinds : []).map(
                  (item) => (
                    <div
                      key={item.source_kind}
                      className="rounded-[12px] border border-white/8 bg-slate-950/45 px-3 py-2.5"
                    >
                      <p className="text-sm font-semibold text-white">
                        {item.source_kind}
                      </p>
                      <p className="mt-1 text-[11px] text-slate-400">
                        {item.count} sources
                      </p>
                    </div>
                  ),
                )}
              </div>
            </div>
          </div>
          </div>
        </SectionShell>
      ) : activePane === "graph" ? (
        <SectionShell
          eyebrow="Graph Chamber"
          title="Visualized domain topology"
          subtitle="A focused view of pack hubs, learned concepts, terms, and linked graph nodes."
          info="This pane renders the real sampled domain topology for the active graph."
          accent={INK.violet}
          action={
            <div className="flex items-center gap-2">
              <Badge size="xs" variant="default">
                {graphView?.terms_sampled ?? 0} sampled terms
              </Badge>
              <Badge size="xs" variant="default">
                {graphView?.linked_nodes_sampled ?? 0} linked nodes
              </Badge>
            </div>
          }
        >
          <div className="px-4 py-3.5 sm:px-4">
            <AnimatePresence mode="wait">
              <motion.div
                key={graphView?.generated_at || "domain-graph"}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.22 }}
              >
                <DomainKnowledgeGraph
                  graphId={activeGraphId}
                  nodes={graphView?.nodes || []}
                  edges={graphView?.edges || []}
                />
              </motion.div>
            </AnimatePresence>
          </div>
        </SectionShell>
      ) : activePane === "signal" ? (
        <SectionShell
          eyebrow="Signal Feed"
          title="What FAIM knows strongest right now"
          subtitle="The highest-signal learned terms for the active graph."
          info="These are the most visible and strongest learned domain entries in the current graph."
          accent={INK.teal}
          action={
            <Badge size="xs" variant="info">
              {overview?.top_terms?.length ?? 0} visible
            </Badge>
          }
        >
          <div className="grid gap-2 px-4 py-3.5 sm:px-4">
            {(overview?.top_terms?.length ? overview.top_terms : []).map(
              (term, index) => (
                <TopTermCard
                  key={`${term.surface_form}-${term.kind}-${term.canonical_form}`}
                  term={term}
                  index={index}
                />
              ),
            )}
            {!overview?.top_terms?.length && (
              <div className="rounded-[14px] border border-dashed border-white/10 px-4 py-6 text-center text-sm text-slate-400">
                {loadingOverview
                  ? "Loading high-signal terms..."
                  : "No learned terms are available for this graph yet."}
              </div>
            )}
          </div>
        </SectionShell>
      ) : (
        <SectionShell
          eyebrow="Term Matrix"
          title="Search, filter, and inspect the learned lexical memory"
          subtitle="A compact matrix of learned terms, canonical forms, graph links, and signal strength."
          info="Use this matrix to verify what FAIM has really absorbed into graph-local domain memory."
          accent={INK.rose}
          action={
            <div className="flex items-center gap-2">
              <Badge size="xs" variant="default">
                {terms?.total ?? 0} rows
              </Badge>
              <Button size="sm" variant="ghost" onClick={() => fetchTerms()}>
                Refresh matrix
              </Button>
            </div>
          }
        >
          <div className="space-y-3 px-4 py-3.5 sm:px-4">
            <div className="grid gap-2.5 xl:grid-cols-[1.36fr_0.64fr]">
              <div className="relative">
                <Search
                  size={14}
                  className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"
                />
                <Input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Search learned term or canonical form"
                  className="pl-9"
                />
              </div>
              <div className="flex items-center justify-start gap-2 xl:justify-end">
                <Button size="sm" onClick={() => fetchTerms()}>
                  Apply filters
                </Button>
              </div>
            </div>

            <div className="grid gap-2.5 xl:grid-cols-2">
              <div className="rounded-[14px] border border-white/8 bg-white/[0.03] p-3">
                <p className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500">
                  Kind filters
                </p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  <FilterChip
                    label="All kinds"
                    active={!kindFilter}
                    onClick={() => setKindFilter("")}
                    accent={INK.rose}
                  />
                  {availableKinds.map((kind) => (
                    <FilterChip
                      key={kind}
                      label={kind}
                      active={kindFilter === kind}
                      onClick={() =>
                        setKindFilter((current) => (current === kind ? "" : kind))
                      }
                      accent={INK.rose}
                    />
                  ))}
                </div>
              </div>

              <div className="rounded-[14px] border border-white/8 bg-white/[0.03] p-3">
                <p className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500">
                  Pack filters
                </p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  <FilterChip
                    label="All packs"
                    active={!packFilter}
                    onClick={() => setPackFilter("")}
                    accent={INK.amber}
                  />
                  {availablePacks.map((pack) => (
                    <FilterChip
                      key={pack}
                      label={pack}
                      active={packFilter === pack}
                      onClick={() =>
                        setPackFilter((current) => (current === pack ? "" : pack))
                      }
                      accent={INK.amber}
                    />
                  ))}
                </div>
              </div>
            </div>

            <div className="overflow-hidden rounded-[14px] border border-white/8">
              <div className="grid grid-cols-[1.3fr_1fr_0.75fr_0.7fr_0.8fr_0.75fr] gap-3 border-b border-white/8 bg-white/[0.03] px-4 py-3 font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500">
                <span>Surface</span>
                <span>Canonical</span>
                <span>Kind</span>
                <span>Pack</span>
                <span>Graph state</span>
                <span>Signal</span>
              </div>

              <div className="max-h-[420px] overflow-auto">
                {(terms?.items?.length ? terms.items : []).map((term, index) => (
                  <motion.div
                    key={`${term.surface_form}-${term.kind}-${term.canonical_form}`}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.16, delay: Math.min(index * 0.01, 0.14) }}
                    className="grid grid-cols-[1.3fr_1fr_0.75fr_0.7fr_0.8fr_0.75fr] gap-3 border-b border-white/6 px-4 py-2.5 text-[13px] transition-colors hover:bg-white/[0.02]"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-white">
                        {term.surface_form}
                      </p>
                      <p className="mt-1 text-[11px] text-slate-500">
                        updated {formatTime(term.updated_at)}
                      </p>
                    </div>
                    <div className="min-w-0">
                      <p className="truncate text-sm text-slate-200">
                        {term.canonical_form}
                      </p>
                      <p className="mt-1 text-[11px] text-slate-500">
                        support {term.support_count}
                      </p>
                    </div>
                    <div className="flex items-center">
                      <Badge size="xs" variant="info">
                        {term.kind}
                      </Badge>
                    </div>
                    <div className="flex items-center">
                      {term.domain_pack ? (
                        <Badge size="xs" variant="default">
                          {term.domain_pack}
                        </Badge>
                      ) : (
                        <span className="text-sm text-slate-500">—</span>
                      )}
                    </div>
                    <div className="flex items-center">
                      <Badge
                        size="xs"
                        variant={term.has_node ? "success" : "warning"}
                      >
                        {term.has_node ? "graph-linked" : "learned-only"}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2.5">
                      <div className="h-1.5 flex-1 rounded-full bg-slate-900/80">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{
                            width: `${Math.max(6, Math.min(100, term.score * 100))}%`,
                          }}
                          transition={{ duration: 0.28, delay: 0.02 + Math.min(index * 0.01, 0.12) }}
                          className="h-1.5 rounded-full bg-[linear-gradient(90deg,#FB7185,#A78BFA,#5EEAD4)]"
                        />
                      </div>
                      <span className="w-10 text-right text-[11px] font-medium text-slate-300">
                        {term.score.toFixed(2)}
                      </span>
                    </div>
                  </motion.div>
                ))}

                {!terms?.items?.length && (
                  <div className="px-4 py-8 text-center text-sm text-slate-400">
                    {loadingTerms
                      ? "Loading learned term matrix..."
                      : "No learned terms matched the current filters."}
                  </div>
                )}
              </div>
            </div>

            <div className="grid gap-2.5 lg:grid-cols-3">
              <div className="rounded-[14px] border border-white/8 bg-white/[0.03] p-3">
                <div className="flex items-center gap-2">
                  <BookOpenText size={14} className="text-teal-300" />
                  <p className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500">
                    Query effect
                  </p>
                </div>
                <p className="mt-2.5 text-[12px] leading-5 text-slate-400">
                  Learned lexical memory feeds canonical matching, alias recall,
                  graph linking, and domain-aware reranking later in the query path.
                </p>
              </div>

              <div className="rounded-[14px] border border-white/8 bg-white/[0.03] p-3">
                <div className="flex items-center gap-2">
                  <Network size={14} className="text-violet-300" />
                  <p className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500">
                    Graph sample
                  </p>
                </div>
                <p className="mt-2.5 text-[12px] leading-5 text-slate-400">
                  {graphView?.packs_sampled ?? 0} pack hubs, {graphView?.terms_sampled ?? 0} sampled
                  terms, and {graphView?.linked_nodes_sampled ?? 0} linked nodes are visible in the
                  current graph chamber.
                </p>
              </div>

              <div className="rounded-[14px] border border-white/8 bg-white/[0.03] p-3">
                <div className="flex items-center gap-2">
                  <ArrowRight size={14} className="text-amber-300" />
                  <p className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500">
                    What to watch
                  </p>
                </div>
                <p className="mt-2.5 text-[12px] leading-5 text-slate-400">
                  Rising support counts, more graph-linked terms, and stronger pack
                  ladders mean FAIM is becoming better grounded in your long-tail domain.
                </p>
              </div>
            </div>
          </div>
        </SectionShell>
      )}
    </div>
  );
}
