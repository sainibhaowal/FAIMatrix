"use client";

import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { useState } from "react";
import Logo from "@/components/brand/Logo";

// ---------------------------------------------------------------------------
// Nav structure
// ---------------------------------------------------------------------------
const NAV_GROUPS = [
  {
    group: "Overview",
    items: [
      { id: "what-is-faim", label: "What is FAIM?" },
      { id: "current-state", label: "Current State" },
      { id: "quickstart", label: "Quick Start" },
      { id: "why-faim", label: "Why FAIM?" },
    ],
  },
  {
    group: "Core System",
    items: [
      { id: "architecture", label: "Architecture" },
      { id: "memory", label: "Memory System" },
      { id: "graph", label: "Knowledge Graph" },
      { id: "retrieval", label: "Retrieval Engine" },
      { id: "cortex", label: "FAIM Cortex" },
      { id: "cortex-runtime", label: "Cortex Runtime" },
    ],
  },
  {
    group: "Advanced ADI Layers",
    items: [
      { id: "canonical-semantics", label: "Canonical Semantics (P2)" },
      { id: "graph-diffusion", label: "Graph Diffusion (P3)" },
      { id: "reranker-v2", label: "Deterministic Reranker V2 (P4)" },
      { id: "scale-ann", label: "Scale & ANN (P5)" },
      { id: "multilingual", label: "Multilingual Bridges (P6)" },
      { id: "multimodal-no-ml", label: "Multimodal without ML (P7)" },
      { id: "domain-adaptation", label: "Domain Adaptation (P8)" },
      { id: "answer-synthesis", label: "Extractive Synthesis (P9)" },
    ],
  },
  {
    group: "Document & Extraction",
    items: [
      { id: "document-intel", label: "Document Intelligence" },
      { id: "ingestion", label: "Ingestion Pipeline" },
    ],
  },
  {
    group: "Platform",
    items: [
      { id: "fig-view", label: "FIG View" },
      { id: "billing", label: "Matrix Billing" },
      { id: "security", label: "Security" },
      { id: "benchmarks", label: "Engine Benchmarks" },
      { id: "deployment", label: "Deployment" },
      { id: "capabilities", label: "Full Capabilities" },
      { id: "roadmap", label: "Roadmap" },
    ],
  },
];

// ---------------------------------------------------------------------------
// Reusable components
// ---------------------------------------------------------------------------
function Card({
  title,
  children,
  color = "default",
}: {
  title: string;
  children: React.ReactNode;
  color?: string;
}) {
  const border =
    color === "cyan"
      ? "border-cyan-500/20 bg-cyan-500/[0.04]"
      : color === "purple"
        ? "border-purple-500/20 bg-purple-500/[0.04]"
        : color === "amber"
          ? "border-amber-500/20 bg-amber-500/[0.04]"
          : color === "emerald"
            ? "border-emerald-500/20 bg-emerald-500/[0.04]"
            : color === "red"
              ? "border-red-500/20 bg-red-500/[0.04]"
              : "border-slate-700/50 bg-slate-900/40";
  return (
    <div className={`rounded-2xl border p-5 ${border}`}>
      <h3 className="text-xs font-bold text-white mb-3 uppercase tracking-widest">
        {title}
      </h3>
      {children}
    </div>
  );
}

function Chip({
  children,
  color = "#22d3ee",
}: {
  children: string;
  color?: string;
}) {
  return (
    <span
      className="rounded-full px-2.5 py-0.5 text-[10px] font-mono border"
      style={{ color, borderColor: color + "44", background: color + "0d" }}
    >
      {children}
    </span>
  );
}

function Code({ children }: { children: string }) {
  return (
    <pre className="mt-3 rounded-xl bg-slate-950 border border-slate-800 p-4 text-[11px] font-mono text-cyan-300 overflow-x-auto leading-relaxed whitespace-pre">
      {children}
    </pre>
  );
}

