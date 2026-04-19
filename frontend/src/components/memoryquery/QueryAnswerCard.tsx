"use client";

import React, { useState } from "react";
import { ChevronDown, ChevronRight, FileText, AlertTriangle } from "lucide-react";
import type { FaimQueryResponse } from "@/contexts/ChatContext";

function anchorLabel(anchor?: Record<string, unknown> | null): string {
  if (!anchor) return "";
  const page = anchor.page ?? anchor.page_number;
  const section = anchor.section;
  if (page != null) return `p.${page}`;
  if (section) return `§${section}`;
  return "";
}

export function QueryAnswerCard({ queryData }: { queryData: FaimQueryResponse }) {
  const [open, setOpen] = useState(false);

  const count = queryData.results?.length ?? 0;
  const spans = queryData.answer?.supporting_spans ?? [];
  const contradictions = queryData.answer?.contradiction_notes ?? [];
  const confidence = queryData.answer?.confidence ?? 0;
  const ms = queryData.duration_ms ? Math.round(queryData.duration_ms) : null;

  // Nothing retrieved — show nothing
  if (count === 0 && spans.length === 0) return null;

  const confColor =
    confidence >= 0.7 ? "text-emerald-400"
    : confidence >= 0.4 ? "text-amber-400"
    : "text-slate-500";

  return (
    <div className="mt-3">
      {/* ── Collapsed pill ── */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-full border text-[11px] font-semibold text-slate-400 hover:text-slate-200 hover:border-slate-600 transition-all"
        style={{ borderColor: "var(--os-stroke)", background: "var(--os-surface-2)" }}
      >
        {open ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
        <span>{count} {count === 1 ? "source" : "sources"} retrieved</span>
        {ms && <span className="text-slate-600">· {ms}ms</span>}
        {confidence > 0 && (
          <span className={`${confColor} ml-1`}>
            · {Math.round(confidence * 100)}% confidence
          </span>
        )}
        {contradictions.length > 0 && (
          <AlertTriangle size={11} className="text-amber-400 ml-1" />
        )}
      </button>

      {/* ── Expanded detail ── */}
      {open && (
        <div className="mt-2 space-y-2 rounded-xl border p-3" style={{ borderColor: "var(--os-stroke)", background: "var(--os-surface-1)" }}>

          {/* Contradictions — only if present */}
          {contradictions.length > 0 && (
            <div className="flex items-start gap-2 px-3 py-2 rounded-lg border border-amber-500/20 bg-amber-500/5 text-xs text-amber-300">
              <AlertTriangle size={12} className="shrink-0 mt-0.5" />
              <ul className="space-y-1">
                {contradictions.map((note, i) => <li key={i}>{note}</li>)}
              </ul>
            </div>
          )}

          {/* Supporting spans — the actual relevant text from documents */}
          {spans.length > 0 ? (
            <div className="space-y-2">
              {spans.map((span, i) => {
                const result = queryData.results.find(r => r.node_id === span.node_id);
                const evidence = result?.evidence;
                const anchor = anchorLabel(evidence?.anchor);
                const sourceLabel = evidence?.raw_id
                  ? evidence.raw_id.slice(0, 20) + (evidence.raw_id.length > 20 ? "…" : "")
                  : null;

                return (
                  <div key={`${span.node_id}-${i}`} className="rounded-lg border px-3 py-2.5" style={{ borderColor: "var(--os-stroke)", background: "var(--os-surface-2)" }}>
                    <p className="text-[13px] text-slate-300 leading-relaxed">{span.text}</p>
                    <div className="mt-1.5 flex items-center gap-2 text-[10px] text-slate-600">
                      {sourceLabel && (
                        <span className="flex items-center gap-1">
                          <FileText size={9} />
                          {sourceLabel}
                          {anchor && <span>{anchor}</span>}
                        </span>
                      )}
                      <span className="ml-auto">relevance {Math.round(span.score * 100)}%</span>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            /* No spans: show a minimal source list */
            <div className="space-y-1.5">
              {queryData.results.slice(0, 5).map((r, i) => {
                const anchor = anchorLabel(r.evidence?.anchor);
                const sourceLabel = r.evidence?.raw_id
                  ? r.evidence.raw_id.slice(0, 24) + (r.evidence.raw_id.length > 24 ? "…" : "")
                  : `Node ${r.node_id.slice(0, 8)}`;
                return (
                  <div key={r.node_id} className="flex items-center gap-2 text-[11px] text-slate-400 px-1">
                    <span className="text-slate-600 w-4">#{i + 1}</span>
                    <FileText size={10} className="shrink-0" />
                    <span className="truncate">{sourceLabel}{anchor ? ` · ${anchor}` : ""}</span>
                    <span className="ml-auto text-slate-600 tabular-nums">{Math.round(r.score * 100)}%</span>
                  </div>
                );
              })}
              {count > 5 && (
                <p className="text-[10px] text-slate-600 px-1">+{count - 5} more sources</p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
