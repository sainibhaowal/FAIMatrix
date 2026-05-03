"use client";

import React, { useMemo, useState } from "react";
import {
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  FileText,
  Layers,
} from "lucide-react";
import {
  ANSWER_MODE_LABELS,
  type AnswerMode,
  type FaimQueryResponse,
} from "@/contexts/ChatContext";

function anchorLabel(anchor?: Record<string, unknown> | null): string {
  if (!anchor) return "";
  const page = anchor.page ?? anchor.page_number;
  const section = anchor.section;
  if (page != null) return `p.${page}`;
  if (section) return `§${section}`;
  return "";
}

function fileLabel(
  resultMap: Record<string, FaimQueryResponse["results"][number]>,
  nodeId: string,
): string {
  const result = resultMap[nodeId];
  const rawId = result?.evidence?.raw_id ?? "";
  const anchor = result?.evidence?.anchor ?? null;
  const page = anchorLabel(anchor);
  const source = rawId ? rawId.slice(0, 22) : `Node ${nodeId.slice(0, 8)}`;
  return page ? `${source} · ${page}` : source;
}

function TraceRow({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-start justify-between gap-4 rounded-xl border border-white/[0.05] bg-white/[0.02] px-3 py-2">
      <span className="text-[9px] font-black uppercase tracking-[0.24em] text-slate-600">
        {label}
      </span>
      <span className="text-[10px] text-slate-300 text-right leading-relaxed">
        {value}
      </span>
    </div>
  );
}

