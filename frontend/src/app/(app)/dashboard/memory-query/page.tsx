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
  HelpCircle,
  Code2,
  Workflow,
  Sparkles,
  Wifi,
  WifiOff,
  MessageSquare,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { ChatInterface } from "@/components/memoryquery/ChatInterface";
import { ChatComposer } from "@/components/memoryquery/ChatComposer";
import { HistoryPanel } from "@/components/memoryquery/HistoryPanel";
import { CortexChat } from "@/components/memoryquery/CortexChat";
import { useUser } from "@/contexts/UserContext";

type ManualSection =
  | "overview"
  | "retrieval"
  | "loop"
  | "hops"
  | "branches"
  | "scenarios"
  | "writeback"
  | "benchmark"
  | "faq";

type ChatMode = "http" | "websocket";

export default function MemoryQueryPage() {
  const { graphId } = useUser();
  const [isManualModalOpen, setIsManualModalOpen] = useState(false);
  const [activeSection, setActiveSection] = useState<ManualSection>("overview");
  const [mounted, setMounted] = useState(false);
  const [chatMode, setChatMode] = useState<ChatMode>("http");

  useEffect(() => {
    setMounted(true);
  }, []);

  const sections: { id: ManualSection; label: string; icon: React.ElementType }[] = [
    { id: "overview", label: "1. Architecture & Compute Layer", icon: Cpu },
    { id: "retrieval", label: "2. FAIM Native Retrieval Spine", icon: Database },
    { id: "loop", label: "3. 5-Stage Control Loop & Router", icon: Zap },
    { id: "hops", label: "4. Adaptive 1–24+ Hop Reasoning Engine", icon: GitBranch },
    { id: "branches", label: "5. 7 Parallel Cognitive Branches", icon: Layers },
    { id: "scenarios", label: "6. Enterprise Lifecycle Scenarios", icon: FileText },
    { id: "writeback", label: "7. Durable Memory Writebacks", icon: RotateCcw },
    { id: "benchmark", label: "8. Technical Benchmark & Matrix", icon: Scale },
    { id: "faq", label: "9. Enterprise Technical FAQ", icon: HelpCircle },
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
            <div className="ml-2 flex items-center gap-1 rounded-lg border border-white/10 bg-black/30 p-0.5">
              <button
                onClick={() => setChatMode("http")}
                className={`rounded-md px-2 py-0.5 text-[10px] font-semibold transition ${
                  chatMode === "http" ? "bg-cyan-500/20 text-cyan-300" : "text-slate-500 hover:text-slate-300"
                }`}
                title="HTTP Query Mode"
              >
                HTTP
              </button>
              <button
                onClick={() => setChatMode("websocket")}
                className={`rounded-md px-2 py-0.5 text-[10px] font-semibold transition ${
                  chatMode === "websocket" ? "bg-cyan-500/20 text-cyan-300" : "text-slate-500 hover:text-slate-300"
                }`}
                title="Real-time WebSocket Chat Mode"
              >
                <Wifi size={10} className="inline mr-1" />
                WebSocket
              </button>
            </div>
          </div>

        </div>
        {/* Workspace: Dynamic Message Stream + Composer */}
        <div className="flex-1 flex flex-col min-h-0 relative">
          {chatMode === "http" ? (
            <>
              <ChatInterface />
              <div className="absolute bottom-0 left-0 right-0 z-30 invisible pointer-events-none">
                <div className="visible pointer-events-auto w-full">
                  <ChatComposer />
                </div>
              </div>
            </>
          ) : (
            <CortexChat
              graphId={graphId || "default-graph"}
              tenantId="default"
            />
          )}
        </div>
      </div>

      {/* Intelligence Sidebar - Floating Right Anchor */}
      {chatMode === "http" && (
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
      )}

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
                  className="relative z-10 w-[94vw] max-w-6xl h-[88vh] max-h-[820px] flex flex-col rounded-[20px] border border-white/10 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.96))] shadow-[0_24px_80px_rgba(0,0,0,0.7)] overflow-hidden"
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
                          FAIM Cortex — Master System Architecture & User Manual
                        </h2>
                        <p className="text-[11px] text-slate-400 mt-0.5">
                          Comprehensive guide to FAIM Cortex cognitive reasoning, native multi-channel retrieval, 1–24+ hop graph traversal, and 3D FIG proofs
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
                        {/* Chapter 1: Architecture & Compute Layer */}
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
                                  Chapter 1: System Architecture & Hardware Compute Topology
                                </h3>
                              </div>
                              <span className="text-[10px] font-mono text-cyan-400/80 bg-cyan-500/10 border border-cyan-500/20 px-2.5 py-1 rounded-full">
                                Enterprise Compute Architecture
                              </span>
                            </div>

                            <p className="text-xs text-slate-300 leading-relaxed">
                              <strong>FAIM Cortex</strong> represents an architectural evolution in enterprise knowledge processing. Traditional AI memory platforms pass unstructured text chunks to an opaque Large Language Model (LLM), forcing the model to implicitly memorize and reason across probabilistic weights. FAIM Cortex cleanly decouples <strong>symbolic memory retrieval & graph reasoning</strong> from output narration.
                            </p>

                            <div className="space-y-4">
                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4 space-y-2">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-cyan-400/80 via-cyan-400/30 to-transparent" />
                                <h4 className="text-xs font-bold text-cyan-200 flex items-center gap-1.5">
                                  <Server size={14} /> CPU Native Execution Baseline
                                </h4>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  Standard FAIM Cortex deployments execute directly on enterprise x86_64 and ARM64 CPU architectures. Using SIMD vector instructions (AVX-512 / ARM Neon), FAIM handles millions of knowledge nodes on standard servers without requiring costly GPU infrastructure. This guarantees $0 GPU overhead for baseline enterprise environments and on-premises deployments.
                                </p>
                              </div>

                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4 space-y-2">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-purple-400/80 via-purple-400/30 to-transparent" />
                                <h4 className="text-xs font-bold text-purple-200 flex items-center gap-1.5">
                                  <Zap size={14} /> Optional CUDA Acceleration Layer
                                </h4>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  For ultra-large-scale enterprise knowledge graphs containing 100M+ assertions, FAIM incorporates an optional high-throughput CUDA acceleration layer. Custom CUDA kernels mirror knowledge vectors into VRAM to execute parallel inner products and Compressed Sparse Row (CSR) matrix graph traversals at sub-millisecond speeds.
                                </p>
                              </div>

                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.02] p-4 space-y-2">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-emerald-400/80 via-emerald-400/30 to-transparent" />
                                <h4 className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                                  <Award size={14} className="text-emerald-400" /> The Mathematical Determinism Principle
                                </h4>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  In neural LLM pipelines, GPUs are utilized for non-deterministic probability sampling, leading to hallucinations and non-reproducible answers. In FAIM Cortex, compute resources are strictly allocated to <strong>exact symbolic inner-products, n-gram shingle matching, and CSR graph operations</strong>. This ensures every query result is 100% reproducible and verifiable against cryptographic SHA-256 evidence hashes.
                                </p>
                              </div>
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
                                  Chapter 2: FAIM Native Multi-Channel Retrieval Spine
                                </h3>
                              </div>
                              <span className="text-[10px] font-mono text-cyan-400/80 bg-cyan-500/10 border border-cyan-500/20 px-2.5 py-1 rounded-full">
                                8 Sidecars + 2.31M+ Semantics
                              </span>
                            </div>

                            <p className="text-xs text-slate-300 leading-relaxed">
                              At the core of FAIM Cortex is the <strong>FAIM Native Retrieval Spine</strong>. Rather than relying on a single vector search or flat keyword matching, FAIM constructs 4 synergistic retrieval layers centered around the canonical dense vector core:
                            </p>

                            <div className="space-y-4">
                              {/* 8 Sidecars Detailed Section */}
                              <div className="relative overflow-hidden rounded-[14px] border border-cyan-500/20 bg-cyan-500/[0.03] p-4 space-y-3">
                                <div className="absolute top-0 left-0 bottom-0 w-[3px] bg-cyan-400" />
                                <h4 className="text-xs font-bold text-cyan-200 flex items-center gap-2">
                                  <Binary size={15} /> Detailed Breakdown of the 8 Semantic Signature Sidecars
                                </h4>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  During document ingestion, FAIM builds 8 additive, deterministic sidecar channels alongside the canonical dense vector. These sidecars allow query scoring to evaluate structural, morphological, and temporal evidence simultaneously:
                                </p>

                                <div className="grid gap-2 sm:grid-cols-2 text-[11px] text-slate-300">
                                  <div className="bg-white/[0.02] border border-white/5 p-2.5 rounded-lg">
                                    <span className="font-bold text-cyan-300">1. Phrase Shingles (N-Grams):</span> Captures multi-word sequence signatures (bigrams, trigrams) to prevent semantic fragmentation of domain terminology.
                                  </div>
                                  <div className="bg-white/[0.02] border border-white/5 p-2.5 rounded-lg">
                                    <span className="font-bold text-cyan-300">2. Concept Keys & Lemmata:</span> Extracts canonical dictionary lemmata to bridge variations in verb tenses and noun plurals deterministically.
                                  </div>
                                  <div className="bg-white/[0.02] border border-white/5 p-2.5 rounded-lg">
                                    <span className="font-bold text-cyan-300">3. Alias Families:</span> Maps acronyms, abbreviations, and organizational aliases (e.g., "FAIM" ↔ "Fractal Antisymmetric Inheritance Memory").
                                  </div>
                                  <div className="bg-white/[0.02] border border-white/5 p-2.5 rounded-lg">
                                    <span className="font-bold text-cyan-300">4. Transliterated Tokens:</span> Standardizes phonetic variations and non-Latin character sets for cross-script retrieval consistency.
                                  </div>
                                  <div className="bg-white/[0.02] border border-white/5 p-2.5 rounded-lg">
                                    <span className="font-bold text-cyan-300">5. Stem Families:</span> Groups morphological root stems to ensure query matching across derivative word forms.
                                  </div>
                                  <div className="bg-white/[0.02] border border-white/5 p-2.5 rounded-lg">
                                    <span className="font-bold text-cyan-300">6. Morphology Buckets:</span> Categorizes syntactic parts of speech and structural sentence roles for exact grammatical alignment.
                                  </div>
                                  <div className="bg-white/[0.02] border border-white/5 p-2.5 rounded-lg">
                                    <span className="font-bold text-cyan-300">7. Relation Cues:</span> Identifies subject-predicate-object assertion markers (e.g., "depends_on", "supersedes", "located_in").
                                  </div>
                                  <div className="bg-white/[0.02] border border-white/5 p-2.5 rounded-lg">
                                    <span className="font-bold text-cyan-300">8. Temporal & Numerical Cues:</span> Indexes ISO timestamps, version numbers, and numerical constraints for precise temporal ordering.
                                  </div>
                                </div>
                              </div>

                              <div className="grid gap-3 sm:grid-cols-3">
                                <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-3.5 space-y-1">
                                  <h4 className="text-xs font-bold text-purple-200 flex items-center gap-1.5">
                                    <Search size={13} /> 2.31M+ ConceptNet Semantic Base
                                  </h4>
                                  <p className="text-[11px] text-slate-400 leading-relaxed">
                                    Includes 2,172,991 pre-compiled ConceptNet synonym assertions, broadening search terms deterministically without stochastic LLM rewrites.
                                  </p>
                                </div>

                                <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-3.5 space-y-1">
                                  <h4 className="text-xs font-bold text-sky-200 flex items-center gap-1.5">
                                    <Globe size={13} /> Multilingual Concept Bridges
                                  </h4>
                                  <p className="text-[11px] text-slate-400 leading-relaxed">
                                    Embedded TSV bridge packs provide cross-language concept expansion (EN, DE, FR, ES) without neural translation overhead.
                                  </p>
                                </div>

                                <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-3.5 space-y-1">
                                  <h4 className="text-xs font-bold text-emerald-200 flex items-center gap-1.5">
                                    <BrainCircuit size={13} /> Graph Domain Memory
                                  </h4>
                                  <p className="text-[11px] text-slate-400 leading-relaxed">
                                    Ingestion workers autonomously mine graph-local concept bundles and paraphrase records to adapt jargon definitions post-ingestion.
                                  </p>
                                </div>
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
                                  Chapter 3: 5-Stage Control Loop & Sub-5ms Task Router
                                </h3>
                              </div>
                              <span className="text-[10px] font-mono text-cyan-400/80 bg-cyan-500/10 border border-cyan-500/20 px-2.5 py-1 rounded-full">
                                Deterministic Control Architecture
                              </span>
                            </div>

                            <p className="text-xs text-slate-300 leading-relaxed">
                              Every turn submitted to FAIM Cortex executes through a deterministic 5-stage cognitive pipeline managed by a zero-latency task router:
                            </p>

                            <div className="space-y-3">
                              {[
                                {
                                  stage: "Stage 1",
                                  title: "Memory Retrieval & Multi-Channel Expansion",
                                  desc: "Query text passes through the 8 semantic sidecars, ConceptNet expander, and canonicalizers to generate weighted candidate pools across vector and relational graph indices.",
                                },
                                {
                                  stage: "Stage 2",
                                  title: "Sub-5ms Deterministic Turn Planner",
                                  desc: "The alias task router classifies query intent into target cognitive modes (Direct, Timeline, Contradiction, Provenance) using static pattern aliases instead of slow LLM prompt classifiers.",
                                },
                                {
                                  stage: "Stage 3",
                                  title: "Parallel Branch Execution",
                                  desc: "Dispatches up to 7 specialized analysis routines concurrently to evaluate graph paths, temporal lineages, and contradiction vectors in parallel.",
                                },
                                {
                                  stage: "Stage 4",
                                  title: "State Reduction (Cortex Brain State)",
                                  desc: "The reducer aggregates parallel branch evidence into a consolidated, inspectable brain state containing candidate nodes, edge weights, and reasoning chains.",
                                },
                                {
                                  stage: "Stage 5",
                                  title: "Grounded Narration & Visual Receipts",
                                  desc: "Generates cited answers anchored strictly to retrieved graph entities while emitting pulse-v2 ledger events to illuminate 3D FIG View node glow receipts.",
                                },
                              ].map((s) => (
                                <div key={s.stage} className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4 flex gap-3 items-start">
                                  <div className="shrink-0 text-cyan-400 font-mono font-bold text-xs bg-cyan-500/10 border border-cyan-500/20 px-2 py-1 rounded-md">
                                    {s.stage}
                                  </div>
                                  <div>
                                    <h4 className="text-xs font-bold text-white">{s.title}</h4>
                                    <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">{s.desc}</p>
                                  </div>
                                </div>
                              ))}
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
                                Multi-Hop Traversal Specification
                              </span>
                            </div>

                            <p className="text-xs text-slate-300 leading-relaxed">
                              Traditional retrieval engines perform a single-pass (1-hop) top-k vector search, failing when answers require navigating multi-step relational chains. FAIM Cortex incorporates an <strong>adaptive dynamic traversal planner</strong> that scales graph depth dynamically:
                            </p>

                            <div className="space-y-4">
                              <div className="grid gap-3 sm:grid-cols-3">
                                <div className="relative overflow-hidden rounded-[14px] border border-cyan-500/30 bg-cyan-500/[0.04] p-4 space-y-1.5">
                                  <span className="text-[10px] font-mono font-bold text-cyan-400">1–3 Hops</span>
                                  <h4 className="text-xs font-bold text-white">Shallow Direct Traversal</h4>
                                  <p className="text-[11px] text-slate-400 leading-relaxed">
                                    Automatically selected for single-entity facts and direct property lookups to maintain minimal execution latency (~5ms).
                                  </p>
                                </div>

                                <div className="relative overflow-hidden rounded-[14px] border border-purple-500/30 bg-purple-500/[0.04] p-4 space-y-1.5">
                                  <span className="text-[10px] font-mono font-bold text-purple-400">Default 24 Hops</span>
                                  <h4 className="text-xs font-bold text-white">Adaptive Traversal Standard</h4>
                                  <p className="text-[11px] text-slate-400 leading-relaxed">
                                    Standard production ceiling for complex investigative queries, evaluating deep relational dependencies across multiple connected documents.
                                  </p>
                                </div>

                                <div className="relative overflow-hidden rounded-[14px] border border-amber-500/30 bg-amber-500/[0.04] p-4 space-y-1.5">
                                  <span className="text-[10px] font-mono font-bold text-amber-400">Up to 128 Hops</span>
                                  <h4 className="text-xs font-bold text-white">Extended Bounded Ceiling</h4>
                                  <p className="text-[11px] text-slate-400 leading-relaxed">
                                    Configurable maximum boundary for navigating massive, highly interconnected enterprise universe graphs.
                                  </p>
                                </div>
                              </div>

                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.02] p-4 space-y-2">
                                <h4 className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                                  <ShieldCheck size={14} className="text-cyan-400" /> Deterministic Frontier Pruning & Path Protection
                                </h4>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  To prevent exponential path explosion during deep 24+ hop traversals, the traversal engine applies deterministic frontier pruning, maximum frontier width caps, and partial-path fallbacks. If no exact goal node is reached within the hop budget, Cortex returns the strongest verified partial path with clear confidence metrics.
                                </p>
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
                                  Chapter 5: Detailed Breakdown of the 7 Parallel Cognitive Branches
                                </h3>
                              </div>
                              <span className="text-[10px] font-mono text-purple-400/80 bg-purple-500/10 border border-purple-500/20 px-2.5 py-1 rounded-full">
                                Parallel Branch Engine
                              </span>
                            </div>

                            <p className="text-xs text-slate-300 leading-relaxed">
                              During every turn, Cortex dispatches up to 7 specialized cognitive branch workers concurrently. Each branch evaluates distinct knowledge dimensions before aggregating results into the reducer:
                            </p>

                            <div className="space-y-3">
                              {[
                                {
                                  num: "01",
                                  name: "Recall Branch",
                                  title: "Multi-Channel Candidate Extraction",
                                  desc: "Extracts top candidate nodes from combined vector indices and 8 semantic sidecar channels, establishing the foundational evidence set.",
                                },
                                {
                                  num: "02",
                                  name: "Timeline Branch",
                                  title: "Temporal Lineage & Chronological Ordering",
                                  desc: "Constructs chronological event timelines, ordering historical document updates, version histories, and temporal assertions.",
                                },
                                {
                                  num: "03",
                                  name: "Contradiction Branch",
                                  title: "Transitive Conflict & Invariant Resolution",
                                  desc: "Evaluates assertion integrity to detect conflicting claims or superseded data, categorizing graph nodes into CURRENT and HISTORICAL states.",
                                },
                                {
                                  num: "04",
                                  name: "Concept Branch",
                                  title: "Higher-Order Concept Clustering",
                                  desc: "Identifies macro concept clusters and maps graph-local entity bundles across domain boundaries.",
                                },
                                {
                                  num: "05",
                                  name: "Prediction Branch",
                                  title: "Forward Graph Trend Projection",
                                  desc: "Evaluates structural graph dynamics to project forward domain implications and potential downstream system impacts.",
                                },
                                {
                                  num: "06",
                                  name: "Provenance Branch",
                                  title: "Cryptographic Evidence Trail & Hashes",
                                  desc: "Traces raw source files, document line numbers, node IDs, and cryptographic SHA-256 evidence hashes for zero-hallucination verification.",
                                },
                                {
                                  num: "07",
                                  name: "Continuity Branch",
                                  title: "Multi-Turn Session Context Persistence",
                                  desc: "Maintains entity bindings and reference continuity across multi-turn conversational sessions.",
                                },
                              ].map((b) => (
                                <div key={b.num} className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4 flex gap-3 items-start">
                                  <div className="shrink-0 text-purple-300 font-mono font-bold text-xs bg-purple-500/10 border border-purple-500/20 px-2 py-1 rounded-md">
                                    {b.num}
                                  </div>
                                  <div>
                                    <h4 className="text-xs font-bold text-white">{b.name} — <span className="text-purple-300 font-normal">{b.title}</span></h4>
                                    <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">{b.desc}</p>
                                  </div>
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
                                  Chapter 6: Enterprise Lifecycle Scenarios & Walkthroughs
                                </h3>
                              </div>
                              <span className="text-[10px] font-mono text-sky-400/80 bg-sky-500/10 border border-sky-500/20 px-2.5 py-1 rounded-full">
                                Operational Workflows
                              </span>
                            </div>

                            <p className="text-xs text-slate-300 leading-relaxed">
                              Walkthroughs of how FAIM Cortex handles common real-world enterprise scenarios:
                            </p>

                            <div className="space-y-4">
                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4 space-y-2">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-cyan-400/80 via-cyan-400/30 to-transparent" />
                                <h4 className="text-xs font-bold text-cyan-200">Scenario A: Grounded Fact Synthesis Walkthrough</h4>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  When a user queries a factual policy, Cortex executes candidate recall, expands concept lemmata, runs path validation, and returns an answer cited directly with source file links and SHA-256 evidence node hashes. The active reasoning path lights up simultaneously in the 3D FIG View canvas.
                                </p>
                              </div>

                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4 space-y-2">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-amber-400/80 via-amber-400/30 to-transparent" />
                                <h4 className="text-xs font-bold text-amber-200">Scenario B: Temporal Contradiction Resolution Walkthrough</h4>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  When documents contain conflicting statements (e.g., an updated server IP or modified compliance rule), the Contradiction Branch detects time-stamped assertion conflicts. Cortex labels superseded nodes as <span className="text-slate-500 font-mono font-bold">HISTORICAL</span> and dims them in 3D FIG View, while promoting active assertions to <span className="text-emerald-400 font-mono font-bold">CURRENT</span>.
                                </p>
                              </div>

                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4 space-y-2">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-purple-400/80 via-purple-400/30 to-transparent" />
                                <h4 className="text-xs font-bold text-purple-200">Scenario C: Continuous Memory Evolution Walkthrough</h4>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  When a user uploads a new PDF or Markdown document, the ingestion pipeline extracts semantic signatures, creates new graph entities, updates relation edges, and triggers background domain memory learning. On the very next Cortex turn, the updated graph state is immediately searchable without model fine-tuning.
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
                                  Chapter 7: Durable Memory Writebacks & Replay Safety
                                </h3>
                              </div>
                              <span className="text-[10px] font-mono text-amber-400/80 bg-amber-500/10 border border-amber-500/20 px-2.5 py-1 rounded-full">
                                Durable Writeback Architecture
                              </span>
                            </div>

                            <p className="text-xs text-slate-300 leading-relaxed">
                              Memory writebacks proposed during Cortex turn reasoning represent structural graph updates. FAIM enforces strict safety policies to prevent unauthorized database drift:
                            </p>

                            <div className="grid gap-4 sm:grid-cols-2">
                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4 space-y-2">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-amber-400/80 via-amber-400/30 to-transparent" />
                                <h4 className="text-xs font-bold text-amber-200 flex items-center gap-1.5">
                                  <Lock size={14} /> Strict Approval Policy Gatekeeping
                                </h4>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  Writeback candidates are initially logged as structured proposals (`auto_approved` or `pending_review`). Automated graph mutations into PostgreSQL are gatekept by tenant security policies to ensure no unauthorized memory rewrites occur.
                                </p>
                              </div>

                              <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4 space-y-2">
                                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-emerald-400/80 via-emerald-400/30 to-transparent" />
                                <h4 className="text-xs font-bold text-emerald-200 flex items-center gap-1.5">
                                  <Check size={14} /> Idempotent Backend Execution
                                </h4>
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  Upon policy approval, writebacks execute through a durable backend worker, persisting execution receipts containing packet hash and written node metrics to ensure replay safety and exact transactional auditing.
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
                                  Chapter 8: Technical Benchmark & Architecture Comparison Matrix
                                </h3>
                              </div>
                              <span className="text-[10px] font-mono text-purple-400/80 bg-purple-500/10 border border-purple-500/20 px-2.5 py-1 rounded-full">
                                Enterprise Benchmarks
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
                                    <td className="py-3 px-4 text-cyan-200 font-semibold">Canonical Dense Core + 8 Semantic Sidecars</td>
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

                        {/* Chapter 9: Enterprise Technical FAQ */}
                        {activeSection === "faq" && (
                          <motion.div
                            key="faq"
                            initial={{ opacity: 0, y: 8 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -8 }}
                            transition={{ duration: 0.2 }}
                            className="space-y-6"
                          >
                            <div className="flex items-center justify-between border-b border-white/6 pb-3">
                              <div className="flex items-center gap-2.5 text-cyan-300">
                                <HelpCircle size={20} />
                                <h3 className="text-base font-bold text-white uppercase tracking-wider">
                                  Chapter 9: Enterprise Technical FAQ
                                </h3>
                              </div>
                              <span className="text-[10px] font-mono text-cyan-400/80 bg-cyan-500/10 border border-cyan-500/20 px-2.5 py-1 rounded-full">
                                Frequently Asked Questions
                              </span>
                            </div>

                            <div className="space-y-3">
                              {[
                                {
                                  q: "Q1: Does FAIM Cortex rely on heavy Deep Learning models or ML training runs for retrieval?",
                                  a: "No. FAIM Cortex uses a symbolic multi-channel indexing spine (canonical dense core, 8 semantic signature sidecars, ConceptNet expansion, and Compressed Sparse Row matrix math) for 100% deterministic, reproducible retrieval without neural drift or retraining runs.",
                                },
                                {
                                  q: "Q2: Does FAIM Matrix require dedicated NVIDIA GPUs to operate?",
                                  a: "No. FAIM is built on a CPU-first execution baseline, enabling standard enterprise x86/ARM CPU servers to execute knowledge operations without compulsory GPU hardware.",
                                },
                                {
                                  q: "Q3: How does FAIM utilize GPUs when enterprise GPU acceleration is enabled?",
                                  a: "When CUDA acceleration is enabled, FAIM uses custom CUDA kernels to accelerate linear algebra inner products and CSR graph matrix multiplication in VRAM for 100M+ node graphs at sub-millisecond speeds.",
                                },
                                {
                                  q: "Q4: How does FAIM guarantee zero hallucinations compared to traditional LLM RAG pipelines?",
                                  a: "Every statement emitted by Cortex is anchored directly to cryptographic SHA-256 evidence node hashes and exact source document lines. Unanchored claims are suppressed prior to narration.",
                                },
                                {
                                  q: "Q5: Can FAIM run inside air-gapped enterprise environments without internet access?",
                                  a: "Yes. The 2.31M+ ConceptNet semantic base and multilingual TSV bridge packs are fully embedded inside the local application binary and container without external cloud API dependencies.",
                                },
                                {
                                  q: "Q6: How does FAIM resolve conflicting statements when documents update over time?",
                                  a: "The Contradiction Branch and Transitive Contradiction Traversal engine automatically evaluate temporal lineage, marking superseded facts as HISTORICAL while promoting active assertions to CURRENT.",
                                },
                                {
                                  q: "Q7: What happens during multi-hop graph reasoning if a goal entity is unreachable within the hop budget?",
                                  a: "The adaptive 1–24+ hop engine applies deterministic frontier pruning and returns the strongest verified partial path along with confidence indicators rather than failing silently.",
                                },
                                {
                                  q: "Q8: Are memory writeback updates executed automatically into the database?",
                                  a: "No. Structural writebacks into PostgreSQL require policy approval and execute through an idempotent, durable backend pipeline emitting verifiable execution receipts.",
                                },
                              ].map((faq, idx) => (
                                <div
                                  key={idx}
                                  className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4 space-y-1.5"
                                >
                                  <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-cyan-400/80 via-purple-400/50 to-transparent" />
                                  <h4 className="text-xs font-bold text-cyan-200">{faq.q}</h4>
                                  <p className="text-[11px] text-slate-400 leading-relaxed">{faq.a}</p>
                                </div>
                              ))}
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
