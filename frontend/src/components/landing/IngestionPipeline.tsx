"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useState, useEffect } from "react";

const PIPELINE_STAGES = [
  {
    id: "upload",
    label: "Upload",
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
      </svg>
    ),
    color: "cyan",
    description: "Upload PDF, DOCX, TXT, or paste text. Multi-file batch upload supported.",
    detail: "File is stored immutably with SHA-256 hash. Raw bytes encrypted at rest.",
    output: "raw_id, sha256, mime_type, size_bytes",
  },
  {
    id: "extract",
    label: "Extract",
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
      </svg>
    ),
    color: "blue",
    description: "Perception router extracts EvidenceBlocks. No crude chunking \u2014 respects document structure.",
    detail: "Paragraphs, headers, tables, lists treated as semantic units.",
    output: "evidence_blocks[], block_count",
  },
  {
    id: "packetize",
    label: "Packetize",
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
      </svg>
    ),
    color: "indigo",
    description: "Blocks become a MemoryPacket with a unique packet_hash (SHA-256 of all blocks).",
    detail: "This hash is the idempotency key \u2014 upload the same file twice, same hash, zero duplicates.",
    output: "packet_hash, memory_packet",
  },
  {
    id: "encode",
    label: "Encode",
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" />
      </svg>
    ),
    color: "purple",
    description: "Each block \u2192 256-dimensional FAIMVector. Deterministic encoding: same text = same vector, always.",
    detail: "No embedding API. Native deterministic encoding path. Every vector gets a SHA-256 vector_hash.",
    output: "faim_vectors[], vector_hashes[]",
  },
  {
    id: "write",
    label: "Write to Graph",
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 3.75H6A2.25 2.25 0 003.75 6v1.5M16.5 3.75H18A2.25 2.25 0 0120.25 6v1.5m0 9V18A2.25 2.25 0 0118 20.25h-1.5m-9 0H6A2.25 2.25 0 013.75 18v-1.5M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    ),
    color: "emerald",
    description: "Vectors enter the engine: parent selection, inheritance computation, antisymmetric merge scan, invariant verification.",
    detail: "8 invariants checked. Graph version bumped. Event journal updated. Graph hash recomputed.",
    output: "nodes_written, merges, graph_version, graph_hash",
  },
];

const DEDUP_EXAMPLE = {
  first: { file: "security-policy-v2.pdf", hash: "a4c1e7f...", result: "3 nodes created" },
  second: { file: "security-policy-v2.pdf", hash: "a4c1e7f...", result: "dedup_hit: true \u2192 0 nodes" },
};

const colorMap: Record<string, { bg: string; text: string; border: string; dot: string }> = {
  cyan: { bg: "bg-cyan-500/10", text: "text-cyan-400", border: "border-cyan-500/30", dot: "bg-cyan-400" },
  blue: { bg: "bg-blue-500/10", text: "text-blue-400", border: "border-blue-500/30", dot: "bg-blue-400" },
  indigo: { bg: "bg-indigo-500/10", text: "text-indigo-400", border: "border-indigo-500/30", dot: "bg-indigo-400" },
  purple: { bg: "bg-purple-500/10", text: "text-purple-400", border: "border-purple-500/30", dot: "bg-purple-400" },
  emerald: { bg: "bg-emerald-500/10", text: "text-emerald-400", border: "border-emerald-500/30", dot: "bg-emerald-400" },
};

