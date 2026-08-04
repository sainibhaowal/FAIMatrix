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
    { id: "overview", label: "1. Overview & Hardware Architecture", icon: Cpu },
    { id: "retrieval", label: "2. FAIM Native Retrieval Spine", icon: Database },
    { id: "loop", label: "3. 5-Step Control Loop & Router", icon: Zap },
    { id: "hops", label: "4. Adaptive 1–24+ Hop Engine", icon: GitBranch },
    { id: "branches", label: "5. 7 Parallel Cognitive Branches", icon: Layers },
    { id: "scenarios", label: "6. Enterprise Scenarios & Life Cycles", icon: FileText },
    { id: "writeback", label: "7. Durable Writebacks & Receipts", icon: RotateCcw },
    { id: "benchmark", label: "8. Enterprise Comparison Matrix", icon: Scale },
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
                          FAIM Cortex — Master Enterprise Operating Architecture & System Manual
                        </h2>
                        <p className="text-[11px] text-slate-400 mt-0.5">
                          Deterministic cognitive control loop, CPU-first & optional CUDA GPU layer, 2.31M+ ConceptNet terms & 3D FIG pulse proofs
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
                        {/* Chapter 1: Overview & Hardware Architecture */}
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
                                  Chapter 1: Overview & Hardware Architecture
                                </h3>
                              </div>
                              <span className="text-[10px] font-mono text-cyan-400/80 bg-cyan-500/10 border border-cyan-500/20 px-2.5 py-1 rounded-full">
                                CPU-First + CUDA GPU Layer
                              </span>
                            </div>

                            <p className="text-xs text-slate-300 leading-relaxed">
                              <strong>FAIM Cortex</strong> is the cognitive memory synthesis engine powering FAIM Matrix.
                              A key question is: <em>"Does FAIM require GPUs, or can it run on CPU? How does it scale for massive enterprise workloads?"</em>
                            </p>

                            <div className="grid gap-4 sm:grid-cols-2">
                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-cyan-400/80 via-cyan-400/30 to-transparent" />
                                <h4 className="text-xs font-bold text-cyan-200 mb-1.5 flex items-center gap-1.5">
                                  <Server size={14} /> CPU-First Zero-Requirement Baseline
                                </h4>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  FAIM does <strong>not require a GPU</strong> to function. Its core symbolic mathematics, n-gram shingle matching, and graph reasoning run at high speed on standard enterprise x86/ARM CPUs, making deployment lightweight and cost-effective.
                                </p>
                              </div>

                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-purple-400/80 via-purple-400/30 to-transparent" />
                                <h4 className="text-xs font-bold text-purple-200 mb-1.5 flex items-center gap-1.5">
                                  <Zap size={14} /> Optional CUDA GPU Acceleration (`VectorBank`)
                                </h4>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  For massive scale (100M+ to billions of facts with sub-millisecond latency), FAIM includes an optional <strong>CUDA GPU Acceleration Layer</strong> (`FAIM_ACCEL_MODE=true`). CUDA kernels execute parallel inner-products and Compressed Sparse Row (CSR) matrix graph traversals directly in VRAM.
                                </p>
                              </div>
                            </div>

                            <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.02] p-4 space-y-2">
                              <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-emerald-400/80 via-emerald-400/30 to-transparent" />
                              <h4 className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                                <Award size={14} className="text-emerald-400" /> Key Difference: FAIM GPU Math vs Neural LLM GPUs
                              </h4>
                              <p className="text-[11px] text-slate-400 leading-relaxed">
                                Neural LLMs use GPUs for non-deterministic probability sampling across billions of neural weights (causing hallucination and GPU memory hogging). FAIM uses GPUs strictly as a <strong>parallel linear algebra & CSR matrix math accelerator</strong> for 100% deterministic, zero-hallucination search!
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
                                Multi-Channel Index
                              </span>
                            </div>

                            <p className="text-xs text-slate-300 leading-relaxed">
                              FAIM Native retrieval does not rely on simple BM25 keyword matching or raw vector similarity. It implements a multi-layer deterministic engine:
                            </p>

                            <div className="grid gap-3 sm:grid-cols-2">
                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-cyan-400/80 via-cyan-400/30 to-transparent" />
                                <div className="flex items-center gap-1.5 text-cyan-300 mb-1 font-bold text-xs">
                                  <Binary size={14} /> 8 Semantic Signature Sidecars
                                </div>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  During ingest, `RepresentationV2` extracts phrase shingles (n-grams), concept keys, alias families, transliterated tokens, stem families, morphology buckets, and temporal/relation cues.
                                </p>
                              </div>

                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-purple-400/80 via-purple-400/30 to-transparent" />
                                <div className="flex items-center gap-1.5 text-purple-300 mb-1 font-bold text-xs">
                                  <Search size={14} /> 2.31M+ ConceptNet Semantic Base
                                </div>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  Ships with an embedded 2,172,991 ConceptNet synonym archive, generating deterministic, source-tagged phrase and token expansions without neural query rewrites.
                                </p>
                              </div>

                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-sky-400/80 via-sky-400/30 to-transparent" />
                                <div className="flex items-center gap-1.5 text-sky-300 mb-1 font-bold text-xs">
                                  <Globe size={14} /> Multilingual Concept Bridges
                                </div>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  Includes compressed TSV enterprise packs for cross-lingual concept coverage (EN, DE, etc.), performing deterministic transliteration and lemma matching.
                                </p>
                              </div>

                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-emerald-400/80 via-emerald-400/30 to-transparent" />
                                <div className="flex items-center gap-1.5 text-emerald-300 mb-1 font-bold text-xs">
                                  <BrainCircuit size={14} /> Graph-Learned Domain Memory
                                </div>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  Autonomous upload workers mine graph-local `concept_bundle` and `semantic_paraphrase` rows, adapting lexicon terms automatically after file uploads.
                                </p>
                              </div>
                            </div>
                          </motion.div>
                        )}

                        {/* Chapter 3: 5-Step Control Loop & Router */}
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
                                  Chapter 3: 5-Step Control Loop & Router
                                </h3>
                              </div>
                              <span className="text-[10px] font-mono text-cyan-400/80 bg-cyan-500/10 border border-cyan-500/20 px-2.5 py-1 rounded-full">
                                Specs 67 & 72
                              </span>
                            </div>

                            <p className="text-xs text-slate-300 leading-relaxed">
                              Cortex uses a small, deterministic task router to classify intent into core cognitive task types in sub-5ms without LLM classifier overhead.
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
                                  Maps turns into cognitive modes (direct, timeline, contradiction, provenance) using alias maps instead of LLM prompt classifiers.
                                </p>
                              </div>

                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-purple-400/80 via-purple-400/30 to-transparent" />
                                <h4 className="text-xs font-bold text-purple-200 mb-1.5">State Reduction</h4>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  Reduces multi-branch evidence into a single inspectable `CortexBrainState` containing evidence nodes and reasoning edge paths.
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
                                  Chapter 4: Adaptive 1–24+ Hop Engine
                                </h3>
                              </div>
                              <span className="text-[10px] font-mono text-indigo-400/80 bg-indigo-500/10 border border-indigo-500/20 px-2.5 py-1 rounded-full">
                                Architecture Spec 69
                              </span>
                            </div>

                            <p className="text-xs text-slate-300 leading-relaxed">
                              FAIM Cortex implements a <strong>real planner-driven adaptive hop runtime</strong> (`planner_enhanced.py`). Cortex thinking is <strong>on by default from the backend</strong>:
                            </p>

                            <div className="space-y-3">
                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4 flex items-center justify-between gap-4">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-cyan-400/80 via-cyan-400/30 to-transparent" />
                                <div>
                                  <p className="text-xs font-bold text-cyan-200">Shallow Direct Turns (1–3 Hops)</p>
                                  <p className="text-[11px] text-slate-400 mt-1">Direct facts and single-document lookups stay at low depth for minimal latency.</p>
                                </div>
                                <span className="shrink-0 text-xs font-mono font-bold text-cyan-400 border border-cyan-500/30 px-2.5 py-1 rounded-md bg-cyan-500/10">1–3 Hops</span>
                              </div>

                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4 flex items-center justify-between gap-4">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-purple-400/80 via-purple-400/30 to-transparent" />
                                <div>
                                  <p className="text-xs font-bold text-purple-200">Adaptive Production Default (1–24 Hops)</p>
                                  <p className="text-[11px] text-slate-400 mt-1">Multi-entity relationship mapping and investigative turns dynamically expand graph traversal depth.</p>
                                </div>
                                <span className="shrink-0 text-xs font-mono font-bold text-purple-400 border border-purple-500/30 px-2.5 py-1 rounded-md bg-purple-500/10">Default 24</span>
                              </div>

                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4 flex items-center justify-between gap-4">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-amber-400/80 via-amber-400/30 to-transparent" />
                                <div>
                                  <p className="text-xs font-bold text-amber-200">Extended Bounded Ceiling (Up to 128 Hops)</p>
                                  <p className="text-[11px] text-slate-400 mt-1">Configurable ceiling for deep domain reasoning across large, highly interconnected universe graphs.</p>
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
                                Parallel Architecture
                              </span>
                            </div>

                            <p className="text-xs text-slate-300 leading-relaxed">
                              During every turn, Cortex executes up to 7 structured reasoning branches in parallel before state reduction:
                            </p>

                            <div className="grid gap-3 sm:grid-cols-2">
                              {[
                                { name: "1. Recall Branch", desc: "Retrieves core candidate nodes from multi-channel vector & lexical stores." },
                                { name: "2. Timeline Branch", desc: "Reconstructs temporal lineages and resolves chronological event ordering." },
                                { name: "3. Contradiction Branch", desc: "Scans graph assertions for conflicts, supersessions, and stale facts." },
                                { name: "4. Concept Branch", desc: "Maps higher-order concept clusters and domain bundle relationships." },
                                { name: "5. Prediction Branch", desc: "Evaluates trend implications and forward domain trajectories." },
                                { name: "6. Provenance Branch", desc: "Exposes raw source files, chunk hashes, and graph traversal paths." },
                                { name: "7. Continuity Branch", desc: "Carries context forward across turns from previous session turns." },
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

                        {/* Chapter 6: Enterprise Scenarios & Life Cycles */}
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
                                  Chapter 6: Enterprise Scenarios & Life Cycles
                                </h3>
                              </div>
                              <span className="text-[10px] font-mono text-sky-400/80 bg-sky-500/10 border border-sky-500/20 px-2.5 py-1 rounded-full">
                                Real User Scenarios
                              </span>
                            </div>

                            <div className="space-y-4">
                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4 space-y-1.5">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-cyan-400/80 via-cyan-400/30 to-transparent" />
                                <h4 className="text-xs font-bold text-cyan-200">Scenario A: Grounded Factual Answer</h4>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  Recalls candidate nodes, expands context, ranks top evidence, returns a cited answer, and highlights the evidence path in FIG View.
                                </p>
                              </div>

                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4 space-y-1.5">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-amber-400/80 via-amber-400/30 to-transparent" />
                                <h4 className="text-xs font-bold text-amber-200">Scenario B: Temporal Contradiction Resolution</h4>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  Detects facts that changed over time, resolves <span className="text-emerald-400 font-mono">CURRENT</span> vs <span className="text-slate-500 font-mono">HISTORICAL</span> state, dims superseded nodes in 3D FIG View, and reports the active truth.
                                </p>
                              </div>

                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4 space-y-1.5">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-purple-400/80 via-purple-400/30 to-transparent" />
                                <h4 className="text-xs font-bold text-purple-200">Scenario C: File Upload Memory Evolution</h4>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  Uploading a new document ingests raw bytes, stores new memory packets, evolves graph topology, and surfaces updated facts on the next Cortex turn.
                                </p>
                              </div>
                            </div>
                          </motion.div>
                        )}

                        {/* Chapter 7: Durable Writebacks & Receipts */}
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
                                  Chapter 7: Durable Writebacks & Receipts
                                </h3>
                              </div>
                              <span className="text-[10px] font-mono text-amber-400/80 bg-amber-500/10 border border-amber-500/20 px-2.5 py-1 rounded-full">
                                Architecture Spec 72
                              </span>
                            </div>

                            <p className="text-xs text-slate-300 leading-relaxed">
                              Memory updates proposed during Cortex reasoning are structural changes requiring safety controls:
                            </p>

                            <div className="grid gap-4 sm:grid-cols-2">
                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-amber-400/80 via-amber-400/30 to-transparent" />
                                <h4 className="text-xs font-bold text-amber-200 mb-1 flex items-center gap-1.5">
                                  <Lock size={13} /> Gatekept Structural Updates
                                </h4>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  Cortex gatekeeps structural writebacks into PostgreSQL, ensuring no rogue automated mutations bypass tenant scoping.
                                </p>
                              </div>

                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-emerald-400/80 via-emerald-400/30 to-transparent" />
                                <h4 className="text-xs font-bold text-emerald-200 mb-1 flex items-center gap-1.5">
                                  <Check size={13} /> Durable Execution & Receipts
                                </h4>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  Approved writebacks execute through a durable, idempotent backend path (`writeback_executor.py`), recording execution receipts (`packet_hash`, `nodes_written`) for replay safety.
                                </p>
                              </div>
                            </div>
                          </motion.div>
                        )}

                        {/* Chapter 8: Enterprise Comparison Matrix */}
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
                                  Chapter 8: Enterprise Comparison Matrix
                                </h3>
                              </div>
                              <span className="text-[10px] font-mono text-purple-400/80 bg-purple-500/10 border border-purple-500/20 px-2.5 py-1 rounded-full">
                                Enterprise Claims
                              </span>
                            </div>

                            <div className="overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.02]">
                              <table className="w-full text-left text-xs">
                                <thead>
                                  <tr className="border-b border-white/6 bg-white/[0.03] text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                                    <th className="py-3 px-4">Architecture Metric</th>
                                    <th className="py-3 px-4 text-cyan-300">FAIM Native & Cortex</th>
                                    <th className="py-3 px-4 text-slate-500">Traditional Chunk RAG</th>
                                    <th className="py-3 px-4 text-slate-500">Heavy ML / LLM Agents</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-white/6 text-slate-300">
                                  <tr>
                                    <td className="py-3 px-4 font-semibold text-slate-200">Retrieval & Indexing Spine</td>
                                    <td className="py-3 px-4 text-cyan-200 font-semibold">`v_native` + 8 Semantic Sidecars</td>
                                    <td className="py-3 px-4 text-slate-500">Top-k text chunks</td>
                                    <td className="py-3 px-4 text-slate-500">Heavy vector embeddings</td>
                                  </tr>
                                  <tr>
                                    <td className="py-3 px-4 font-semibold text-slate-200">Expansion Base</td>
                                    <td className="py-3 px-4 text-cyan-200 font-semibold">2.31M+ ConceptNet terms + Multilingual TSVs</td>
                                    <td className="py-3 px-4 text-slate-500">Flat keyword search</td>
                                    <td className="py-3 px-4 text-slate-500">LLM query rewrite (stochastic)</td>
                                  </tr>
                                  <tr>
                                    <td className="py-3 px-4 font-semibold text-slate-200">Reasoning Depth</td>
                                    <td className="py-3 px-4 text-cyan-200 font-semibold">Adaptive 1–24+ Hops (Ceiling 128)</td>
                                    <td className="py-3 px-4 text-slate-500">Single-pass 1-hop lookup</td>
                                    <td className="py-3 px-4 text-slate-500">Unbounded agentic loops (slow)</td>
                                  </tr>
                                  <tr>
                                    <td className="py-3 px-4 font-semibold text-slate-200">Hallucination Protection</td>
                                    <td className="py-3 px-4 text-emerald-400 font-semibold flex items-center gap-1.5">
                                      <CheckCircle2 size={14} /> 100% Grounded (SHA-256 Hashes)
                                    </td>
                                    <td className="py-3 px-4 text-amber-400/80">High Hallucination Risk</td>
                                    <td className="py-3 px-4 text-amber-400/80">Drift & Stochastic Output</td>
                                  </tr>
                                  <tr>
                                    <td className="py-3 px-4 font-semibold text-slate-200">Hardware & GPU Acceleration</td>
                                    <td className="py-3 px-4 text-emerald-400 font-semibold">CPU-First (Optional CUDA GPU Layer)</td>
                                    <td className="py-3 px-4 text-slate-300">CPU Vector DB</td>
                                    <td className="py-3 px-4 text-red-400">High-cost multi-GPU clusters</td>
                                  </tr>
                                  <tr>
                                    <td className="py-3 px-4 font-semibold text-slate-200">Visual Proof & Audit</td>
                                    <td className="py-3 px-4 text-cyan-200">Full 3D FIG View Pulse Receipts</td>
                                    <td className="py-3 px-4 text-slate-500">Black Box Text Output</td>
                                    <td className="py-3 px-4 text-slate-500">Opaque Chain-of-Thought logs</td>
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
