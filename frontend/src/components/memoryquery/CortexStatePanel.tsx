"use client";

import React, { useMemo } from "react";
import {
  ArrowRight,
  GitBranch,
  Layers,
  Orbit,
  Sparkles,
} from "lucide-react";
import type { FaimCortexTurnResponse } from "@/contexts/ChatContext";

function Pill({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: "neutral" | "primary" | "amber";
}) {
  const classes =
    tone === "primary"
      ? "border-primary-500/20 bg-primary-500/10 text-primary-200"
      : tone === "amber"
        ? "border-amber-500/20 bg-amber-500/10 text-amber-200"
        : "border-white/10 bg-white/[0.03] text-slate-300";
  return (
    <span
      className={[
        "inline-flex items-center rounded-full border px-2.5 py-1 text-[8px] font-black uppercase tracking-[0.24em]",
        classes,
      ].join(" ")}
    >
      {children}
    </span>
  );
}

export function CortexStatePanel({
  cortexData,
}: {
  cortexData: FaimCortexTurnResponse;
}) {
  const brain = cortexData.brain_state;

  const topBranches = useMemo(
    () => brain.reasoning_tree.slice(0, 4),
    [brain.reasoning_tree],
  );
  const retrievalSummary = useMemo(
    () => (brain.retrieval_summary ?? {}) as Record<string, unknown>,
    [brain.retrieval_summary],
  );
  const topResult = useMemo(
    () =>
      (retrievalSummary.top_result ?? {}) as {
        active_layers?: string[];
        strongest_layers?: Array<{ layer?: string; contribution?: number }>;
      },
    [retrievalSummary],
  );
  const candidatePool = useMemo(
    () =>
      (retrievalSummary.candidate_pool ?? {}) as {
        total?: number;
        lexical_scored?: number;
        domain_candidates?: number;
        graph_candidates?: number;
      },
    [retrievalSummary],
  );
  const recentTurns = useMemo(
    () => brain.recent_turns.slice(-4),
    [brain.recent_turns],
  );

  return (
    <section className="rounded-[24px] border border-white/8 bg-black/20 px-5 py-5 shadow-[0_18px_60px_rgba(0,0,0,0.22)]">
      <div className="flex flex-wrap items-center gap-2 text-[9px] font-black uppercase tracking-[0.28em]">
        <span className="text-primary-300">Cortex State</span>
        <Pill tone="primary">{brain.task_type}</Pill>
        <Pill>{Math.round((brain.confidence ?? 0) * 100)}% confidence</Pill>
        <Pill>{brain.next_actions.length} next actions</Pill>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div className="rounded-2xl border border-white/8 bg-white/[0.02] p-3">
          <div className="flex items-center gap-2 text-[9px] font-black uppercase tracking-[0.24em] text-slate-500">
            <Sparkles size={11} className="text-primary-300" />
            Goal
          </div>
          <p className="mt-2 text-[12px] leading-6 text-slate-200">
            {brain.goal || "Answer the user from grounded FAIM memory."}
          </p>
        </div>

        <div className="rounded-2xl border border-white/8 bg-white/[0.02] p-3">
          <div className="flex items-center gap-2 text-[9px] font-black uppercase tracking-[0.24em] text-slate-500">
            <GitBranch size={11} className="text-primary-300" />
            Next Actions
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            {brain.next_actions.length > 0 ? (
              brain.next_actions.map((action) => (
                <Pill key={action} tone="primary">
                  {action.replace(/_/g, " ")}
                </Pill>
              ))
            ) : (
              <span className="text-[12px] text-slate-500">None</span>
            )}
          </div>
        </div>
      </div>

      {!!topResult.active_layers?.length && (
        <div className="mt-3 rounded-2xl border border-cyan-500/15 bg-cyan-500/[0.04] p-3">
          <div className="flex items-center gap-2 text-[9px] font-black uppercase tracking-[0.24em] text-cyan-300">
            <Orbit size={11} />
            Retrieval Fusion
          </div>
          <p className="mt-2 text-[12px] leading-6 text-slate-200">
            FAIM combined these active retrieval layers on the winning result.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {topResult.active_layers?.map((layer) => (
              <Pill key={layer} tone="primary">
                {String(layer).replace(/_/g, " ")}
              </Pill>
            ))}
          </div>
          <div className="mt-3 grid gap-2 md:grid-cols-2">
            <div className="rounded-xl border border-white/[0.05] bg-black/20 p-3">
              <div className="text-[8px] font-black uppercase tracking-[0.22em] text-slate-500">
                Candidate Pool
              </div>
              <p className="mt-2 text-[12px] text-slate-200">
                {candidatePool.total ?? 0} total · {candidatePool.lexical_scored ?? 0} lexical ·{" "}
                {candidatePool.graph_candidates ?? 0} graph · {candidatePool.domain_candidates ?? 0} domain
              </p>
            </div>
            <div className="rounded-xl border border-white/[0.05] bg-black/20 p-3">
              <div className="text-[8px] font-black uppercase tracking-[0.22em] text-slate-500">
                Strongest Layers
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                {(topResult.strongest_layers ?? []).slice(0, 4).map((layer, index) => (
                  <Pill key={`${layer.layer ?? "layer"}-${index}`}>
                    {String(layer.layer ?? "layer").replace(/_/g, " ")}{" "}
                    {typeof layer.contribution === "number"
                      ? layer.contribution.toFixed(3)
                      : ""}
                  </Pill>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="mt-3 rounded-2xl border border-white/8 bg-white/[0.02] p-3">
        <div className="flex items-center justify-between gap-2 text-[9px] font-black uppercase tracking-[0.24em] text-slate-500">
          <span>Session Continuity</span>
          <span className="text-primary-300">
            {brain.session_turn_count} turns
          </span>
        </div>
        <p className="mt-2 text-[12px] leading-6 text-slate-200">
          {brain.session_summary || "Single-turn session memory so far."}
        </p>
        {recentTurns.length > 0 ? (
          <div className="mt-3 space-y-2">
            {recentTurns.map((turn) => (
              <div
                key={turn.turn_id}
                className="rounded-xl border border-white/[0.05] bg-black/20 px-3 py-2"
              >
                <div className="flex flex-wrap items-center gap-2 text-[8px] font-black uppercase tracking-[0.22em]">
                  <Pill tone="primary">{turn.task_type}</Pill>
                  <Pill>{turn.answer_mode}</Pill>
                  <span className="text-slate-600">
                    {Math.round((turn.confidence ?? 0) * 100)}%
                  </span>
                </div>
                <p className="mt-1.5 text-[12px] leading-6 text-slate-200">
                  {turn.query_text}
                </p>
                {turn.narrative ? (
                  <p className="mt-1 text-[11px] leading-5 text-slate-500 line-clamp-2">
                    {turn.narrative}
                  </p>
                ) : null}
                {(turn.open_question_count > 0 ||
                  turn.contradiction_count > 0) && (
                  <p className="mt-1 text-[10px] uppercase tracking-[0.2em] text-amber-300">
                    {turn.open_question_count > 0
                      ? `${turn.open_question_count} open question${turn.open_question_count === 1 ? "" : "s"}`
                      : ""}
                    {turn.open_question_count > 0 &&
                    turn.contradiction_count > 0
                      ? " · "
                      : ""}
                    {turn.contradiction_count > 0
                      ? `${turn.contradiction_count} conflict${turn.contradiction_count === 1 ? "" : "s"}`
                      : ""}
                  </p>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="mt-2 text-[11px] text-slate-500">
            No prior turns were found in this session yet.
          </p>
        )}
      </div>

      {brain.open_questions.length > 0 && (
        <div className="mt-3 rounded-2xl border border-amber-500/15 bg-amber-500/[0.05] p-3">
          <div className="text-[9px] font-black uppercase tracking-[0.24em] text-amber-300">
            Open Questions
          </div>
          <ul className="mt-2 space-y-1 text-[12px] leading-6 text-amber-50/80">
            {brain.open_questions.map((question) => (
              <li key={question} className="flex gap-2">
                <ArrowRight
                  size={11}
                  className="mt-1 text-amber-300 shrink-0"
                />
                <span>{question}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {brain.predictions.length > 0 && (
        <div className="mt-3 rounded-2xl border border-white/8 bg-white/[0.02] p-3">
          <div className="text-[9px] font-black uppercase tracking-[0.24em] text-slate-500">
            Predictions
          </div>
          <div className="mt-2 space-y-2">
            {brain.predictions.map((prediction) => (
              <p
                key={prediction}
                className="text-[12px] leading-6 text-slate-200"
              >
                {prediction}
              </p>
            ))}
          </div>
        </div>
      )}

      {topBranches.length > 0 && (
        <div className="mt-4 space-y-2">
          <div className="text-[9px] font-black uppercase tracking-[0.24em] text-slate-500">
            Reasoning Tree
          </div>
          {topBranches.map((node) => (
            <div
              key={node.node_id}
              className="rounded-2xl border border-white/8 bg-white/[0.02] p-3"
            >
              <div className="flex flex-wrap items-center gap-2 text-[8px] font-black uppercase tracking-[0.24em]">
                <Pill tone="primary">{node.branch}</Pill>
                <Pill>{Math.round((node.confidence ?? 0) * 100)}%</Pill>
                <span className="text-slate-600">{node.title}</span>
              </div>
              <p className="mt-2 text-[12px] leading-6 text-slate-200">
                {node.summary}
              </p>
              {node.evidence_node_ids.length > 0 && (
                <p className="mt-2 text-[10px] uppercase tracking-[0.22em] text-slate-500">
                  Evidence: {node.evidence_node_ids.slice(0, 4).join(", ")}
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {brain.writeback_candidates.length > 0 && (
        <div className="mt-4 rounded-2xl border border-primary-500/15 bg-primary-500/[0.05] p-3">
          <div className="flex items-center justify-between">
            <div className="text-[9px] font-black uppercase tracking-[0.24em] text-primary-300">
              Writeback Candidates
            </div>
            <div className="flex flex-wrap items-center gap-1 text-[8px] uppercase tracking-[0.2em] text-slate-500">
              <Pill tone="primary">
                {
                  brain.writeback_candidates.filter(
                    (c: { status?: string }) => c.status === "auto_approved",
                  ).length
                }{" "}
                approved
              </Pill>
              <Pill>
                {
                  brain.writeback_candidates.filter(
                    (c: { execution_status?: string }) =>
                      c.execution_status === "executed" ||
                      c.execution_status === "replayed",
                  ).length
                }{" "}
                executed
              </Pill>
            </div>
          </div>
          <div className="mt-2 space-y-2">
            {brain.writeback_candidates.map(
              (
                item: {
                  kind?: string;
                  text?: string;
                  reason?: string;
                  status?: string;
                  execution_status?: string;
                  execution_key?: string | null;
                  execution_request_hash?: string | null;
                  execution_receipt?: Record<string, unknown> | null;
                  execution_receipt_json?: Record<string, unknown> | null;
                  execution_error?: string | null;
                  executed_at?: string | null;
                  confidence?: number;
                },
                index: number,
              ) => (
                <div
                  key={`${String(item.kind ?? "candidate")}-${index}`}
                  className="flex items-start gap-2"
                >
                  <div
                    className={`mt-0.5 w-2 h-2 rounded-full shrink-0 ${item.status === "auto_approved" ? "bg-emerald-400" : "bg-amber-400"}`}
                  />
                  <div className="flex-1">
                    <p className="text-[12px] leading-6 text-slate-200">
                      {String(item.text ?? item.reason ?? "proposed update")}
                    </p>
                    <div className="mt-1 flex flex-wrap items-center gap-2">
                      <Pill tone={item.status === "auto_approved" ? "primary" : "amber"}>
                        {String(item.status ?? "proposed").replace(/_/g, " ")}
                      </Pill>
                      <Pill tone={
                        item.execution_status === "executed" ||
                        item.execution_status === "replayed"
                          ? "primary"
                          : item.execution_status === "failed"
                            ? "amber"
                            : "neutral"
                      }>
                        {String(item.execution_status ?? "skipped").replace(/_/g, " ")}
                      </Pill>
                      <span className="text-[8px] uppercase tracking-[0.2em] text-slate-500">
                        {Math.round((item.confidence ?? 0) * 100)}% confidence
                      </span>
                    </div>
                    {(item.execution_key ||
                      item.executed_at ||
                      item.execution_error ||
                      item.execution_request_hash) && (
                      <div className="mt-2 grid gap-2 md:grid-cols-2">
                        {item.execution_key ? (
                          <div className="rounded-xl border border-white/[0.05] bg-black/20 px-2.5 py-2">
                            <div className="text-[8px] font-black uppercase tracking-[0.2em] text-slate-500">
                              Execution Key
                            </div>
                            <p className="mt-1 break-all text-[10px] leading-5 text-slate-200">
                              {item.execution_key}
                            </p>
                          </div>
                        ) : null}
                        {item.executed_at ? (
                          <div className="rounded-xl border border-white/[0.05] bg-black/20 px-2.5 py-2">
                            <div className="text-[8px] font-black uppercase tracking-[0.2em] text-slate-500">
                              Executed At
                            </div>
                            <p className="mt-1 text-[10px] leading-5 text-slate-200">
                              {item.executed_at}
                            </p>
                          </div>
                        ) : null}
                        {item.execution_request_hash ? (
                          <div className="rounded-xl border border-white/[0.05] bg-black/20 px-2.5 py-2 md:col-span-2">
                            <div className="text-[8px] font-black uppercase tracking-[0.2em] text-slate-500">
                              Request Hash
                            </div>
                            <p className="mt-1 break-all text-[10px] leading-5 text-slate-200">
                              {item.execution_request_hash}
                            </p>
                          </div>
                        ) : null}
                        {item.execution_error ? (
                          <div className="rounded-xl border border-amber-500/15 bg-amber-500/[0.05] px-2.5 py-2 md:col-span-2">
                            <div className="text-[8px] font-black uppercase tracking-[0.2em] text-amber-300">
                              Execution Error
                            </div>
                            <p className="mt-1 text-[10px] leading-5 text-amber-50/85">
                              {item.execution_error}
                            </p>
                          </div>
                        ) : null}
                        {(item.execution_receipt_json || item.execution_receipt) ? (
                          <div className="rounded-xl border border-white/[0.05] bg-black/20 px-2.5 py-2 md:col-span-2">
                            <div className="text-[8px] font-black uppercase tracking-[0.2em] text-slate-500">
                              Receipt
                            </div>
                            <pre className="mt-1 overflow-x-auto whitespace-pre-wrap break-words text-[10px] leading-5 text-slate-300">
                              {JSON.stringify(
                                item.execution_receipt_json ?? item.execution_receipt,
                                null,
                                2,
                              )}
                            </pre>
                          </div>
                        ) : null}
                      </div>
                    )}
                  </div>
                </div>
              ),
            )}
          </div>
        </div>
      )}
    </section>
  );
}
