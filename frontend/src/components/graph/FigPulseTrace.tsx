"use client";

import { motion } from "framer-motion";
import { Badge, Spinner } from "@/components/ui";
import { nodeColorByState } from "@/lib/figViewLayout";
import { nodeStateClass, safeNodeTitle } from "@/lib/figViewSafety";
import type {
  FigInteractionPulse,
  FigNode,
  FigNodeDisplayState,
  FigPulseTrace,
  FigQueryExplain,
} from "@/types/figView";

type FigPulseTraceProps = {
  pulseTrace: FigPulseTrace | null | undefined;
  nodeIndex: Map<string, FigNode>;
  queryExplain?: FigQueryExplain | null;
  livePulse?: FigInteractionPulse | null;
  focusNodeId?: string | null;
  loading?: boolean;
  emptyText?: string;
};

function SignalChip({
  label,
  value,
}: {
  label: string;
  value: number | string;
}) {
  return (
    <div className="rounded-lg border border-slate-800/60 bg-slate-900/40 px-2.5 py-2">
      <p className="text-[9px] uppercase tracking-widest text-slate-500">
        {label}
      </p>
      <p className="mt-0.5 font-mono text-[11px] text-slate-200">{value}</p>
    </div>
  );
}

function SectionTitle({
  title,
  subtitle,
}: {
  title: string;
  subtitle?: string;
}) {
  return (
    <div className="space-y-0.5">
      <p className="text-[9px] font-semibold uppercase tracking-[0.3em] text-cyan-300/70">
        {title}
      </p>
      {subtitle && (
        <p className="text-[10px] leading-relaxed text-slate-400">{subtitle}</p>
      )}
    </div>
  );
}

function StatRow({
  label,
  value,
}: {
  label: string;
  value: number | string | null | undefined;
}) {
  return (
    <div className="rounded-lg border border-slate-800/60 bg-slate-950/40 px-2.5 py-2">
      <p className="text-[8px] uppercase tracking-widest text-slate-500">
        {label}
      </p>
      <p className="mt-0.5 text-[11px] font-mono text-slate-200">
        {value ?? "—"}
      </p>
    </div>
  );
}