export function MemoryTraceFooter({
  queryData,
  answerMode = "direct",
}: {
  queryData: FaimQueryResponse;
  answerMode?: AnswerMode;
}) {
  const [open, setOpen] = useState(false);

  const citations = queryData.answer?.citations ?? [];
  const spans = queryData.answer?.supporting_spans ?? [];
  const contradictions = queryData.answer?.contradiction_notes ?? [];
  const confidence = queryData.answer?.confidence ?? 0;
  const ms = queryData.duration_ms ? Math.round(queryData.duration_ms) : null;
  const provenance = queryData.answer?.provenance ?? {};

  const resultMap = useMemo(() => {
    const map: Record<string, FaimQueryResponse["results"][number]> = {};
    for (const result of queryData.results ?? []) map[result.node_id] = result;
    return map;
  }, [queryData.results]);

  const topAnchors = useMemo(() => {
    const fromCitations = citations.slice(0, 4).map((citation) => ({
      nodeId: citation.node_id,
      label: fileLabel(resultMap, citation.node_id),
      score: citation.score,
      temporalStatus:
        resultMap[citation.node_id]?.temporal_status ?? null,
    }));
    if (fromCitations.length > 0) return fromCitations;

    if (spans.length === 0) {
      return (queryData.results ?? []).slice(0, 4).map((result) => ({
        nodeId: result.node_id,
        label: fileLabel(resultMap, result.node_id),
        score: result.score,
        temporalStatus: result.temporal_status ?? null,
      }));
    }

    return spans.slice(0, 4).map((span) => ({
      nodeId: span.node_id,
      label: fileLabel(resultMap, span.node_id),
      score: span.score,
      temporalStatus: span.temporal_status ?? null,
    }));
  }, [citations, spans, resultMap]);

  const temporalTags = useMemo(() => {
    const tags = new Set<string>();
    for (const span of spans) {
      const tag = (span.temporal_status || "").trim();
      if (tag) tags.add(tag.toUpperCase());
    }
    return Array.from(tags).slice(0, 3);
  }, [spans]);

  const anchorCount = citations.length || spans.length || queryData.results.length;

  return (
    <footer className="mt-4 border-t border-white/[0.06] pt-4">
      <button
        onClick={() => setOpen((prev) => !prev)}
        className="flex w-full flex-wrap items-center gap-2 text-left text-[10px] font-black uppercase tracking-[0.24em] text-slate-500 transition-colors hover:text-slate-300"
      >
        <span className="inline-flex items-center gap-1.5 rounded-full border border-primary-500/15 bg-primary-500/[0.04] px-2.5 py-1 text-[8px] text-primary-300">
          <Layers size={9} />
          {ANSWER_MODE_LABELS[answerMode]}
        </span>
        <span>{anchorCount} memory anchors</span>
        {ms != null && <span className="text-slate-600">· {ms}ms</span>}
        {confidence > 0 && (
          <span className="text-primary-300">
            · {Math.round(confidence * 100)}% confidence
          </span>
        )}
        {temporalTags.map((tag) => (
          <span
            key={tag}
            className="rounded-full border border-white/[0.07] px-2 py-1 text-[8px] text-slate-400"
          >
            {tag}
          </span>
        ))}
        {contradictions.length > 0 && (
          <span className="inline-flex items-center gap-1 rounded-full border border-amber-500/20 bg-amber-500/[0.05] px-2 py-1 text-[8px] text-amber-300">
            <AlertTriangle size={9} />
            Conflict
          </span>
        )}
        <span className="ml-auto inline-flex items-center gap-1 text-primary-300">
          {open ? "Hide trace" : "Show trace"}
          {open ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
        </span>
      </button>

      <div className="mt-2 flex flex-wrap gap-2">
        {topAnchors.map((anchor) => (
          <span
            key={`${anchor.nodeId}-${anchor.label}`}
            className="inline-flex items-center gap-1.5 rounded-full border border-white/[0.06] bg-white/[0.03] px-2.5 py-1 text-[10px] text-slate-400"
          >
            <FileText size={10} className="text-slate-500" />
            <span className="truncate">{anchor.label}</span>
            <span className="text-slate-600">
              {Math.round(anchor.score * 100)}%
            </span>
          </span>
        ))}
      </div>

      {open && (
        <div className="mt-3 rounded-2xl border border-white/[0.06] bg-black/20 p-4">
          {contradictions.length > 0 && (
            <div className="mb-4 rounded-xl border border-amber-500/15 bg-amber-500/[0.05] p-3 text-xs text-amber-200">
              <div className="mb-2 flex items-center gap-2 font-black uppercase tracking-[0.22em] text-amber-300">
                <AlertTriangle size={12} />
                Contradictions
              </div>
              <ul className="space-y-1">
                {contradictions.map((note, index) => (
                  <li key={`${note}-${index}`}>{note}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="grid gap-2 md:grid-cols-2">
            <TraceRow
              label="Graph"
              value={`${String(provenance.graph_id ?? queryData.graph_id)} · v${queryData.graph_version}`}
            />
            <TraceRow
              label="Query"
              value={String(provenance.query_hash ?? queryData.query_hash)}
            />
            <TraceRow
              label="Spans"
              value={`${spans.length} supporting span${spans.length === 1 ? "" : "s"}`}
            />
            <TraceRow
              label="Citations"
              value={`${citations.length} citation${citations.length === 1 ? "" : "s"}`}
            />
          </div>

          {spans.length > 0 && (
            <div className="mt-4 space-y-2">
              {spans.slice(0, 4).map((span, index) => {
                const result = resultMap[span.node_id];
                const anchor = anchorLabel(result?.evidence?.anchor);
                const source = result?.evidence?.raw_id
                  ? result.evidence.raw_id.slice(0, 24) +
                    (result.evidence.raw_id.length > 24 ? "..." : "")
                  : `Node ${span.node_id.slice(0, 8)}`;

                return (
                  <div
                    key={`${span.node_id}-${index}`}
                    className="rounded-xl border border-white/[0.05] bg-white/[0.02] px-3 py-2"
                  >
                    <p className="text-[13px] leading-relaxed text-slate-300">
                      {span.text}
                    </p>
                    <div className="mt-1.5 flex flex-wrap items-center gap-2 text-[10px] text-slate-600">
                      <span className="flex items-center gap-1">
                        <FileText size={9} />
                        {source}
                        {anchor && <span>{anchor}</span>}
                      </span>
                      <span className="ml-auto">
                        relevance {Math.round(span.score * 100)}%
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </footer>
  );
}
