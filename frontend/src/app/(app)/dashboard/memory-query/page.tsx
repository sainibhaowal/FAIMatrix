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
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { ChatInterface } from "@/components/memoryquery/ChatInterface";
import { ChatComposer } from "@/components/memoryquery/ChatComposer";
import { HistoryPanel } from "@/components/memoryquery/HistoryPanel";

type ManualSection =
  | "overview"
  | "retrieval"
  | "pipeline"
  | "modes"
  | "hops"
  | "comparison";

export default function MemoryQueryPage() {
  const [isManualModalOpen, setIsManualModalOpen] = useState(false);
  const [activeSection, setActiveSection] = useState<ManualSection>("overview");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const sections: { id: ManualSection; label: string; icon: React.ElementType }[] = [
    { id: "overview", label: "1. Overview & Cortex Core", icon: Cpu },
    { id: "retrieval", label: "2. FAIM Native Retrieval Spine", icon: Database },
    { id: "pipeline", label: "3. 6-Stage Cognitive Pipeline", icon: Layers },
    { id: "modes", label: "4. Cognitive Answer Modes", icon: FileText },
    { id: "hops", label: "5. Dynamic Hop Budgeting", icon: GitBranch },
    { id: "comparison", label: "6. Capabilities vs Standard RAG", icon: Activity },
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
                  className="relative z-10 w-[92vw] max-w-5xl h-[82vh] max-h-[720px] flex flex-col rounded-[20px] border border-white/10 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.96))] shadow-[0_24px_80px_rgba(0,0,0,0.7)] overflow-hidden"
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
                          FAIM Cortex — Professional Operating Manual & Architecture
                        </h2>
                        <p className="text-[11px] text-slate-400 mt-0.5">
                          Deterministic memory synthesis engine built on FAIM Native retrieval, 2.31M+ ConceptNet semantics, and 3D FIG View receipts
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
                                  Chapter 1: Overview & Cortex Core
                                </h3>
                              </div>
                              <span className="text-[10px] font-mono text-cyan-400/80 bg-cyan-500/10 border border-cyan-500/20 px-2.5 py-1 rounded-full">
                                Native Architecture
                              </span>
                            </div>

                            <p className="text-xs text-slate-300 leading-relaxed">
                              <strong>FAIM Cortex</strong> is the cognitive memory synthesis engine of FAIM Matrix.
                              Rather than treating retrieval as a single-pass chunk lookup, Cortex operates directly on top of the <strong>FAIM Native Retrieval Spine</strong>, combining dense vector indexing (`v_native`), 8 semantic signature sidecars, multi-source weighted expansions, and planner-driven graph traversal.
                            </p>

                            <div className="grid gap-4 sm:grid-cols-2">
                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-cyan-400/80 via-cyan-400/30 to-transparent" />
                                <h4 className="text-xs font-bold text-cyan-200 mb-1.5 flex items-center gap-1.5">
                                  <Zap size={13} /> Planner-Driven Reasoning
                                </h4>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  Uses a deterministic alias router to classify turn intent into 8 core cognitive task types without LLM classifier latency or non-deterministic intent drift.
                                </p>
                              </div>

                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-purple-400/80 via-purple-400/30 to-transparent" />
                                <h4 className="text-xs font-bold text-purple-200 mb-1.5 flex items-center gap-1.5">
                                  <ShieldCheck size={13} /> Zero Hallucination Grounding
                                </h4>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  Every statement is anchored strictly to retrieved evidence node IDs and cryptographic SHA-256 evidence hashes.
                                </p>
                              </div>
                            </div>

                            <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.02] p-4 space-y-2">
                              <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-emerald-400/80 via-emerald-400/30 to-transparent" />
                              <h4 className="text-xs font-bold text-slate-200">Core System Principles</h4>
                              <ul className="text-[11px] text-slate-400 space-y-1.5 list-disc list-inside">
                                <li><strong>Vector Spine</strong>: `v_native` provides canonical dense representation without external model lock-in.</li>
                                <li><strong>Explainable Fusion</strong>: Exposes exact query fusion summaries and phase scores in explain payloads.</li>
                                <li><strong>3D Visual Proof</strong>: Emits pulse-v2 ledger events that illuminate reasoning paths in 3D FIG View.</li>
                              </ul>
                            </div>
                          </motion.div>
                        )}

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
                              FAIM Native retrieval does not rely on simple keyword BM25 or raw vector search alone. It implements a multi-channel retrieval engine:
                            </p>

                            <div className="grid gap-3 sm:grid-cols-2">
                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-cyan-400/80 via-cyan-400/30 to-transparent" />
                                <div className="flex items-center gap-1.5 text-cyan-300 mb-1 font-bold text-xs">
                                  <Binary size={14} /> 8 Semantic Signature Sidecars
                                </div>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  Ingest extracts phrase shingles (n-grams), concept keys, alias families, transliterated tokens, stem families, morphology buckets, and relation/time cues into `RepresentationV2`.
                                </p>
                              </div>

                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-purple-400/80 via-purple-400/30 to-transparent" />
                                <div className="flex items-center gap-1.5 text-purple-300 mb-1 font-bold text-xs">
                                  <Search size={14} /> 2.31M+ ConceptNet Semantic Base
                                </div>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  Ships with an embedded 2,172,991 ConceptNet synonym archive, providing deterministic, source-tagged phrase and token expansion without neural query rewrites.
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

                        {activeSection === "pipeline" && (
                          <motion.div
                            key="pipeline"
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
                                  Chapter 3: 6-Stage Cognitive Pipeline
                                </h3>
                              </div>
                              <span className="text-[10px] font-mono text-purple-400/80 bg-purple-500/10 border border-purple-500/20 px-2.5 py-1 rounded-full">
                                Execution Flow
                              </span>
                            </div>

                            <p className="text-xs text-slate-300 leading-relaxed">
                              Every query submitted to FAIM Cortex executes through a deterministic 6-stage cognitive processing pipeline:
                            </p>

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
                                  className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4"
                                >
                                  <div className={`absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b ${stage.color} to-transparent`} />
                                  <span className="text-[10px] font-mono font-bold text-cyan-300 uppercase">{stage.num}</span>
                                  <p className="text-xs font-bold text-slate-100 mt-0.5">{stage.title}</p>
                                  <p className="text-[11px] text-slate-400 mt-1.5 leading-relaxed">{stage.desc}</p>
                                </div>
                              ))}
                            </div>
                          </motion.div>
                        )}

                        {activeSection === "modes" && (
                          <motion.div
                            key="modes"
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
                                  Chapter 4: Cognitive Answer Modes
                                </h3>
                              </div>
                              <span className="text-[10px] font-mono text-sky-400/80 bg-sky-500/10 border border-sky-500/20 px-2.5 py-1 rounded-full">
                                4 Modes Available
                              </span>
                            </div>

                            <p className="text-xs text-slate-300 leading-relaxed">
                              Cortex adjusts its synthesis strategy depending on your selected Cognitive Answer Mode:
                            </p>

                            <div className="grid gap-4 sm:grid-cols-2">
                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-cyan-400/80 via-cyan-400/30 to-transparent" />
                                <div className="flex items-center gap-1.5 text-cyan-300 mb-1.5">
                                  <Zap size={15} />
                                  <span className="text-xs font-bold uppercase">Direct Mode</span>
                                </div>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  Provides concise, immediate answers grounded directly in top evidence nodes. Ideal for direct facts or specific lookups.
                                </p>
                              </div>

                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-sky-400/80 via-sky-400/30 to-transparent" />
                                <div className="flex items-center gap-1.5 text-sky-300 mb-1.5">
                                  <Clock size={15} />
                                  <span className="text-xs font-bold uppercase">Timeline Mode</span>
                                </div>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  Reconstructs chronological event lineages, showing how assertions, documents, or memory items evolved over time.
                                </p>
                              </div>

                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-amber-400/80 via-amber-400/30 to-transparent" />
                                <div className="flex items-center gap-1.5 text-amber-300 mb-1.5">
                                  <AlertTriangle size={15} />
                                  <span className="text-xs font-bold uppercase">Contradiction Mode</span>
                                </div>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  Scans the graph for conflicting statements or stale invariant violations and reports competing assertions.
                                </p>
                              </div>

                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-purple-400/80 via-purple-400/30 to-transparent" />
                                <div className="flex items-center gap-1.5 text-purple-300 mb-1.5">
                                  <Network size={15} />
                                  <span className="text-xs font-bold uppercase">Provenance Mode</span>
                                </div>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  Exposes explicit graph traversal paths, source files, and cryptographic evidence hashes powering the answer.
                                </p>
                              </div>
                            </div>
                          </motion.div>
                        )}

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
                                  Chapter 5: Dynamic Hop Budgeting
                                </h3>
                              </div>
                              <span className="text-[10px] font-mono text-indigo-400/80 bg-indigo-500/10 border border-indigo-500/20 px-2.5 py-1 rounded-full">
                                1 - 128 Hops
                              </span>
                            </div>

                            <p className="text-xs text-slate-300 leading-relaxed">
                              FAIM Cortex eliminates fixed retrieval depth constraints. Rather than forcing all queries to use a static 1-hop lookup, Cortex dynamically scales its hop budget based on the complexity of the task:
                            </p>

                            <div className="space-y-3">
                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4 flex items-center justify-between gap-4">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-cyan-400/80 via-cyan-400/30 to-transparent" />
                                <div>
                                  <p className="text-xs font-bold text-cyan-200">Shallow Traversal (1–3 Hops)</p>
                                  <p className="text-[11px] text-slate-400 mt-1">Used for direct entity lookups, key-value queries, and single-document facts.</p>
                                </div>
                                <span className="shrink-0 text-xs font-mono font-bold text-cyan-400 border border-cyan-500/30 px-2.5 py-1 rounded-md bg-cyan-500/10">Fast Path</span>
                              </div>

                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4 flex items-center justify-between gap-4">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-purple-400/80 via-purple-400/30 to-transparent" />
                                <div>
                                  <p className="text-xs font-bold text-purple-200">Adaptive Traversal (1–24 Hops Default)</p>
                                  <p className="text-[11px] text-slate-400 mt-1">Used for multi-entity relationship mapping, investigative questions, and root cause analysis.</p>
                                </div>
                                <span className="shrink-0 text-xs font-mono font-bold text-purple-400 border border-purple-500/30 px-2.5 py-1 rounded-md bg-purple-500/10">Default Path</span>
                              </div>

                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4 flex items-center justify-between gap-4">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-amber-400/80 via-amber-400/30 to-transparent" />
                                <div>
                                  <p className="text-xs font-bold text-amber-200">Extended Bounded Ceiling (Up to 128 Hops)</p>
                                  <p className="text-[11px] text-slate-400 mt-1">Configurable ceiling for deep domain reasoning across large, highly interconnected universe graphs.</p>
                                </div>
                                <span className="shrink-0 text-xs font-mono font-bold text-amber-400 border border-amber-500/30 px-2.5 py-1 rounded-md bg-amber-500/10">Deep Ceiling</span>
                              </div>
                            </div>
                          </motion.div>
                        )}

                        {activeSection === "comparison" && (
                          <motion.div
                            key="comparison"
                            initial={{ opacity: 0, y: 8 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -8 }}
                            transition={{ duration: 0.2 }}
                            className="space-y-6"
                          >
                            <div className="flex items-center justify-between border-b border-white/6 pb-3">
                              <div className="flex items-center gap-2.5 text-purple-300">
                                <Activity size={20} />
                                <h3 className="text-base font-bold text-white uppercase tracking-wider">
                                  Chapter 6: Capabilities Comparison (FAIM Native vs RAG)
                                </h3>
                              </div>
                              <span className="text-[10px] font-mono text-purple-400/80 bg-purple-500/10 border border-purple-500/20 px-2.5 py-1 rounded-full">
                                Benchmarking
                              </span>
                            </div>

                            <div className="overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.02]">
                              <table className="w-full text-left text-xs">
                                <thead>
                                  <tr className="border-b border-white/6 bg-white/[0.03] text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                                    <th className="py-3 px-4">Feature</th>
                                    <th className="py-3 px-4 text-cyan-300">FAIM Native & Cortex</th>
                                    <th className="py-3 px-4 text-slate-500">Traditional Chunk RAG</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-white/6 text-slate-300">
                                  <tr>
                                    <td className="py-3 px-4 font-semibold text-slate-200">Vector Spine</td>
                                    <td className="py-3 px-4 text-cyan-200 font-semibold">`v_native` canonical dense core</td>
                                    <td className="py-3 px-4 text-slate-500">Generic third-party embeddings</td>
                                  </tr>
                                  <tr>
                                    <td className="py-3 px-4 font-semibold text-slate-200">Semantic Sidecars</td>
                                    <td className="py-3 px-4 text-cyan-200">8 channels (shingles, concepts, aliases, transliterations, stems, morphology, relations, time)</td>
                                    <td className="py-3 px-4 text-slate-500">Raw text chunks only</td>
                                  </tr>
                                  <tr>
                                    <td className="py-3 px-4 font-semibold text-slate-200">Expansion Engine</td>
                                    <td className="py-3 px-4 text-cyan-200">2.31M+ ConceptNet terms + Multilingual TSV + Graph Domain Memory</td>
                                    <td className="py-3 px-4 text-slate-500">Flat LLM query rewriting (non-deterministic)</td>
                                  </tr>
                                  <tr>
                                    <td className="py-3 px-4 font-semibold text-slate-200">Reasoning Model</td>
                                    <td className="py-3 px-4 text-cyan-200">Bounded multi-hop graph traversal (1–24 hops default, up to 128)</td>
                                    <td className="py-3 px-4 text-slate-500">Single-pass top-k vector chunk retrieval</td>
                                  </tr>
                                  <tr>
                                    <td className="py-3 px-4 font-semibold text-slate-200">Hallucination Protection</td>
                                    <td className="py-3 px-4 text-emerald-400 font-semibold flex items-center gap-1.5">
                                      <CheckCircle2 size={14} /> 100% grounded in evidence node SHA-256 hashes
                                    </td>
                                    <td className="py-3 px-4 text-amber-400/80">High risk of LLM hallucination</td>
                                  </tr>
                                  <tr>
                                    <td className="py-3 px-4 font-semibold text-slate-200">3D Visual Proof</td>
                                    <td className="py-3 px-4 text-cyan-200">Full 3D FIG View graph node glow & path receipts</td>
                                    <td className="py-3 px-4 text-slate-500">Black box text output</td>
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