export default function FigPulseTrace({
  pulseTrace,
  nodeIndex,
  queryExplain = null,
  livePulse = null,
  focusNodeId = null,
  loading = false,
  emptyText = "No pulse trace available for this relation.",
}: FigPulseTraceProps) {
  if (loading) {
    return (
      <div className="rounded-xl border border-slate-800/60 bg-slate-950/50 px-3 py-4">
        <div className="flex items-center gap-2 text-slate-300">
          <Spinner size="sm" />
          <span className="text-xs">Building pulse trace…</span>
        </div>
      </div>
    );
  }

  if (!pulseTrace) {
    return (
      <div className="rounded-xl border border-dashed border-slate-800/60 bg-slate-950/30 px-3 py-4">
        <p className="text-xs text-slate-500">{emptyText}</p>
      </div>
    );
  }

  const steps = pulseTrace.steps ?? [];
  const layerSummary = pulseTrace.layer_summary ?? {};
  const strongLayers = Object.entries(layerSummary).sort(
    (left, right) => right[1] - left[1] || left[0].localeCompare(right[0]),
  );
  const qExp = queryExplain ?? null;
  const queryExpansion = qExp?.phaseB_query_expansion ?? null;
  const domainRelevance = qExp?.domain_relevance ?? null;
  const graphScore = qExp?.phase3_graph_score ?? null;
  const reranker = qExp?.phase4_reranker ?? null;
  const lateInteraction = qExp?.phaseC_late_interaction ?? null;
  const fusion = qExp?.fusion_summary ?? null;
  const queryFusion = qExp?.query_fusion_summary ?? null;
  const semanticSignature = qExp?.semantic_signature ?? null;
  const reasonLedger = qExp?.reason_source_ledger ?? null;
  const pulseEvents = reasonLedger?.events ?? qExp?.pulse_event_stream ?? pulseTrace.events ?? [];
  const liveEvents = livePulse?.events ?? [];
  const rerankerExplain =
    reranker?.explain && typeof reranker.explain === "object"
      ? (reranker.explain as Record<string, unknown>)
      : null;
  const lateExplain =
    lateInteraction?.explain && typeof lateInteraction.explain === "object"
      ? (lateInteraction.explain as Record<string, unknown>)
      : null;
  const rerankerQuerySignature =
    typeof rerankerExplain?.query_signature === "string"
      ? rerankerExplain.query_signature
      : null;
  const rerankerDocSignature =
    typeof rerankerExplain?.doc_signature === "string"
      ? rerankerExplain.doc_signature
      : null;
  const rerankerEvidenceComponents = Array.isArray(
    rerankerExplain?.evidence_components,
  )
    ? (rerankerExplain.evidence_components as Array<{
        label?: string;
        value?: number;
      }>)
    : [];
  const lateMatchedUnits =
    lateExplain?.matched_units && typeof lateExplain.matched_units === "object"
      ? (lateExplain.matched_units as Record<string, unknown>)
      : null;

  return (
    <div className="space-y-3 rounded-2xl border border-cyan-500/15 bg-slate-950/60 p-3">
      <div className="flex items-center justify-between gap-2">
        <div>
          <p className="text-[9px] font-semibold uppercase tracking-[0.3em] text-cyan-300/70">
            Pulse Protocol
          </p>
          <p className="text-[11px] text-slate-400">
            Backend-backed trace over path, semantic signature, metrics, and provenance.
          </p>
        </div>
        <div className="flex items-center gap-1.5">
          <Badge size="sm" variant="outline">
            {pulseTrace.protocol}
          </Badge>
          <Badge size="sm" variant="secondary">
            {steps.length} steps
          </Badge>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <SignalChip label="Trace ID" value={(pulseTrace.trace_id ?? "none").slice(0, 12)} />
        <SignalChip label="Path Length" value={pulseTrace.path_length} />
        <SignalChip label="Source" value={pulseTrace.source} />
        <SignalChip label="Signals" value={Object.keys(layerSummary).length} />
      </div>

      <div className="flex flex-wrap gap-1.5">
        {strongLayers.length === 0 ? (
          <span className="text-[10px] text-slate-600">No runtime evidence layers reported.</span>
        ) : (
          strongLayers.slice(0, 8).map(([layer, count]) => (
            <Badge key={layer} size="sm" variant="outline">
              {layer}: {count}
            </Badge>
          ))
        )}
      </div>

      {qExp && (
        <div className="space-y-3 rounded-2xl border border-violet-500/15 bg-violet-500/5 p-3">
          <SectionTitle
            title="Reason layers"
            subtitle="Query-time layers that shaped the current result and its overlay state."
          />

          {reasonLedger && (
            <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/5 p-3 space-y-2">
              <SectionTitle
                title="Reason source ledger"
                subtitle="Canonical per-node pulse ledger reused by the canvas, inspector, and relation drawer."
              />
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                <StatRow label="Protocol" value={reasonLedger.protocol} />
                <StatRow
                  label="Confidence"
                  value={`${(reasonLedger.confidence * 100).toFixed(0)}%`}
                />
                <StatRow label="Events" value={reasonLedger.event_count} />
                <StatRow
                  label="Trace"
                  value={(reasonLedger.trace_id ?? "none").slice(0, 12)}
                />
              </div>
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(reasonLedger.source_summary ?? {})
                  .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
                  .slice(0, 10)
                  .map(([source, count]) => (
                    <Badge key={source} size="sm" variant="outline">
                      {source}: {count}
                    </Badge>
                  ))}
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                <div className="rounded-lg border border-slate-800/60 bg-slate-950/40 p-2">
                  <p className="text-[9px] uppercase tracking-widest text-slate-500">
                    Why this node glows
                  </p>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {Object.entries(reasonLedger.why_glowing.expansion_sources ?? {})
                      .slice(0, 6)
                      .map(([source, count]) => (
                        <Badge key={source} size="sm" variant="secondary">
                          {source}: {count}
                        </Badge>
                      ))}
                    {Object.entries(reasonLedger.why_glowing.reranker_components ?? {})
                      .filter(([, value]) => Math.abs(Number(value)) > 0)
                      .slice(0, 4)
                      .map(([source, value]) => (
                        <Badge key={source} size="sm" variant="outline">
                          rerank {source}: {Number(value).toFixed(2)}
                        </Badge>
                      ))}
                    {Object.entries(reasonLedger.why_glowing.late_interaction_components ?? {})
                      .filter(([, value]) => Math.abs(Number(value)) > 0)
                      .slice(0, 4)
                      .map(([source, value]) => (
                        <Badge key={source} size="sm" variant="outline">
                          late {source}: {Number(value).toFixed(2)}
                        </Badge>
                      ))}
                  </div>
                </div>
                <div className="rounded-lg border border-slate-800/60 bg-slate-950/40 p-2">
                  <p className="text-[9px] uppercase tracking-widest text-slate-500">
                    Hop and domain proof
                  </p>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {(reasonLedger.why_glowing.graph_hops ?? []).slice(0, 5).map((hop, idx) => (
                      <Badge key={`${idx}-${String(hop.kind ?? "hop")}`} size="sm" variant="secondary">
                        hop {String(hop.hop ?? idx + 1)}: {String(hop.kind ?? "edge")}
                      </Badge>
                    ))}
                    {(reasonLedger.why_glowing.domain_memory?.query_links ?? [])
                      .slice(0, 5)
                      .map((link, idx) => (
                        <Badge key={`${idx}-${String(link.term ?? link.node_id ?? "domain")}`} size="sm" variant="outline">
                          {String(link.term ?? link.canonical_form ?? "domain").slice(0, 24)}
                        </Badge>
                      ))}
                  </div>
                </div>
              </div>
              {pulseEvents.length > 0 && (
                <div className="rounded-lg border border-slate-800/60 bg-slate-950/40 p-2">
                  <p className="text-[9px] uppercase tracking-widest text-slate-500">
                    Event stream
                  </p>
                  <div className="mt-2 max-h-44 space-y-1 overflow-auto pr-1">
                    {pulseEvents.slice(0, 18).map((event) => (
                      <div
                        key={event.event_id}
                        className="grid grid-cols-[72px_1fr_52px] gap-2 rounded-md border border-slate-800/50 bg-slate-950/50 px-2 py-1.5 text-[10px]"
                      >
                        <span className="font-mono text-cyan-300">
                          {event.stage}
                        </span>
                        <span className="truncate text-slate-300">
                          {event.source}
                          {event.hop != null ? ` · hop ${event.hop}` : ""}
                        </span>
                        <span className="text-right font-mono text-slate-400">
                          {(event.strength * 100).toFixed(0)}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <StatRow
              label="Top node"
              value={focusNodeId ? focusNodeId.slice(0, 12) : "current"}
            />
            <StatRow
              label="Expansion terms"
              value={queryExpansion?.expansion_count ?? 0}
            />
            <StatRow
              label="Domain candidates"
              value={domainRelevance?.candidate_count ?? 0}
            />
            <StatRow
              label="Final score"
              value={
                fusion?.final_score != null
                  ? fusion.final_score.toFixed(3)
                  : "—"
              }
            />
          </div>

          {semanticSignature && (
            <div className="rounded-xl border border-slate-800/60 bg-slate-950/35 p-3 space-y-2">
              <SectionTitle
                title="Semantic signature"
                subtitle="Additive lexical and concept channels used to ground the node."
              />
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                <StatRow
                  label="Alias families"
                  value={semanticSignature.alias_families?.length ?? 0}
                />
                <StatRow
                  label="Translit tokens"
                  value={semanticSignature.transliterated_tokens?.length ?? 0}
                />
                <StatRow
                  label="Stem families"
                  value={semanticSignature.stem_families?.length ?? 0}
                />
                <StatRow
                  label="Relation cues"
                  value={semanticSignature.relation_cues?.length ?? 0}
                />
                <StatRow
                  label="Value cues"
                  value={semanticSignature.value_cues?.length ?? 0}
                />
                <StatRow
                  label="Temporal cues"
                  value={semanticSignature.temporal_cues?.length ?? 0}
                />
              </div>
            </div>
          )}

          {queryExpansion && (
            <div className="rounded-xl border border-slate-800/60 bg-slate-950/35 p-3 space-y-2">
              <SectionTitle
                title="Weighted expansion"
                subtitle="Deterministic, capped sources that widened the query before scoring."
              />
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {Object.entries(queryExpansion.source_counts ?? {})
                  .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
                  .slice(0, 4)
                  .map(([source, count]) => (
                    <StatRow key={source} label={source} value={count} />
                  ))}
              </div>
              <div className="flex flex-wrap gap-1.5">
                {(queryExpansion.expansions ?? []).slice(0, 10).map((exp) => (
                  <Badge key={`${exp.term ?? "term"}-${exp.score ?? 0}`} size="sm" variant="outline">
                    {(exp.term ?? "term").slice(0, 28)}
                    {exp.score != null ? ` · ${(exp.score * 100).toFixed(0)}%` : ""}
                  </Badge>
                ))}
              </div>
              {queryExpansion.semantic_registry && (
                <div className="grid grid-cols-3 gap-2">
                  <StatRow
                    label="Registry terms"
                    value={queryExpansion.semantic_registry.registry_term_count ?? 0}
                  />
                  <StatRow
                    label="Static terms"
                    value={queryExpansion.semantic_registry.static_term_count ?? 0}
                  />
                  <StatRow
                    label="Registry expansions"
                    value={queryExpansion.semantic_registry.expansion_count ?? 0}
                  />
                </div>
              )}
            </div>
          )}

          <div className="grid gap-3 lg:grid-cols-2">
            {domainRelevance && (
              <div className="rounded-xl border border-slate-800/60 bg-slate-950/35 p-3 space-y-2">
                <SectionTitle
                  title="Domain memory"
                  subtitle="Terms and candidate support pulled from graph-local knowledge."
                />
                <div className="grid grid-cols-2 gap-2">
                  <StatRow
                    label="Candidates"
                    value={domainRelevance.candidate_count ?? 0}
                  />
                  <StatRow
                    label="Matched terms"
                    value={domainRelevance.query_links?.length ?? 0}
                  />
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {(domainRelevance.query_links ?? []).slice(0, 8).map((link) => (
                    <Badge key={`${link.term ?? link.node_id ?? "link"}-${link.kind ?? "k"}`} size="sm" variant="secondary">
                      {(link.term ?? link.node_id ?? "link").slice(0, 26)}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {graphScore && (
              <div className="rounded-xl border border-slate-800/60 bg-slate-950/35 p-3 space-y-2">
                <SectionTitle
                  title="Graph score"
                  subtitle="Path, diffusion, neighborhood, and contradiction signal balance."
                />
                <div className="grid grid-cols-2 gap-2">
                  <StatRow label="Total" value={graphScore.total?.toFixed(3) ?? "—"} />
                  <StatRow label="Path" value={graphScore.path?.toFixed(3) ?? "—"} />
                  <StatRow label="Diffusion" value={graphScore.diffusion?.toFixed(3) ?? "—"} />
                  <StatRow label="Neighborhood" value={graphScore.neighborhood?.toFixed(3) ?? "—"} />
                  <StatRow label="Contradiction" value={graphScore.contradiction?.toFixed(3) ?? "—"} />
                </div>
              </div>
            )}
          </div>

          <div className="grid gap-3 lg:grid-cols-2">
          {reranker && (
            <div className="rounded-xl border border-slate-800/60 bg-slate-950/35 p-3 space-y-2">
                <SectionTitle
                  title="Reranker"
                  subtitle="Deterministic evidence alignment and contradiction handling."
                />
                <div className="grid grid-cols-2 gap-2">
                  <StatRow label="Total" value={reranker.total?.toFixed(3) ?? "—"} />
                  <StatRow
                    label="Components"
                    value={Object.keys(reranker.components ?? {}).length}
                  />
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {Object.entries(reranker.components ?? {})
                    .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
                    .slice(0, 6)
                    .map(([key, value]) => (
                      <Badge key={key} size="sm" variant="outline">
                        {key}: {value.toFixed(3)}
                      </Badge>
                    ))}
                </div>
                {rerankerExplain && (
                  <div className="rounded-lg border border-slate-800/50 bg-slate-950/30 p-2 space-y-1.5">
                    <p className="text-[9px] uppercase tracking-widest text-slate-500">
                      Signature trail
                    </p>
                    <div className="grid grid-cols-1 gap-1.5 text-[10px] text-slate-300">
                      {rerankerQuerySignature && (
                        <p className="font-mono text-slate-400 break-words">
                          query: {rerankerQuerySignature}
                        </p>
                      )}
                      {rerankerDocSignature && (
                        <p className="font-mono text-slate-400 break-words">
                          doc: {rerankerDocSignature}
                        </p>
                      )}
                    </div>
                    {rerankerEvidenceComponents.length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {rerankerEvidenceComponents.slice(0, 6).map((part, idx) => (
                            <Badge key={`${idx}-${part.label ?? "e"}`} size="sm" variant="secondary">
                              {(part.label ?? "evidence").slice(0, 22)}
                              {part.value != null ? `: ${Number(part.value).toFixed(3)}` : ""}
                            </Badge>
                          ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {lateInteraction && (
              <div className="rounded-xl border border-slate-800/60 bg-slate-950/35 p-3 space-y-2">
                <SectionTitle
                  title="Late interaction"
                  subtitle="Token, phrase, and proposition alignment used for additive reranking."
                />
                <div className="grid grid-cols-2 gap-2">
                  <StatRow
                    label="Total"
                    value={lateInteraction.total?.toFixed(3) ?? "—"}
                  />
                  <StatRow
                    label="Components"
                    value={Object.keys(lateInteraction.components ?? {}).length}
                  />
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {Object.entries(lateInteraction.components ?? {})
                    .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
                    .slice(0, 6)
                    .map(([key, value]) => (
                      <Badge key={key} size="sm" variant="outline">
                        {key}: {value.toFixed(3)}
                      </Badge>
                    ))}
                </div>
                {lateMatchedUnits && (
                  <div className="rounded-lg border border-slate-800/50 bg-slate-950/30 p-2 space-y-1.5">
                    <p className="text-[9px] uppercase tracking-widest text-slate-500">
                      Matched units
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {Object.entries(lateMatchedUnits)
                        .flatMap(([label, values]) =>
                          Array.isArray(values)
                            ? values.slice(0, 3).map((value) => ({
                                label,
                                value: String(value),
                              }))
                            : [],
                        )
                        .slice(0, 12)
                        .map((item, idx) => (
                          <Badge key={`${item.label}-${idx}`} size="sm" variant="secondary">
                            {item.label}: {item.value.slice(0, 18)}
                          </Badge>
                        ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {queryFusion && (
            <div className="rounded-xl border border-slate-800/60 bg-slate-950/35 p-3 space-y-2">
              <SectionTitle
                title="Fusion summary"
                subtitle="How the final candidate set was assembled from all active layers."
              />
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {Object.entries(queryFusion.candidate_pool ?? {})
                  .slice(0, 4)
                  .map(([label, value]) => (
                    <StatRow key={label} label={label} value={value} />
                  ))}
              </div>
              <div className="flex flex-wrap gap-1.5">
                {(fusion?.active_layers ?? []).slice(0, 8).map((layer) => (
                  <Badge key={layer} size="sm" variant="secondary">
                    {layer}
                  </Badge>
                ))}
              </div>
              {queryFusion?.top_result?.strongest_layers && (
                <div className="flex flex-wrap gap-1.5">
                  {queryFusion.top_result.strongest_layers.slice(0, 6).map((layer, idx) => (
                    <Badge key={`${layer.layer ?? "layer"}-${idx}`} size="sm" variant="outline">
                      {layer.layer ?? "layer"}
                      {layer.contribution != null
                        ? `: ${(layer.contribution * 100).toFixed(0)}%`
                        : ""}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {livePulse && (
        <div className="space-y-3 rounded-2xl border border-fuchsia-500/15 bg-fuchsia-500/5 p-3">
          <SectionTitle
            title="Live FIG interaction pulse"
            subtitle="A shared pulse-v2 interaction ledger derived from the current FIG state."
          />
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <StatRow label="Protocol" value={livePulse.protocol} />
            <StatRow
              label="Confidence"
              value={`${(livePulse.confidence * 100).toFixed(0)}%`}
            />
            <StatRow label="Events" value={livePulse.event_count} />
            <StatRow
              label="Trace"
              value={(livePulse.trace_id ?? "none").slice(0, 12)}
            />
          </div>
          <div className="flex flex-wrap gap-1.5">
            {(livePulse.active_layers ?? []).slice(0, 8).map((layer) => (
              <Badge key={layer} size="sm" variant="outline">
                {layer}
              </Badge>
            ))}
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            <div className="rounded-lg border border-slate-800/60 bg-slate-950/40 p-2">
              <p className="text-[9px] uppercase tracking-widest text-slate-500">
                UI context
              </p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {livePulse.ui_context?.selected_node_id && (
                  <Badge size="sm" variant="secondary">
                    selected: {livePulse.ui_context.selected_node_id.slice(0, 12)}
                  </Badge>
                )}
                {livePulse.ui_context?.hovered_node_id && (
                  <Badge size="sm" variant="outline">
                    hover: {livePulse.ui_context.hovered_node_id.slice(0, 12)}
                  </Badge>
                )}
                {livePulse.ui_context?.overlay_mode && (
                  <Badge size="sm" variant="outline">
                    overlay: {livePulse.ui_context.overlay_mode}
                  </Badge>
                )}
                {livePulse.ui_context?.top_mode && (
                  <Badge size="sm" variant="outline">
                    mode: {livePulse.ui_context.top_mode}
                  </Badge>
                )}
              </div>
            </div>
            <div className="rounded-lg border border-slate-800/60 bg-slate-950/40 p-2">
              <p className="text-[9px] uppercase tracking-widest text-slate-500">
                UI source summary
              </p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {Object.entries(livePulse.source_summary ?? {})
                  .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
                  .slice(0, 10)
                  .map(([source, count]) => (
                    <Badge key={source} size="sm" variant="outline">
                      {source}: {count}
                    </Badge>
                  ))}
              </div>
            </div>
          </div>
          {liveEvents.length > 0 && (
            <div className="rounded-lg border border-slate-800/60 bg-slate-950/40 p-2">
              <p className="text-[9px] uppercase tracking-widest text-slate-500">
                Live event stream
              </p>
              <div className="mt-2 max-h-44 space-y-1 overflow-auto pr-1">
                {liveEvents.slice(0, 18).map((event) => (
                  <div
                    key={event.event_id}
                    className="grid grid-cols-[72px_1fr_52px] gap-2 rounded-md border border-slate-800/50 bg-slate-950/50 px-2 py-1.5 text-[10px]"
                  >
                    <span className="font-mono text-fuchsia-300">
                      {event.stage}
                    </span>
                    <span className="truncate text-slate-300">
                      {event.source}
                      {event.hop != null ? ` · hop ${event.hop}` : ""}
                    </span>
                    <span className="text-right font-mono text-slate-400">
                      {(event.strength * 100).toFixed(0)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="space-y-2">
        {steps.length === 0 ? (
          <p className="text-[10px] text-slate-500">{emptyText}</p>
        ) : (
          steps.map((step) => {
            const n = nodeIndex.get(step.node_id);
            const title = n ? safeNodeTitle(n) : step.title;
            const state = (n ? nodeStateClass(n) : "unknown") as FigNodeDisplayState;
            const stateColor = nodeColorByState(state, false);
            return (
              <motion.div
                key={`${step.node_id}-${step.index}`}
                layout
                className="rounded-xl border border-slate-800/60 bg-slate-900/40 p-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 min-w-0">
                      <span
                        className="h-2.5 w-2.5 rounded-full shrink-0"
                        style={{ backgroundColor: stateColor }}
                      />
                      <p className="truncate text-[12px] font-semibold text-slate-100">
                        {title}
                      </p>
                    </div>
                    <p className="mt-1 text-[9px] uppercase tracking-widest text-slate-500">
                      Hop {step.index + 1}
                      {step.via_edge ? ` via ${step.via_edge.kind}` : ""}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-[9px] uppercase tracking-widest text-slate-500">
                      Pulse
                    </p>
                    <p className="font-mono text-[12px] text-cyan-300">
                      {(step.pulse_strength * 100).toFixed(0)}%
                    </p>
                  </div>
                </div>

                <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
                  <SignalChip label="Touches" value={step.touch_count} />
                  <SignalChip label="Residual" value={step.residual.toFixed(3)} />
                  <SignalChip label="Level" value={step.level} />
                  <SignalChip
                    label="Evidence"
                    value={step.evidence_sources.length}
                  />
                </div>

                <div className="mt-3 flex flex-wrap gap-1.5">
                  {step.evidence_sources.map((source) => (
                    <Badge key={source} size="sm" variant="outline">
                      {source}
                    </Badge>
                  ))}
                </div>

                <div className="mt-3 grid grid-cols-3 gap-2 text-[10px]">
                  <div className="rounded-lg border border-slate-800/60 bg-slate-950/40 px-2 py-1.5">
                    <p className="text-slate-500 uppercase tracking-widest text-[8px]">
                      Semantic phrases
                    </p>
                    <p className="mt-0.5 text-slate-200">
                      {step.semantic_signature.semantic_phrase_bucket_count}
                    </p>
                  </div>
                  <div className="rounded-lg border border-slate-800/60 bg-slate-950/40 px-2 py-1.5">
                    <p className="text-slate-500 uppercase tracking-widest text-[8px]">
                      Concept buckets
                    </p>
                    <p className="mt-0.5 text-slate-200">
                      {step.semantic_signature.concept_bucket_count}
                    </p>
                  </div>
                  <div className="rounded-lg border border-slate-800/60 bg-slate-950/40 px-2 py-1.5">
                    <p className="text-slate-500 uppercase tracking-widest text-[8px]">
                      Morphology
                    </p>
                    <p className="mt-0.5 text-slate-200">
                      {step.semantic_signature.morphology_bucket_count}
                    </p>
                  </div>
                </div>

                {step.via_edge && (
                  <div className="mt-3 rounded-lg border border-cyan-500/15 bg-cyan-500/5 px-2.5 py-2 text-[10px] text-cyan-100">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-semibold">
                        {step.via_edge.kind}
                      </span>
                      <span className="font-mono text-cyan-200/80">
                        w:{step.via_edge.weight.toFixed(3)}
                      </span>
                    </div>
                    <p className="mt-1 text-cyan-200/80">
                      {step.via_edge.src_node_id.slice(0, 8)} →{" "}
                      {step.via_edge.dst_node_id.slice(0, 8)}
                    </p>
                  </div>
                )}
              </motion.div>
            );
          })
        )}
      </div>
    </div>
  );
}