export default function IngestionPipeline() {
  const [activeStage, setActiveStage] = useState(0);
  const [isAnimating, setIsAnimating] = useState(true);

  // Auto-advance through stages
  useEffect(() => {
    if (!isAnimating) return;
    const timer = setInterval(() => {
      setActiveStage((prev) => (prev + 1) % PIPELINE_STAGES.length);
    }, 3000);
    return () => clearInterval(timer);
  }, [isAnimating]);

  const stage = PIPELINE_STAGES[activeStage];
  const colors = colorMap[stage.color];

  return (
    <section id="ingestion" className="py-28 px-4 bg-gradient-to-b from-slate-950 to-[#070a18] relative overflow-hidden">
      <div className="absolute inset-0 faim-grid" />

      <div className="max-w-6xl mx-auto relative">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <span className="text-cyan-400 text-sm font-medium tracking-wider uppercase">
            Ingestion System
          </span>
          <h2 className="mt-4 text-4xl md:text-5xl font-bold text-white">
            From File to{" "}
            <span className="bg-gradient-to-r from-cyan-400 to-emerald-400 bg-clip-text text-transparent">
              Living Graph
            </span>
          </h2>
          <p className="mt-4 text-slate-400 max-w-2xl mx-auto">
            Five deterministic stages. Every step produces a verifiable hash.
            Upload the same file twice \u2014 zero duplicates, guaranteed.
          </p>
        </motion.div>

        {/* Pipeline Visualizer */}
        <div className="grid lg:grid-cols-5 gap-3 mb-12">
          {PIPELINE_STAGES.map((s, i) => {
            const c = colorMap[s.color];
            const isActive = i === activeStage;
            return (
              <motion.button
                key={s.id}
                onClick={() => { setActiveStage(i); setIsAnimating(false); }}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.08 }}
                className={`relative p-4 rounded-xl border text-center transition-all duration-300 ${
                  isActive
                    ? `${c.border} ${c.bg}`
                    : "border-slate-800/50 bg-slate-900/20 hover:border-slate-700"
                }`}
              >
                {/* Progress bar */}
                {isActive && isAnimating && (
                  <motion.div
                    className={`absolute bottom-0 left-0 h-0.5 rounded-full ${c.dot}`}
                    initial={{ width: "0%" }}
                    animate={{ width: "100%" }}
                    transition={{ duration: 3, ease: "linear" }}
                    key={activeStage}
                  />
                )}

                <div className={`inline-flex p-2 rounded-lg ${isActive ? c.bg : "bg-slate-800/50"} mb-2`}>
                  <div className={isActive ? c.text : "text-slate-500"}>{s.icon}</div>
                </div>
                <p className={`text-xs font-bold ${isActive ? c.text : "text-slate-500"}`}>
                  {String(i + 1).padStart(2, "0")}
                </p>
                <p className={`text-sm font-medium mt-0.5 ${isActive ? "text-white" : "text-slate-400"}`}>
                  {s.label}
                </p>

                {/* Arrow connector */}
                {i < PIPELINE_STAGES.length - 1 && (
                  <div className="absolute -right-2 top-1/2 -translate-y-1/2 text-slate-700 hidden lg:block z-10">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                )}
              </motion.button>
            );
          })}
        </div>

        {/* Active Stage Detail */}
        <div className="grid lg:grid-cols-2 gap-8">
          <AnimatePresence mode="wait">
            <motion.div
              key={stage.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              transition={{ duration: 0.3 }}
              className={`p-8 rounded-2xl border ${colors.border} bg-gradient-to-b from-slate-900/60 to-slate-900/20`}
            >
              <div className="flex items-center gap-3 mb-4">
                <div className={`p-2.5 rounded-xl ${colors.bg}`}>
                  <div className={colors.text}>{stage.icon}</div>
                </div>
                <div>
                  <p className={`text-xs font-mono ${colors.text}`}>Stage {activeStage + 1}</p>
                  <h3 className="text-xl font-bold text-white">{stage.label}</h3>
                </div>
              </div>

              <p className="text-slate-300 text-sm leading-relaxed mb-4">
                {stage.description}
              </p>
              <p className="text-slate-500 text-sm leading-relaxed mb-6">
                {stage.detail}
              </p>

              {/* Output */}
              <div className="p-4 rounded-lg bg-slate-950 border border-slate-800">
                <p className="text-[10px] text-slate-600 font-mono uppercase tracking-wider mb-2">Output</p>
                <p className="text-sm font-mono text-slate-300">{stage.output}</p>
              </div>
            </motion.div>
          </AnimatePresence>

          {/* Dedup Proof */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="p-8 rounded-2xl border border-slate-800 bg-slate-900/30"
          >
            <h3 className="text-lg font-bold text-white mb-2">Idempotent by Design</h3>
            <p className="text-slate-400 text-sm mb-6">
              Every file produces a unique packet_hash. Upload the same file again \u2014
              FAIM detects the duplicate and returns the cached result. Zero new nodes.
            </p>

            {/* First upload */}
            <div className="space-y-4">
              <div className="p-4 rounded-lg border border-emerald-500/20 bg-emerald-500/[0.04]">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-2 h-2 rounded-full bg-emerald-400" />
                  <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider">First Upload</span>
                </div>
                <p className="text-sm text-white font-mono">{DEDUP_EXAMPLE.first.file}</p>
                <p className="text-xs text-slate-500 font-mono mt-1">
                  packet_hash: {DEDUP_EXAMPLE.first.hash}
                </p>
                <p className="text-xs text-emerald-400 mt-1">\u2192 {DEDUP_EXAMPLE.first.result}</p>
              </div>

              {/* Arrow */}
              <div className="flex justify-center">
                <svg className="w-5 h-5 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                </svg>
              </div>

              {/* Second upload */}
              <div className="p-4 rounded-lg border border-amber-500/20 bg-amber-500/[0.04]">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-2 h-2 rounded-full bg-amber-400" />
                  <span className="text-xs font-bold text-amber-400 uppercase tracking-wider">Same File Again</span>
                </div>
                <p className="text-sm text-white font-mono">{DEDUP_EXAMPLE.second.file}</p>
                <p className="text-xs text-slate-500 font-mono mt-1">
                  packet_hash: {DEDUP_EXAMPLE.second.hash} <span className="text-amber-400">(match!)</span>
                </p>
                <p className="text-xs text-amber-400 mt-1">\u2192 {DEDUP_EXAMPLE.second.result}</p>
              </div>
            </div>

            {/* Events */}
            <div className="mt-6 p-4 rounded-lg bg-slate-950 border border-slate-800">
              <p className="text-[10px] text-slate-600 font-mono uppercase tracking-wider mb-2">Events Emitted</p>
              <div className="space-y-1 text-xs font-mono text-slate-400">
                <p><span className="text-cyan-400">INGEST_START</span> \u2192 PACKET_CREATED \u2192 ENCODED</p>
                <p>\u2192 <span className="text-emerald-400">WRITE_ATOMS_DONE</span> \u2192 INDEX_UPSERTED</p>
                <p>\u2192 <span className="text-purple-400">INGEST_PHASE_LATENCY</span></p>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
