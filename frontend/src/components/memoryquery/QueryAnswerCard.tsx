"use client";

import React from "react";
import { AlertTriangle, ChevronDown, ExternalLink, FileText, Globe2, ImageIcon, Link2, Network, ScanSearch, ShieldCheck, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui";
import { MarkdownRenderer } from "./MarkdownRenderer";
import type { FaimQueryResponse, FaimQueryResultItem } from "@/contexts/ChatContext";

function temporalVariant(status?: string | null): "success" | "warning" | "outline" {
  if (status === "CURRENT") return "success";
  if (status === "HISTORICAL") return "warning";
  return "outline";
}

function hasSemanticPath(result: FaimQueryResultItem, kinds: string[]): boolean {
  const graphPaths = (result.explain?.graph_paths as Array<Record<string, unknown>> | undefined) || [];
  return graphPaths.some((path) => kinds.includes(String(path.kind || "")));
}

function hasScore(result: FaimQueryResultItem, key: string): boolean {
  return Number(result.score_components?.[key] || 0) > 0;
}

function anchorSummary(anchor?: Record<string, unknown> | null): string {
  if (!anchor) return "source";
  const parts: string[] = [];
  const page = anchor.page ?? anchor.page_number;
  const section = anchor.section;
  const paragraph = anchor.paragraph;
  if (page != null) parts.push(`p.${page}`);
  if (section) parts.push(`sec.${section}`);
  if (paragraph != null) parts.push(`para.${paragraph}`);
  return parts.length ? parts.join(" · ") : "source";
}

function scoreValue(value?: number): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "0.00";
  return value.toFixed(2);
}

function scoreComponentEntries(result: FaimQueryResultItem): Array<[string, number]> {
  return Object.entries(result.score_components || {})
    .filter(([, value]) => typeof value === "number" && value > 0)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8);
}

function resultBadges(result: FaimQueryResultItem): Array<{ label: string; variant: "info" | "secondary" | "warning" | "success" }> {
  const badges: Array<{ label: string; variant: "info" | "secondary" | "warning" | "success" }> = [];

  if (hasSemanticPath(result, ["translation", "concept_surface"])) {
    badges.push({ label: "Concept-linked", variant: "info" });
  }
  if (hasScore(result, "modality")) {
    badges.push({ label: "Multimodal", variant: "secondary" });
  }
  if (hasScore(result, "domain") || hasScore(result, "domain_entity_link") || hasScore(result, "domain_fact_support")) {
    badges.push({ label: "Domain-linked", variant: "warning" });
  }
  if (hasScore(result, "graph")) {
    badges.push({ label: "Graph-ranked", variant: "success" });
  }

  return badges;
}

