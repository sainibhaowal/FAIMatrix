"use client";

import React, { useState } from "react";
import {
  BrainCircuit,
  ChevronDown,
  ChevronUp,
  Cpu,
  Database,
  GitBranch,
  Layers,
  ShieldCheck,
  Sparkles,
  Zap,
  Activity,
  CheckCircle2,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { ChatInterface } from "@/components/memoryquery/ChatInterface";
import { ChatComposer } from "@/components/memoryquery/ChatComposer";
import { HistoryPanel } from "@/components/memoryquery/HistoryPanel";

export default function MemoryQueryPage() {
  const [manualOpen, setManualOpen] = useState(true);

  return (
    <div className="flex h-full text-slate-100 overflow-hidden bg-transparent">
      {/*
          Main Command Space
          - Top: FAIM Cortex User Manual (collapsible)
          - Center: Dynamic Message Stream
          - Right: Intelligence History Pane
      */}
      <div className="flex-1 flex flex-col min-w-0 h-full relative overflow-y-auto custom-scrollbar">
        {/* ── Top FAIM Cortex User Manual Banner ────────────────── */}
        <div className="p-4 pb-0 shrink-0">
          <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)] transition-all">
            {/* Top horizontal gradient accent bar */}
            <div className="absolute top-0 left-6 right-6 h-[2px] bg-gradient-to-r from-cyan-500/80 via-purple-400/50 to-transparent rounded-full" />

            {/* Manual Header & Toggle */}
            <button
              onClick={() => setManualOpen((prev) => !prev)}
              className="w-full flex items-center justify-between px-6 py-4 text-left transition-colors hover:bg-white/[0.02]"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-cyan-500/30 bg-cyan-500/10 text-cyan-300">
                  <BrainCircuit size={20} />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-sm font-bold text-white tracking-wide">
                      FAIM Cortex — Operating Manual & Architecture
                    </h2>
                    <span className="inline-flex items-center gap-1 rounded-full border border-cyan-400/25 bg-cyan-500/10 px-2 py-0.5 text-[10px] font-semibold text-cyan-300">
                      <Zap size={10} /> Active Engine
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Deterministic memory synthesis engine with bounded multi-hop graph reasoning & zero-hallucination provenance
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 text-xs text-cyan-400 font-medium">
                <span>{manualOpen ? "Hide Manual" : "Open Manual"}</span>
                {manualOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              </div>
            </button>

            {/* Collapsible Manual Body */}
            <AnimatePresence>
              {manualOpen && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.3 }}
                  className="overflow-hidden border-t border-white/6 px-6 py-5 space-y-6"
                >
                  {/* Overview Cards */}
                  <div className="grid gap-4 md:grid-cols-3">
                    <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                      <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-cyan-400/80 via-cyan-400/30 to-transparent" />
                      <div className="flex items-center gap-2 text-cyan-300 mb-1.5">
                        <Cpu size={15} />
                        <span className="text-xs font-bold uppercase tracking-wider">What is Cortex?</span>
                      </div>
                      <p className="text-[12px] text-slate-300 leading-relaxed">
                        The cognitive memory synthesis engine of FAIM Matrix. Unlike standard chunk-RAG, Cortex performs planner-driven multi-hop graph reasoning directly over your live knowledge graph.
                      </p>
                    </div>

                    <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                      <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-purple-400/80 via-purple-400/30 to-transparent" />
                      <div className="flex items-center gap-2 text-purple-300 mb-1.5">
                        <GitBranch size={15} />
                        <span className="text-xs font-bold uppercase tracking-wider">Adaptive Hops</span>
                      </div>
                      <p className="text-[12px] text-slate-300 leading-relaxed">
                        Dynamically allocates 1–3 hops for simple lookups, expands to 1–24 adaptive hops by default for investigative turns, and scales up to 128 bounded hops for deep reasoning.
                      </p>
                    </div>

                    <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                      <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-emerald-400/80 via-emerald-400/30 to-transparent" />
                      <div className="flex items-center gap-2 text-emerald-300 mb-1.5">
                        <ShieldCheck size={15} />
                        <span className="text-xs font-bold uppercase tracking-wider">Zero Hallucination</span>
                      </div>
                      <p className="text-[12px] text-slate-300 leading-relaxed">
                        Every answer statement is cryptographically anchored to evidence node IDs & SHA-256 hashes with transparent receipts visualised in the 3D FIG View.
                      </p>
                    </div>
                  </div>

                  {/* 6-Stage Execution Pipeline */}
                  <div>
                    <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-3 flex items-center gap-2">
                      <Layers size={14} className="text-cyan-400" />
                      6-Stage Cognitive Execution Pipeline
                    </h3>

                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                      {[
                        {
                          step: "01",
                          title: "Intent & Hop Budgeting",
                          desc: "Deterministic alias router maps queries to cognitive tasks (direct, timeline, contradiction, provenance) without LLM classifier latency.",
                          color: "from-cyan-400/80 via-cyan-400/30",
                        },
                        {
                          step: "02",
                          title: "Multi-Signal Expansion",
                          desc: "Blends 2.31M+ semantic terms, ConceptNet, domain memory, vector search, late interaction, and graph diffusion.",
                          color: "from-sky-400/80 via-sky-400/30",
                        },
                        {
                          step: "03",
                          title: "Parallel Branching",
                          desc: "Runs dedicated reasoning branches: Temporal (timeline), Contradiction (conflict detection), and Multi-hop evidence walks.",
                          color: "from-purple-400/80 via-purple-400/30",
                        },
                        {
                          step: "04",
                          title: "State & Tree Reduction",
                          desc: "Aggregates evidence nodes & reasoning edges into a unified CortexBrainState and confidence-weighted reasoning tree.",
                          color: "from-indigo-400/80 via-indigo-400/30",
                        },
                        {
                          step: "05",
                          title: "Grounded Synthesis",
                          desc: "Generates cited answers anchored strictly to retrieved graph provenance and evidence hashes with zero hallucination.",
                          color: "from-emerald-400/80 via-emerald-400/30",
                        },
                        {
                          step: "06",
                          title: "FIG View Persistence",
                          desc: "Persists structured turn state and triggers node glow receipts in the interactive 3D Fast Interactive Graph (FIG) View.",
                          color: "from-amber-400/80 via-amber-400/30",
                        },
                      ].map((s) => (
                        <div
                          key={s.step}
                          className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-3.5"
                        >
                          <div className={`absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b ${s.color} to-transparent`} />
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-[10px] font-mono font-bold text-cyan-300 uppercase">
                              Stage {s.step}
                            </span>
                          </div>
                          <p className="text-xs font-bold text-slate-100">{s.title}</p>
                          <p className="mt-1 text-[11px] text-slate-400 leading-relaxed">{s.desc}</p>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Feature Comparison Table */}
                  <div>
                    <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-3 flex items-center gap-2">
                      <Activity size={14} className="text-purple-400" />
                      Capabilities Comparison
                    </h3>
                    <div className="overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.02]">
                      <table className="w-full text-left text-xs">
                        <thead>
                          <tr className="border-b border-white/6 bg-white/[0.03] text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                            <th className="py-2.5 px-4">Feature</th>
                            <th className="py-2.5 px-4 text-cyan-300">FAIM Cortex</th>
                            <th className="py-2.5 px-4 text-slate-500">Traditional RAG</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-white/6 text-slate-300">
                          <tr>
                            <td className="py-2.5 px-4 font-semibold text-slate-200">Reasoning Model</td>
                            <td className="py-2.5 px-4 text-cyan-200">Bounded multi-hop graph traversal (1–24 hops default, up to 128)</td>
                            <td className="py-2.5 px-4 text-slate-500">Single-pass top-k vector chunk retrieval</td>
                          </tr>
                          <tr>
                            <td className="py-2.5 px-4 font-semibold text-slate-200">Hallucination Protection</td>
                            <td className="py-2.5 px-4 text-emerald-400 font-semibold flex items-center gap-1.5">
                              <CheckCircle2 size={13} /> 100% grounded in evidence node hashes
                            </td>
                            <td className="py-2.5 px-4 text-amber-400/80">High risk of LLM hallucination</td>
                          </tr>
                          <tr>
                            <td className="py-2.5 px-4 font-semibold text-slate-200">Contradiction Scanning</td>
                            <td className="py-2.5 px-4 text-cyan-200">Automatic invariant & conflict branch scanning</td>
                            <td className="py-2.5 px-4 text-slate-500">Not supported</td>
                          </tr>
                          <tr>
                            <td className="py-2.5 px-4 font-semibold text-slate-200">3D Visual Receipts</td>
                            <td className="py-2.5 px-4 text-cyan-200">Full 3D FIG View graph node glow & path receipts</td>
                            <td className="py-2.5 px-4 text-slate-500">Black box text output</td>
                          </tr>
                          <tr>
                            <td className="py-2.5 px-4 font-semibold text-slate-200">Memory Autonomy</td>
                            <td className="py-2.5 px-4 text-cyan-200">Self-Evolve & Self-Invent background worker integration</td>
                            <td className="py-2.5 px-4 text-slate-500">Static index without auto-invention</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Workspace: Message Stream + Composer */}
        <div className="flex-1 flex flex-col min-h-0 relative">
          <ChatInterface />

          <div className="absolute bottom-0 left-0 right-0 z-30 invisible pointer-events-none">
            <div className="visible pointer-events-auto w-full">
              <ChatComposer />
            </div>
          </div>
        </div>
      </div>

      {/* Intelligence Sidebar - Floating Right Anchor */}
      <div className="hidden xl:block shrink-0 h-full w-[360px] pt-2.5 pl-2.5 pr-2.5 pb-0">
        <div
          className="h-full rounded-t-[28px] overflow-hidden border-t border-l border-r shadow-2xl"
          style={{
            borderColor: "rgba(255,255,255,0.08)",
            background: "linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))",
          }}
        >
          <HistoryPanel />
        </div>
      </div>
    </div>
  );
}
