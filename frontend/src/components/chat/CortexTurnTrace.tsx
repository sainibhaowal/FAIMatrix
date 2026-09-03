"use client";

import React, { useState, useMemo } from "react";
import {
  ChevronDown,
  ChevronRight,
  Brain,
  Database,
  Search,
  GitBranch,
  Zap,
  FileText,
  Clock,
  CheckCircle,
  AlertCircle,
  ExternalLink,
  ArrowRight,
  Layers,
  Network,
  Filter,
  BarChart2,
  Sparkles,
  Eye,
  EyeOff,
  Copy,
  Check,
  Loader2,
  MessageSquare,
  Terminal,
  Settings,
  Link2,
} from "lucide-react";

interface CortexTurnTraceProps {
  cortexTurn: any;
  queryData: any;
  isStreaming: boolean;
  onClose: () => void;
}

const STEP_CONFIG = [
  {
    id: "planning",
    label: "Planning & Classification",
    icon: Brain,
    color: "text-violet-400",
    bg: "bg-violet-400/10",
    border: "border-violet-400/30",
    description: "Enhanced planner analyzes query, sets hop budget, branching factor, task type",
  },
  {
    id: "retrieval",
    label: "Multi-Modal Retrieval",
    icon: Search,
    color: "text-cyan-400",
    bg: "bg-cyan-400/10",
    border: "border-cyan-400/30",
    description: "Lexical (BM25) + Vector (Qdrant) + Graph Diffusion + Multi-hop traversal",
  },
  {
    id: "reranking",
    label: "Late-Interaction Reranking",
    icon: Filter,
    color: "text-blue-400",
    bg: "bg-blue-400/10",
    border: "border-blue-400/30",
    description: "ColBERT late interaction + Cross-encoder cross-attention reranking",
  },
  {
    id: "branches",
    label: "Parallel Reasoning Branches",
    icon: GitBranch,
    color: "text-emerald-400",
    bg: "bg-emerald-400/10",
    border: "border-emerald-400/30",
    description: "Evidence, Contradiction, Trajectory, Gap-Analysis, Provenance branches run in parallel",
  },
  {
    id: "reduce",
    label: "State Reduction",
    icon: Layers,
    color: "text-amber-400",
    bg: "bg-amber-400/10",
    border: "border-amber-400/30",
    description: "Merge all branch outputs into unified CortexBrainState with confidence calibration",
  },
  {
    id: "synthesis",
    label: "Answer Synthesis",
    icon: Sparkles,
    color: "text-rose-400",
    bg: "bg-rose-400/10",
    border: "border-rose-400/30",
    description: "Grounded answer generation with inline citations, contradiction resolution",
  },
  {
    id: "persistence",
    label: "Durable Persistence",
    icon: Database,
    color: "text-slate-400",
    bg: "bg-slate-400/10",
    border: "border-slate-400/30",
    description: "Store turn in cortex_turns table with full reasoning tree for audit/replay",
  },
  {
    id: "llm_synthesis",
    label: "LLM Streaming Synthesis",
    icon: MessageSquare,
    color: "text-orange-400",
    bg: "bg-orange-400/10",
    border: "border-orange-400/30",
    description: "Final LLM generates natural language response with citations from evidence",
  },
] as const;

type StepId = typeof STEP_CONFIG[number]["id"];

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms.toFixed(0)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

function CopyButton({ text, label }: { text: string; label: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      onClick={handleCopy}
      className="flex items-center gap-1.5 px-2 py-1 text-[10px] font-mono rounded border border-white/10 hover:border-white/20 hover:bg-white/5 transition-colors"
      title={`Copy ${label}`}
    >
      {copied ? <Check size={11} className="text-emerald-400" /> : <Copy size={11} />}
      <span>{copied ? "Copied!" : label}</span>
    </button>
  );
}