export function QueryAnswerCard({ queryData }: { queryData: FaimQueryResponse }) {
  const answer = queryData.answer;
  const topResults = queryData.results.slice(0, 5);

  return (
    <div className="mt-4 space-y-4 rounded-2xl border border-primary-500/15 bg-primary-500/[0.03] p-4">
      {answer && (
        <section className="space-y-3 rounded-2xl border border-white/8 bg-black/20 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="primary" size="sm" icon={<Sparkles size={12} />}>
              Answer
            </Badge>
            <Badge variant={answer.confidence >= 0.75 ? "success" : answer.confidence >= 0.45 ? "warning" : "outline"} size="sm" icon={<ShieldCheck size={12} />}>
              Confidence {scoreValue(answer.confidence)}
            </Badge>
            <Badge variant="outline" size="sm">
              {queryData.duration_ms ? `${Math.round(queryData.duration_ms)} ms` : "runtime n/a"}
            </Badge>
          </div>

          <div className="prose-faim">
            <MarkdownRenderer content={answer.direct_answer || "No direct answer extracted from current evidence."} />
          </div>

          {answer.contradiction_notes.length > 0 && (
            <div className="space-y-2 rounded-xl border border-amber-500/20 bg-amber-500/5 p-3">
              <div className="flex items-center gap-2 text-[11px] font-black uppercase tracking-[0.2em] text-amber-300">
                <AlertTriangle size={14} />
                Contradictions
              </div>
              <ul className="space-y-1 text-sm text-slate-300">
                {answer.contradiction_notes.map((note, idx) => (
                  <li key={`${note}-${idx}`}>{note}</li>
                ))}
              </ul>
            </div>
          )}

          {answer.supporting_spans.length > 0 && (
            <div className="space-y-2">
              <div className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400">Supporting Evidence</div>
              <div className="space-y-2">
                {answer.supporting_spans.map((span) => (
                  <div key={`${span.node_id}-${span.score}`} className="rounded-xl border border-white/8 bg-white/[0.02] p-3">
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      <Badge variant={temporalVariant(span.temporal_status)} size="xs">
                        {span.temporal_status || "UNSPECIFIED"}
                      </Badge>
                      <Badge variant="outline" size="xs">
                        Node {span.node_id.slice(0, 8)}
                      </Badge>
                      <Badge variant="outline" size="xs">
                        Span {scoreValue(span.score)}
                      </Badge>
                    </div>
                    <p className="text-sm leading-6 text-slate-300">{span.text}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {(answer.citations.length > 0 || answer.provenance) && (
            <div className="grid gap-3 lg:grid-cols-[1.2fr_0.8fr]">
              <div className="space-y-2 rounded-xl border border-white/8 bg-white/[0.02] p-3">
                <div className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400">Citations</div>
                <div className="space-y-2">
                  {answer.citations.map((citation) => (
                    <div key={`${citation.node_id}-${citation.block_id || citation.raw_id}`} className="flex flex-wrap items-center gap-2 text-xs text-slate-300">
                      <a
                        href="/dashboard/storage"
                        className="inline-flex items-center gap-1 text-primary-300 hover:text-primary-200"
                      >
                        <FileText size={12} />
                        {citation.raw_id || citation.block_id || citation.node_id.slice(0, 8)}
                        <ExternalLink size={11} />
                      </a>
                      <Badge variant="outline" size="xs">
                        {anchorSummary(citation.anchor)}
                      </Badge>
                      <Badge variant="outline" size="xs">
                        Score {scoreValue(citation.score)}
                      </Badge>
                    </div>
                  ))}
                </div>
              </div>

              <div className="space-y-2 rounded-xl border border-white/8 bg-white/[0.02] p-3">
                <div className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400">Provenance</div>
                <div className="space-y-2 text-xs text-slate-300">
                  {Object.entries(answer.provenance || {}).map(([key, value]) => (
                    <div key={key} className="flex items-start justify-between gap-3">
                      <span className="uppercase tracking-wide text-slate-500">{key}</span>
                      <span className="text-right font-mono text-slate-300 break-all">
                        {typeof value === "string" || typeof value === "number" ? String(value) : JSON.stringify(value)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </section>
      )}

      {topResults.length > 0 && (
        <section className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline" size="sm" icon={<Link2 size={12} />}>
              Retrieved {queryData.results.length} result{queryData.results.length === 1 ? "" : "s"}
            </Badge>
            <Badge variant="outline" size="sm">
              Graph {queryData.graph_id}
            </Badge>
          </div>

          <div className="space-y-3">
            {topResults.map((result, index) => {
              const badges = resultBadges(result);
              const evidence = result.evidence;

              return (
                <div key={result.node_id} className="rounded-2xl border border-white/8 bg-black/20 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="outline" size="xs">
                          #{index + 1}
                        </Badge>
                        <Badge variant={temporalVariant(result.temporal_status)} size="xs">
                          {result.temporal_status || "UNSPECIFIED"}
                        </Badge>
                        <Badge variant="outline" size="xs">
                          Score {scoreValue(result.score)}
                        </Badge>
                        <Badge variant="outline" size="xs">
                          L{result.level}
                        </Badge>
                        {badges.map((badge) => (
                          <Badge key={`${result.node_id}-${badge.label}`} variant={badge.variant} size="xs">
                            {badge.label}
                          </Badge>
                        ))}
                      </div>
                      <div className="text-xs text-slate-400">
                        Node <span className="font-mono text-slate-300">{result.node_id}</span>
                      </div>
                    </div>
                    {evidence && (
                      <div className="flex flex-wrap items-center gap-2 text-xs">
                        <a href="/dashboard/storage" className="inline-flex items-center gap-1 text-primary-300 hover:text-primary-200">
                          <FileText size={12} />
                          {evidence.raw_id || evidence.block_id || "source"}
                          <ExternalLink size={11} />
                        </a>
                        <Badge variant="outline" size="xs">
                          {anchorSummary(evidence.anchor)}
                        </Badge>
                      </div>
                    )}
                  </div>

                  <details className="mt-3 rounded-xl border border-white/8 bg-white/[0.02] p-3">
                    <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-[11px] font-black uppercase tracking-[0.2em] text-slate-300">
                      Why this answer
                      <ChevronDown size={14} className="text-slate-500" />
                    </summary>
                    <div className="mt-3 space-y-4">
                      <div className="grid gap-2 md:grid-cols-2">
                        {scoreComponentEntries(result).map(([key, value]) => (
                          <div key={`${result.node_id}-${key}`} className="rounded-lg border border-white/6 bg-black/20 px-3 py-2">
                            <div className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">{key.replaceAll("_", " ")}</div>
                            <div className="mt-1 text-sm text-slate-200">{scoreValue(value)}</div>
                          </div>
                        ))}
                      </div>

                      {result.explain && (
                        <div className="grid gap-3 lg:grid-cols-[0.9fr_1.1fr]">
                          <div className="space-y-2 rounded-xl border border-white/8 bg-black/20 p-3">
                            <div className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400">Reasoning Graph</div>
                            <div className="space-y-2 text-xs text-slate-300">
                              {(((result.explain.graph_paths as Array<Record<string, unknown>> | undefined) || []).slice(0, 6)).map((path, idx) => (
                                <div key={`${result.node_id}-path-${idx}`} className="flex items-center gap-2">
                                  <Network size={12} className="text-primary-300" />
                                  <span>{String(path.kind || "path")}</span>
                                  <Badge variant="outline" size="xs">
                                    {scoreValue(Number(path.weight || 0))}
                                  </Badge>
                                </div>
                              ))}
                              {hasSemanticPath(result, ["translation", "concept_surface"]) && (
                                <div className="flex items-center gap-2">
                                  <Globe2 size={12} className="text-cyan-300" />
                                  <span>Cross-lingual concept bridge detected</span>
                                </div>
                              )}
                              {hasScore(result, "modality") && (
                                <div className="flex items-center gap-2">
                                  <ImageIcon size={12} className="text-violet-300" />
                                  <span>OCR / table / filename evidence contributed</span>
                                </div>
                              )}
                              {hasScore(result, "domain") && (
                                <div className="flex items-center gap-2">
                                  <ScanSearch size={12} className="text-amber-300" />
                                  <span>Domain-linked entity or fact support contributed</span>
                                </div>
                              )}
                            </div>
                          </div>

                          <div className="space-y-2 rounded-xl border border-white/8 bg-black/20 p-3">
                            <div className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400">Explain Payload</div>
                            <pre className="max-h-72 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-black/30 p-3 text-[11px] leading-5 text-slate-300">
                              {JSON.stringify(result.explain, null, 2)}
                            </pre>
                          </div>
                        </div>
                      )}
                    </div>
                  </details>
                </div>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}