function KV({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-4 py-1.5 border-b border-slate-800/50 last:border-0">
      <span className="text-slate-500 text-[11px] shrink-0">{label}</span>
      <span className="text-slate-300 text-[11px] font-mono text-right">
        {value}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section content panels
// ---------------------------------------------------------------------------

function SectionWhatIsFaim() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">What is FAIM?</h2>
        <p className="text-slate-400 leading-relaxed">
          FAIM (Fully Autonomous Intelligence Memory) is a deterministic,
          self-hostable memory, retrieval, and answer engine. It is not an LLM.
          It is not a vector database wrapper. It is a complete memory operating
          system built on pure mathematics.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="The Core Idea" color="cyan">
          <p className="text-sm text-slate-400 leading-relaxed">
            You upload documents. FAIM extracts every block of content, encodes
            it into a 256-dimensional deterministic vector using pure math (no
            neural network), connects blocks into a typed knowledge graph, and
            stores everything with SHA-256 fingerprints. When you query, FAIM
            retrieves the most relevant nodes, re-ranks them through 7 scoring
            components, and gives you citation-first answers — no external ML
            service required.
          </p>
        </Card>
        <Card title="Key Properties" color="purple">
          <ul className="space-y-2 text-sm text-slate-400">
            {[
              [
                "Zero ML",
                "No neural network in the core memory or retrieval path",
              ],
              [
                "Deterministic",
                "Same input always produces the same output, forever",
              ],
              [
                "Self-hostable",
                "Runs entirely on your infrastructure, no cloud dependency",
              ],
              [
                "Auditable",
                "Every node has a SHA-256 fingerprint + full provenance chain",
              ],
              [
                "Graph-native",
                "Opposition, inheritance, and semantic edges built-in from day one",
              ],
            ].map(([k, v]) => (
              <li key={k as string} className="flex gap-2">
                <span className="text-cyan-400 shrink-0 font-mono text-xs pt-0.5">
                  {k}:
                </span>
                <span>{v}</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card title="What FAIM Is Not" color="amber">
        <div className="grid md:grid-cols-3 gap-3 text-sm">
          {[
            [
              "Not an LLM",
              "FAIM does not generate text. It retrieves, ranks, and grounds answers in your own documents.",
            ],
            [
              "Not a vector DB",
              "A vector DB stores embeddings. FAIM also builds a knowledge graph, applies memory tiers, and re-ranks with 7 scoring components.",
            ],
            [
              "Not a RAG wrapper",
              "RAG wraps an LLM with retrieval. FAIM replaces the LLM dependency entirely — it can work without any language model.",
            ],
          ].map(([t, d]) => (
            <div key={t as string}>
              <p className="text-amber-400 font-mono text-xs mb-1">{t}</p>
              <p className="text-slate-500 text-xs leading-relaxed">{d}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function SectionCurrentState() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">Current State (May 2026)</h2>
        <p className="text-slate-400 leading-relaxed">
          FAIM has evolved into a production-grade cognitive infrastructure. The engine now features an 8M+ Omni-Lexicon, a 1M+ Semantic Registry, GPU-hardened 3D visualization, and a multi-tier Matrix subscription ecosystem.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="Latest Upgrades" color="cyan">
          <ul className="space-y-2 text-sm text-slate-400">
            {[
              "Deterministic Semantic Registry: 1M+ professional concepts with zero-ML overhead.",
              "Global Omni-Lexicon: 8M+ ConceptNet edges powering O(1) multi-lingual vocabulary expansion.",
              "GPU Hardened FIG View: Static asset registry eliminates rendering-induced crashes.",
              "Neural Pulse Trace: Real-time visualization of reasoning paths in the 3D globe.",
              "Memory Writeback Proposals: Human-in-the-loop safety for structural memory updates.",
              "FAIM Matrix Tiers: 4 professional subscription levels (Explorer to Matrix).",
            ].map((item) => (
              <li key={item} className="flex gap-2">
                <span className="text-cyan-400 shrink-0">→</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </Card>
        <Card title="Core Stability" color="purple">
          <ul className="space-y-2 text-sm text-slate-400">
            {[
              "256-dim Native Core remains deterministic and mathematically invariant.",
              "SHA-256 node fingerprinting ensures 100% auditable provenance.",
              "Elastic physics engine tuned for stable high-density graph interaction.",
              "Hot/Warm/Cold memory tiers automated for cost-efficient intelligence.",
            ].map((item) => (
              <li key={item} className="flex gap-2">
                <span className="text-purple-400 shrink-0">→</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  );
}

function SectionQuickStart() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">Quick Start</h2>
        <p className="text-slate-400 leading-relaxed">
          Get FAIM running and answer your first query in under 5 minutes.
        </p>
      </div>

      <Card title="Step 1 — Create an Account" color="cyan">
        <ol className="space-y-3">
          {[
            "Sign up at the Get Started page",
            "A knowledge graph is automatically created for your account",
            "You land on the Dashboard — this is your control centre",
          ].map((s, i) => (
            <li key={i} className="flex gap-3 text-sm text-slate-400">
              <span className="w-5 h-5 rounded-full bg-cyan-500/20 text-cyan-400 flex items-center justify-center text-xs shrink-0 font-mono">
                {i + 1}
              </span>
              {s}
            </li>
          ))}
        </ol>
      </Card>

      <Card title="Step 2 — Upload Your First Document" color="purple">
        <ol className="space-y-3">
          {[
            "Go to Dashboard → Storage tab",
            "Click Upload and select a PDF, DOCX, PPTX, XLSX, image, or code file",
            "FAIM extracts every block, builds the 256-dim vector, and adds nodes to your graph",
            "Status shows: processing → ready",
            "You can also Rebuild Memory Index after upload to refresh Representation V2 sidecars",
          ].map((s, i) => (
            <li key={i} className="flex gap-3 text-sm text-slate-400">
              <span className="w-5 h-5 rounded-full bg-purple-500/20 text-purple-400 flex items-center justify-center text-xs shrink-0 font-mono">
                {i + 1}
              </span>
              {s}
            </li>
          ))}
        </ol>
      </Card>

      <Card title="Step 3 — Run FAIM Cortex" color="emerald">
        <ol className="space-y-3">
          {[
            "Go to Dashboard → FAIM Cortex tab",
            "Type any question about the documents you uploaded",
            "FAIM retrieves the most relevant nodes, re-ranks them, and returns a grounded answer",
            "Every answer shows which document + page + section it came from",
            "Try asking: 'How many documents do I have?' to see the document inventory in action",
          ].map((s, i) => (
            <li key={i} className="flex gap-3 text-sm text-slate-400">
              <span className="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-xs shrink-0 font-mono">
                {i + 1}
              </span>
              {s}
            </li>
          ))}
        </ol>
      </Card>

      <Card title="Step 4 — Explore the Graph" color="amber">
        <ol className="space-y-3">
          {[
            "Go to Dashboard → FIG View tab",
            "Every node from your documents is visible as a graph",
            "Click any node to inspect its block_type, page, section, temperature (🔥/◆/❄), and connections",
            "Use the layout controls: Surface (all nodes), Neighborhood (K-hop), Timeline, Path",
            "Filter by node kind or edge kind using the legend panel on the right",
          ].map((s, i) => (
            <li key={i} className="flex gap-3 text-sm text-slate-400">
              <span className="w-5 h-5 rounded-full bg-amber-500/20 text-amber-400 flex items-center justify-center text-xs shrink-0 font-mono">
                {i + 1}
              </span>
              {s}
            </li>
          ))}
        </ol>
      </Card>
    </div>
  );
}

function SectionWhyFaim() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">Why FAIM?</h2>
        <p className="text-slate-400 leading-relaxed">
          Most knowledge systems are either raw vector databases (no graph, no
          structure) or LLM wrappers (hallucination-prone, non-auditable). FAIM
          occupies a fundamentally different category.
        </p>
      </div>

      <div className="rounded-2xl border border-slate-800 bg-slate-900/30 overflow-hidden">
        <div className="grid grid-cols-4 gap-0 px-4 py-3 border-b border-slate-800 bg-slate-900/60 text-[10px] font-bold uppercase tracking-widest text-slate-500">
          <span>Feature</span>
          <span>FAIM</span>
          <span>Vector DB</span>
          <span>LLM RAG</span>
        </div>
        {[
          ["Deterministic retrieval", "✅", "❌", "❌"],
          ["Zero ML core", "✅", "❌", "❌"],
          ["Graph edges (opposition, inheritance)", "✅", "❌", "❌"],
          ["SHA-256 node fingerprints", "✅", "❌", "❌"],
          ["Hot / warm / cold memory tiers", "✅", "❌", "❌"],
          ["Contradiction detection + suppression", "✅", "❌", "❌"],
          ["Self-hostable, no cloud required", "✅", "Partial", "❌"],
          ["Citation-first, page-grounded answers", "✅", "❌", "Partial"],
          ["Multi-column PDF, table, scanned OCR", "✅", "❌", "Partial"],
          ["Tenant isolation built-in", "✅", "Partial", "❌"],
          ["Idempotent ingestion (no duplicates)", "✅", "❌", "❌"],
          ["Graph scorecard: density, entropy, λ", "✅", "❌", "❌"],
        ].map(([f, a, b, c]) => (
          <div
            key={f as string}
            className="grid grid-cols-4 gap-0 px-4 py-2.5 border-b border-slate-800/50 last:border-0 hover:bg-slate-800/20 transition-colors"
          >
            <span className="text-sm text-slate-300">{f}</span>
            <span className="text-sm text-emerald-400 font-mono">{a}</span>
            <span className="text-sm text-slate-500 font-mono">{b}</span>
            <span className="text-sm text-slate-500 font-mono">{c}</span>
          </div>
        ))}
      </div>

      <Card title="Who FAIM Is For" color="cyan">
        <div className="grid md:grid-cols-2 gap-4 text-sm text-slate-400">
          <ul className="space-y-2">
            <li className="flex gap-2">
              <span className="text-cyan-400">→</span>Teams that need
              deterministic, auditable retrieval
            </li>
            <li className="flex gap-2">
              <span className="text-cyan-400">→</span>Organizations that cannot
              send data to cloud AI services
            </li>
            <li className="flex gap-2">
              <span className="text-cyan-400">→</span>Regulated industries
              (legal, healthcare, finance) requiring traceable answers
            </li>
          </ul>
          <ul className="space-y-2">
            <li className="flex gap-2">
              <span className="text-cyan-400">→</span>Research teams building
              explainable knowledge systems
            </li>
            <li className="flex gap-2">
              <span className="text-cyan-400">→</span>Any use case where "I need
              to verify that answer" matters
            </li>
            <li className="flex gap-2">
              <span className="text-cyan-400">→</span>Teams who want a memory
              system that doesn't drift over time
            </li>
          </ul>
        </div>
      </Card>
    </div>
  );
}

function SectionArchitecture() {
  const layers = [
    {
      label: "User / LLM / API Client",
      color: "#22d3ee",
      desc: "Any consumer: browser app, API call, or an LLM using FAIM as memory",
    },
    {
      label: "Query Engine  ·  RerankerV2  ·  Answer Synthesis",
      color: "#a78bfa",
      desc: "7-component scoring → proposition-aware reranking → citation-first answer",
    },
    {
      label: "Representation V2  ·  Sparse + Dense  ·  K-hop Diffusion",
      color: "#60a5fa",
      desc: "Sparse sidecars (word/phrase/entity/time/layout) + bounded graph diffusion",
    },
    {
      label: "Knowledge Graph  ·  Nodes · Edges · Opposition · Inheritance",
      color: "#34d399",
      desc: "Typed edges, hot/warm/cold tiers, opposition suppression, inheritance weighting",
    },
    {
      label: "256-dim Native Vectors  ·  SHA-256 Fingerprints  ·  Memory Tiers",
      color: "#fbbf24",
      desc: "Deterministic encoding: 240 n-gram dims + 16 text-stat dims, no neural net",
    },
    {
      label: "PostgreSQL  ·  Qdrant  ·  Redis  ·  Raw Blob Store",
      color: "#f87171",
      desc: "Storage substrate: relational graph, ANN index, query cache, raw files",
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">Architecture</h2>
        <p className="text-slate-400 leading-relaxed">
          FAIM is a layered stack. Each layer is independently verifiable and
          deterministic. No layer depends on a neural network or external ML
          service.
        </p>
      </div>

      <div className="rounded-2xl border border-slate-800 bg-slate-900/30 p-5">
        <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-4">
          System Stack — Top to Bottom
        </p>
        <div className="space-y-1.5">
          {layers.map((l, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -16 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.06 }}
              className="rounded-xl px-4 py-3"
              style={{
                background: l.color + "0d",
                border: `1px solid ${l.color}33`,
              }}
            >
              <div className="flex items-center justify-between gap-4">
                <span className="text-sm font-mono" style={{ color: l.color }}>
                  {l.label}
                </span>
                <span className="text-[10px] font-mono text-slate-600 shrink-0">
                  L{layers.length - 1 - i}
                </span>
              </div>
              <p className="text-[10px] text-slate-600 mt-1">{l.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        <Card title="Storage Layer (L0)" color="red">
          <ul className="space-y-1.5 text-[11px] text-slate-400">
            <li className="flex gap-2">
              <span className="text-slate-600">·</span>PostgreSQL — nodes,
              edges, repr_v2 sidecars
            </li>
            <li className="flex gap-2">
              <span className="text-slate-600">·</span>Qdrant — ANN approximate
              nearest-neighbor index
            </li>
            <li className="flex gap-2">
              <span className="text-slate-600">·</span>Redis — query result
              cache + hot node hints
            </li>
            <li className="flex gap-2">
              <span className="text-slate-600">·</span>Raw blob store — original
              uploaded files by SHA-256
            </li>
          </ul>
        </Card>
        <Card title="Memory Layer (L1–L2)" color="amber">
          <ul className="space-y-1.5 text-[11px] text-slate-400">
            <li className="flex gap-2">
              <span className="text-slate-600">·</span>256-dim native vectors
              (zero ML)
            </li>
            <li className="flex gap-2">
              <span className="text-slate-600">·</span>SHA-256 fingerprint per
              node
            </li>
            <li className="flex gap-2">
              <span className="text-slate-600">·</span>Hot / Warm / Cold
              automatic tiering
            </li>
            <li className="flex gap-2">
              <span className="text-slate-600">·</span>Idempotent upsert — no
              duplicate nodes
            </li>
            <li className="flex gap-2">
              <span className="text-slate-600">·</span>Sparse Repr V2 sidecars
              alongside dense vector
            </li>
          </ul>
        </Card>
        <Card title="Intelligence Layer (L3–L5)" color="cyan">
          <ul className="space-y-1.5 text-[11px] text-slate-400">
            <li className="flex gap-2">
              <span className="text-slate-600">·</span>7-component deterministic
              scoring
            </li>
            <li className="flex gap-2">
              <span className="text-slate-600">·</span>RerankerV2 —
              proposition-aware reranking
            </li>
            <li className="flex gap-2">
              <span className="text-slate-600">·</span>K-hop bounded graph
              diffusion
            </li>
            <li className="flex gap-2">
              <span className="text-slate-600">·</span>Answer synthesis —
              extractive, citation-first
            </li>
            <li className="flex gap-2">
              <span className="text-slate-600">·</span>Opposition suppression in
              ranking
            </li>
          </ul>
        </Card>
      </div>
    </div>
  );
}

function SectionMemory() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">Memory System</h2>
        <p className="text-slate-400 leading-relaxed">
          FAIM's core memory is built on 256-dimensional deterministic vectors
          with SHA-256 fingerprinting, automatic memory temperature
          classification, and cold pruning support.
        </p>
      </div>

      <Card title="256-Dimensional Native Vector" color="cyan">
        <p className="text-sm text-slate-400 mb-3 leading-relaxed">
          Every text block is encoded into a 256-dim vector using pure math — no
          neural network, no GPU, no model to download. Encoding has two
          components:
        </p>
        <div className="grid md:grid-cols-2 gap-3">
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
            <p className="text-xs font-mono text-cyan-400 mb-1.5">
              dims 0–239 — Character n-grams
            </p>
            <p className="text-[11px] text-slate-500 leading-relaxed">
              SHA-256 hash of character 2-grams and 3-grams, bucketed into 240
              dimensions. Captures morphological and lexical patterns without
              any vocabulary table.
            </p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
            <p className="text-xs font-mono text-cyan-400 mb-1.5">
              dims 240–255 — Text statistics
            </p>
            <p className="text-[11px] text-slate-500 leading-relaxed">
              Word count, sentence length, punctuation density, capitalization
              ratio, digit ratio, and other structural features. These 16 dims
              encode the shape and style of the block.
            </p>
          </div>
        </div>
      </Card>

      <Card title="SHA-256 Fingerprinting — Idempotency" color="emerald">
        <p className="text-sm text-slate-400 leading-relaxed mb-3">
          Every block is hashed with SHA-256 before storage. If you upload the
          same document twice, FAIM detects the matching{" "}
          <code className="text-emerald-400 font-mono text-xs">
            vector_hash
          </code>{" "}
          and increments{" "}
          <code className="text-emerald-400 font-mono text-xs">
            touch_count
          </code>{" "}
          instead of creating a duplicate node. The graph stays clean regardless
          of how many times files are re-uploaded.
        </p>
        <Code>{`vector_hash = SHA-256(content + anchor_json)

On ingest:
  if hash exists → UPDATE touch_count += 1
  else           → INSERT new node`}</Code>
      </Card>

      <Card title="Hot / Warm / Cold Memory Tiers" color="amber">
        <p className="text-sm text-slate-400 mb-3">
          Every node is automatically classified into one of three memory
          temperature tiers based on access recency and frequency:
        </p>
        <div className="space-y-3">
          {[
            {
              tier: "🔥 HOT",
              rule: "last_access within 7 days",
              effect:
                "Highest retrieval priority — most recently used knowledge",
              color: "#f97316",
            },
            {
              tier: "◆ WARM",
              rule: "last_access within 30 days  OR  touch_count ≥ 5",
              effect: "Active working memory — still in regular use",
              color: "#fbbf24",
            },
            {
              tier: "❄ COLD",
              rule: "last_access > 90 days  OR  never accessed + age > 7 days",
              effect: "Candidate for pruning — forgotten knowledge",
              color: "#64748b",
            },
          ].map((t) => (
            <div
              key={t.tier}
              className="rounded-xl border border-slate-800 bg-slate-950/40 px-4 py-3"
            >
              <div className="flex items-center gap-3 mb-1">
                <span
                  className="font-mono text-sm font-bold"
                  style={{ color: t.color }}
                >
                  {t.tier}
                </span>
                <code className="text-[10px] text-slate-500 font-mono">
                  {t.rule}
                </code>
              </div>
              <p className="text-[11px] text-slate-500">{t.effect}</p>
            </div>
          ))}
        </div>
      </Card>

      <Card title="Cold Pruning" color="default">
        <p className="text-sm text-slate-400 leading-relaxed mb-3">
          Level-0 atom nodes that have never been accessed (
          <code className="text-slate-300 font-mono text-xs">
            touch_count = 0
          </code>
          ,{" "}
          <code className="text-slate-300 font-mono text-xs">
            last_access = null
          </code>
          ) and are older than the cold threshold (default 90 days) can be
          deleted to reclaim space.
        </p>
        <div className="grid md:grid-cols-2 gap-3">
          <div className="rounded-xl border border-slate-800 bg-slate-950/40 px-3 py-2.5">
            <p className="text-xs font-mono text-slate-400 mb-1">
              Dry-run preview
            </p>
            <p className="text-[11px] text-slate-600">
              Shows exactly how many nodes qualify for pruning. No data deleted.
              Use this first.
            </p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/40 px-3 py-2.5">
            <p className="text-xs font-mono text-slate-400 mb-1">
              Live pruning
            </p>
            <p className="text-[11px] text-slate-600">
              Deletes qualifying cold nodes, bumps graph version, returns count
              of nodes removed.
            </p>
          </div>
        </div>
        <p className="text-[10px] text-slate-600 mt-3 font-mono">
          Both options are in Dashboard → Storage → Maintenance. Long-term nodes
          are always skipped.
        </p>
      </Card>

      <Card title="Long-term Memory Flag" color="emerald">
        <p className="text-sm text-slate-400 leading-relaxed mb-3">
          Any node can be marked{" "}
          <code className="text-emerald-400 font-mono text-xs">
            long_term = true
          </code>{" "}
          to protect it from cold pruning permanently — regardless of age,
          touch_count, or last_access. Use this for nodes that represent
          foundational facts you never want deleted.
        </p>
        <div className="grid md:grid-cols-2 gap-3">
          <div className="rounded-xl border border-slate-800 bg-slate-950/40 px-3 py-2.5">
            <p className="text-xs font-mono text-emerald-400 mb-1">
              How to set it
            </p>
            <p className="text-[11px] text-slate-500">
              Open FIG View → click any node → scroll to "Long-term Memory" at
              the bottom of the inspector → click "Set Long-term". Takes effect
              immediately via API.
            </p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/40 px-3 py-2.5">
            <p className="text-xs font-mono text-emerald-400 mb-1">
              What it does
            </p>
            <p className="text-[11px] text-slate-500">
              The cold prune endpoint adds{" "}
              <code className="font-mono text-[10px] text-slate-400">
                long_term = false
              </code>{" "}
              to its WHERE clause. Protected nodes are never in the candidate
              set, even in live prune mode.
            </p>
          </div>
        </div>
      </Card>

      <Card title="Topic Clustering — K-means on v_native" color="purple">
        <p className="text-sm text-slate-400 leading-relaxed mb-3">
          FAIM can group all nodes into topic clusters using deterministic
          k-means++ on v_native vectors. Once clusters are computed, every query
          automatically scopes recall to the top-2 matching clusters before
          doing a full cosine scan — improving speed and precision as the graph
          grows.
        </p>
        <div className="space-y-2">
          {[
            [
              "Algorithm",
              "k-means++ initialisation, cosine distance, L2-normalised centroids",
            ],
            [
              "K selection",
              "Auto: sqrt(N/2) clamped to [2, 20]. Or pass k= explicitly.",
            ],
            [
              "Determinism",
              "RNG seeded from SHA-256 of graph_id — same graph always produces same clusters",
            ],
            ["Convergence", "Max 50 iterations or until centroids stop moving"],
            [
              "Query scoping",
              "At query time: find top-2 cluster centres, filter recall to those clusters (falls back to full scan if too few results)",
            ],
            [
              "How to run",
              "Dashboard → Storage → Maintenance → Run Topic Clustering",
            ],
          ].map(([k, v]) => (
            <div
              key={k}
              className="flex gap-3 py-1 border-b border-slate-800/40 last:border-0"
            >
              <span className="text-slate-500 text-[11px] shrink-0 w-28">
                {k}
              </span>
              <span className="text-slate-300 text-[11px]">{v}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function SectionGraph() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">Knowledge Graph</h2>
        <p className="text-slate-400 leading-relaxed">
          FAIM's graph is the intelligence layer. Nodes hold atomic facts. Edges
          define relationships. The graph grows with every document ingested and
          every query answered.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="Node Structure" color="cyan">
          <Code>{`node_id      UUID — unique identifier
graph_id     String — tenant graph scope
vector_hash  SHA-256 content fingerprint
raw_id       UUID — source file reference
block_id     String — block within source
anchor_json  {page, section, block_type,
              column, row_start, doc_type}
level        0 = atom, 1+ = macro/parent
touch_count  Times retrieved in queries
last_access  ISO datetime of last query hit
created_at   ISO datetime of first ingest`}</Code>
        </Card>

        <Card title="Node Types" color="purple">
          <div className="space-y-3 text-sm text-slate-400">
            <div>
              <p className="text-purple-300 font-mono text-xs mb-1">
                atom (level = 0)
              </p>
              <p>
                Leaf node. Represents one extracted block of content — a
                paragraph, table, code snippet, or image caption. This is what
                FAIM retrieves.
              </p>
            </div>
            <div>
              <p className="text-purple-300 font-mono text-xs mb-1">
                macro (level ≥ 1)
              </p>
              <p>
                Aggregated parent node. Groups multiple atoms that belong to the
                same section or document. Inheritance edges flow from macro →
                atom.
              </p>
            </div>
          </div>
        </Card>
      </div>

      <Card title="Edge Types" color="emerald">
        <div className="space-y-4">
          {[
            {
              type: "inheritance",
              color: "#60a5fa",
              desc: "Parent → child concept flow. When a macro node is retrieved, its children get a proportional score boost. Used to model document hierarchy: document → section → paragraph.",
              rule: "Directed, weighted, additive",
            },
            {
              type: "opposition (antisymmetric)",
              color: "#f87171",
              desc: "When two nodes contradict each other (temporal conflict, direct contradiction), FAIM adds a bidirectional opposition edge. The lower-confidence node is suppressed in retrieval scoring automatically.",
              rule: "Bidirectional, suppressive, deterministic",
            },
            {
              type: "semantic",
              color: "#a78bfa",
              desc: "Related meaning, co-occurrence, temporal proximity, or domain-linked concepts identified via PMI (Pointwise Mutual Information) and rule-based patterns. Used in K-hop expansion during retrieval.",
              rule: "Bidirectional, weighted by PMI score",
            },
            {
              type: "causal",
              color: "#fbbf24",
              desc: "Directed cause → effect relation. Detected from causal language patterns in the document text. Tells the retrieval engine that one fact caused another.",
              rule: "Directed, single-hop priority",
            },
          ].map((e) => (
            <div
              key={e.type}
              className="flex gap-3 rounded-xl border border-slate-800 bg-slate-950/40 px-4 py-3"
            >
              <span className="w-16 shrink-0">
                <span
                  className="text-xs font-mono font-bold"
                  style={{ color: e.color }}
                >
                  {e.type}
                </span>
              </span>
              <div className="min-w-0">
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  {e.desc}
                </p>
                <p className="text-[10px] text-slate-600 font-mono mt-1">
                  {e.rule}
                </p>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card title="Graph Scorecard — Computed from Topology" color="default">
        <div className="grid md:grid-cols-3 gap-3">
          {[
            {
              metric: "D — Density",
              formula: "Edges ÷ (Nodes × (Nodes−1))",
              range: "0 = no connections · 1 = complete graph",
              color: "#22d3ee",
            },
            {
              metric: "H — Entropy",
              formula: "Shannon entropy of edge kinds (bits)",
              range: "0 = all same · log₂(kinds) = maximum",
              color: "#a78bfa",
            },
            {
              metric: "λ — Spectral Radius",
              formula: "Largest eigenvalue (power iteration)",
              range: "Higher = tighter clustering · Lower = sparse",
              color: "#34d399",
            },
          ].map((s) => (
            <div
              key={s.metric}
              className="rounded-xl border border-slate-800 bg-slate-950/40 p-3"
            >
              <p
                className="text-xs font-mono font-bold mb-1"
                style={{ color: s.color }}
              >
                {s.metric}
              </p>
              <p className="text-[10px] text-slate-500 mb-1">{s.formula}</p>
              <p className="text-[9px] text-slate-600">{s.range}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function SectionRetrieval() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">Retrieval Engine</h2>
        <p className="text-slate-400 leading-relaxed">
          FAIM runs a multi-stage retrieval pipeline. Every query hits all data
          stores, scores through 7 deterministic components, and re-ranks before
          synthesizing a grounded answer.
        </p>
      </div>

      <Card title="Retrieval Pipeline — Step by Step" color="cyan">
        <div className="space-y-2 mt-1">
          {[
            {
              step: "1",
              label: "Query arrives",
              detail:
                "Text query is normalized: Porter stemming, stop-word removal, entity token extraction",
              color: "#22d3ee",
            },
            {
              step: "2",
              label: "Cache check",
              detail:
                "Redis: if identical query was run before, return cached result immediately",
              color: "#34d399",
            },
            {
              step: "3",
              label: "PostgreSQL recall",
              detail:
                "Brute-force cosine similarity scan against all v_native vectors for the graph_id",
              color: "#60a5fa",
            },
            {
              step: "4",
              label: "Qdrant ANN",
              detail:
                "Approximate nearest-neighbor for large graphs, merged with PostgreSQL brute-force results",
              color: "#a78bfa",
            },
            {
              step: "5",
              label: "7-component scoring",
              detail:
                "Cosine similarity · Novelty · Opposition · Redundancy · Recency · Usage frequency · Level penalty",
              color: "#fbbf24",
            },
            {
              step: "6",
              label: "RerankerV2",
              detail:
                "Proposition-aware deterministic reranking: scores adjusted by block_type weight, section match, and graph neighbourhood",
              color: "#f97316",
            },
            {
              step: "7",
              label: "Answer synthesis",
              detail:
                "Top-N nodes → extractive answer with citations (filename · page · section per node)",
              color: "#34d399",
            },
          ].map((s) => (
            <div key={s.step} className="flex gap-3 items-start">
              <span
                className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0"
                style={{ background: s.color + "22", color: s.color }}
              >
                {s.step}
              </span>
              <div className="flex-1 rounded-xl border border-slate-800 bg-slate-950/40 px-3 py-2">
                <p className="text-xs font-mono font-bold text-white">
                  {s.label}
                </p>
                <p className="text-[10px] text-slate-500 mt-0.5">{s.detail}</p>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card title="Representation V2 — Sparse Sidecars" color="purple">
        <p className="text-sm text-slate-400 mb-3">
          Alongside the 256-dim dense vector, every node has a set of sparse
          channels computed by Representation V2. These enable lexically-rich
          matching on top of vector similarity.
        </p>
        <div className="grid md:grid-cols-2 gap-2">
          {[
            [
              "word_counts",
              "Porter-stemmed token buckets — handles morphological variants",
            ],
            [
              "phrase_counts",
              "2-gram phrase frequency buckets — matches multi-word expressions",
            ],
            [
              "skip_counts",
              "Skip-gram patterns — long-range co-occurrence capture",
            ],
            [
              "entity_tokens",
              "Emails, URLs, UUIDs, identifiers, phone numbers",
            ],
            ["time_tokens", "Dates, years, quarters, temporal markers"],
            ["layout_tokens", "block_type + page + section encoded as tokens"],
          ].map(([k, v]) => (
            <div
              key={k}
              className="rounded-lg border border-slate-800 bg-slate-950/40 px-3 py-2"
            >
              <p className="text-[10px] font-mono text-purple-400 mb-0.5">
                {k}
              </p>
              <p className="text-[10px] text-slate-600">{v}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function SectionCortex() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">FAIM Cortex</h2>
        <p className="text-slate-400 leading-relaxed">
          The high-level reasoning layer that transforms graph retrieval into structured prose and actionable insights.
        </p>
      </div>

      <Card title="1M+ Semantic Alias Engine" color="cyan">
        <p className="text-sm text-slate-400 leading-relaxed mb-4">
          FAIM Cortex uses a deterministic registry of over 1,000,000 professional concepts to classify intent without the latency or drift of a traditional LLM.
        </p>
        <div className="grid md:grid-cols-2 gap-3 mb-6">
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
            <p className="text-xs font-mono text-cyan-400 mb-1.5">Deterministic Routing</p>
            <p className="text-[11px] text-slate-500 leading-relaxed">
              Keywords and concepts are mapped to 8 core cognitive tasks (Timeline, Contradiction, etc.) using high-speed dictionary hashing.
            </p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
            <p className="text-xs font-mono text-cyan-400 mb-1.5">Zero-Latency Classification</p>
            <p className="text-[11px] text-slate-500 leading-relaxed">
              Avoids the 2-5 second "thought" delay of LLMs. Routing happens in &lt;10ms.
            </p>
          </div>
        </div>

        <div className="p-4 rounded-xl border border-cyan-500/10 bg-cyan-500/[0.02]">
          <p className="text-xs font-bold text-cyan-400 uppercase tracking-widest mb-3">Registry Technical Spec</p>
          <ul className="grid grid-cols-2 gap-x-6 gap-y-2 text-[10px] text-slate-500 font-mono">
            <li className="flex justify-between"><span>Dictionary Hashing</span><span className="text-slate-300">O(1) complexity</span></li>
            <li className="flex justify-between"><span>Total Concepts</span><span className="text-slate-300">1,024,000+</span></li>
            <li className="flex justify-between"><span>Collision Resistance</span><span className="text-slate-300">SHA-256 gated</span></li>
            <li className="flex justify-between"><span>Search Strategy</span><span className="text-slate-300">Trie-based prefix</span></li>
            <li className="flex justify-between"><span>Compute Requirement</span><span className="text-slate-300">&lt; 25MB RAM</span></li>
            <li className="flex justify-between"><span>Availability</span><span className="text-slate-300">100% Offline</span></li>
          </ul>
        </div>
      </Card>

      <Card title="Memory Writeback Proposals" color="amber">
        <p className="text-sm text-slate-400 leading-relaxed">
          Safety first: Cortex never writes directly to permanent memory. Instead, it generates <strong>Proposals</strong>. These appear as pending nodes in the FIG View, requiring your explicit approval before they are committed to the long-term knowledge graph.
        </p>
      </Card>
    </div>
  );
}

function SectionCortexRuntime() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">Cortex Runtime Architecture</h2>
        <p className="text-slate-400 leading-relaxed">
          The stateful control loop above memory retrieval. It classifies requests, runs parallel reasoning branches, and synthesizes answers.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="Runtime Phases" color="cyan">
          <ul className="space-y-2 text-xs text-slate-400">
            <li><strong>Turn Controller:</strong> Classifies intent into 8 cognitive modes using the 1M+ Registry.</li>
            <li><strong>Parallel Branches:</strong> Simultaneous recall, timeline, and contradiction analysis.</li>
            <li><strong>Reducer:</strong> Merges branch outputs into a unified brain state.</li>
            <li><strong>Narrator:</strong> Produces the final prose answer with citations.</li>
          </ul>
        </Card>

        <Card title="Cognitive Modes (The 1M+ Engine)" color="emerald">
          <div className="overflow-hidden rounded-lg border border-slate-800 bg-slate-950/40">
            <table className="w-full text-[10px] text-left">
              <thead className="bg-slate-900/50 text-slate-500 uppercase tracking-tighter">
                <tr>
                  <th className="px-3 py-2">Mode</th>
                  <th className="px-3 py-2">Focus</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                <tr><td className="px-3 py-2 text-cyan-400 font-bold">TIMELINE</td><td className="px-3 py-2 text-slate-400">Chronological event sequencing</td></tr>
                <tr><td className="px-3 py-2 text-red-400 font-bold">CONTRADICTION</td><td className="px-3 py-2 text-slate-400">Conflict detection & resolution</td></tr>
                <tr><td className="px-3 py-2 text-purple-400 font-bold">CONSOLIDATE</td><td className="px-3 py-2 text-slate-400">Fragmented data merging</td></tr>
                <tr><td className="px-3 py-2 text-blue-400 font-bold">PROVENANCE</td><td className="px-3 py-2 text-slate-400">Full evidence lineage tracing</td></tr>
                <tr><td className="px-3 py-2 text-amber-400 font-bold">INVESTIGATE</td><td className="px-3 py-2 text-slate-400">Deep 24-hop causal analysis</td></tr>
              </tbody>
            </table>
          </div>
        </Card>
        <Card title="Safety & Stability" color="purple">
          <ul className="space-y-2 text-xs text-slate-400">
            <li>No raw chain-of-thought storage (structured only).</li>
            <li>Deterministic results for identical graph states.</li>
            <li>Human-in-the-loop memory persistence.</li>
          </ul>
        </Card>
      </div>

      <Card title="24-Hop Reasoning Spec" color="indigo">
        <div className="grid md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <p className="text-sm text-slate-400 leading-relaxed">
              FAIM Cortex traverses the graph substrate using a bounded diffusion strategy. Every hop is a semantic junction where the engine re-evaluates the evidence context.
            </p>
            <div className="flex gap-4">
              <div className="flex-1 p-3 rounded-lg border border-indigo-500/10 bg-indigo-500/[0.02]">
                <p className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest mb-1">Max Hops</p>
                <p className="text-xl font-bold text-white">24</p>
              </div>
              <div className="flex-1 p-3 rounded-lg border border-indigo-500/10 bg-indigo-500/[0.02]">
                <p className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest mb-1">Max Breadth</p>
                <p className="text-xl font-bold text-white">5</p>
              </div>
            </div>
          </div>
          <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/40">
            <p className="text-xs font-bold text-indigo-400 uppercase tracking-widest mb-3">Diffusion Parameters</p>
            <ul className="space-y-2 text-[10px] text-slate-500 font-mono">
              <li className="flex justify-between"><span>Decay Factor</span><span className="text-slate-300">0.85 per hop</span></li>
              <li className="flex justify-between"><span>Convergence Threshold</span><span className="text-slate-300">0.05 residual</span></li>
              <li className="flex justify-between"><span>Inference Path</span><span className="text-slate-300">Directed Acyclic</span></li>
              <li className="flex justify-between"><span>Provenance</span><span className="text-slate-300">Full-Chain Citations</span></li>
            </ul>
          </div>
        </div>
      </Card>

      <Card title="Reasoning Depth (What is a Hop?)" color="cyan">
        <div className="space-y-4">
          <p className="text-sm text-slate-400 leading-relaxed">
            In FAIM, a <strong>Hop</strong> is a single semantic step between two nodes. While traditional AI only looks at immediate neighbors, FAIM's <strong>Neural Tier</strong> can traverse up to 24 steps in a single reasoning turn.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/40">
              <p className="text-xs font-bold text-cyan-400 mb-2 uppercase tracking-widest">1-4 Hops</p>
              <p className="text-[10px] text-slate-500">Surface-level retrieval. Answers "Who", "What", and "When".</p>
            </div>
            <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/40">
              <p className="text-xs font-bold text-purple-400 mb-2 uppercase tracking-widest">5-12 Hops</p>
              <p className="text-[10px] text-slate-500">Deep synthesis. Connects documents across different folders and dates.</p>
            </div>
            <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/40">
              <p className="text-xs font-bold text-amber-400 mb-2 uppercase tracking-widest">13-24 Hops</p>
              <p className="text-[10px] text-slate-500">Full investigation. Answers "Why" by tracing complex causal chains.</p>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}

function SectionFigView() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">FIG View</h2>
        <p className="text-slate-400 leading-relaxed">
          Professional-grade 3D visualization for exploring complex cognitive landscapes.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="Neural Pulse Interaction" color="purple">
          <p className="text-sm text-slate-400 leading-relaxed">
            As Cortex reasons, you see it. Neural pulses trace the paths of evidence through your graph in real-time. We've optimized the interaction by making visual glow layers <strong>Raycast-Invisible</strong>, ensuring that you can always grab and "stretch" nodes with 100% native elasticity.
          </p>
        </Card>

        <Card title="GPU Resource Hardening" color="red">
          <ul className="space-y-2 text-xs text-slate-400">
            <li className="flex gap-2"><span className="text-red-400">→</span><strong>Static Asset Registry:</strong> Reuses 3D geometries and materials to eliminate memory leaks.</li>
            <li className="flex gap-2"><span className="text-red-400">→</span><strong>Render Loop Memoization:</strong> Prevents unnecessary re-renders during high-density graph manipulation.</li>
            <li className="flex gap-2"><span className="text-red-400">→</span><strong>Gravitational Anchor:</strong> Physics constants tuned (centerStrength: 0.5) to keep atoms from drifting during interaction.</li>
          </ul>
        </Card>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="Canvas — Visualization Modes" color="cyan">
          <div className="space-y-3 text-sm text-slate-400">
            {[
              { mode: "Surface", desc: "Default view showing up to 500 nodes." },
              { mode: "Neighborhood", desc: "K-hop expansion from a selected node." },
              { mode: "Timeline", desc: "Nodes arranged by creation time." },
              { mode: "Path", desc: "The shortest semantic path connecting two nodes." },
              { mode: "Analyze", desc: "Full graph with live scorecard (density, entropy)." },
            ].map((m) => (
              <div key={m.mode}>
                <p className="text-cyan-400 font-mono text-xs">{m.mode}</p>
                <p className="text-[11px] text-slate-500">{m.desc}</p>
              </div>
            ))}
          </div>
        </Card>

        <Card title="Canvas — Color Modes" color="purple">
          <div className="space-y-3 text-sm text-slate-400">
            {[
              { mode: "By state", desc: "Colors nodes by memory state (hot/warm/cold)." },
              { mode: "By frequency", desc: "Brighter = more touch_count (retrieved more often)." },
              { mode: "By temporal order", desc: "Spectrum from oldest to newest." },
              { mode: "By lineage depth", desc: "Darker = deeper ancestry (more parent hops)." },
            ].map((m) => (
              <div key={m.mode}>
                <p className="text-purple-400 font-mono text-xs">{m.mode}</p>
                <p className="text-[11px] text-slate-500">{m.desc}</p>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

function SectionBilling() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">Matrix Billing</h2>
        <p className="text-slate-400 leading-relaxed">
          FAIM is tiered by cognitive capacity (Nodes and Hops) rather than token counts.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        {[
          { name: "Explorer", desc: "1,000 Nodes, 1-Hop reasoning. Free forever." },
          { name: "Architect", desc: "10,000 Nodes, 4-Hop reasoning. Includes Snapshots." },
          { name: "Neural", desc: "100,000 Nodes, 24-Hop reasoning. Cross-graph synthesis." },
          { name: "Matrix", desc: "Unlimited. Private memory shards and dedicated workers." }
        ].map(tier => (
          <Card key={tier.name} title={tier.name} color={tier.name === "Neural" ? "purple" : "default"}>
            <p className="text-xs text-slate-400">{tier.desc}</p>
          </Card>
        ))}
      </div>
    </div>
  );
}

function SectionDocIntel() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">
          Document Intelligence
        </h2>
        <p className="text-slate-400 leading-relaxed">
          FAIM Native extractor handles all major document formats with zero ML
          dependencies. Every tool used is a deterministic library — PyMuPDF,
          python-docx, openpyxl, python-pptx, Tesseract.
        </p>
      </div>

      <Card title="PDF — Multi-column, Tables, and Scanned" color="red">
        <div className="grid md:grid-cols-2 gap-5 text-sm text-slate-400">
          <div>
            <p className="text-red-400 font-mono text-xs mb-2">Text PDF</p>
            <ul className="space-y-1.5">
              {[
                "Multi-column layout via x-coordinate gap analysis",
                "Table extraction using PyMuPDF find_tables()",
                "Double-extraction guard: table regions not re-extracted as text",
                "Page number anchored on every extracted block",
                "Column position (left/right/centre) stored in anchor_json",
              ].map((f) => (
                <li key={f} className="flex gap-2">
                  <span className="text-emerald-400 shrink-0 text-xs pt-0.5">
                    ✓
                  </span>
                  {f}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-amber-400 font-mono text-xs mb-2">
              Scanned PDF (Image-only pages)
            </p>
            <ul className="space-y-1.5">
              {[
                "Auto-detect pure image pages (no extractable text)",
                "Render at 300 DPI (up from 180 — better OCR accuracy)",
                "Minimum 2000px width upscale before OCR",
                "Autocontrast + sharpen preprocessing",
                "Tesseract PSM 3 — automatic layout detection",
                "Paragraph break preservation in output",
              ].map((f) => (
                <li key={f} className="flex gap-2">
                  <span className="text-emerald-400 shrink-0 text-xs pt-0.5">
                    ✓
                  </span>
                  {f}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </Card>

      <div className="grid md:grid-cols-3 gap-4">
        <Card title="DOCX Support" color="cyan">
          <ul className="space-y-1.5 text-[11px] text-slate-400">
            {[
              "Section heading tracking",
              "Table header row detection",
              "Paragraph and table block separation",
              "Section anchor stored per block",
              "python-docx — zero ML",
            ].map((f) => (
              <li key={f} className="flex gap-2">
                <span className="text-emerald-400 shrink-0">✓</span>
                {f}
              </li>
            ))}
          </ul>
        </Card>
        <Card title="PPTX Support" color="purple">
          <ul className="space-y-1.5 text-[11px] text-slate-400">
            {[
              "Shapes sorted by position (top, left)",
              "Text boxes and table shapes extracted",
              "Speaker notes extracted as separate block",
              "Slide number anchoring per block",
              "python-pptx — zero ML",
            ].map((f) => (
              <li key={f} className="flex gap-2">
                <span className="text-emerald-400 shrink-0">✓</span>
                {f}
              </li>
            ))}
          </ul>
        </Card>
        <Card title="XLSX Support" color="emerald">
          <ul className="space-y-1.5 text-[11px] text-slate-400">
            {[
              "data_only=True — computed cell values",
              "Header row heuristic detection",
              "Sheet name anchoring per block",
              "Row start/end range stored in anchor",
              "openpyxl — zero ML",
            ].map((f) => (
              <li key={f} className="flex gap-2">
                <span className="text-emerald-400 shrink-0">✓</span>
                {f}
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card
        title="Block Anchor — What Gets Stored Per Extracted Block"
        color="default"
      >
        <p className="text-sm text-slate-400 mb-3">
          Every extracted block carries a full structural anchor in the graph
          node. This anchor is used in retrieval, display, and FIG View
          inspection.
        </p>
        <div className="grid md:grid-cols-2 gap-1">
          {[
            ["block_type", "text · table · code · image · heading"],
            ["doc_type", "pdf · docx · pptx · xlsx · image · code"],
            ["page", "Page number (PDFs) or slide number (PPTX)"],
            ["section", "Document section heading at time of extraction"],
            ["column", "Column position in multi-column layout"],
            ["row_start / row_end", "Table row range (XLSX, table blocks)"],
            ["char_start / char_end", "Character offset within page text"],
            ["raw_id", "Reference to original uploaded file blob"],
          ].map(([k, v]) => (
            <KV key={k} label={k} value={v} />
          ))}
        </div>
      </Card>
    </div>
  );
}

function SectionIngestion() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">
          Ingestion Pipeline
        </h2>
        <p className="text-slate-400 leading-relaxed">
          Every document goes through the same deterministic pipeline. Nothing
          is lost between upload and retrieval. Every block preserves full
          structural metadata.
        </p>
      </div>

      <Card title="Pipeline Stages" color="purple">
        <div className="space-y-2 mt-1">
          {[
            {
              label: "Upload",
              color: "#22d3ee",
              detail:
                "File received, stored in raw blob store with SHA-256 packet_hash",
            },
            {
              label: "Extract",
              color: "#60a5fa",
              detail:
                "FAIM Native extractor parses format: multi-column, tables, OCR for images",
            },
            {
              label: "Block",
              color: "#a78bfa",
              detail:
                "Content split into EvidenceBlocks: content + anchor_json + block_type",
            },
            {
              label: "Vectorize",
              color: "#34d399",
              detail:
                "256-dim native vector computed: 240 n-gram dims + 16 text-stat dims",
            },
            {
              label: "Repr V2",
              color: "#fbbf24",
              detail:
                "Sparse sidecars computed: word/phrase/skip/entity/time/layout",
            },
            {
              label: "Upsert",
              color: "#f97316",
              detail:
                "SHA-256 hash checked: if match → increment touch_count, else insert",
            },
            {
              label: "Graph",
              color: "#f87171",
              detail:
                "Edges created: inheritance (doc→section→block) + opposition detection",
            },
            {
              label: "Qdrant Sync",
              color: "#a78bfa",
              detail:
                "Node upserted into ANN index for approximate nearest-neighbor queries",
            },
          ].map((s, i) => (
            <div key={s.label} className="flex gap-3 items-start">
              <span
                className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0"
                style={{ background: s.color + "22", color: s.color }}
              >
                {i + 1}
              </span>
              <div className="flex-1 rounded-xl border border-slate-800 bg-slate-950/40 px-3 py-2">
                <p
                  className="text-xs font-mono font-bold"
                  style={{ color: s.color }}
                >
                  {s.label}
                </p>
                <p className="text-[10px] text-slate-500 mt-0.5">{s.detail}</p>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card title="Rebuild Memory Index" color="cyan">
        <p className="text-sm text-slate-400 leading-relaxed mb-3">
          After uploading documents, you can trigger a Representation V2 rebuild
          from the Storage maintenance panel. This re-computes all sparse
          sidecars (word/phrase/entity/time/layout channels) for nodes that were
          ingested before Repr V2 was enabled, or after a pipeline update.
        </p>
        <div className="grid md:grid-cols-3 gap-2 text-[10px]">
          {[
            ["files_scanned", "Total files checked in the graph"],
            [
              "matched_nodes",
              "Nodes that already had matching repr_v2 entries",
            ],
            [
              "updated / inserted",
              "Sidecars that were refreshed or newly created",
            ],
          ].map(([k, v]) => (
            <div
              key={k}
              className="rounded-lg border border-slate-800 bg-slate-950/40 px-2.5 py-2"
            >
              <p className="font-mono text-cyan-400 mb-0.5">{k}</p>
              <p className="text-slate-600">{v}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function SectionSecurity() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">Security</h2>
        <p className="text-slate-400 leading-relaxed">
          FAIM is designed for regulated, auditable, and air-gapped
          environments. Every design decision prioritizes data integrity, tenant
          isolation, and zero-trust storage.
        </p>
      </div>

      <Card title="Cryptographic Integrity" color="emerald">
        <div className="space-y-2 text-sm text-slate-400">
          {[
            [
              "vector_hash per node",
              "SHA-256 of content + anchor_json. Detects any tampering with a node after ingestion.",
            ],
            [
              "packet_hash per file",
              "SHA-256 of raw file bytes stored at upload time. Detects file-level tampering.",
            ],
            [
              "Graph version counter",
              "Bumped on every mutation (insert, delete, edge change). Full audit trail of graph state.",
            ],
            [
              "Idempotent writes",
              "Duplicate data never enters the graph — SHA-256 collision detection before every insert.",
            ],
            [
              "Inheritance + boundedness checks",
              "Graph invariant checks run after mutations to keep graph structure valid.",
            ],
          ].map(([k, v]) => (
            <div key={k as string} className="flex gap-3">
              <span className="text-emerald-400 font-mono text-xs shrink-0 pt-0.5 w-36">
                {k}
              </span>
              <span className="text-slate-500 text-[11px]">{v}</span>
            </div>
          ))}
        </div>
      </Card>

      <Card title="Tenant Isolation" color="cyan">
        <div className="space-y-2 text-sm text-slate-400">
          {[
            [
              "tenant_id on every node",
              "All database queries filter by tenant_id. Cross-tenant reads are structurally impossible.",
            ],
            [
              "graph_id scoping",
              "Each user or team has their own graph_id within their tenant. Graphs are isolated by default.",
            ],
            [
              "JWT-based auth",
              "Every API request carries a JWT. graph_id is derived from the verified token — never from user input.",
            ],
            [
              "Storage API enforcement",
              "graph_id is validated on every storage operation — read, write, prune, and rebuild.",
            ],
          ].map(([k, v]) => (
            <div key={k as string} className="flex gap-3">
              <span className="text-cyan-400 font-mono text-xs shrink-0 pt-0.5 w-36">
                {k}
              </span>
              <span className="text-slate-500 text-[11px]">{v}</span>
            </div>
          ))}
        </div>
      </Card>

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="Operational Security" color="purple">
          <ul className="space-y-2 text-[11px] text-slate-400">
            {[
              "No cloud dependency — all computation is local",
              "No ML model downloads at runtime",
              "All secrets via environment variables — no hardcoded keys",
              "Entrypoint gating — refuses to start with a stale database schema",
              "Non-root container user — principle of least privilege",
              "Docling removed — zero heavy ML pipeline dependency",
            ].map((f) => (
              <li key={f} className="flex gap-2">
                <span className="text-purple-400 shrink-0">·</span>
                {f}
              </li>
            ))}
          </ul>
        </Card>
        <Card title="Data Lifecycle" color="amber">
          <ul className="space-y-2 text-[11px] text-slate-400">
            {[
              "delete_requested flag: soft delete before hard delete",
              "Cold pruning: configurable threshold (30–365 days)",
              "Dry-run preview before any live deletion",
              "Provenance: every node traces back to original file + page",
              "Download original: retrieve raw blob by raw_id at any time",
              "graph_version bump on every prune — audit trail preserved",
            ].map((f) => (
              <li key={f} className="flex gap-2">
                <span className="text-amber-400 shrink-0">·</span>
                {f}
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  );
}

function SectionDeployment() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">Deployment</h2>
        <p className="text-slate-400 leading-relaxed">
          Production now uses one real env file per target. Local prod and VPS
          prod mirror the same stack, but they stay isolated so the deploy path
          is deterministic and clean.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="Local Production" color="cyan">
          <ul className="space-y-2 text-sm text-slate-400">
            {[
              ".env.localprod is the single local-prod source of truth.",
              "npm run faim:localprod:up brings up the production-like stack.",
              "npm run faim:localprod:up frontend, api, worker, or migrate supports selective rebuilds.",
              "npm run faim:localprod:smoke checks the edge, readiness, and health endpoints.",
            ].map((item) => (
              <li key={item} className="flex gap-2">
                <span className="text-cyan-400 shrink-0">→</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </Card>
        <Card title="VPS Production" color="purple">
          <ul className="space-y-2 text-sm text-slate-400">
            {[
              "deploy/env.vpsprod is copied separately to the VPS and not synced by rsync.",
              "scripts/vps_sync.sh excludes docs, tests, the root Runtime/ scratch folder, and secret env files.",
              "npm run faim:vps:up uses docker-compose.vps.yml with the VPS env file.",
              "Selective rebuilds keep frontend, api, worker, and migrate rebuilds small.",
            ].map((item) => (
              <li key={item} className="flex gap-2">
                <span className="text-purple-400 shrink-0">→</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card title="Deployment Rules" color="emerald">
        <div className="grid md:grid-cols-2 gap-4 text-sm text-slate-400">
          <div>
            <p className="text-emerald-300 font-mono text-xs mb-2">
              Keep These Safe
            </p>
            <ul className="space-y-2">
              {[
                "Do not use git pull on the VPS deploy path.",
                "Do not treat frontend env files as a separate production source.",
                "Only full rebuild when Dockerfile, compose files, or dependencies change.",
              ].map((item) => (
                <li key={item} className="flex gap-2">
                  <span className="text-emerald-400 shrink-0">→</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-emerald-300 font-mono text-xs mb-2">
              What to Check
            </p>
            <ul className="space-y-2">
              {[
                "docker compose config before up",
                "docker compose ps after rebuild",
                "curl /api/v1/health/live and /api/v1/health/ready after deploy",
                "logs for api, worker, frontend, and caddy if anything fails",
              ].map((item) => (
                <li key={item} className="flex gap-2">
                  <span className="text-emerald-400 shrink-0">→</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </Card>
    </div>
  );
}

function SectionCapabilities() {
  const groups = [
    {
      cat: "Memory Core",
      color: "#22d3ee",
      items: [
        [
          "SHA-256 fingerprints",
          "Every node has vector_hash (SHA-256 of content + anchor)",
          "done",
        ],
        [
          "Idempotency match",
          "Duplicate ingestion → same hash → touch_count increment, no duplicate",
          "done",
        ],
        [
          "Native 256-dim vectors",
          "240 n-gram dims + 16 text-stat dims — zero ML",
          "done",
        ],
        [
          "Hot / Warm / Cold tiers",
          "Auto-classified by last_access + touch_count at retrieval time",
          "done",
        ],
        [
          "Cold pruning",
          "90d configurable, dry-run preview available from Storage UI",
          "done",
        ],
        [
          "Long-term Memory Flag",
          "long_term=true permanently protects any node from cold pruning regardless of age or access",
          "done",
        ],
        [
          "Graph invariant checks",
          "Inheritance sum + boundedness checked after mutations",
          "done",
        ],
      ],
    },
    {
      cat: "Knowledge Graph",
      color: "#a78bfa",
      items: [
        [
          "Opposition edges (antisymmetric)",
          "Contradiction detection + retrieval suppression",
          "done",
        ],
        [
          "Inheritance edges",
          "Parent → child weight propagation in scoring",
          "done",
        ],
        ["Semantic edge typing", "PMI + rules-based typed relations", "done"],
        [
          "Temporal contradiction labeling",
          "SUPERSEDED / CONFLICTED status per node",
          "done",
        ],
        [
          "K-hop graph expansion",
          "Bounded diffusion during retrieval recall",
          "done",
        ],
        [
          "Topic Clustering",
          "K-means++ on v_native (256-dim). Auto-K = sqrt(N/2). cluster_id scopes recall to top-2 nearest clusters before full scan",
          "done",
        ],
        [
          "Graph scorecard",
          "Density, entropy, spectral radius computed from topology",
          "done",
        ],
      ],
    },
    {
      cat: "Retrieval",
      color: "#60a5fa",
      items: [
        [
          "Sparse + dense retrieval",
          "Representation V2: word/phrase/skip/entity/time/layout sidecars",
          "done",
        ],
        [
          "7-component scoring",
          "Vector · IDF · phrase · entity · temporal · graph · opposition",
          "done",
        ],
        ["RerankerV2", "Proposition-aware deterministic reranking", "done"],
        [
          "Answer synthesis",
          "Citation-first, extractive, span-grounded answers",
          "done",
        ],
        [
          "Redis cache layer",
          "Query results cached — sub-millisecond repeat hits",
          "done",
        ],
      ],
    },
    {
      cat: "Document Intelligence",
      color: "#f97316",
      items: [
        [
          "Multi-column PDF support",
          "X-coordinate gap analysis for layout column detection",
          "done",
        ],
        [
          "Table extraction",
          "PyMuPDF find_tables() — no double-extraction",
          "done",
        ],
        [
          "Figure / Diagram nodes",
          "PyMuPDF type=1 image blocks → block_type=figure nodes with bbox anchor (x0/y0/x1/y1, area fraction, page)",
          "done",
        ],
        [
          "Scanned PDF OCR",
          "300 DPI, autocontrast, sharpen, Tesseract PSM 3",
          "done",
        ],
        [
          "DOCX support",
          "Section tracking, table headers, paragraph blocks",
          "done",
        ],
        ["PPTX support", "Shape sorting, speaker notes, table shapes", "done"],
        ["XLSX support", "data_only mode, header row detection", "done"],
      ],
    },
    {
      cat: "LLM Integration",
      color: "#34d399",
      items: [
        [
          "Rich system prompt",
          "Filename, page, block_type, temperature per node in prompt",
          "done",
        ],
        [
          "Memory inventory in prompt",
          "Total docs, file types, file names, node counts for meta-queries",
          "done",
        ],
        [
          "FAIM Cortex answer modes",
          "Direct, Timeline, Contradiction-aware, and Provenance-first prose synthesis",
          "done",
        ],
        [
          "Conversational bypass",
          "Greetings skip FAIM retrieval — no false document retrievals",
          "done",
        ],
        [
          "Structured node output",
          "doc_type, block_type, section, column in every retrieved node",
          "done",
        ],
      ],
    },
    {
      cat: "FIG View",
      color: "#fbbf24",
      items: [
        [
          "Temperature badge",
          "🔥/◆/❄ on every node in inspector panel",
          "done",
        ],
        [
          "Structure section",
          "block_type, page, section, column, rows, chars per node",
          "done",
        ],
        [
          "5 visualization modes",
          "Surface, neighborhood, timeline, path, analyze",
          "done",
        ],
        [
          "Warm state (amber)",
          "Third tier between active (green) and cold (grey)",
          "done",
        ],
        [
          "Memory signal cards",
          "Novelty, redundancy, recency with color coding",
          "done",
        ],
        [
          "Prev/Next navigation",
          "Cycle through relevant nodes ranked by similarity",
          "done",
        ],
        [
          "Cluster badge",
          "Violet cluster X badge in node header — populated after running Topic Clustering",
          "done",
        ],
        [
          "Long-term toggle",
          "Per-node ♾ long-term protection toggle in inspector — immediate API write",
          "done",
        ],
      ],
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">
          Full Capabilities
        </h2>
        <p className="text-slate-400 leading-relaxed">
          Every item below is tested, deployed, and running in the current
          version of FAIM.
        </p>
      </div>

      <div className="rounded-2xl border border-slate-800 bg-slate-900/30 overflow-hidden">
        {groups.map((group) => (
          <div key={group.cat}>
            <div
              className="px-4 py-2.5 border-b border-slate-800"
              style={{ background: group.color + "0a" }}
            >
              <span
                className="text-[10px] font-bold uppercase tracking-widest"
                style={{ color: group.color }}
              >
                {group.cat}
              </span>
            </div>
            {group.items.map(([label, value]) => (
              <div
                key={label as string}
                className="flex items-start gap-3 px-4 py-2.5 border-b border-slate-800/50 last:border-0 hover:bg-slate-800/20 transition-colors"
              >
                <span className="text-emerald-400 text-xs shrink-0 pt-0.5">
                  ✅
                </span>
                <div className="flex-1 min-w-0">
                  <span className="text-slate-300 text-sm">{label}</span>
                  <p className="text-slate-600 text-[10px] mt-0.5">{value}</p>
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

function SectionBenchmarks() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">
          Engine Benchmarks
        </h2>
        <p className="text-slate-400 leading-relaxed">
          Real-time performance monitoring, stress testing, and state-of-the-art
          benchmarking with deterministic, reproducible measurement of
          FAIM-Native's speed, efficiency, and system health.
        </p>
      </div>

      <Card title="8-Phase Benchmark System" color="cyan">
        <div className="space-y-4 text-sm text-slate-400">
          <p>
            FAIM's benchmarks measure real performance across multiple
            dimensions — no synthetics, no hardcoded metrics. Every data point
            is measured live from your graph, infrastructure, and stress tests.
          </p>
          <div className="space-y-3">
            {[
              {
                num: "1–3",
                label: "Baseline Suite",
                desc: "BM-1 through BM-9 tests: ingest latency, retrieval latency, graph evolution speed, cluster stability.",
              },
              {
                num: "4",
                label: "Golden Signals",
                desc: "Google SRE's Four Golden Signals: Latency (p50/p95/p99), Traffic (req/sec), Errors (error_rate), Saturation (CPU/memory/DB).",
              },
              {
                num: "5",
                label: "Series Tracking",
                desc: "Historical benchmark runs stored in PostgreSQL. Track performance trends over time as your graph grows.",
              },
              {
                num: "6",
                label: "Stress Testing",
                desc: "Progressive load testing: concurrency [1, 2, 5, 10], measure throughput and latency at each level, detect saturation point.",
              },
              {
                num: "7",
                label: "Series Trending",
                desc: "Compare current run against historical baseline. Detect performance regressions before they impact production.",
              },
              {
                num: "8",
                label: "Anomaly Detection",
                desc: "Rule-based alerts: 9 conditions (latency spikes, memory pressure, error rates, invariant violations) with severity levels.",
              },
              {
                num: "8",
                label: "Exportable Reports",
                desc: "Download complete benchmark snapshots as JSON with SHA-256 integrity hash for audit trails and compliance.",
              },
            ].map(({ num, label, desc }) => (
              <div
                key={label}
                className="flex gap-3 p-3 rounded-lg border border-slate-800 bg-slate-950/40"
              >
                <span className="text-cyan-400 font-mono text-xs shrink-0 w-12 pt-0.5 font-bold">
                  {num}
                </span>
                <div className="flex-1">
                  <p className="text-slate-200 font-semibold text-xs">
                    {label}
                  </p>
                  <p className="text-slate-500 text-[11px] mt-1">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </Card>

      <Card title="Live Metrics — Real Infrastructure Data" color="purple">
        <p className="text-sm text-slate-400 mb-3">
          Every metric is measured directly from your running system, not
          estimated or cached:
        </p>
        <div className="grid md:grid-cols-2 gap-3 text-[11px]">
          {[
            [
              "CPU utilization",
              "From Docker cgroup limits — actual % of container CPU used",
            ],
            [
              "Memory usage",
              "From container memory — actual % of allocated memory",
            ],
            [
              "Database connections",
              "From pg_stat_activity — active connections vs max_connections",
            ],
            [
              "Database size",
              "pg_total_relation_size() — actual storage footprint",
            ],
            [
              "Redis memory",
              "INFO memory — hit rate, evicted keys, command latency",
            ],
            ["Ingest throughput", "Documents per second during stress test"],
            [
              "Query latency",
              "p50/p95/p99 milliseconds from live query sampling",
            ],
            [
              "Graph invariants",
              "Inheritance sum check, boundedness check, opposition validation",
            ],
          ].map(([metric, desc]) => (
            <div
              key={metric}
              className="rounded-lg border border-slate-800 bg-slate-950/40 px-3 py-2"
            >
              <p className="font-mono text-purple-400 text-[10px] mb-0.5">
                {metric}
              </p>
              <p className="text-slate-600 text-[10px]">{desc}</p>
            </div>
          ))}
        </div>
      </Card>

      <Card title="Stress Testing — Progressive Load" color="emerald">
        <p className="text-sm text-slate-400 mb-3">
          Measure how your graph handles increasing concurrency. FAIM runs at 1,
          2, 5, and 10 concurrent ingest streams:
        </p>
        <div className="space-y-2 text-[11px]">
          {[
            [
              "Concurrency",
              "Progressive load levels: [1, 2, 5, 10] concurrent document streams",
            ],
            [
              "Throughput",
              "Documents ingested per second at each concurrency level",
            ],
            [
              "Latency percentiles",
              "p50, p95, p99 ingest latency in milliseconds per concurrency",
            ],
            [
              "Saturation detection",
              "Identifies where throughput plateaus (<10% improvement) — your saturation point",
            ],
            [
              "Invariant stability",
              "Verifies that graph invariants remain valid under load — no corruption",
            ],
          ].map(([k, v]) => (
            <div
              key={k}
              className="flex gap-3 py-1 border-b border-slate-800/40 last:border-0"
            >
              <span className="text-slate-500 text-[11px] shrink-0 w-28 font-mono">
                {k}
              </span>
              <span className="text-slate-300">{v}</span>
            </div>
          ))}
        </div>
      </Card>

      <Card title="Anomaly Alerts — 9 Rule-Based Conditions" color="amber">
        <p className="text-sm text-slate-400 mb-3">
          Deterministic rule-based detection (no ML) across 9 alert categories:
        </p>
        <div className="space-y-2">
          {[
            {
              rule: "Latency spike (CRITICAL)",
              cond: "Ingest latency > 2× SpeedBudget target",
            },
            {
              rule: "Latency warning (WARNING)",
              cond: "Ingest latency > 1.5× SpeedBudget target",
            },
            {
              rule: "Cache hit rate low (WARNING)",
              cond: "Redis hit rate < 50%",
            },
            {
              rule: "Energy approaching bound (CRITICAL)",
              cond: "E > 1.8 (out of 2.0 max)",
            },
            {
              rule: "High redundancy (WARNING)",
              cond: "Graph redundancy > 50%",
            },
            {
              rule: "Database disconnected (CRITICAL)",
              cond: "PostgreSQL unavailable",
            },
            {
              rule: "Memory pressure (WARNING)",
              cond: "Container memory usage > 85%",
            },
            { rule: "CPU throttle (INFO)", cond: "Container CPU usage > 80%" },
            {
              rule: "Invariant violation (CRITICAL)",
              cond: "Inheritance sum ≠ 1.0 or boundedness violated",
            },
          ].map(({ rule, cond }) => (
            <div
              key={rule}
              className="flex gap-3 p-2 rounded-lg border border-slate-800/50 bg-slate-950/20"
            >
              <span className="text-amber-400 font-mono text-[10px] shrink-0">
                {rule}
              </span>
              <span className="text-slate-500 text-[10px]">{cond}</span>
            </div>
          ))}
        </div>
      </Card>

      <Card title="Accessing Benchmarks" color="default">
        <p className="text-sm text-slate-400 mb-3">
          All benchmarks are available from the Dashboard:
        </p>
        <div className="space-y-2 text-sm text-slate-400">
          <div className="flex gap-2">
            <span className="text-slate-500">1.</span>Go to Dashboard →
            Benchmarks tab
          </div>
          <div className="flex gap-2">
            <span className="text-slate-500">2.</span>Click "Run Benchmark" to
            execute the full BM-1 to BM-9 suite (takes ~10s)
          </div>
          <div className="flex gap-2">
            <span className="text-slate-500">3.</span>Click "Stress Test" to run
            progressive load testing (5–10min depending on graph size)
          </div>
          <div className="flex gap-2">
            <span className="text-slate-500">4.</span>View Golden Signals,
            Alerts, and historical trends in the tabs
          </div>
          <div className="flex gap-2">
            <span className="text-slate-500">5.</span>Click "Export" to download
            a complete JSON report with SHA-256 integrity hash
          </div>
        </div>
      </Card>
    </div>
  );
}

function SectionRoadmap() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">Roadmap</h2>
        <p className="text-slate-400 leading-relaxed">
          What is built, what is partially built, and what comes next.
        </p>
      </div>

      <div className="space-y-3">
        {[
          {
            phase: "Phase 1–8",
            label: "Core Memory + Graph",
            status: "done",
            detail:
              "Opposition, inheritance, temporal, semantic edges, IDF weighting, Porter stemming, entity expansion, stop-word removal, 8M+ ConceptNet Lexicon, graph diffusion — all complete and tested.",
          },
          {
            phase: "Phase 9",
            label: "Hot/Warm/Cold Tiers + Cold Pruning",
            status: "done",
            detail:
              "Automatic 3-tier memory temperature classification by last_access and touch_count. Dry-run + live pruning from Storage UI. FIG View shows temperature badge per node.",
          },
          {
            phase: "Phase 9",
            label: "Rich Block Anchors + FIG Structure Panel",
            status: "done",
            detail:
              "block_type, page, section, column, row ranges exposed per node in FIG View Inspector as a dedicated Structure section.",
          },
          {
            phase: "Phase 9",
            label: "LLM Memory Inventory Context",
            status: "done",
            detail:
              "LLM system prompt includes document inventory (file names, types, node counts, ingestion dates) so it can answer meta-questions about what it knows.",
          },
          {
            phase: "Phase 9",
            label: "FIG Memory Signal Cards + Prev/Next Navigation",
            status: "done",
            detail:
              "Novelty, redundancy, recency signal cards with color coding per node. Deterministic Prev/Next navigation through relevant nodes.",
          },
          {
            phase: "Phase 10",
            label: "Topic Clustering",
            status: "done",
            detail:
              "Deterministic k-means++ on v_native vectors. Auto-selects K = sqrt(N/2), seeded from graph_id for reproducibility. cluster_id stored on every node. Query engine scopes recall to top-2 clusters before full scan. FIG View shows cluster badge per node. Triggered from Storage → Maintenance → Run Topic Clustering.",
          },
          {
            phase: "Phase 10",
            label: "Long-term Memory Preservation",
            status: "done",
            detail:
              "long_term flag (BOOLEAN) on every node. Nodes marked long-term are never deleted by cold pruning regardless of age or access count. Toggle per-node from FIG View Inspector. Cold prune endpoint enforces the flag automatically.",
          },
          {
            phase: "Phase 10",
            label: "Figure / Diagram Nodes",
            status: "done",
            detail:
              "PyMuPDF type=1 image blocks detected as inline figures on text pages. block_type=figure nodes created with spatial bbox anchor (x0/y0/x1/y1, area fraction, page). Excluded from text extraction to prevent overlap. New PDFs automatically produce figure nodes.",
          },
          {
            phase: "Benchmark",
            label: "8-Phase Benchmark System",
            status: "done",
            detail:
              "Golden Signals (latency/traffic/errors/saturation), stress testing with saturation point detection, anomaly alerts (9 rule-based conditions), exportable SHA256-hashed reports. All real measured data, no synthetics.",
          },
          {
            phase: "Future",
            label: "Self-organizing Cluster Entropy",
            status: "planned",
            detail:
              "When graph entropy exceeds a configured threshold, automatically trigger re-clustering of cold zones. Graph organizes itself over time.",
          },
          {
            phase: "Future",
            label: "Inverted Index Scale Path",
            status: "planned",
            detail:
              "WAND shortlist algorithm for large-scale sparse retrieval across millions of nodes. Enables production-scale knowledge bases.",
          },
        ].map((item) => (
          <div
            key={item.label}
            className="flex gap-4 rounded-xl border border-slate-800 bg-slate-900/30 p-4"
          >
            <div className="shrink-0 w-16 text-right">
              <span
                className={`text-[10px] font-mono ${item.status === "done" ? "text-emerald-400" : "text-slate-600"}`}
              >
                {item.phase}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                <span
                  className={`text-sm font-semibold ${item.status === "done" ? "text-white" : "text-slate-400"}`}
                >
                  {item.label}
                </span>
                <span
                  className={`text-[10px] px-2 py-0.5 rounded-full border font-mono ${item.status === "done" ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400" : "border-slate-700 text-slate-500"}`}
                >
                  {item.status === "done" ? "✅ done" : "○ planned"}
                </span>
              </div>
              <p className="text-[11px] text-slate-500 leading-relaxed">
                {item.detail}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function SectionCanonicalSemantics() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">Canonical Semantics Pipeline (P2)</h2>
        <p className="text-slate-400 leading-relaxed">
          FAIM matches concepts using deterministic lemmatization and Broadeners instead of relying on stochastic learned semantics models.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="Porter Stemmer & Lemmatization" color="cyan">
          <p className="text-sm text-slate-400 leading-relaxed">
            Every text node is normalized by reducing terms to their base roots via a deterministic, rule-based Porter Stemmer. This eliminates the need to run costly learned lemmatization engines on every search loop.
          </p>
        </Card>
        <Card title="Acronym Expansion Registry" color="purple">
          <p className="text-sm text-slate-400 leading-relaxed">
            Acronyms (like "ROI" or "CAGR") are expanded deterministically during text tokenization, matching their canonical form and ensuring exact search coverage.
          </p>
        </Card>
      </div>

      <Card title="Distributional Synonyms & ConceptNet" color="amber">
        <p className="text-sm text-slate-400 leading-relaxed mb-4">
          Unsupervised synonyms are mined using Jaccard and PMI co-occurrence calculations from the active corpus. Broad semantic associations are linked using the local 8M+ ConceptNet semantic registry.
        </p>
        <Code>{`PMI(w_1, w_2) = log_2 ( P(w_1, w_2) / (P(w_1) * P(w_2)) )
synonym_edge = PMI >= tau_pmi AND jaccard >= tau_jaccard`}</Code>
      </Card>
    </div>
  );
}

function SectionGraphDiffusion() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">Graph Semantics and Diffusion (P3)</h2>
        <p className="text-slate-400 leading-relaxed">
          FAIM traverses active query paths using bounded multi-hop walks and deterministic diffusion equations to reward localized neighborhood coherence.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="Decaying Path Score" color="indigo">
          <p className="text-sm text-slate-400 leading-relaxed">
            Score weights decay geometrically with each traversal hop, ensuring that localized neighborhood connections are rewarded over distant semantic jumps.
          </p>
        </Card>
        <Card title="Temporal Opposition Suppression" color="red">
          <p className="text-sm text-slate-400 leading-relaxed">
            Chronological conflicts and contradictory properties are flagged during path traversal, suppressing the older candidate before re-ranking.
          </p>
        </Card>
      </div>

      <Card title="PageRank style Bounded Diffusion" color="purple">
        <p className="text-sm text-slate-400 leading-relaxed mb-4">
          Scores diffuse outward from seed nodes using a deterministic, PageRank-style matrix propagation across the active adjacency graph.
        </p>
        <Code>{`y^(k+1) = (1 - alpha) * y_seed + alpha * P^T * y^(k)
hops_max = 24, convergence_threshold = 0.05`}</Code>
      </Card>
    </div>
  );
}

function SectionRerankerV2() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">Deterministic Reranker V2 (P4)</h2>
        <p className="text-slate-400 leading-relaxed">
          Fuses sparse, dense, and graph components into a single multi-signal score to achieve extreme precision without learned cross-encoders.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="Multi-Signal Score Blend" color="cyan">
          <p className="text-sm text-slate-400 leading-relaxed">
            Combines lexical term frequencies, graph path scores, matching entities, chronological times, and evidence density.
          </p>
        </Card>
        <Card title="Pairwise Dominance Suppression" color="emerald">
          <p className="text-sm text-slate-400 leading-relaxed">
            If two nodes assert contradicting values for the same entity and relation, the younger node suppresses the older candidate pairwise.
          </p>
        </Card>
      </div>

      <Card title="The V2 Reranker Equation" color="purple">
        <p className="text-sm text-slate-400 leading-relaxed mb-4">
          The final score is synthesized using a deterministic linear combination of structural and temporal components:
        </p>
        <Code>{`S_rerank = lexical + graph + entity + time
           + evidence_span + proposition_match
           - contradiction_penalty - redundancy_penalty`}</Code>
      </Card>
    </div>
  );
}

function SectionScaleANN() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">Scale and ANN (P5)</h2>
        <p className="text-slate-400 leading-relaxed">
          FAIM scales retrieval to millions of nodes using a 4-stage progressive flow, WAND pruning, and deterministic hash levels.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="Block-Max WAND Pruning" color="cyan">
          <p className="text-sm text-slate-400 leading-relaxed">
            Computes a dynamic score upper bound for term blocks, instantly skipping non-matching ranges to deliver sublinear candidate shortlist times.
          </p>
        </Card>
        <Card title="Stable Hash HNSW Levels" color="purple">
          <p className="text-sm text-slate-400 leading-relaxed">
            Locks in absolute search determinism by assigning HNSW node entry levels using a stable SHA-256 hash of the node's identifier.
          </p>
        </Card>
      </div>

      <Card title="The 4-Stage Progressive Retrieval Flow" color="amber">
        <div className="space-y-3 text-sm text-slate-400">
          {[
            { stage: "Stage 1", desc: "Sparse postings shortlist using Block-Max WAND upper bounds." },
            { stage: "Stage 2", desc: "Native vector shortlist query using deterministic stable HNSW levels." },
            { stage: "Stage 3", desc: "Graph expansion and bounded multi-hop neighborhood diffusion." },
            { stage: "Stage 4", desc: "Deterministic V2 reranking with pairwise dominance suppression." }
          ].map((s) => (
            <div key={s.stage}>
              <p className="text-amber-400 font-mono text-xs">{s.stage}</p>
              <p className="text-[11px] text-slate-500">{s.desc}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function SectionMultilingual() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">Multilingual & Cross-Lingual Semantics (P6)</h2>
        <p className="text-slate-400 leading-relaxed">
          Bridges English and German terms directly onto language-agnostic conceptual nodes using deterministic lexicons.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="German Transliteration" color="cyan">
          <p className="text-sm text-slate-400 leading-relaxed">
            Unifies spelling differences by standardizing German umlauts deterministically (ä → ae, ö → oe, ü → ue, ß → ss).
          </p>
        </Card>
        <Card title="Light German Stemmer" color="purple">
          <p className="text-sm text-slate-400 leading-relaxed">
            Stems German roots deterministically to handle inflections and plural variants perfectly without heavy dictionary runtimes.
          </p>
        </Card>
      </div>

      <Card title="Bilingual Concept Node Bridges" color="emerald">
        <p className="text-sm text-slate-400 leading-relaxed mb-4">
          German and English surface forms map directly to a unified conceptual ID, resolving cross-lingual query matches in microseconds:
        </p>
        <Code>{`surface_form(EN) -> concept_key <- surface_form(DE)
"sales" -> Concept: revenue <- "umsatz"`}</Code>
      </Card>
    </div>
  );
}

function SectionMultimodalNoML() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">Multimodal Without ML (P7)</h2>
        <p className="text-slate-400 leading-relaxed">
          Deterministic support for spreadsheet tables, page layout coordinates, and visual assets without heavy transformer models.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="Table Linearization" color="cyan">
          <p className="text-sm text-slate-400 leading-relaxed">
            Transforms pipe-delimited table rows into standardized, semicolon-delimited grids row-by-row, keeping cells grouped for keyword proximity queries.
          </p>
        </Card>
        <Card title="Image Perceptual Hash (pHash)" color="purple">
          <p className="text-sm text-slate-400 leading-relaxed">
            Generates a stable 16-character fingerprint proxy based on SHA-256 to identify exact or near-duplicate visual assets instantly.
          </p>
        </Card>
      </div>

      <Card title="Layout Coordinates & Metadata" color="amber">
        <p className="text-sm text-slate-400 leading-relaxed mb-4">
          Saves and indexes physical layout boundaries (page numbers, slides, sections, block types) as easily queryable search tokens.
        </p>
        <Code>{`layout_token = "page:{nr}" | "slide:{nr}" | "section:{header}" | "block_type:{type}"`}</Code>
      </Card>
    </div>
  );
}

function SectionDomainAdaptation() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">Long-Tail Knowledge & Domain Adaptation (P8)</h2>
        <p className="text-slate-400 leading-relaxed">
          Solves specialized domain jargon by ingesting curated corporate KB dumps and executing algebraic neighborhood walks.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="Deterministic Entity Linking" color="cyan">
          <p className="text-sm text-slate-400 leading-relaxed">
            Substring-matches input query words against the localized graph lexicon, resolving them directly to specific target seed node UUIDs.
          </p>
        </Card>
        <Card title="Multi-Relational Graph Walks" color="purple">
          <p className="text-sm text-slate-400 leading-relaxed">
            Starting at seed nodes, the engine executes neighborhood walks across adjacent entity relationships, fact values, and source citations.
          </p>
        </Card>
      </div>

      <Card title="Knowledge Base Edge-Scaling Multipliers" color="indigo">
        <p className="text-sm text-slate-400 leading-relaxed mb-4">
          Adjacent activated nodes receive relevance boosts scaled by normalized edge weights and connecting multipliers:
        </p>
        <Code>{`W(e) = clamp( weight_db / 10^9 )
S_fact_support = max( S_fact_support, Multiplier * W(e) )
(Multipliers: entity_relation = 0.65, fact_value = 0.55, domain_term = 0.50)`}</Code>
      </Card>
    </div>
  );
}

function SectionAnswerSynthesis() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">Extractive Answer Synthesis (P9)</h2>
        <p className="text-slate-400 leading-relaxed">
          Composes 100% auditable, citation-first extractive prose and exact confidence intervals without generative LLM drift.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="Extractive Span Selector" color="cyan">
          <p className="text-sm text-slate-400 leading-relaxed">
            Splits text candidates into sentences and scores them based on term overlap, document rank, and temporal active/historical markers.
          </p>
        </Card>
        <Card title="Contradiction Warnings" color="red">
          <p className="text-sm text-slate-400 leading-relaxed">
            Automatically flags value conflicts asserting different figures for the same entity and relation in top retrieval candidates.
          </p>
        </Card>
      </div>

      <Card title="Evidence Confidence Interval Equation" color="purple">
        <p className="text-sm text-slate-400 leading-relaxed mb-4">
          Computes a mathematically sound confidence index $[0, 1]$ based on evidence breadth, active span ratio, and contradiction penalties:
        </p>
        <Code>{`S_confidence = clamp( 0.45 * S_avg_span + 0.30 * S_breadth + 0.25 * S_active - S_penalty )
S_breadth = min( 1.0, unique_docs / 3.0 ), S_penalty = min( 0.5, 0.15 * conflicts )`}</Code>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section renderer
// ---------------------------------------------------------------------------
const SECTION_COMPONENTS: Record<string, React.ComponentType> = {
  "what-is-faim": SectionWhatIsFaim,
  "current-state": SectionCurrentState,
  quickstart: SectionQuickStart,
  "why-faim": SectionWhyFaim,
  architecture: SectionArchitecture,
  memory: SectionMemory,
  graph: SectionGraph,
  retrieval: SectionRetrieval,
  cortex: SectionCortex,
  "cortex-runtime": SectionCortexRuntime,
  "canonical-semantics": SectionCanonicalSemantics,
  "graph-diffusion": SectionGraphDiffusion,
  "reranker-v2": SectionRerankerV2,
  "scale-ann": SectionScaleANN,
  "multilingual": SectionMultilingual,
  "multimodal-no-ml": SectionMultimodalNoML,
  "domain-adaptation": SectionDomainAdaptation,
  "answer-synthesis": SectionAnswerSynthesis,
  "document-intel": SectionDocIntel,
  ingestion: SectionIngestion,
  "fig-view": SectionFigView,
  billing: SectionBilling,
  security: SectionSecurity,
  benchmarks: SectionBenchmarks,
  deployment: SectionDeployment,
  capabilities: SectionCapabilities,
  roadmap: SectionRoadmap,
};

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------
export default function DocsPage() {
  const [active, setActive] = useState("what-is-faim");
  const Content = SECTION_COMPONENTS[active] ?? SectionWhatIsFaim;

  return (
    <main className="min-h-screen bg-slate-950">
      {/* Navbar */}
      <nav className="fixed top-0 left-0 right-0 z-50 pt-4 px-4">
        <div className="max-w-7xl mx-auto px-6 py-3 bg-slate-900/80 backdrop-blur-xl border border-slate-700/50 rounded-2xl">
          <div className="flex items-center justify-between">
            <Link href="/">
              <Logo px={32} />
            </Link>
            <div className="flex items-center gap-6">
              <Link
                href="/"
                className="text-sm text-slate-400 hover:text-white transition-colors"
              >
                ← Home
              </Link>
              <Link
                href="/auth/signup"
                className="text-sm px-4 py-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/20 transition-all"
              >
                Get Started
              </Link>
            </div>
          </div>
        </div>
      </nav>

      <div className="pt-28 pb-20 px-4">
        <div className="max-w-7xl mx-auto flex gap-8">
          {/* Sidebar */}
          <aside className="hidden lg:block w-52 shrink-0">
            <div className="sticky top-28 space-y-5">
              <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 px-3">
                FAIM Docs
              </p>
              {NAV_GROUPS.map((group) => (
                <div key={group.group}>
                  <p className="text-[9px] font-semibold uppercase tracking-widest text-slate-600 px-3 mb-1">
                    {group.group}
                  </p>
                  <div className="space-y-0.5">
                    {group.items.map((item) => (
                      <button
                        key={item.id}
                        onClick={() => setActive(item.id)}
                        className={`w-full text-left px-3 py-1.5 rounded-lg text-sm transition-all ${
                          active === item.id
                            ? "bg-cyan-500/10 text-cyan-300 border border-cyan-500/20"
                            : "text-slate-500 hover:text-slate-300 hover:bg-slate-800/40 border border-transparent"
                        }`}
                      >
                        {item.label}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </aside>

          {/* Content panel — only active section shown */}
          <div className="flex-1 min-w-0 max-w-4xl">
            <AnimatePresence mode="wait">
              <motion.div
                key={active}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.2 }}
              >
                <Content />
              </motion.div>
            </AnimatePresence>

            {/* Bottom nav */}
            <div className="mt-12 pt-6 border-t border-slate-800/60 flex items-center justify-between">
              {(() => {
                const allItems = NAV_GROUPS.flatMap((g) => g.items);
                const idx = allItems.findIndex((i) => i.id === active);
                const prev = allItems[idx - 1];
                const next = allItems[idx + 1];
                return (
                  <>
                    {prev ? (
                      <button
                        onClick={() => setActive(prev.id)}
                        className="flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors"
                      >
                        <span>←</span> {prev.label}
                      </button>
                    ) : (
                      <span />
                    )}
                    {next ? (
                      <button
                        onClick={() => setActive(next.id)}
                        className="flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors"
                      >
                        {next.label} <span>→</span>
                      </button>
                    ) : (
                      <span />
                    )}
                  </>
                );
              })()}
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