function StepCard({
  step,
  data,
  isActive,
  isComplete,
  expanded,
  onToggle,
}: {
  step: typeof STEP_CONFIG[number];
  data: any;
  isActive: boolean;
  isComplete: boolean;
  expanded: boolean;
  onToggle: () => void;
}) {
  const statusIcon = isComplete
    ? <CheckCircle className="w-5 h-5 text-emerald-400" />
    : isActive
      ? <Loader2 className="w-5 h-5 animate-spin" style={{ color: step.color }} />
      : <ChevronRight className="w-5 h-5 text-slate-500" />;

  return (
    <div
      className={`relative rounded-[14px] border transition-all ${
        isActive
          ? `border-2 ${step.border} bg-[${step.bg}] shadow-[0_0_12px_${step.color.replace("text-", "")}33]`
          : expanded
            ? "border-white/10 bg-white/[0.02]"
            : "border-white/6 bg-white/[0.015]"
      }`}
    >
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-3 p-4 text-left"
        aria-expanded={expanded}
      >
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <div
            className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${step.bg} ${step.border}`}
          >
            <step.icon size={16} className={step.color} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h4 className="font-semibold text-white truncate">{step.label}</h4>
              {isActive && (
                <span className="text-[10px] font-mono uppercase tracking-wider text-emerald-300 animate-pulse">
                  Running
                </span>
              )}
              {isComplete && !isActive && (
                <span className="text-[10px] font-mono uppercase tracking-wider text-emerald-400">
                  Complete
                </span>
              )}
            </div>
            <p className="text-[11px] text-slate-400 truncate mt-0.5">{step.description}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {data?.duration_ms && (
            <span className="text-[10px] font-mono text-slate-500 px-2 py-0.5 rounded bg-slate-900/50 border border-white/5">
              <Clock size={10} className="inline mr-0.5" />
              {formatDuration(data.duration_ms)}
            </span>
          )}
          <ChevronDown
            size={16}
            className={`text-slate-500 transition-transform ${expanded ? "rotate-180" : ""}`}
          />
        </div>
      </button>

      {expanded && (
        <div className="border-t border-white/6 p-4 bg-black/20 animate-in fade-in-10 duration-150">
          <div className="space-y-3">
            {renderStepContent(step.id, data)}
          </div>
        </div>
      )}
    </div>
  );
}

function renderStepContent(stepId: StepId, data: any) {
  const bt = data?.brain_state;
  const rt = data?.reasoning_tree;
  const ap = data?.answer_packet;
  const qr = data?.query_result;
  const planned = data?.planned;

  switch (stepId) {
    case "planning":
      return (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <MetricCard label="Task Type" value={planned?.task_type ?? bt?.task_type ?? "direct"} />
            <MetricCard label="Max Hops" value={planned?.max_hops ?? "auto"} />
            <MetricCard label="Branching Factor" value={planned?.branching_factor ?? "auto"} />
            <MetricCard label="Answer Mode" value={planned?.answer_mode ?? "direct"} />
            <MetricCard label="Confidence Threshold" value={planned?.min_confidence ?? 0.1} />
            <MetricCard label="Multi-Hop Enabled" value={planned?.enable_multi_hop ? "Yes" : "No"} />
          </div>
          {planned?.traversal_goal && (
            <DetailBlock label="Traversal Goal" value={planned.traversal_goal} />
          )}
          {planned?.constraints && (
            <DetailBlock label="Constraints" value={JSON.stringify(planned.constraints, null, 2)} code />
          )}
          {planned?.reasoning && (
            <DetailBlock label="Planner Reasoning" value={planned.reasoning} />
          )}
        </div>
      );

    case "retrieval":
      return (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <MetricCard label="Candidates Found" value={qr?.results?.length ?? 0} />
            <MetricCard label="Query Hash" value={qr?.query_hash?.slice(0, 16) ?? "—"} />
            <MetricCard label="Graph Version" value={qr?.graph_version ?? "—"} />
            <MetricCard label="Graph Hash" value={qr?.graph_hash?.slice(0, 16) ?? "—"} />
          </div>
          <DetailBlock
            label="Top Results"
            value={
              qr?.results?.slice(0, 5).map((r: any, i: number) => (
                <div key={i} className="text-[10px] font-mono text-slate-300 mb-1">
                  {i + 1}. {r.node_id?.slice(0, 12)} — score: {r.score?.toFixed(4)} — layers:{Array.from(new Set(r.explain?.fusion_summary?.active_layers ?? [])).join(",")}
                </div>
              ))
            }
          />
          {qr?.explain?.query_fusion_summary && (
            <DetailBlock
              label="Query Fusion Summary"
              value={JSON.stringify(qr.explain.query_fusion_summary, null, 2)}
              code
            />
          )}
        </div>
      );

    case "reranking":
      return (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <MetricCard label="Reranker Active" value={bt?.reranker_active ? "Yes" : "No"} />
            <MetricCard label="Late Interaction" value={bt?.late_interaction_used ? "Yes" : "No"} />
            <MetricCard label="Cross-Encoder" value={bt?.cross_encoder_used ? "Yes" : "No"} />
            <MetricCard label="Results After Rerank" value={bt?.reranked_count ?? "—"} />
          </div>
          {bt?.reranker_scores && (
            <DetailBlock
              label="Reranker Scores (top 5)"
              value={
                Object.entries(bt.reranker_scores)
                  .slice(0, 5)
                  .map(([k, v]) => `${k}: ${(v as number).toFixed(4)}`)
                  .join("\n")
              }
              code
            />
          )}
        </div>
      );

    case "branches":
      return (
        <div className="space-y-3">
          {rt?.map((branch: any, i: number) => (
            <div key={i} className="rounded-xl border border-white/8 bg-white/[0.02] p-3">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-[10px] font-mono uppercase tracking-wider text-cyan-300">
                  {branch.branch?.toUpperCase()}
                </span>
                <span className="text-[10px] font-mono text-slate-500">
                  confidence: {branch.confidence?.toFixed(3) ?? "—"}
                </span>
                <span className="text-[10px] font-mono text-slate-500 ml-auto">
                  {branch.evidence_node_ids?.length ?? 0} evidence nodes
                </span>
              </div>
              <div className="text-[11px] text-slate-300">
                {branch.output?.summary ?? branch.reasoning ?? "—"}
              </div>
              {branch.evidence_node_ids?.length && (
                <DetailBlock
                  label="Evidence Nodes"
                  value={branch.evidence_node_ids.join(", ")}
                  code
                />
              )}
            </div>
          ))}
          {(!rt || rt.length === 0) && (
            <p className="text-slate-500 text-center py-4">No reasoning branches executed</p>
          )}
        </div>
      );

    case "reduce":
      return (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <MetricCard label="Final Task Type" value={bt?.task_type ?? "—"} />
            <MetricCard label="Evidence Nodes" value={bt?.evidence_nodes?.length ?? 0} />
            <MetricCard label="Total Reasoning Nodes" value={rt?.length ?? 0} />
            <MetricCard label="Answer Confidence" value={ap?.confidence?.toFixed(3) ?? "—"} />
          </div>
          {bt?.answer_packet && (
            <DetailBlock
              label="Answer Packet"
              value={JSON.stringify(bt.answer_packet, null, 2)}
              code
            />
          )}
          {bt?.contradiction_notes?.length && (
            <DetailBlock
              label="Contradiction Notes"
              value={bt.contradiction_notes.join("\n\n")}
              code
            />
          )}
        </div>
      );

    case "synthesis":
      return (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <MetricCard label="Direct Answer Length" value={ap?.direct_answer?.length ?? 0} />
            <MetricCard label="Supporting Spans" value={ap?.supporting_spans?.length ?? 0} />
            <MetricCard label="Contradiction Notes" value={ap?.contradiction_notes?.length ?? 0} />
            <MetricCard label="Results Referenced" value={qr?.results?.length ?? 0} />
          </div>
          {ap?.direct_answer && (
            <DetailBlock label="Direct Answer" value={ap.direct_answer} />
          )}
          {ap?.supporting_spans?.length && (
            <DetailBlock
              label="Supporting Spans"
              value={
                ap.supporting_spans.map((s: any, i: number) => (
                  <div key={i} className="text-[10px] font-mono text-slate-300 mb-1">
                    {i + 1}. [{s.node_id?.slice(0, 12)}] "{s.text?.slice(0, 80)}..." (score: {s.score?.toFixed(3)})
                  </div>
                ))
              }
            />
          )}
        </div>
      );

    case "persistence":
      return (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <MetricCard label="Turn ID" value={data?.turn_id?.slice(0, 16) ?? "—"} />
            <MetricCard label="Session ID" value={data?.session_id?.slice(0, 16) ?? "—"} />
            <MetricCard label="Graph Version" value={data?.graph_version ?? "—"} />
            <MetricCard label="Duration" value={formatDuration(data?.duration_ms)} />
          </div>
          <DetailBlock
            label="Stored Fields"
            value={
              [
                "turn_id, tenant_id, graph_id, session_id",
                "query_hash, task_type, answer_mode",
                "answer (direct_answer, spans, confidence)",
                "brain_state (reasoning_tree, evidence_nodes)",
                "narrative, duration_ms",
              ].join("\n")
            }
            code
          />
        </div>
      );

    case "llm_synthesis":
      return (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <MetricCard label="Provider" value={data?.provider ?? "—"} />
            <MetricCard label="Model" value={data?.model ?? "—"} />
            <MetricCard label="Tokens (est.)" value={data?.tokens_estimate ?? "—"} />
            <MetricCard label="Streaming" value={data?.isStreaming ? "Active" : "Complete"} />
          </div>
          <DetailBlock
            label="System Prompt Preview"
            value={
              data?.systemPrompt?.slice(0, 500) + (data?.systemPrompt?.length > 500 ? "..." : "")
            }
            code
          />
        </div>
      );

    default:
      return <p className="text-slate-500">No details available</p>;
  }
}

function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-white/8 bg-white/[0.02] p-3">
      <p className="text-[9px] font-mono uppercase tracking-wider text-slate-500 mb-1">{label}</p>
      <p className="font-mono text-white text-sm">{value}</p>
    </div>
  );
}

function DetailBlock({ label, value, code = false }: { label: string; value: any; code?: boolean }) {
  const renderValue = () => {
    if (code) {
      return <pre className="whitespace-pre-wrap">{value}</pre>;
    }
    if (Array.isArray(value)) {
      return value.map((v, i) => <div key={i}>{v}</div>);
    }
    return <span>{value}</span>;
  };

  return (
    <div className="rounded-xl border border-white/6 bg-white/[0.015] p-3">
      <p className="text-[9px] font-mono uppercase tracking-wider text-slate-500 mb-2">{label}</p>
      <div className="text-[10px] font-mono text-slate-300 max-h-48 overflow-y-auto">
        {renderValue()}
      </div>
    </div>
  );
}

export function CortexTurnTrace({
  cortexTurn,
  queryData,
  isStreaming,
  onClose,
}: CortexTurnTraceProps) {
  const [expandedSteps, setExpandedSteps] = useState<Set<StepId>>(new Set<StepId>(["planning", "retrieval"]));

  const stepData = useMemo(() => {
    const bt = cortexTurn?.brain_state;
    const rt = cortexTurn?.reasoning_tree;
    const ap = cortexTurn?.answer_packet ?? queryData?.answer;
    const qr = cortexTurn?.query_result;
    const planned = cortexTurn?.planned;

    return {
      planning: {
        duration_ms: cortexTurn?.planning_duration_ms,
        planned,
        bt,
      },
      retrieval: {
        duration_ms: cortexTurn?.retrieval_duration_ms,
        query_result: qr,
        bt,
      },
      reranking: {
        duration_ms: cortexTurn?.rerank_duration_ms,
        bt,
      },
      branches: {
        duration_ms: cortexTurn?.branches_duration_ms,
        reasoning_tree: rt,
        bt,
      },
      reduce: {
        duration_ms: cortexTurn?.reduce_duration_ms,
        brain_state: bt,
        answer_packet: ap,
        reasoning_tree: rt,
      },
      synthesis: {
        duration_ms: cortexTurn?.synthesis_duration_ms,
        answer_packet: ap,
        query_result: qr,
      },
      persistence: {
        persist_duration_ms: cortexTurn?.persist_duration_ms,
        turn_id: cortexTurn?.turn_id,
        session_id: cortexTurn?.session_id,
        graph_version: cortexTurn?.graph_version,
        total_duration_ms: cortexTurn?.duration_ms,
      },
      llm_synthesis: {
        duration_ms: cortexTurn?.llm_duration_ms,
        provider: cortexTurn?.provider,
        model: cortexTurn?.model,
        tokens_estimate: cortexTurn?.tokens_estimate,
        isStreaming,
        systemPrompt: cortexTurn?.system_prompt,
      },
    };
  }, [cortexTurn, queryData, isStreaming]);

  const toggleStep = (id: StepId) => {
    setExpandedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const expandAll = () => setExpandedSteps(new Set<StepId>(STEP_CONFIG.map((s) => s.id)));
  const collapseAll = () => setExpandedSteps(new Set<StepId>());

  return (
    <div className="fixed inset-0 z-[100] flex flex-col bg-[#04060c]/97 backdrop-blur-xl text-slate-100">
      <div className="flex items-center justify-between gap-4 border-b border-white/8 bg-black/40 px-5 py-3">
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border bg-white/[0.04] text-cyan-400" style={{ borderColor: "#22d3ee4D" }}>
            <Terminal size={18} />
          </span>
          <div className="min-w-0">
            <p className="text-sm font-semibold tracking-tight text-white">Cortex Turn Execution Trace</p>
            <p className="truncate font-mono text-[10px] uppercase tracking-widest text-slate-500">
              Turn {cortexTurn?.turn_id?.slice(0, 8)} · {formatDuration(cortexTurn?.duration_ms)} · {cortexTurn?.task_type ?? "direct"}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={expandAll}
            className="px-2 py-1 text-[10px] font-mono rounded border border-white/10 hover:bg-white/5 transition-colors"
          >
            Expand All
          </button>
          <button
            onClick={collapseAll}
            className="px-2 py-1 text-[10px] font-mono rounded border border-white/10 hover:bg-white/5 transition-colors"
          >
            Collapse All
          </button>
          <button
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 text-slate-300 transition-colors hover:bg-white/5 hover:text-white"
            aria-label="Close trace"
          >
            <ExternalLink size={15} />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar p-4">
        <div className="mx-auto max-w-5xl space-y-3">
          {STEP_CONFIG.map((step) => {
            const data = stepData[step.id as keyof typeof stepData];
            const stepDuration = step.id === "persistence"
              ? ((data as any)?.persist_duration_ms ?? (data as any)?.total_duration_ms ?? 0)
              : ((data as any)?.duration_ms ?? 0);
            const isComplete = data && stepDuration > 0;
            const isActive = isStreaming && step.id === "llm_synthesis";
            const expanded = expandedSteps.has(step.id);

            return (
              <StepCard
                key={step.id}
                step={step}
                data={data}
                isActive={isActive}
                isComplete={isComplete}
                expanded={expanded}
                onToggle={() => toggleStep(step.id)}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
}