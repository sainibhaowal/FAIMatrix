"use client";

import React, { useState, useEffect } from "react";
import { createPortal } from "react-dom";
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
  ChevronRight,
  Database,
  Search,
  Globe,
  Binary,
  RotateCcw,
  Eye,
  Check,
  Scale,
  Award,
  Server,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { ChatInterface } from "@/components/memoryquery/ChatInterface";
import { ChatComposer } from "@/components/memoryquery/ChatComposer";
import { HistoryPanel } from "@/components/memoryquery/HistoryPanel";

type ManualSection =
  | "overview"
  | "retrieval"
  | "loop"
  | "hops"
  | "branches"
  | "scenarios"
  | "writeback"
  | "benchmark";

export default function MemoryQueryPage() {
  const [isManualModalOpen, setIsManualModalOpen] = useState(false);
  const [activeSection, setActiveSection] = useState<ManualSection>("overview");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const sections: { id: ManualSection; label: string; icon: React.ElementType }[] = [
    { id: "overview", label: "1. Core Architecture & Compute Layer", icon: Cpu },
    { id: "retrieval", label: "2. FAIM Native Retrieval Spine", icon: Database },
    { id: "loop", label: "3. 5-Stage Control Loop & Router", icon: Zap },
    { id: "hops", label: "4. Adaptive 1–24+ Hop Reasoning Engine", icon: GitBranch },
    { id: "branches", label: "5. 7 Parallel Cognitive Branches", icon: Layers },
    { id: "scenarios", label: "6. Enterprise Lifecycle Scenarios", icon: FileText },
    { id: "writeback", label: "7. Durable Memory Writebacks", icon: RotateCcw },
    { id: "benchmark", label: "8. Technical Benchmark & Matrix", icon: Scale },
  ];

  const handleSelectSection = (id: ManualSection) => {
    setActiveSection(id);
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

      {/* ── OVERLAY MODAL via PORTAL: Floating Fullscreen Backdrop (No Sidebar Clashing) ── */}
      {mounted &&
        createPortal(
          <AnimatePresence>
            {isManualModalOpen && (
              <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 sm:p-6 md:p-10 bg-black/80 backdrop-blur-md">
                {/* Backdrop Click Listener */}
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="absolute inset-0"
                  onClick={() => setIsManualModalOpen(false)}
                />

                {/* Modal Window Container */}
                <motion.div
                  initial={{ opacity: 0, scale: 0.95, y: 16 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95, y: 16 }}
                  transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
                  className="relative z-10 w-[92vw] max-w-5xl h-[86vh] max-h-[780px] flex flex-col rounded-[20px] border border-white/10 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.96))] shadow-[0_24px_80px_rgba(0,0,0,0.7)] overflow-hidden"
                >
                  {/* Top horizontal accent bar */}
                  <div className="absolute top-0 left-8 right-8 h-[2px] bg-gradient-to-r from-cyan-500/80 via-purple-400/50 to-transparent rounded-full" />

                  {/* Modal Header */}
                  <div className="flex items-center justify-between px-6 py-4 border-b border-white/6 shrink-0 bg-white/[0.01]">
                    <div className="flex items-center gap-3">
                      <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-cyan-500/30 bg-cyan-500/10 text-cyan-300 shrink-0">
                        <BrainCircuit size={20} />
                      </div>
                      <div>
                        <h2 className="text-sm font-bold text-white tracking-wide flex items-center gap-2">
                          FAIM Cortex — Technical Specification & Operating Manual
                        </h2>
                        <p className="text-[11px] text-slate-400 mt-0.5">
                          Deterministic cognitive control loop, dual CPU/CUDA execution topology, 2.31M+ semantic base & 3D FIG pulse ledgers
                        </p>
                      </div>
                    </div>

                    <button
                      onClick={() => setIsManualModalOpen(false)}
                      className="flex h-8 w-8 items-center justify-center rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition-colors shrink-0"
                      title="Close Manual"
                    >
                      <X size={16} />
                    </button>
                  </div>

                  {/* Modal Body: 2-Column Clean Layout */}
                  <div className="flex min-h-0 flex-1 overflow-hidden">
                    {/* Left Table of Contents Sidebar */}
                    <div className="w-64 sm:w-72 md:w-80 shrink-0 border-r border-white/6 bg-white/[0.01] p-4 space-y-2 overflow-y-auto custom-scrollbar">
                      <p className="text-[10px] uppercase font-bold tracking-widest text-slate-500 mb-3 px-2 flex items-center gap-1.5">
                        <Compass size={12} className="text-cyan-400" /> Manual Chapters
                      </p>

                      {sections.map((sec) => {
                        const Icon = sec.icon;
                        const active = activeSection === sec.id;
                        return (
                          <button
                            key={sec.id}
                            onClick={() => handleSelectSection(sec.id)}
                            className={`w-full flex items-center justify-between px-3.5 py-3 rounded-[12px] text-xs transition-all text-left relative overflow-hidden border ${
                              active
                                ? "border-cyan-500/50 bg-cyan-500/10 text-cyan-200 font-bold shadow-[0_0_20px_rgba(6,182,212,0.1)]"
                                : "border-white/5 bg-white/[0.02] text-slate-400 hover:border-white/15 hover:text-slate-200"
                            }`}
                          >
                            {active && (
                              <div className="absolute top-0 left-0 bottom-0 w-[3px] bg-cyan-400" />
                            )}
                            <div className="flex items-center gap-2.5 min-w-0">
                              <Icon size={15} className={active ? "text-cyan-300 shrink-0" : "shrink-0 opacity-60"} />
                              <span className="truncate">{sec.label}</span>
                            </div>
                            <ChevronRight size={13} className={active ? "text-cyan-400 shrink-0" : "shrink-0 opacity-30"} />
                          </button>
                        );
                      })}
                    </div>

                    {/* Right Dedicated Chapter Content Viewer */}
                    <div className="flex-1 min-w-0 p-6 overflow-y-auto custom-scrollbar bg-black/20">
                      <AnimatePresence mode="wait">
                        {/* Chapter 1: Core Architecture & Compute Layer */}
                        {activeSection === "overview" && (
                          <motion.div
                            key="overview"
                            initial={{ opacity: 0, y: 8 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -8 }}
                            transition={{ duration: 0.2 }}
                            className="space-y-6"
                          >
                            <div className="flex items-center justify-between border-b border-white/6 pb-3">
                              <div className="flex items-center gap-2.5 text-cyan-300">
                                <Cpu size={20} />
                                <h3 className="text-base font-bold text-white uppercase tracking-wider">
                                  Chapter 1: Core Architecture & Compute Layer
                                </h3>
                              </div>
                              <span className="text-[10px] font-mono text-cyan-400/80 bg-cyan-500/10 border border-cyan-500/20 px-2.5 py-1 rounded-full">
                                Enterprise Compute Architecture
                              </span>
                            </div>

                            <p className="text-xs text-slate-300 leading-relaxed">
                              <strong>FAIM Cortex</strong> is the cognitive memory synthesis engine of the FAIM Matrix architecture.
                              The system decoupling separates high-speed symbolic graph retrieval from output narration, delivering high-precision memory synthesis across both edge and multi-node enterprise environments.
                            </p>

                            <div className="grid gap-4 sm:grid-cols-2">
                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-cyan-400/80 via-cyan-400/30 to-transparent" />
                                <h4 className="text-xs font-bold text-cyan-200 mb-1.5 flex items-center gap-1.5">
                                  <Server size={14} /> CPU Native Execution Baseline
                                </h4>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  Standard deployments run directly on enterprise x86/ARM CPU architectures using SIMD vector instructions, eliminating compulsory GPU hardware requirements for core knowledge indexing and retrieval operations.
                                </p>
                              </div>

                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-purple-400/80 via-purple-400/30 to-transparent" />
                                <h4 className="text-xs font-bold text-purple-200 mb-1.5 flex items-center gap-1.5">
                                  <Zap size={14} /> Optional CUDA Acceleration (`VectorBank`)
                                </h4>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  For multi-million node graphs requiring sub-millisecond latency, FAIM enables an optional CUDA Acceleration Layer (`FAIM_ACCEL_MODE=true`). CUDA kernels execute parallel inner-products and Compressed Sparse Row (CSR) matrix graph operations directly in VRAM.
                                </p>
                              </div>
                            </div>

                            <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.02] p-4 space-y-2">
                              <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-emerald-400/80 via-emerald-400/30 to-transparent" />
                              <h4 className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                                <Award size={14} className="text-emerald-400" /> Mathematical Determinism Guarantee
                              </h4>
                              <p className="text-[11px] text-slate-400 leading-relaxed">
                                Unlike neural LLM inference which uses GPUs for stochastic sampling across non-transparent weights, FAIM utilizes compute resources strictly for <strong>symbolic inner-products, n-gram shingle matching, and CSR graph operations</strong>, ensuring 100% reproducible, zero-hallucination results.
                              </p>
                            </div>
                          </motion.div>
                        )}

                        {/* Chapter 2: FAIM Native Retrieval Spine */}
                        {activeSection === "retrieval" && (
                          <motion.div
                            key="retrieval"
                            initial={{ opacity: 0, y: 8 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -8 }}
                            transition={{ duration: 0.2 }}
                            className="space-y-6"
                          >
                            <div className="flex items-center justify-between border-b border-white/6 pb-3">
                              <div className="flex items-center gap-2.5 text-cyan-300">
                                <Database size={20} />
                                <h3 className="text-base font-bold text-white uppercase tracking-wider">
                                  Chapter 2: FAIM Native Retrieval Spine
                                </h3>
                              </div>
                              <span className="text-[10px] font-mono text-cyan-400/80 bg-cyan-500/10 border border-cyan-500/20 px-2.5 py-1 rounded-full">
                                Multi-Channel Indexing
                              </span>
                            </div>

                            <p className="text-xs text-slate-300 leading-relaxed">
                              Retrieval in FAIM Native operates across 4 complementary semantic channels centered around the `v_native` canonical dense vector core:
                            </p>

                            <div className="grid gap-3 sm:grid-cols-2">
                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-cyan-400/80 via-cyan-400/30 to-transparent" />
                                <div className="flex items-center gap-1.5 text-cyan-300 mb-1 font-bold text-xs">
                                  <Binary size={14} /> 8 Semantic Signature Sidecars
                                </div>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  `RepresentationV2` extracts phrase shingles (n-grams), concept keys, alias families, transliterated tokens, stem families, morphology buckets, and temporal/relation cues during document ingestion.
                                </p>
                              </div>

                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-purple-400/80 via-purple-400/30 to-transparent" />
                                <div className="flex items-center gap-1.5 text-purple-300 mb-1 font-bold text-xs">
                                  <Search size={14} /> 2.31M+ ConceptNet Semantic Base
                                </div>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  Integrates 2,172,991 ConceptNet synonym assertions to provide deterministic, source-tagged term and phrase expansions without neural query modification.
                                </p>
                              </div>

                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-sky-400/80 via-sky-400/30 to-transparent" />
                                <div className="flex items-center gap-1.5 text-sky-300 mb-1 font-bold text-xs">
                                  <Globe size={14} /> Multilingual Concept Bridges
                                </div>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  Utilizes compressed TSV bridge packs for cross-language matching (EN, DE, etc.), enabling deterministic transliteration and lemma mapping.
                                </p>
                              </div>

                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-emerald-400/80 via-emerald-400/30 to-transparent" />
                                <div className="flex items-center gap-1.5 text-emerald-300 mb-1 font-bold text-xs">
                                  <BrainCircuit size={14} /> Graph-Learned Domain Memory
                                </div>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  Autonomous ingestion operators dynamically mine graph-local `concept_bundle` and `semantic_paraphrase` records to adapt vocabulary definitions post-ingestion.
                                </p>
                              </div>
                            </div>
                          </motion.div>
                        )}

                        {/* Chapter 3: 5-Stage Control Loop & Router */}
                        {activeSection === "loop" && (
                          <motion.div
                            key="loop"
                            initial={{ opacity: 0, y: 8 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -8 }}
                            transition={{ duration: 0.2 }}
                            className="space-y-6"
                          >
                            <div className="flex items-center justify-between border-b border-white/6 pb-3">
                              <div className="flex items-center gap-2.5 text-cyan-300">
                                <Zap size={20} />
                                <h3 className="text-base font-bold text-white uppercase tracking-wider">
                                  Chapter 3: 5-Stage Control Loop & Router
                                </h3>
                              </div>
                              <span className="text-[10px] font-mono text-cyan-400/80 bg-cyan-500/10 border border-cyan-500/20 px-2.5 py-1 rounded-full">
                                Control Loop Spec 67
                              </span>
                            </div>

                            <p className="text-xs text-slate-300 leading-relaxed">
                              Turns are processed through a deterministic 5-stage pipeline, managed by an alias task router executing in sub-5ms latency:
                            </p>

                            <div className="rounded-[14px] border border-cyan-500/20 bg-cyan-500/[0.04] p-4 font-mono text-xs text-cyan-200 text-center flex flex-wrap items-center justify-center gap-2">
                              <span>Memory Retrieval</span>
                              <ChevronRight size={14} className="text-cyan-500" />
                              <span>Turn Planner</span>
                              <ChevronRight size={14} className="text-cyan-500" />
                              <span>Parallel Branches</span>
                              <ChevronRight size={14} className="text-cyan-500" />
                              <span>State Reducer</span>
                              <ChevronRight size={14} className="text-cyan-500" />
                              <span>Grounded Narrator</span>
                            </div>

                            <div className="grid gap-4 sm:grid-cols-2">
                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-cyan-400/80 via-cyan-400/30 to-transparent" />
                                <h4 className="text-xs font-bold text-cyan-200 mb-1.5">Deterministic Router</h4>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  Classifies queries into distinct operational modes (direct, timeline, contradiction, provenance) via static alias mapping without LLM classification overhead.
                                </p>
                              </div>

                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-purple-400/80 via-purple-400/30 to-transparent" />
                                <h4 className="text-xs font-bold text-purple-200 mb-1.5">State Reduction</h4>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  Consolidates evidence from active branches into an auditable `CortexBrainState` structure containing candidate nodes and edge reasoning chains.
                                </p>
                              </div>
                            </div>
                          </motion.div>
                        )}

                        {/* Chapter 4: Adaptive 1-24+ Hop Engine */}
                        {activeSection === "hops" && (
                          <motion.div
                            key="hops"
                            initial={{ opacity: 0, y: 8 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -8 }}
                            transition={{ duration: 0.2 }}
                            className="space-y-6"
                          >
                            <div className="flex items-center justify-between border-b border-white/6 pb-3">
                              <div className="flex items-center gap-2.5 text-indigo-300">
                                <GitBranch size={20} />
                                <h3 className="text-base font-bold text-white uppercase tracking-wider">
                                  Chapter 4: Adaptive 1–24+ Hop Reasoning Engine
                                </h3>
                              </div>
                              <span className="text-[10px] font-mono text-indigo-400/80 bg-indigo-500/10 border border-indigo-500/20 px-2.5 py-1 rounded-full">
                                Architecture Spec 69
                              </span>
                            </div>

                            <p className="text-xs text-slate-300 leading-relaxed">
                              Graph traversal depth is computed dynamically per query via `planner_enhanced.py`, enforcing strict bounded depth ceilings:
                            </p>

                            <div className="space-y-3">
                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4 flex items-center justify-between gap-4">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-cyan-400/80 via-cyan-400/30 to-transparent" />
                                <div>
                                  <p className="text-xs font-bold text-cyan-200">Shallow Direct Traversal (1–3 Hops)</p>
                                  <p className="text-[11px] text-slate-400 mt-1">Applied for single-node facts and direct property lookups to maintain low execution latency.</p>
                                </div>
                                <span className="shrink-0 text-xs font-mono font-bold text-cyan-400 border border-cyan-500/30 px-2.5 py-1 rounded-md bg-cyan-500/10">1–3 Hops</span>
                              </div>

                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4 flex items-center justify-between gap-4">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-purple-400/80 via-purple-400/30 to-transparent" />
                                <div>
                                  <p className="text-xs font-bold text-purple-200">Adaptive Traversal Default (1–24 Hops)</p>
                                  <p className="text-[11px] text-slate-400 mt-1">Standard depth ceiling for multi-entity relational queries and complex path investigations.</p>
                                </div>
                                <span className="shrink-0 text-xs font-mono font-bold text-purple-400 border border-purple-500/30 px-2.5 py-1 rounded-md bg-purple-500/10">Default 24</span>
                              </div>

                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4 flex items-center justify-between gap-4">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-amber-400/80 via-amber-400/30 to-transparent" />
                                <div>
                                  <p className="text-xs font-bold text-amber-200">Extended Bounded Ceiling (Up to 128 Hops)</p>
                                  <p className="text-[11px] text-slate-400 mt-1">Configurable maximum boundary (`FAIM_CORTEX_MAX_HOPS`) for large, deeply interconnected knowledge topologies.</p>
                                </div>
                                <span className="shrink-0 text-xs font-mono font-bold text-amber-400 border border-amber-500/30 px-2.5 py-1 rounded-md bg-amber-500/10">Up to 128</span>
                              </div>
                            </div>
                          </motion.div>
                        )}

                        {/* Chapter 5: 7 Parallel Cognitive Branches */}
                        {activeSection === "branches" && (
                          <motion.div
                            key="branches"
                            initial={{ opacity: 0, y: 8 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -8 }}
                            transition={{ duration: 0.2 }}
                            className="space-y-6"
                          >
                            <div className="flex items-center justify-between border-b border-white/6 pb-3">
                              <div className="flex items-center gap-2.5 text-purple-300">
                                <Layers size={20} />
                                <h3 className="text-base font-bold text-white uppercase tracking-wider">
                                  Chapter 5: 7 Parallel Cognitive Branches
                                </h3>
                              </div>
                              <span className="text-[10px] font-mono text-purple-400/80 bg-purple-500/10 border border-purple-500/20 px-2.5 py-1 rounded-full">
                                Branch Architecture
                              </span>
                            </div>

                            <p className="text-xs text-slate-300 leading-relaxed">
                              The Cortex runtime dispatches up to 7 specialized analysis routines concurrently during each query cycle:
                            </p>

                            <div className="grid gap-3 sm:grid-cols-2">
                              {[
                                { name: "1. Recall Branch", desc: "Retrieves candidate nodes from combined vector and multi-channel lexical indices." },
                                { name: "2. Timeline Branch", desc: "Constructs temporal event sequences and orders chronological assertions." },
                                { name: "3. Contradiction Branch", desc: "Evaluates assertion integrity to detect conflicting or superseded knowledge." },
                                { name: "4. Concept Branch", desc: "Identifies concept clusters and domain-level entity groupings." },
                                { name: "5. Prediction Branch", desc: "Projects structural graph trends and forward domain trajectories." },
                                { name: "6. Provenance Branch", desc: "Traces exact document sources, node identifiers, and SHA-256 evidence hashes." },
                                { name: "7. Continuity Branch", desc: "Maintains conversational context across multi-turn sessions." },
                              ].map((b) => (
                                <div
                                  key={b.name}
                                  className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-3.5"
                                >
                                  <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-purple-400/80 via-purple-400/30 to-transparent" />
                                  <p className="text-xs font-bold text-purple-200">{b.name}</p>
                                  <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">{b.desc}</p>
                                </div>
                              ))}
                            </div>
                          </motion.div>
                        )}

                        {/* Chapter 6: Enterprise Lifecycle Scenarios */}
                        {activeSection === "scenarios" && (
                          <motion.div
                            key="scenarios"
                            initial={{ opacity: 0, y: 8 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -8 }}
                            transition={{ duration: 0.2 }}
                            className="space-y-6"
                          >
                            <div className="flex items-center justify-between border-b border-white/6 pb-3">
                              <div className="flex items-center gap-2.5 text-sky-300">
                                <FileText size={20} />
                                <h3 className="text-base font-bold text-white uppercase tracking-wider">
                                  Chapter 6: Enterprise Lifecycle Scenarios
                                </h3>
                              </div>
                              <span className="text-[10px] font-mono text-sky-400/80 bg-sky-500/10 border border-sky-500/20 px-2.5 py-1 rounded-full">
                                Operational Scenarios
                              </span>
                            </div>

                            <div className="space-y-4">
                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4 space-y-1.5">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-cyan-400/80 via-cyan-400/30 to-transparent" />
                                <h4 className="text-xs font-bold text-cyan-200">Scenario A: Grounded Fact Synthesis</h4>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  Retrieves relevant evidence nodes, validates path continuity, and synthesizes a fully cited response linked directly to verified graph entities.
                                </p>
                              </div>

                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4 space-y-1.5">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-amber-400/80 via-amber-400/30 to-transparent" />
                                <h4 className="text-xs font-bold text-amber-200">Scenario B: Temporal Contradiction Resolution</h4>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  Identifies conflicting assertions over time, categorizing nodes into <span className="text-emerald-400 font-mono">CURRENT</span> and <span className="text-slate-500 font-mono">HISTORICAL</span> states while updating visual state in FIG View.
                                </p>
                              </div>

                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4 space-y-1.5">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-purple-400/80 via-purple-400/30 to-transparent" />
                                <h4 className="text-xs font-bold text-purple-200">Scenario C: Continuous Memory Evolution</h4>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  Document ingest pipeline creates new entity nodes and updates graph edges, making newly ingested facts instantly searchable on subsequent turns.
                                </p>
                              </div>
                            </div>
                          </motion.div>
                        )}

                        {/* Chapter 7: Durable Memory Writebacks */}
                        {activeSection === "writeback" && (
                          <motion.div
                            key="writeback"
                            initial={{ opacity: 0, y: 8 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -8 }}
                            transition={{ duration: 0.2 }}
                            className="space-y-6"
                          >
                            <div className="flex items-center justify-between border-b border-white/6 pb-3">
                              <div className="flex items-center gap-2.5 text-amber-300">
                                <RotateCcw size={20} />
                                <h3 className="text-base font-bold text-white uppercase tracking-wider">
                                  Chapter 7: Durable Memory Writebacks
                                </h3>
                              </div>
                              <span className="text-[10px] font-mono text-amber-400/80 bg-amber-500/10 border border-amber-500/20 px-2.5 py-1 rounded-full">
                                Execution Spec 72
                              </span>
                            </div>

                            <p className="text-xs text-slate-300 leading-relaxed">
                              Memory updates generated during Cortex reasoning follow strict structural persistence policies:
                            </p>

                            <div className="grid gap-4 sm:grid-cols-2">
                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-amber-400/80 via-amber-400/30 to-transparent" />
                                <h4 className="text-xs font-bold text-amber-200 mb-1 flex items-center gap-1.5">
                                  <Lock size={13} /> Strict Access Controls
                                </h4>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  Structural graph modifications require explicit approval mechanisms to enforce tenant isolation and prevent unintended state drift.
                                </p>
                              </div>

                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-emerald-400/80 via-emerald-400/30 to-transparent" />
                                <h4 className="text-xs font-bold text-emerald-200 mb-1 flex items-center gap-1.5">
                                  <Check size={13} /> Idempotent Execution Path
                                </h4>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  Approved writebacks are executed via `writeback_executor.py`, producing execution receipts containing `packet_hash` and `nodes_written` for replay verification.
                                </p>
                              </div>
                            </div>
                          </motion.div>
                        )}

                        {/* Chapter 8: Technical Benchmark & Matrix */}
                        {activeSection === "benchmark" && (
                          <motion.div
                            key="benchmark"
                            initial={{ opacity: 0, y: 8 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -8 }}
                            transition={{ duration: 0.2 }}
                            className="space-y-6"
                          >
                            <div className="flex items-center justify-between border-b border-white/6 pb-3">
                              <div className="flex items-center gap-2.5 text-purple-300">
                                <Scale size={20} />
                                <h3 className="text-base font-bold text-white uppercase tracking-wider">
                                  Chapter 8: Technical Benchmark & Matrix
                                </h3>
                              </div>
                              <span className="text-[10px] font-mono text-purple-400/80 bg-purple-500/10 border border-purple-500/20 px-2.5 py-1 rounded-full">
                                System Benchmarks
                              </span>
                            </div>

                            <div className="overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.02]">
                              <table className="w-full text-left text-xs">
                                <thead>
                                  <tr className="border-b border-white/6 bg-white/[0.03] text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                                    <th className="py-3 px-4">Architecture Metric</th>
                                    <th className="py-3 px-4 text-cyan-300">FAIM Native & Cortex</th>
                                    <th className="py-3 px-4 text-slate-500">Traditional Chunk RAG</th>
                                    <th className="py-3 px-4 text-slate-500">Heavy ML / LLM Architectures</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-white/6 text-slate-300">
                                  <tr>
                                    <td className="py-3 px-4 font-semibold text-slate-200">Retrieval & Indexing Spine</td>
                                    <td className="py-3 px-4 text-cyan-200 font-semibold">`v_native` + 8 Semantic Sidecars</td>
                                    <td className="py-3 px-4 text-slate-500">Unstructured Text Chunks</td>
                                    <td className="py-3 px-4 text-slate-500">Heavy Vector Embeddings</td>
                                  </tr>
                                  <tr>
                                    <td className="py-3 px-4 font-semibold text-slate-200">Expansion Engine</td>
                                    <td className="py-3 px-4 text-cyan-200 font-semibold">2.31M+ ConceptNet Terms + Multilingual TSVs</td>
                                    <td className="py-3 px-4 text-slate-500">Static Keyword Matching</td>
                                    <td className="py-3 px-4 text-slate-500">Stochastic LLM Query Rewriting</td>
                                  </tr>
                                  <tr>
                                    <td className="py-3 px-4 font-semibold text-slate-200">Reasoning Depth</td>
                                    <td className="py-3 px-4 text-cyan-200 font-semibold">Adaptive 1–24+ Hops (Ceiling 128)</td>
                                    <td className="py-3 px-4 text-slate-500">Single-Pass 1-Hop Lookup</td>
                                    <td className="py-3 px-4 text-slate-500">Unbounded Agent Loops</td>
                                  </tr>
                                  <tr>
                                    <td className="py-3 px-4 font-semibold text-slate-200">Hallucination Verification</td>
                                    <td className="py-3 px-4 text-emerald-400 font-semibold flex items-center gap-1.5">
                                      <CheckCircle2 size={14} /> 100% Grounded (SHA-256 Hashes)
                                    </td>
                                    <td className="py-3 px-4 text-amber-400/80">Unverified Context Chunks</td>
                                    <td className="py-3 px-4 text-amber-400/80">Non-Deterministic Sampling Drift</td>
                                  </tr>
                                  <tr>
                                    <td className="py-3 px-4 font-semibold text-slate-200">Compute Hardware Profile</td>
                                    <td className="py-3 px-4 text-emerald-400 font-semibold">CPU-First (Optional CUDA GPU Layer)</td>
                                    <td className="py-3 px-4 text-slate-300">CPU Vector DB</td>
                                    <td className="py-3 px-4 text-red-400">Multi-GPU Clusters Required</td>
                                  </tr>
                                  <tr>
                                    <td className="py-3 px-4 font-semibold text-slate-200">Visual Audit & Proof</td>
                                    <td className="py-3 px-4 text-cyan-200">3D FIG View Pulse Ledgers</td>
                                    <td className="py-3 px-4 text-slate-500">Unformatted Text Output</td>
                                    <td className="py-3 px-4 text-slate-500">Opaque Internal Logs</td>
                                  </tr>
                                </tbody>
                              </table>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  </div>

                  {/* Modal Footer */}
                  <div className="flex items-center justify-between px-6 py-3 border-t border-white/6 bg-white/[0.01] shrink-0 text-xs">
                    <span className="text-[11px] text-slate-400">
                      Click any chapter on the left to view its dedicated manual page. Click Close when finished.
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
          </AnimatePresence>,
          document.body
        )}
    </div>
  );
}
