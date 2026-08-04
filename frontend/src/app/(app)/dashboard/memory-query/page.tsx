"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  BrainCircuit,
  Cpu,
  GitBranch,
  Layers,
  ShieldCheck,
  Zap,
  Activity,
  CheckCircle2,
  BookOpen,
  Compass,
  FileText,
  Clock,
  AlertTriangle,
  Network,
  Share2,
  Lock,
  X,
  ArrowRight,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { ChatInterface } from "@/components/memoryquery/ChatInterface";
import { ChatComposer } from "@/components/memoryquery/ChatComposer";
import { HistoryPanel } from "@/components/memoryquery/HistoryPanel";

type ManualSection =
  | "overview"
  | "pipeline"
  | "modes"
  | "hops"
  | "provenance"
  | "comparison";

export default function MemoryQueryPage() {
  // Modal overlay defaults to open when visiting FAIM Cortex
  const [isManualModalOpen, setIsManualModalOpen] = useState(true);
  const [activeSection, setActiveSection] = useState<ManualSection>("overview");
  const sectionContentRef = useRef<HTMLDivElement>(null);

  const sections: { id: ManualSection; label: string; icon: React.ElementType }[] = [
    { id: "overview", label: "1. Overview & Core Concept", icon: Cpu },
    { id: "pipeline", label: "2. 6-Stage Execution Pipeline", icon: Layers },
    { id: "modes", label: "3. Cognitive Answer Modes", icon: FileText },
    { id: "hops", label: "4. Dynamic Hop Budgeting", icon: GitBranch },
    { id: "provenance", label: "5. Provenance & Zero-Hallucination", icon: ShieldCheck },
    { id: "comparison", label: "6. Capabilities vs RAG", icon: Activity },
  ];

  // When clicking a section title from the list, update active section and close overlay modal
  const handleSelectSection = (id: ManualSection) => {
    setActiveSection(id);
    setIsManualModalOpen(false); // Disappears so user can read / work and re-open via header button
  };

  return (
    <div className="flex h-full text-slate-100 overflow-hidden bg-transparent relative">
      {/* Main Workspace Column */}
      <div className="flex-1 flex flex-col min-w-0 h-full relative">
        {/* ── Top Header Toolbar with Small Cortex Manual Button ────────────────── */}
        <div className="h-12 border-b border-white/6 px-4 flex items-center justify-between bg-black/20 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg border border-cyan-500/30 bg-cyan-500/10 text-cyan-300">
              <BrainCircuit size={16} />
            </div>
            <span className="text-xs font-bold tracking-wide text-white">
              FAIM Cortex
            </span>
            <span className="inline-flex items-center gap-1 rounded-full border border-cyan-400/25 bg-cyan-500/10 px-2 py-0.5 text-[9px] font-semibold text-cyan-300">
              <Zap size={9} /> Active Engine
            </span>
          </div>

          {/* Small Top Header Manual Trigger Button */}
          <button
            onClick={() => setIsManualModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-cyan-500/30 bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 text-xs font-semibold tracking-wide transition-all shadow-[0_0_15px_rgba(6,182,212,0.1)] active:scale-95"
            title="Open FAIM Cortex Operating Manual"
          >
            <BookOpen size={13} />
            <span>Cortex Manual</span>
          </button>
        </div>

        {/* Workspace: Dynamic Message Stream + Composer */}
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

      {/* ── OVERLAY MODAL: FAIM Cortex Professional Operating Manual ────────────── */}
      <AnimatePresence>
        {isManualModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 md:p-6 bg-black/75 backdrop-blur-md">
            {/* Modal Backdrop click listener */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0"
              onClick={() => setIsManualModalOpen(false)}
            />

            {/* Modal Content Window */}
            <motion.div
              initial={{ opacity: 0, scale: 0.96, y: 12 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96, y: 12 }}
              transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
              className="relative z-10 w-full max-w-5xl max-h-[85vh] flex flex-col rounded-[22px] border border-white/10 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.96))] shadow-[0_24px_80px_rgba(0,0,0,0.6)] overflow-hidden"
            >
              {/* Top horizontal accent bar */}
              <div className="absolute top-0 left-8 right-8 h-[2px] bg-gradient-to-r from-cyan-500/80 via-purple-400/50 to-transparent rounded-full" />

              {/* Modal Header */}
              <div className="flex items-center justify-between px-6 py-4 border-b border-white/6 shrink-0 bg-white/[0.01]">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-cyan-500/30 bg-cyan-500/10 text-cyan-300">
                    <BrainCircuit size={20} />
                  </div>
                  <div>
                    <h2 className="text-sm font-bold text-white tracking-wide flex items-center gap-2">
                      FAIM Cortex — Professional Operating Manual & Architecture
                    </h2>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      Deterministic memory synthesis engine with bounded multi-hop graph reasoning & zero-hallucination provenance
                    </p>
                  </div>
                </div>

                <button
                  onClick={() => setIsManualModalOpen(false)}
                  className="flex h-8 w-8 items-center justify-center rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
                  title="Close Manual"
                >
                  <X size={16} />
                </button>
              </div>

              {/* Modal Body: 2-Column Layout */}
              <div className="grid grid-cols-1 md:grid-cols-12 min-h-0 flex-1 overflow-hidden">
                {/* Left Table of Contents / Sidebar */}
                <div className="md:col-span-4 border-r border-white/6 bg-white/[0.01] p-4 space-y-2 overflow-y-auto custom-scrollbar">
                  <p className="text-[10px] uppercase font-bold tracking-widest text-slate-500 mb-3 px-2 flex items-center gap-1.5">
                    <Compass size={12} className="text-cyan-400" /> Select Chapter to View & Dismiss
                  </p>

                  {sections.map((sec) => {
                    const Icon = sec.icon;
                    const active = activeSection === sec.id;
                    return (
                      <button
                        key={sec.id}
                        onClick={() => handleSelectSection(sec.id)}
                        className={`w-full flex items-center justify-between px-3 py-2.5 rounded-[12px] text-xs transition-all text-left relative overflow-hidden border ${
                          active
                            ? "border-cyan-500/40 bg-cyan-500/10 text-cyan-200 font-bold"
                            : "border-white/5 bg-white/[0.02] text-slate-400 hover:border-white/15 hover:text-slate-200"
                        }`}
                      >
                        {active && (
                          <div className="absolute top-0 left-0 bottom-0 w-[3px] bg-cyan-400" />
                        )}
                        <div className="flex items-center gap-2.5 min-w-0">
                          <Icon size={14} className={active ? "text-cyan-300 shrink-0" : "shrink-0 opacity-60"} />
                          <span className="truncate">{sec.label}</span>
                        </div>
                        <ArrowRight size={12} className="shrink-0 opacity-40" />
                      </button>
                    );
                  })}
                </div>

                {/* Right Chapter Content Viewer */}
                <div
                  ref={sectionContentRef}
                  className="md:col-span-8 p-6 overflow-y-auto custom-scrollbar space-y-10 bg-black/20"
                >
                  {/* Section 1: Overview */}
                  <div id="section-overview" className="space-y-4 pt-1">
                    <div className="flex items-center gap-2 text-cyan-300 border-b border-white/6 pb-2">
                      <Cpu size={18} />
                      <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                        1. Overview & Core Concept
                      </h3>
                    </div>
                    <p className="text-xs text-slate-300 leading-relaxed">
                      <strong>FAIM Cortex</strong> is the cognitive memory synthesis engine powering the FAIM Matrix platform.
                      Unlike traditional Retrieval-Augmented Generation (RAG) which relies solely on top-k vector similarity and passes unstructured chunks to an LLM, FAIM Cortex performs <strong>planner-driven, bounded multi-hop graph reasoning</strong> directly over your live graph scope.
                    </p>

                    <div className="grid gap-3 sm:grid-cols-2">
                      <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                        <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-cyan-400/80 via-cyan-400/30 to-transparent" />
                        <h4 className="text-xs font-bold text-cyan-200 mb-1">Deterministic Architecture</h4>
                        <p className="text-[11px] text-slate-400 leading-relaxed">
                          Combines canonical semantics, a 2.31M+ term semantic registry base, ConceptNet broadening, and graph-learned domain memory for exact evidence identification.
                        </p>
                      </div>

                      <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                        <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-purple-400/80 via-purple-400/30 to-transparent" />
                        <h4 className="text-xs font-bold text-purple-200 mb-1">Zero Hallucination</h4>
                        <p className="text-[11px] text-slate-400 leading-relaxed">
                          Every output statement is strictly anchored to evidence node IDs and cryptographic SHA-256 evidence hashes.
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Section 2: 6-Stage Execution Pipeline */}
                  <div id="section-pipeline" className="space-y-4 pt-4 border-t border-white/6">
                    <div className="flex items-center gap-2 text-purple-300 border-b border-white/6 pb-2">
                      <Layers size={18} />
                      <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                        2. 6-Stage Cognitive Execution Pipeline
                      </h3>
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2">
                      {[
                        {
                          num: "Stage 01",
                          title: "Intent & Hop Budgeting",
                          desc: "Deterministic alias router classifies query intent into core cognitive task types without LLM classifier delay.",
                          color: "from-cyan-400/80 via-cyan-400/30",
                        },
                        {
                          num: "Stage 02",
                          title: "Multi-Signal Expansion",
                          desc: "Combines vector search, lexical sidecars, late-interaction matching, and graph diffusion across Postgres, Redis, and Qdrant.",
                          color: "from-sky-400/80 via-sky-400/30",
                        },
                        {
                          num: "Stage 03",
                          title: "Parallel Branching",
                          desc: "Executes targeted parallel branches: Temporal (timeline), Contradiction (conflict detection), and Multi-hop evidence walks.",
                          color: "from-purple-400/80 via-purple-400/30",
                        },
                        {
                          num: "Stage 04",
                          title: "State & Tree Reduction",
                          desc: "Aggregates evidence nodes & reasoning edges into a unified CortexBrainState and confidence-weighted reasoning tree.",
                          color: "from-indigo-400/80 via-indigo-400/30",
                        },
                        {
                          num: "Stage 05",
                          title: "Grounded Synthesis",
                          desc: "Generates cited answers anchored strictly to retrieved graph provenance and evidence hashes with zero hallucination.",
                          color: "from-emerald-400/80 via-emerald-400/30",
                        },
                        {
                          num: "Stage 06",
                          title: "FIG View Persistence",
                          desc: "Persists structured turn state and triggers node glow receipts in the interactive 3D Fast Interactive Graph (FIG) View.",
                          color: "from-amber-400/80 via-amber-400/30",
                        },
                      ].map((stage) => (
                        <div
                          key={stage.num}
                          className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-3.5"
                        >
                          <div className={`absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b ${stage.color} to-transparent`} />
                          <span className="text-[10px] font-mono font-bold text-cyan-300 uppercase">{stage.num}</span>
                          <p className="text-xs font-bold text-slate-100 mt-0.5">{stage.title}</p>
                          <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">{stage.desc}</p>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Section 3: Cognitive Answer Modes */}
                  <div id="section-modes" className="space-y-4 pt-4 border-t border-white/6">
                    <div className="flex items-center gap-2 text-sky-300 border-b border-white/6 pb-2">
                      <FileText size={18} />
                      <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                        3. Cognitive Answer Modes
                      </h3>
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2">
                      <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                        <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-cyan-400/80 via-cyan-400/30 to-transparent" />
                        <div className="flex items-center gap-1.5 text-cyan-300 mb-1">
                          <Zap size={14} />
                          <span className="text-xs font-bold uppercase">Direct Mode</span>
                        </div>
                        <p className="text-[11px] text-slate-400 leading-relaxed">
                          Provides focused, immediate answers grounded directly in top evidence nodes. Ideal for direct facts or specific lookups.
                        </p>
                      </div>

                      <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                        <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-sky-400/80 via-sky-400/30 to-transparent" />
                        <div className="flex items-center gap-1.5 text-sky-300 mb-1">
                          <Clock size={14} />
                          <span className="text-xs font-bold uppercase">Timeline Mode</span>
                        </div>
                        <p className="text-[11px] text-slate-400 leading-relaxed">
                          Reconstructs chronological event lineages, showing how assertions, documents, or memory items evolved over time.
                        </p>
                      </div>

                      <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                        <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-amber-400/80 via-amber-400/30 to-transparent" />
                        <div className="flex items-center gap-1.5 text-amber-300 mb-1">
                          <AlertTriangle size={14} />
                          <span className="text-xs font-bold uppercase">Contradiction Mode</span>
                        </div>
                        <p className="text-[11px] text-slate-400 leading-relaxed">
                          Scans the graph for conflicting statements or stale invariant violations and reports competing assertions.
                        </p>
                      </div>

                      <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                        <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-purple-400/80 via-purple-400/30 to-transparent" />
                        <div className="flex items-center gap-1.5 text-purple-300 mb-1">
                          <Network size={14} />
                          <span className="text-xs font-bold uppercase">Provenance Mode</span>
                        </div>
                        <p className="text-[11px] text-slate-400 leading-relaxed">
                          Exposes explicit graph traversal paths, source files, and cryptographic evidence hashes powering the answer.
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Section 4: Dynamic Hop Budgeting */}
                  <div id="section-hops" className="space-y-4 pt-4 border-t border-white/6">
                    <div className="flex items-center gap-2 text-indigo-300 border-b border-white/6 pb-2">
                      <GitBranch size={18} />
                      <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                        4. Dynamic Hop Budgeting
                      </h3>
                    </div>

                    <p className="text-xs text-slate-300 leading-relaxed">
                      FAIM Cortex eliminates fixed retrieval depth constraints. Rather than forcing all queries to use a static 1-hop lookup, Cortex dynamically scales its hop budget based on the complexity of the task:
                    </p>

                    <div className="space-y-2">
                      <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-3.5 flex items-center justify-between gap-4">
                        <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-cyan-400/80 via-cyan-400/30 to-transparent" />
                        <div>
                          <p className="text-xs font-bold text-cyan-200">Shallow Traversal (1–3 Hops)</p>
                          <p className="text-[11px] text-slate-400">Used for direct entity lookups, key-value queries, and single-document facts.</p>
                        </div>
                        <span className="shrink-0 text-xs font-mono font-bold text-cyan-400">Fast Path</span>
                      </div>

                      <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-3.5 flex items-center justify-between gap-4">
                        <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-purple-400/80 via-purple-400/30 to-transparent" />
                        <div>
                          <p className="text-xs font-bold text-purple-200">Adaptive Traversal (1–24 Hops Default)</p>
                          <p className="text-[11px] text-slate-400">Used for multi-entity relationship mapping, investigative questions, and root cause analysis.</p>
                        </div>
                        <span className="shrink-0 text-xs font-mono font-bold text-purple-400">Default Path</span>
                      </div>

                      <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-3.5 flex items-center justify-between gap-4">
                        <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-amber-400/80 via-amber-400/30 to-transparent" />
                        <div>
                          <p className="text-xs font-bold text-amber-200">Extended Bounded Ceiling (Up to 128 Hops)</p>
                          <p className="text-[11px] text-slate-400">Configurable ceiling for deep domain reasoning across large, highly interconnected universe graphs.</p>
                        </div>
                        <span className="shrink-0 text-xs font-mono font-bold text-amber-400">Deep Ceiling</span>
                      </div>
                    </div>
                  </div>

                  {/* Section 5: Provenance & Zero Hallucination */}
                  <div id="section-provenance" className="space-y-4 pt-4 border-t border-white/6">
                    <div className="flex items-center gap-2 text-emerald-300 border-b border-white/6 pb-2">
                      <ShieldCheck size={18} />
                      <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                        5. Provenance & Zero Hallucination
                      </h3>
                    </div>

                    <p className="text-xs text-slate-300 leading-relaxed">
                      In traditional LLM apps, hallucination is a constant risk because the generative model generates facts from memory weights. FAIM Cortex separates <strong>retrieval reasoning</strong> from <strong>narration</strong>.
                    </p>

                    <div className="grid gap-3 sm:grid-cols-2">
                      <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                        <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-emerald-400/80 via-emerald-400/30 to-transparent" />
                        <div className="flex items-center gap-1.5 text-emerald-300 mb-1">
                          <Lock size={14} />
                          <span className="text-xs font-bold uppercase">Cryptographic Hashes</span>
                        </div>
                        <p className="text-[11px] text-slate-400 leading-relaxed">
                          Every ingested file and graph packet has a SHA-256 hash. Citation badges link directly back to verified raw source packets.
                        </p>
                      </div>

                      <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                        <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-cyan-400/80 via-cyan-400/30 to-transparent" />
                        <div className="flex items-center gap-1.5 text-cyan-300 mb-1">
                          <Share2 size={14} />
                          <span className="text-xs font-bold uppercase">FIG 3D Glow Receipts</span>
                        </div>
                        <p className="text-[11px] text-slate-400 leading-relaxed">
                          The 3D FIG View displays visual receipts for every turn, causing the exact reasoning tree nodes to illuminate in real time.
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Section 6: Capabilities vs RAG */}
                  <div id="section-comparison" className="space-y-4 pt-4 border-t border-white/6">
                    <div className="flex items-center gap-2 text-purple-300 border-b border-white/6 pb-2">
                      <Activity size={18} />
                      <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                        6. Capabilities Comparison (Cortex vs RAG)
                      </h3>
                    </div>

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
                </div>
              </div>

              {/* Modal Footer */}
              <div className="flex items-center justify-between px-6 py-3 border-t border-white/6 bg-white/[0.01] shrink-0 text-xs">
                <span className="text-[11px] text-slate-400">
                  Select any chapter from the list to view it and automatically return to Cortex chat.
                </span>
                <button
                  onClick={() => setIsManualModalOpen(false)}
                  className="px-4 py-1.5 rounded-lg border border-cyan-500/30 bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 font-semibold text-xs transition-colors"
                >
                  Close & Open Chat Workspace
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
