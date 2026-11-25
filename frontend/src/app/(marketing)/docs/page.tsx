"use client";

import { motion, AnimatePresence } from "framer-motion";
import {
  BookOpen,
  ChevronDown,
  ChevronRight,
  Cpu,
  FileText,
  Layers,
  Menu,
  Search,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import Logo from "@/components/brand/Logo";
import {
  DocsBookBanner,
  VisualArchitectureFlow,
  VisualBenchmarkChart,
  VisualDomainDiagram,
  VisualGraphTopology,
  VisualHybridRouter,
  VisualLexiconDistribution,
  VisualScoreCalculator,
  VisualVectorTierExplorer,
} from "@/components/docs/DocsVisuals";
import BenchmarkResultsBoard from "@/components/landing/BenchmarkResultsBoard";
import { APP_VERSION } from "@/lib/appVersion";

// ---------------------------------------------------------------------------
// Nav structure
// ---------------------------------------------------------------------------
const NAV_GROUPS = [
  {
    group: "Overview",
    items: [
      { id: "what-is-faim", label: "What is FAIM?" },
      { id: "current-state", label: "Research & Thesis" },
      { id: "quickstart", label: "Quick Start" },
      { id: "why-faim", label: "Why FAIM?" },
    ],
  },
  {
    group: "Core System",
    items: [
      { id: "architecture", label: "System Architecture" },
      { id: "memory", label: "Memory System & Tiers" },
      { id: "graph", label: "Knowledge Graph" },
      { id: "retrieval", label: "Retrieval Engine" },
      { id: "hybrid-routing", label: "Dynamic CPU/GPU Routing" },
      { id: "cortex", label: "MCP & Agent Access" },
      { id: "cortex-runtime", label: "Query & Hop Runtime" },
    ],
  },
  {
    group: "Retrieval & Semantics",
    items: [
      { id: "canonical-semantics", label: "Canonical Semantics" },
      { id: "graph-diffusion", label: "Graph Diffusion" },
      { id: "reranker-v2", label: "Deterministic Reranker V2" },
      { id: "scale-ann", label: "Indexing, WAND & ANN" },
      { id: "multilingual", label: "Cross-Lingual Bridges" },
      { id: "multimodal-no-ml", label: "Structural & Visual Indexing" },
      { id: "domain-adaptation", label: "Domain Adaptation" },
      { id: "answer-synthesis", label: "Extractive Synthesis" },
    ],
  },
  {
    group: "Documents & Extraction",
    items: [
      { id: "document-intel", label: "Document Intelligence" },
      { id: "ingestion", label: "Ingestion Pipeline" },
    ],
  },
  {
    group: "Platform & Operations",
    items: [
      { id: "fig-view", label: "FIG View (3D Explorer)" },
      { id: "api-reference", label: "REST API Reference" },
      { id: "security", label: "Security & Isolation" },
      { id: "benchmarks", label: "Benchmarks & Evaluation" },
      { id: "deployment", label: "Deployment & Configuration" },
      { id: "billing", label: "Subscription Plans" },
      { id: "capabilities", label: "Capabilities Matrix" },
      { id: "roadmap", label: "Architecture Milestones" },
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
          self-hostable memory, retrieval, and citation synthesis engine. It is
          neither a generative LLM nor a standalone vector database. It fuses a
          pure-math 256-dimensional native core with optional pre-bundled local
          Granite 97M multilingual embeddings, a typed knowledge graph, and
          immutable SHA-256 provenance.
        </p>
      </div>

      <VisualArchitectureFlow />

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="Dual-Path Hybrid Intelligence" color="cyan">
          <p className="text-sm text-slate-400 leading-relaxed">
            Every uploaded document is segmented into layout-anchored blocks,
            encoded into a canonical 256-dimensional mathematical vector (240
            SHA-256 character n-gram buckets plus 16 text-statistic features),
            and optionally paired with a local 384-dimensional Granite 97M
            Multilingual R2 dense vector. When querying, FAIM merges vector
            shortlists, sparse Representation V2 sidecars, bounded multi-hop
            graph diffusion, and 7-component Reranker V2 before returning
            extractive spans with page and section provenance.
          </p>
        </Card>
        <Card title="Core Architectural Properties" color="purple">
          <ul className="space-y-2 text-sm text-slate-400">
            {[
              [
                "Zero ML Fast Path",
                "FAIM-Pure executes English FAST retrieval on pure CPU math with zero neural inference.",
              ],
              [
                "Local Hybrid Option",
                "Bundled IBM Granite 97M R2 (97M params, 384-dim, 32K context) activates without external cloud APIs.",
              ],
              [
                "Deterministic",
                "Identical graph state and query parameters produce reproducible rankings and SHA-256 audit hashes.",
              ],
              [
                "Graph-Native",
                "Inheritance, antisymmetric opposition, causal, and PMI semantic edges resolve conflicts structurally.",
              ],
              [
                "Self-Hostable",
                "Runs completely inside your Docker/VPS/GPU environment via one unified docker-compose.yml.",
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

      <Card title="System Boundaries (What FAIM Is Not)" color="amber">
        <div className="grid md:grid-cols-3 gap-4 text-sm">
          {[
            [
              "Not a Generative LLM",
              "FAIM never hallucinates free-form prose. It extracts, ranks, and verifies grounded sentence spans directly from indexed source blocks.",
            ],
            [
              "Not a Flat Vector Store",
              "Vector stores only compute approximate nearest neighbors. FAIM enforces SHA-256 deduplication, memory decay tiers, opposition edges, and multi-hop provenance.",
            ],
            [
              "Not a Cloud Wrapper",
              "There are zero external embedding API keys required. Both the 256-dim native math engine and Granite 97M weights execute locally under your control.",
            ],
          ].map(([t, d]) => (
            <div key={t as string}>
              <p className="text-amber-400 font-mono text-xs mb-1">{t}</p>
              <p className="text-slate-400 text-xs leading-relaxed">{d}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function SectionCurrentState() {
  const researchQuestions = [
    {
      q: "Q1: Can deterministic native math match or beat neural retrieval on CPU?",
      a: "Yes. On the full 5,183-doc / 300-query BeIR SciFact evaluation, pure zero-ML FAIM-Pure achieved 0.6871 nDCG@10 (Recall@5 0.7554) at 86.31 ms CPU CI latency, outperforming both standard BM25 (0.6644 nDCG@10) and standalone Granite 97M dense (0.6806 nDCG@10).",
      tag: "Verified: +0.0227 vs BM25",
      color: "cyan",
    },
    {
      q: "Q2: What happens when deterministic structure fuses with compact local ML?",
      a: "Pairing FAIM's graph, lexical Representation V2, and Concept-MaxSim signals with local Granite 97M R2 elevates BeIR SciFact to 0.6900 nDCG@10 (Recall@5 0.7704), NFCorpus to 0.3314 nDCG@10 (+6.6% over BM25), and ArguAna to 0.7266 Recall@10 at 1.86x lower median latency than BM25.",
      tag: "Verified: 0.6900 SciFact",
      color: "emerald",
    },
    {
      q: "Q3: How does dynamic routing avoid paying GPU latency on simple English queries?",
      a: "With FAIM_FAST_ML_EMBEDDING=auto, English FAST queries route directly through FAIM-Pure on CPU without invoking neural inference, while non-English queries and BALANCED/STRICT modes invoke bundled Granite 97M embeddings automatically.",
      tag: "Adaptive: auto Policy",
      color: "purple",
    },
    {
      q: "Q4: How do contradictory updates avoid corrupting long-lived agent memory?",
      a: "Every ingested block carries a SHA-256 content+anchor fingerprint (vector_hash) for idempotency and forms antisymmetric opposition and inheritance edges. Superseded claims are penalized pairwise or excluded while retaining auditable provenance.",
      tag: "Invariant: SHA-256 + TCE",
      color: "amber",
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">
          Research &amp; Core Thesis
        </h2>
        <p className="text-slate-400 leading-relaxed">
          FAIM is engineered around a foundational research question: can a
          retrieval and memory system stay mathematically deterministic,
          cryptographically traceable, and conflict-aware while beating dense
          black-box vector pipelines?
        </p>
      </div>

      <VisualBenchmarkChart />

      <div className="grid md:grid-cols-2 gap-4">
        {researchQuestions.map((item) => (
          <Card key={item.q} title={item.tag} color={item.color}>
            <p className="text-sm font-semibold text-white mb-2">{item.q}</p>
            <p className="text-xs text-slate-400 leading-relaxed">{item.a}</p>
          </Card>
        ))}
      </div>

      <VisualLexiconDistribution />

      <Card title="Universal Architectural Guarantees" color="cyan">
        <div className="grid md:grid-cols-2 gap-4 text-xs text-slate-400">
          <ul className="space-y-2">
            {[
              "256-dim Native Core remains canonical and invariant across all graph states.",
              "Semantic Registry (2,319,589 shipped terms) adds explainable lexical broadening without replacing native math.",
              "SHA-256 node and packet hashes enforce idempotent writes and end-to-end lineage.",
            ].map((item) => (
              <li key={item} className="flex gap-2">
                <span className="text-cyan-400 shrink-0">→</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
          <ul className="space-y-2">
            {[
              "Graph autonomy (self-evolve and self-invent) stays off by default until explicitly enabled per workspace.",
              "Hot, Warm, and Cold memory tiers manage retention automatically without manual index rewrites.",
              "Tenant DEK envelope encryption and row-level isolation enforce strict workspace boundaries.",
            ].map((item) => (
              <li key={item} className="flex gap-2">
                <span className="text-emerald-400 shrink-0">→</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </Card>
    </div>
  );
}

function SectionQuickStart() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">Quick Start</h2>
        <p className="text-slate-400 leading-relaxed">
          Launch the full self-hosted FAIM stack, ingest structured documents,
          and execute provenance-backed queries in minutes.
        </p>
      </div>

      <Card title="Local Stack Bootstrap (Docker Compose)" color="indigo">
        <Code>{`# 1. Configure shared environment variables
cp .env.example .env

# 2. Launch API, Workers, PostgreSQL, Redis, Qdrant, and Frontend
docker compose up -d

# 3. Verify health & readiness endpoints
curl -fsS http://localhost:8000/health && curl -fsS http://localhost:8000/ready`}</Code>
      </Card>

      <Card title="Step 1: Create a Workspace Account" color="cyan">
        <ol className="space-y-3">
          {[
            "Register at the Get Started page to initialize your isolated tenant scope",
            "A dedicated knowledge graph is provisioned automatically for your workspace",
            "Manage ingestion, evolution opt-in settings, and keys from the Dashboard control center",
            "Keep autonomous graph evolution off for static corpora or opt in when continuous adaptation is desired",
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

      <Card title="Step 2: Ingest Documents" color="purple">
        <ol className="space-y-3">
          {[
            "Open Dashboard → Storage and upload PDF, DOCX, PPTX, XLSX, images, or text/code files",
            "FAIM segments every block with structural anchors, computes its 256-dim native vector, and attaches Representation V2 sidecars",
            "Status transitions cleanly from processing to ready with zero duplicate node inserts",
            "Trigger Rebuild Memory Index from Storage maintenance routes whenever refreshing sidecars",
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

      <Card title="Step 3: Connect Agents via MCP or REST" color="emerald">
        <ol className="space-y-3">
          {[
            "Open Dashboard → MCP to copy your /mcp endpoint for Cursor, Claude, or VS Code (OAuth 2.1 + PKCE)",
            "Or create a one-time X-API-Key secret in Dashboard → API Keys for REST, Python SDK, or stdio faim-mcp",
            "Call POST /api/v1/query or POST /api/v1/memory/search with graph_max_hops (1 to 24, default 2)",
            "Receive ranked extractive evidence alongside page/section anchors and confidence scores",
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

      <Card title="Step 4: Inspect Provenance in 3D FIG View" color="amber">
        <ol className="space-y-3">
          {[
            "Open Dashboard → FIG View to explore indexed atoms, macro parent nodes, and typed edges",
            "Click any node to inspect block_type, page, section, temperature (Hot/Warm/Cold), and SHA-256 fingerprint",
            "Switch modes across Surface, Neighborhood (K-hop), Timeline, Path (pulse-v2), and Analyze",
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
          Conventional knowledge stacks force a tradeoff between opaque flat
          vector databases and hallucination-prone LLM wrappers. FAIM unifies
          deterministic mathematics, typed graph structure, and local hybrid
          acceleration into one auditable substrate.
        </p>
      </div>

      <VisualBenchmarkChart />

      <div className="rounded-2xl border border-slate-800 bg-slate-900/30 overflow-hidden">
        <div className="grid grid-cols-4 gap-0 px-4 py-3 border-b border-slate-800 bg-slate-900/60 text-[10px] font-bold uppercase tracking-widest text-slate-500">
          <span>Capability</span>
          <span>FAIM</span>
          <span>Vector DB</span>
          <span>LLM RAG</span>
        </div>
        {[
          ["Deterministic core ranking", "Yes", "No", "No"],
          ["Zero ML CPU fast path (FAIM-Pure)", "Yes", "No", "No"],
          [
            "Bundled local Granite 97M hybrid option",
            "Yes",
            "External API",
            "External API",
          ],
          ["Typed edges (opposition, inheritance, causal)", "Yes", "No", "No"],
          ["SHA-256 node & file fingerprints", "Yes", "No", "No"],
          ["Hot / Warm / Cold memory lifecycle", "Yes", "No", "No"],
          ["Contradiction detection + pairwise suppression", "Yes", "No", "No"],
          ["Self-hostable zero-cloud operation", "Yes", "Partial", "No"],
          ["Citation-first extractive span answers", "Yes", "No", "Partial"],
          ["Multi-column PDF, table & OCR layout", "Yes", "No", "Partial"],
          ["2.32M shipped deterministic semantic registry", "Yes", "No", "No"],
          ["Topological scorecard (D, H, lambda)", "Yes", "No", "No"],
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

      <Card title="Ideal Engineering & Compliance Use Cases" color="cyan">
        <div className="grid md:grid-cols-2 gap-4 text-sm text-slate-400">
          <ul className="space-y-2">
            <li className="flex gap-2">
              <span className="text-cyan-400">→</span>Regulated enterprises
              (legal, healthcare, finance) needing strict source lineage
            </li>
            <li className="flex gap-2">
              <span className="text-cyan-400">→</span>Air-gapped or VPC
              deployments prohibiting external LLM/embedding calls
            </li>
            <li className="flex gap-2">
              <span className="text-cyan-400">→</span>Long-horizon agent memory
              requiring conflict &amp; temporal resolution
            </li>
          </ul>
          <ul className="space-y-2">
            <li className="flex gap-2">
              <span className="text-cyan-400">→</span>Teams scaling across both
              CPU-only VPS nodes and CUDA GPU hosts
            </li>
            <li className="flex gap-2">
              <span className="text-cyan-400">→</span>Workflows where
              reproducible scoring and explainable paths are mandatory
            </li>
            <li className="flex gap-2">
              <span className="text-cyan-400">→</span>Research groups evaluating
              hybrid symbolic + neural retrieval tradeoffs
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
      label: "PostgreSQL  ·  Dense Cache  ·  Redis  ·  Raw Blob Store",
      color: "#f87171",
      desc: "Storage substrate: relational graph, deterministic ANN cache, query cache, raw files",
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">
          System Architecture
        </h2>
        <p className="text-slate-400 leading-relaxed">
          FAIM is a layered runtime combining deterministic native vectors,
          additive sparse sidecars, optional local Granite 97M embeddings, and
          relational graph storage without external cloud dependencies.
        </p>
      </div>

      <VisualArchitectureFlow />

      <div className="rounded-2xl border border-slate-800 bg-slate-900/30 p-5">
        <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-4">
          System Stack (Top to Bottom)
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
              <span className="text-slate-600">·</span>PostgreSQL: nodes, edges,
              repr_v2 sidecars
            </li>
            <li className="flex gap-2">
              <span className="text-slate-600">·</span>Deterministic ANN -
              graph-versioned dense shortlist cache
            </li>
            <li className="flex gap-2">
              <span className="text-slate-600">·</span>Redis: query result cache
              + hot node hints
            </li>
            <li className="flex gap-2">
              <span className="text-slate-600">·</span>Raw blob store: original
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
              <span className="text-slate-600">·</span>Idempotent upsert: no
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
              <span className="text-slate-600">·</span>RerankerV2 -
              proposition-aware reranking
            </li>
            <li className="flex gap-2">
              <span className="text-slate-600">·</span>K-hop bounded graph
              diffusion
            </li>
            <li className="flex gap-2">
              <span className="text-slate-600">·</span>Answer synthesis -
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
        <h2 className="text-2xl font-bold text-white mb-2">
          Memory System &amp; Tiers
        </h2>
        <p className="text-slate-400 leading-relaxed">
          FAIM's canonical memory layer pairs 256-dimensional pure-math native
          vectors with SHA-256 deduplication fingerprints, automated
          Hot/Warm/Cold temperature tiers, and deterministic topic clustering.
        </p>
      </div>

      <VisualVectorTierExplorer />

      <Card title="256-Dimensional Native Vector" color="cyan">
        <p className="text-sm text-slate-400 mb-3 leading-relaxed">
          Every text block is encoded into a 256-dim vector using deterministic
          mathematics (zero ML required in the fast native core). Encoding has
          two fixed components:
        </p>
        <div className="grid md:grid-cols-2 gap-3">
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
            <p className="text-xs font-mono text-cyan-400 mb-1.5">
              dims 0 to 239: Character n-grams
            </p>
            <p className="text-[11px] text-slate-500 leading-relaxed">
              SHA-256 hash of character 2-grams and 3-grams, bucketed into 240
              dimensions (NGRAM_BUCKETS = 240). Captures morphological and
              lexical patterns with zero vocabulary table.
            </p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
            <p className="text-xs font-mono text-cyan-400 mb-1.5">
              dims 240 to 255: Text statistics
            </p>
            <p className="text-[11px] text-slate-500 leading-relaxed">
              Word count, sentence length, punctuation density, capitalization
              ratio, digit ratio, and structural features encoded into 16
              normalized dimensions.
            </p>
          </div>
        </div>
      </Card>

      <Card title="SHA-256 Fingerprinting & Idempotency" color="emerald">
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
                "Highest retrieval priority: most recently used knowledge",
              color: "#f97316",
            },
            {
              tier: "◆ WARM",
              rule: "last_access within 30 days  OR  touch_count ≥ 5",
              effect: "Active working memory: still in regular use",
              color: "#fbbf24",
            },
            {
              tier: "❄ COLD",
              rule: "last_access > 90 days  OR  never accessed + age > 7 days",
              effect: "Candidate for pruning: forgotten knowledge",
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
          Both options are exposed through the storage maintenance routes.
          Long-term nodes are always skipped.
        </p>
      </Card>

      <Card title="Long-term Memory Flag" color="emerald">
        <p className="text-sm text-slate-400 leading-relaxed mb-3">
          Any node can be marked{" "}
          <code className="text-emerald-400 font-mono text-xs">
            long_term = true
          </code>{" "}
          to protect it from cold pruning permanently: regardless of age,
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

      <Card title="Topic Clustering: K-means on v_native" color="purple">
        <p className="text-sm text-slate-400 leading-relaxed mb-3">
          FAIM can group all nodes into topic clusters using deterministic
          k-means++ on v_native vectors. Once clusters are computed, every query
          automatically scopes recall to the top-2 matching clusters before
          doing a full cosine scan: improving speed and precision as the graph
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
              "RNG seeded from SHA-256 of graph_id: same graph always produces same clusters",
            ],
            ["Convergence", "Max 50 iterations or until centroids stop moving"],
            [
              "Query scoping",
              "At query time: find top-2 cluster centres, filter recall to those clusters (falls back to full scan if too few results)",
            ],
            [
              "How to run",
              "Use the storage maintenance routes to run topic clustering",
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
          FAIM's graph is the relational intelligence layer. Atom and macro
          nodes hold anchored facts while typed edges encode hierarchy,
          contradiction, causation, and PMI co-occurrence.
        </p>
      </div>

      <VisualGraphTopology />

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="Node Structure" color="cyan">
          <Code>{`node_id      UUID (unique identifier)
graph_id     String (tenant graph scope)
vector_hash  SHA-256 content fingerprint
raw_id       UUID (source file reference)
block_id     String (block within source)
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
                Leaf node. Represents one extracted block of content: a
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

      <Card title="Graph Scorecard: Computed from Topology" color="default">
        <div className="grid md:grid-cols-3 gap-3">
          {[
            {
              metric: "D: Density",
              formula: "Edges ÷ (Nodes × (Nodes−1))",
              range: "0 = no connections · 1 = complete graph",
              color: "#22d3ee",
            },
            {
              metric: "H: Entropy",
              formula: "Shannon entropy of edge kinds (bits)",
              range: "0 = all same · log₂(kinds) = maximum",
              color: "#a78bfa",
            },
            {
              metric: "λ: Spectral Radius",
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
          FAIM runs a multi-stage deterministic retrieval pipeline fusing
          256-dim native math, optional local Granite 97M embeddings, sparse
          Representation V2 sidecars, Semantic Registry broadening (2,319,589
          terms), native late interaction, and 7-component Reranker V2.
        </p>
      </div>

      <VisualScoreCalculator mode="scoring" />

      <Card title="Retrieval Pipeline Step by Step" color="cyan">
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
              label: "Weighted expansion engine",
              detail:
                "Query-time expansion merges canonical semantics, semantic registry runtime surfaces, ConceptNet token and phrase broadening, multilingual graph mappings, broader concept-bridge surfaces, and graph-learned domain lexicon terms. Every expansion is capped, weighted, deterministic, and source-tagged.",
              color: "#38bdf8",
            },
            {
              step: "4",
              label: "Canonical vector recall",
              detail:
                "Qdrant ANN recall for model embeddings and native vectors when indexed, with bounded SQL/exact fallback for legacy graphs or outages",
              color: "#60a5fa",
            },
            {
              step: "5",
              label: "Lexical-semantic sidecars",
              detail:
                "Representation V2 plus Semantic Signature V1 add phrase, concept, alias, transliteration, morphology, relation, value, and temporal matching beside the canonical vector",
              color: "#8b5cf6",
            },
            {
              step: "6",
              label: "Native late interaction",
              detail:
                "An additive FAIM-native symbolic interaction layer compares query/doc tokens, phrases, semantic phrases, concepts, stems, aliases, transliterations, relation cues, value cues, and temporal cues before the final score is written",
              color: "#c084fc",
            },
            {
              step: "7",
              label: "Deterministic ANN",
              detail:
                "Graph-versioned cached dense shortlist using deterministic VP-tree search, merged with sparse recall",
              color: "#a78bfa",
            },
            {
              step: "8",
              label: "7-component scoring",
              detail:
                "Cosine similarity · Novelty · Opposition · Redundancy · Recency · Usage frequency · Level penalty",
              color: "#fbbf24",
            },
            {
              step: "9",
              label: "RerankerV2",
              detail:
                "Proposition-aware deterministic reranking: scores adjusted by block_type weight, section match, graph neighbourhood, and additive late-interaction evidence",
              color: "#f97316",
            },
            {
              step: "10",
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

      <Card title="Benchmark isolation and publication gate" color="emerald">
        <div className="space-y-3 text-sm text-slate-400">
          <p>
            Reproducible benchmark jobs run with self-evolution and domain
            autonomy isolated from ingestion. Worker transactions rollback
            before retry, native and semantic vectors use batch Qdrant writes,
            and PostgreSQL remains the canonical source of truth.
          </p>
          <p>
            A result is publishable only when the dataset and commit are pinned,
            the run uses API-key authentication, health checks pass, errors are
            zero, and the report includes configuration and variance evidence.
            In zero-ML CPU fast mode (
            <code className="text-cyan-300">FAIM-Pure</code> with collision-free
            BM25+, <code className="text-cyan-300">GraphIndexArtifacts</code>{" "}
            RAM caching, vectorized{" "}
            <code className="text-cyan-300">float32</code> BLAS scoring, cached{" "}
            <code className="text-cyan-300">_maxsim_units</code> &amp;
            propositions, and <code className="text-cyan-300">RerankerV2</code>{" "}
            soft-suppression), FAIM achieved{" "}
            <code className="text-emerald-300">nDCG@10 = 0.6871</code>,{" "}
            <code className="text-emerald-300">Recall@5 = 0.7554</code>, and{" "}
            <code className="text-emerald-300">86.31 ms</code> CPU CI P50 on the
            full 5,183-doc / 300-query SciFact split ({" "}
            <code className="text-emerald-300">Publication gate: READY</code>)
            vs <code className="text-slate-300">BM25-Baseline</code> (
            <code className="text-slate-300">0.6644</code> nDCG@10 /{" "}
            <code className="text-slate-300">0.7193</code> Recall@5). Pairing
            Granite 97M Multilingual R2 raises SciFact to{" "}
            <code className="text-cyan-300">0.6900 nDCG@10</code> and{" "}
            <code className="text-cyan-300">0.7704 Recall@5</code> (140.17 ms
            P50).
          </p>
        </div>
      </Card>

      <Card title="Representation V2: Sparse Sidecars" color="purple">
        <p className="text-sm text-slate-400 mb-3">
          Alongside the 256-dim dense vector, every node has a set of sparse
          channels computed by Representation V2. These enable lexically-rich
          matching on top of vector similarity. Semantic Signature V1 extends
          this same additive sidecar path rather than replacing the core vector.
          The Weighted Expansion Layer then strengthens the query ahead of
          retrieval so alias, phrase, multilingual, and domain-memory matches
          enrich dense and sparse scoring. A Native Late-Interaction pass then
          allows these same channels to participate in fine-grained
          query/document matching before final ranking.
        </p>
        <div className="grid md:grid-cols-2 gap-2">
          {[
            [
              "word_counts",
              "Porter-stemmed token buckets: handles morphological variants",
            ],
            [
              "phrase_counts",
              "2-gram phrase frequency buckets: matches multi-word expressions",
            ],
            [
              "skip_counts",
              "Skip-gram patterns: long-range co-occurrence capture",
            ],
            [
              "semantic_phrase_counts",
              "Hashed semantic phrase and skip-phrase buckets for stronger fuzzy phrase matching",
            ],
            [
              "concept_counts",
              "Deterministic concept-family buckets mined from alias and concept-key broadening",
            ],
            [
              "morphology_counts",
              "Prefix / suffix / shape buckets for stronger morphology-level recall",
            ],
            [
              "entity_tokens",
              "Emails, URLs, UUIDs, identifiers, phone numbers",
            ],
            ["time_tokens", "Dates, years, quarters, temporal markers"],
            ["layout_tokens", "block_type + page + section encoded as tokens"],
            [
              "alias_families",
              "Known alias groups such as AI ↔ artificial intelligence",
            ],
            [
              "transliterated_tokens",
              "Cross-lingual bridging tokens such as München → muenchen",
            ],
            [
              "stem_families",
              "Stem-linked surface families preserved for explainable fuzzy matching",
            ],
            [
              "relation/value/temporal cues",
              "Deterministic cues for relations, numeric language, and time phrasing",
            ],
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

      <Card title="Weighted Expansion Engine" color="amber">
        <p className="text-sm text-slate-400 mb-4 leading-relaxed">
          Before dense recall and reranking, FAIM now runs a weighted
          deterministic expansion layer over the query itself. This is not a
          neural rewrite model. It is a bounded FAIM-native merger of multiple
          retrieval-strengthening sources.
        </p>
        <div className="grid md:grid-cols-2 gap-4 mb-4">
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
            <p className="text-xs font-mono text-amber-400 mb-1.5">
              Expansion sources
            </p>
            <ul className="space-y-1.5 text-[11px] text-slate-500 leading-relaxed">
              <li>ConceptNet token and phrase broadening</li>
              <li>Graph-local canonical semantics</li>
              <li>Multilingual concept and translation mappings</li>
              <li>Graph-learned domain lexicon terms</li>
            </ul>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
            <p className="text-xs font-mono text-amber-400 mb-1.5">
              Safety rules
            </p>
            <ul className="space-y-1.5 text-[11px] text-slate-500 leading-relaxed">
              <li>Capped globally to avoid runaway broadening</li>
              <li>Weighted and stable across repeated runs</li>
              <li>Source-tagged for explainability</li>
              <li>Additive only: no change to native vector identity</li>
            </ul>
          </div>
        </div>
        <p className="text-[11px] text-slate-500 leading-relaxed">
          In explain mode, FAIM can expose the expanded query text, source
          counts, and per-expansion weights/origins so the broadening path stays
          inspectable in production.
        </p>
      </Card>

      <Card title="Native Late Interaction" color="purple">
        <p className="text-sm text-slate-400 mb-4 leading-relaxed">
          After expansion and shortlist generation, FAIM now applies a
          fine-grained symbolic interaction layer inspired by the efficiency
          goals of late-interaction retrieval systems, but implemented as
          FAIM-native deterministic math instead of transformer token vectors.
        </p>
        <div className="grid md:grid-cols-2 gap-4 mb-4">
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
            <p className="text-xs font-mono text-purple-400 mb-1.5">
              Interaction channels
            </p>
            <ul className="space-y-1.5 text-[11px] text-slate-500 leading-relaxed">
              <li>Exact token overlap</li>
              <li>Phrase and semantic-phrase overlap</li>
              <li>Concept-family overlap</li>
              <li>Alias and transliteration bridges</li>
              <li>Stem and morphology overlap</li>
              <li>Relation, value, and temporal cue alignment</li>
            </ul>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
            <p className="text-xs font-mono text-purple-400 mb-1.5">
              Safety rules
            </p>
            <ul className="space-y-1.5 text-[11px] text-slate-500 leading-relaxed">
              <li>Additive only: base scorer still stands on its own</li>
              <li>Deterministic and explainable per channel</li>
              <li>Bounded contribution into the final score</li>
              <li>No change to the canonical native vector contract</li>
            </ul>
          </div>
        </div>
        <p className="text-[11px] text-slate-500 leading-relaxed">
          In explain mode, FAIM surfaces a per-channel breakdown so you can see
          whether a match was helped by phrase overlap, alias bridging, concept
          alignment, value cues, or time cues.
        </p>
      </Card>

      <Card title="Cross-Lingual Bridges" color="emerald">
        <p className="text-sm text-slate-400 mb-4 leading-relaxed">
          FAIM’s multilingual layer now spans EN, DE, ES, FR, IT, PT, and NL
          instead of being limited to the older narrow bridge. The deterministic
          multilingual surface supports broader concept-key mapping,
          transliteration-safe matching, and graph-local multilingual bridge
          reuse across the shipped enterprise language set.
        </p>
        <div className="grid md:grid-cols-2 gap-4 mb-4">
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
            <p className="text-xs font-mono text-emerald-400 mb-1.5">
              What widened
            </p>
            <ul className="space-y-1.5 text-[11px] text-slate-500 leading-relaxed">
              <li>Static lexicon resources now load from multiple TSVs</li>
              <li>
                Compressed enterprise lexicon packs now load directly at runtime
              </li>
              <li>Language detection spans EN, DE, ES, FR, IT, PT, and NL</li>
              <li>Token and phrase surface matching improved</li>
              <li>
                Cross-language bridge forms remain bounded and explainable
              </li>
            </ul>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
            <p className="text-xs font-mono text-emerald-400 mb-1.5">
              Why it matters
            </p>
            <ul className="space-y-1.5 text-[11px] text-slate-500 leading-relaxed">
              <li>Better zero-setup multilingual recall</li>
              <li>Stronger cross-language concept matching</li>
              <li>Tens of thousands of shipped multilingual surface forms</li>
              <li>No neural translation dependency added</li>
              <li>No change to the canonical `v_native` contract</li>
            </ul>
          </div>
        </div>
      </Card>

      <Card title="IWQE: Inheritance-Weighted Query Expansion" color="indigo">
        <p className="text-sm text-slate-400 mb-4 leading-relaxed">
          Dynamic query reformulation mechanism that runs on retrieval and
          rewrites the query vector in 256-dimensional space, blending taxonomic
          ancestry and semantic neighbors before final scoring.
        </p>
        <div className="grid md:grid-cols-2 gap-4 mb-4">
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
            <p className="text-xs font-mono text-indigo-400 mb-1.5">
              Layer A: Taxonomic Inheritance
            </p>
            <p className="text-[11px] text-slate-500 leading-relaxed">
              Adds contribution vectors from parents scaled by edge weights and
              parent semantic importance, preserving context ancestry.
            </p>
            <div className="mt-3 p-2 rounded-lg bg-slate-950 border border-slate-800 text-[10px] font-mono text-cyan-400">
              {"q_expanded = q + sum( alpha * fraction * weight * v_parent )"}
            </div>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
            <p className="text-xs font-mono text-indigo-400 mb-1.5">
              Layer B: Semantic Associations
            </p>
            <p className="text-[11px] text-slate-500 leading-relaxed">
              Blends semantic neighbors (synonyms, translations, domain terms)
              using halved blending strength for taxonomic dominance.
            </p>
            <div className="mt-3 p-2 rounded-lg bg-slate-950 border border-slate-800 text-[10px] font-mono text-cyan-400">
              {
                "q_expanded = q_expanded + sum( alpha_sem * strength * v_neighbor )"
              }
            </div>
          </div>
        </div>
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60 flex items-center justify-between text-xs">
          <span className="text-slate-500">L2 Re-normalization Lock:</span>
          <span className="font-mono text-indigo-300">
            {"q_final = q_expanded / ||q_expanded||_2"}
          </span>
        </div>
      </Card>

      <Card title="TCT: Transitive Contradiction Traversal" color="red">
        <p className="text-sm text-slate-400 mb-4 leading-relaxed">
          Real-world facts change. TCT resolves conflicts transitivity: if node
          C inherits from B, and B is in opposition with A, the system detects
          that C conflicts with A.
        </p>
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60 font-mono text-[10px] text-cyan-400 mb-4 text-center">
          {
            "exists a in Ancestors(c_i), b in Ancestors(c_j) s.t. (a, b) in E_opposition"
          }
        </div>
        <div className="grid md:grid-cols-2 gap-4">
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
            <p className="text-xs font-mono text-red-400 mb-1.5">
              Soft Suppression (include_historical = true)
            </p>
            <p className="text-[11px] text-slate-500 leading-relaxed">
              Outdated nodes are retained in final results but annotated with
              temporal status (HISTORICAL / CURRENT) and superseded lineage
              links to trace history.
            </p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
            <p className="text-xs font-mono text-red-400 mb-1.5">
              Hard Suppression (include_historical = false)
            </p>
            <p className="text-[11px] text-slate-500 leading-relaxed">
              Older, superseded nodes are filtered out completely from final
              output, ensuring the retrieval engine operates on a mathematically
              clean, current state.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}

function SectionCortex() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">
          MCP &amp; Agent Access
        </h2>
        <p className="text-slate-400 leading-relaxed">
          Zero-LLM deterministic memory access for external AI agents over
          Remote MCP (/mcp), OAuth 2.1 + PKCE, offline faim-mcp CLI, and scoped
          API keys.
        </p>
      </div>

      <VisualDomainDiagram kind="mcp" />

      <Card title="Remote MCP + OAuth 2.1 / PKCE" color="cyan">
        <p className="text-sm text-slate-400 leading-relaxed mb-4">
          Connect Cursor, Claude Code / Desktop, and VS Code to your
          tenant-isolated knowledge graph with automatic browser login and
          1-click session revocation in Dashboard → MCP.
        </p>
        <div className="grid md:grid-cols-2 gap-3 mb-6">
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
            <p className="text-xs font-mono text-cyan-400 mb-1.5">
              6 Exposed MCP Tools
            </p>
            <p className="text-[11px] text-slate-500 leading-relaxed">
              faim_memory_write, faim_memory_search, faim_query,
              faim_ingest_text, faim_memory_get, and faim_graph_surface.
            </p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
            <p className="text-xs font-mono text-cyan-400 mb-1.5">
              Offline CLI &amp; Python SDK
            </p>
            <p className="text-[11px] text-slate-500 leading-relaxed">
              Run faim-mcp locally over stdio with OAuth credentials or a
              one-time API key from Dashboard → API Keys.
            </p>
          </div>
        </div>

        <div className="p-4 rounded-xl border border-cyan-500/10 bg-cyan-500/[0.02]">
          <p className="text-xs font-bold text-cyan-400 uppercase tracking-widest mb-3">
            Access &amp; Embedding Spec
          </p>
          <ul className="grid grid-cols-2 gap-x-6 gap-y-2 text-[10px] text-slate-500 font-mono">
            <li className="flex justify-between">
              <span>MCP Transport</span>
              <span className="text-slate-300">Streamable HTTP + stdio</span>
            </li>
            <li className="flex justify-between">
              <span>OAuth Flow</span>
              <span className="text-slate-300">OAuth 2.1 + PKCE</span>
            </li>
            <li className="flex justify-between">
              <span>Semantic Embeddings</span>
              <span className="text-slate-300">Built-in multilingual</span>
            </li>
            <li className="flex justify-between">
              <span>Hop Budget</span>
              <span className="text-slate-300">graph_max_hops (1–24)</span>
            </li>
            <li className="flex justify-between">
              <span>API Keys</span>
              <span className="text-slate-300">
                One-time + permanent delete
              </span>
            </li>
            <li className="flex justify-between">
              <span>LLM Dependency</span>
              <span className="text-slate-300">Zero-LLM core</span>
            </li>
          </ul>
        </div>
      </Card>

      <Card title="Direct Idempotent Memory Writes" color="amber">
        <p className="text-sm text-slate-400 leading-relaxed">
          Memory writes execute deterministically through idempotent REST and
          MCP endpoints (faim_memory_write, faim_ingest_text) with full tenant
          isolation, provenance tracking, and no approval-queue bottleneck.
        </p>
      </Card>
    </div>
  );
}

function SectionCortexRuntime() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">
          Query &amp; Hop Runtime Architecture
        </h2>
        <p className="text-slate-400 leading-relaxed">
          The deterministic retrieval loop over your knowledge graph. Callers
          and MCP agents control traversal depth via graph_max_hops (1 to 24,
          defaulting to 2) while hybrid vector, lexical, and graph signals rank
          evidence with provenance.
        </p>
      </div>

      <VisualGraphTopology />

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="Runtime Phases" color="cyan">
          <ul className="space-y-2 text-xs text-slate-400">
            <li>
              <strong>Query Prep:</strong> Normalizes tokens, canonical forms,
              aliases, and temporal cues deterministically.
            </li>
            <li>
              <strong>Agent Hop Budget:</strong> Uses caller-specified
              graph_max_hops (1–24, default 2) on /api/v1/query and
              /api/v1/memory/search.
            </li>
            <li>
              <strong>Retrieval Fusion:</strong> Combines v_native, built-in
              multilingual embeddings, Representation V2, and Semantic Signature
              V1.
            </li>
            <li>
              <strong>Late Interaction:</strong> Adds a symbolic query/document
              interaction score before final ranking so fuzzy phrase and concept
              matches stay inspectable.
            </li>
            <li>
              <strong>Graph Traversal:</strong> Bounded multi-hop diffusion and
              exact path tracing with temporal conflict checks.
            </li>
            <li>
              <strong>Reranker V2:</strong> Deterministic score fusion across
              dense, sparse, and graph signals.
            </li>
            <li>
              <strong>Evidence Delivery:</strong> Returns ranked chunks,
              provenance, and traversal-path metadata to your agent or app.
            </li>
          </ul>
        </Card>

        <Card
          title="Cognitive Modes (The Deterministic Engine)"
          color="emerald"
        >
          <div className="overflow-hidden rounded-lg border border-slate-800 bg-slate-950/40">
            <table className="w-full text-[10px] text-left">
              <thead className="bg-slate-900/50 text-slate-500 uppercase tracking-tighter">
                <tr>
                  <th className="px-3 py-2">Mode</th>
                  <th className="px-3 py-2">Focus</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                <tr>
                  <td className="px-3 py-2 text-cyan-400 font-bold">
                    TIMELINE
                  </td>
                  <td className="px-3 py-2 text-slate-400">
                    Chronological event sequencing
                  </td>
                </tr>
                <tr>
                  <td className="px-3 py-2 text-red-400 font-bold">
                    CONTRADICTION
                  </td>
                  <td className="px-3 py-2 text-slate-400">
                    Conflict detection & resolution
                  </td>
                </tr>
                <tr>
                  <td className="px-3 py-2 text-purple-400 font-bold">
                    CONSOLIDATE
                  </td>
                  <td className="px-3 py-2 text-slate-400">
                    Fragmented data merging
                  </td>
                </tr>
                <tr>
                  <td className="px-3 py-2 text-blue-400 font-bold">
                    PROVENANCE
                  </td>
                  <td className="px-3 py-2 text-slate-400">
                    Full evidence lineage tracing
                  </td>
                </tr>
                <tr>
                  <td className="px-3 py-2 text-amber-400 font-bold">
                    INVESTIGATE
                  </td>
                  <td className="px-3 py-2 text-slate-400">
                    Bounded causal analysis with planner-selected hop limits
                  </td>
                </tr>
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

      <Card title="Bounded Multi-Hop Reasoning Spec" color="indigo">
        <div className="grid md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <p className="text-sm text-slate-400 leading-relaxed">
              FAIM uses a caller-controlled bounded hop runtime. Simple lookups
              can stay at 1–2 hops, while investigative queries from agents or
              API callers can set{" "}
              <code className="text-indigo-300">graph_max_hops</code> up to 24
              (default 2) with deterministic pruning and path auditability.
            </p>
            <div className="flex gap-4">
              <div className="flex-1 p-3 rounded-lg border border-indigo-500/10 bg-indigo-500/[0.02]">
                <p className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest mb-1">
                  Default Runtime
                </p>
                <p className="text-xl font-bold text-white">1-24</p>
              </div>
              <div className="flex-1 p-3 rounded-lg border border-indigo-500/10 bg-indigo-500/[0.02]">
                <p className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest mb-1">
                  Configurable Ceiling
                </p>
                <p className="text-xl font-bold text-white">128</p>
              </div>
            </div>
          </div>
          <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/40">
            <p className="text-xs font-bold text-indigo-400 uppercase tracking-widest mb-3">
              Diffusion Parameters
            </p>
            <ul className="space-y-2 text-[10px] text-slate-500 font-mono">
              <li className="flex justify-between">
                <span>Planner Ceiling</span>
                <span className="text-slate-300">
                  24 default / 128 max config
                </span>
              </li>
              <li className="flex justify-between">
                <span>Traversal Guards</span>
                <span className="text-slate-300">
                  frontier + expansion caps
                </span>
              </li>
              <li className="flex justify-between">
                <span>Inference Path</span>
                <span className="text-slate-300">
                  bounded, deterministic, cycle-safe
                </span>
              </li>
              <li className="flex justify-between">
                <span>Provenance</span>
                <span className="text-slate-300">
                  exact path metadata + citations
                </span>
              </li>
            </ul>
          </div>
        </div>
      </Card>

      <Card title="Reasoning Depth (What is a Hop?)" color="cyan">
        <div className="space-y-4">
          <p className="text-sm text-slate-400 leading-relaxed">
            In FAIM, a <strong>Hop</strong> is a single semantic step between
            two nodes. The runtime uses bounded hop budgets rather than
            unlimited traversal, so the planner can stay deterministic while
            still reaching deeper evidence when needed.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/40">
              <p className="text-xs font-bold text-cyan-400 mb-2 uppercase tracking-widest">
                1-4 Hops
              </p>
              <p className="text-[10px] text-slate-500">
                Surface-level retrieval. Answers "Who", "What", and "When".
              </p>
            </div>
            <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/40">
              <p className="text-xs font-bold text-purple-400 mb-2 uppercase tracking-widest">
                5-24 Hops
              </p>
              <p className="text-[10px] text-slate-500">
                Deep synthesis and investigation. Connects documents, facts,
                timelines, and dependencies through bounded exact traversal.
              </p>
            </div>
            <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/40">
              <p className="text-xs font-bold text-amber-400 mb-2 uppercase tracking-widest">
                24-128 Hops
              </p>
              <p className="text-[10px] text-slate-500">
                Advanced bounded deployments only. Higher ceilings remain
                deterministic but must still obey pruning, frontier, and
                expansion guards.
              </p>
            </div>
          </div>
        </div>
      </Card>

      <Card title="Query Life-Cycle & End-to-End Proof" color="amber">
        <p className="text-sm text-slate-400 mb-4 leading-relaxed">
          FAIM processes every query through a 5-stage deterministic life-cycle,
          moving from canonical query preparation to pulse-v2 explain ledgers
          and provenance-backed evidence delivery.
        </p>
        <div className="space-y-4">
          {[
            {
              phase: "Stage 1: Input & Auto-Classification",
              desc: "Query text (e.g., 'Why is the database failing?') is processed by the deterministic semantic router, resolving intents (e.g., FAIL, DATABASE) and dynamically selecting the best cognitive task mode.",
            },
            {
              phase: "Stage 2: Bounded Memory Discovery",
              desc: "FAIM executes bounded multi-hop traversal through relevant document, config, and relational nodes up to graph_max_hops. The 3D FIG View renders the pulse-v2 path and query evidence events attached to the current explain payload.",
            },
            {
              phase: "Stage 3: Causal Traceback Proof",
              desc: "Identifies semantic junctions along the bounded traversal frontier where recent changes or properties BLOCKS or ENABLES target states, establishing a verifiable causal proof chain.",
            },
            {
              phase: "Stage 4: Output & Multi-Signal Badges",
              desc: "Streams citation-first extracted sentences annotated with [INVESTIGATE], [CONTRADICTION], or [PROVENANCE] badges, highlighting specific graph pathways in the FIG overlay.",
            },
            {
              phase: "Stage 5: Provenance & Idempotent Memory Updates",
              desc: "Returns ranked evidence with provenance and traversal receipts, while any new agent memory writes execute deterministically through idempotent REST or MCP endpoints.",
            },
          ].map((p, idx) => (
            <div
              key={p.phase}
              className="flex gap-4 p-3 rounded-xl border border-slate-800 bg-slate-950/60"
            >
              <span className="text-xs font-mono font-bold text-amber-400 shrink-0 w-6 h-6 rounded-lg bg-amber-500/10 flex items-center justify-center">
                {idx + 1}
              </span>
              <div>
                <p className="text-xs font-bold text-white mb-0.5">{p.phase}</p>
                <p className="text-[11px] text-slate-500 leading-relaxed">
                  {p.desc}
                </p>
              </div>
            </div>
          ))}
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
          Interactive 3D visualization for exploring nodes, pulse-v2 reasoning
          paths, memory temperatures, and structural provenance.
        </p>
      </div>

      <VisualDomainDiagram kind="fig" />

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="Pulse-v2 Reason Ledger" color="purple">
          <p className="text-sm text-slate-400 leading-relaxed">
            During query traversal, FIG View reads the backend pulse-v2 ledger:
            graph hops, expansion sources, semantic registry signals,
            domain-memory links, reranker factors, and late-interaction matches.
            Glow and path motion are driven by those events, while
            raycast-invisible visual layers keep node dragging responsive.
          </p>
        </Card>

        <Card title="GPU Resource Hardening" color="red">
          <ul className="space-y-2 text-xs text-slate-400">
            <li className="flex gap-2">
              <span className="text-red-400">→</span>
              <strong>Static Asset Registry:</strong> Reuses 3D geometries and
              materials to eliminate memory leaks.
            </li>
            <li className="flex gap-2">
              <span className="text-red-400">→</span>
              <strong>Render Loop Memoization:</strong> Prevents unnecessary
              re-renders during high-density graph manipulation.
            </li>
            <li className="flex gap-2">
              <span className="text-red-400">→</span>
              <strong>Gravitational Anchor:</strong> Physics constants tuned
              (centerStrength: 0.5) to keep atoms from drifting during
              interaction.
            </li>
          </ul>
        </Card>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="Canvas: Visualization Modes" color="cyan">
          <div className="space-y-3 text-sm text-slate-400">
            {[
              {
                mode: "Surface",
                desc: "Default view showing up to 500 nodes.",
              },
              {
                mode: "Neighborhood",
                desc: "K-hop expansion from a selected node.",
              },
              { mode: "Timeline", desc: "Nodes arranged by creation time." },
              {
                mode: "Path",
                desc: "The shortest semantic path connecting two nodes.",
              },
              {
                mode: "Analyze",
                desc: "Full graph with live scorecard (density, entropy).",
              },
            ].map((m) => (
              <div key={m.mode}>
                <p className="text-cyan-400 font-mono text-xs">{m.mode}</p>
                <p className="text-[11px] text-slate-500">{m.desc}</p>
              </div>
            ))}
          </div>
        </Card>

        <Card title="Canvas: 6 Cognitive Overlays" color="purple">
          <div className="space-y-3 text-sm text-slate-400">
            {[
              { mode: "None", desc: "Standard physical 3D graph structure." },
              {
                mode: "Cognitive",
                desc: "Colors nodes by their deterministic semantic router classification (Logic, Evidence, contradiction).",
              },
              {
                mode: "Retrieval",
                desc: "Highlights nodes currently being read into the active MemoryRefSet.",
              },
              {
                mode: "Evolution",
                desc: "Visualizes nodes that have changed or evolved over time (State Delta).",
              },
              {
                mode: "Temporal",
                desc: "Spectrum from oldest to newest based on the createdAt timestamp.",
              },
              {
                mode: "Causality",
                desc: "Highlights targeted CAUSES, BLOCKS, and ENABLES relational edges.",
              },
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
        <h2 className="text-2xl font-bold text-white mb-2">
          Subscription Plans
        </h2>
        <p className="text-slate-400 leading-relaxed">
          Workspaces scale cleanly by knowledge graph nodes, reasoning depth,
          and dedicated isolation without token metering.
        </p>
      </div>

      <VisualDomainDiagram kind="billing" />

      <div className="grid md:grid-cols-2 gap-4">
        {[
          {
            name: "Explorer ($0 / forever)",
            desc: "1,000 cognitive nodes, 1-hop reasoning, 3D FIG View, and basic semantic search.",
          },
          {
            name: "Architect ($29 / month)",
            desc: "10,000 nodes, 4-hop reasoning, full Semantic Alias Engine, Graph Snapshots, and REST API access.",
          },
          {
            name: "Neural ($99 / month)",
            desc: "100,000 nodes, bounded multi-hop reasoning (up to 24 hops), cross-graph synthesis, and priority workers.",
          },
          {
            name: "Matrix (Custom)",
            desc: "Unlimited nodes and hops, private memory shards, dedicated GPU workers, SSO, and on-premise deployment.",
          },
        ].map((tier) => (
          <Card
            key={tier.name}
            title={tier.name}
            color={tier.name.startsWith("Neural") ? "purple" : "default"}
          >
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
          FAIM Native extractor handles structured and scanned document formats
          deterministically using PyMuPDF, python-docx, openpyxl, python-pptx,
          and 300 DPI Tesseract OCR.
        </p>
      </div>

      <VisualDomainDiagram kind="extraction" />

      <Card title="PDF: Multi-column, Tables, and Scanned" color="red">
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
                "Render at 300 DPI (up from 180: better OCR accuracy)",
                "Minimum 2000px width upscale before OCR",
                "Autocontrast + sharpen preprocessing",
                "Tesseract PSM 3: automatic layout detection",
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
              "python-docx: zero ML",
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
              "python-pptx: zero ML",
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
              "data_only=True: computed cell values",
              "Header row heuristic detection",
              "Sheet name anchoring per block",
              "Row start/end range stored in anchor",
              "openpyxl: zero ML",
            ].map((f) => (
              <li key={f} className="flex gap-2">
                <span className="text-emerald-400 shrink-0">✓</span>
                {f}
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card title="Block Anchor: Per-Block Structural Metadata" color="default">
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
          Every document traverses the same deterministic pipeline so no
          structural metadata is lost between upload and graph retrieval.
        </p>
      </div>

      <VisualArchitectureFlow />

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
              label: "Dense Sync",
              color: "#a78bfa",
              detail:
                "Node upserted into deterministic dense shortlist index for fast semantic retrieval",
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
          from the Storage maintenance routes. This re-computes all sparse
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
        <h2 className="text-2xl font-bold text-white mb-2">
          Security &amp; Isolation
        </h2>
        <p className="text-slate-400 leading-relaxed">
          FAIM is engineered for regulated and air-gapped environments,
          prioritizing cryptographic provenance, envelope key rotation, and
          strict tenant scoping.
        </p>
      </div>

      <VisualDomainDiagram kind="security" />

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
              "Duplicate data never enters the graph: SHA-256 collision detection before every insert.",
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
              "Every API request carries a JWT. graph_id is derived from the verified token: never from user input.",
            ],
            [
              "Storage API enforcement",
              "graph_id is validated on every storage operation: read, write, prune, and rebuild.",
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
              "Zero external cloud dependency: local computation on CPU or GPU",
              "Pre-bundled local Granite 97M (no runtime downloads required) plus zero-ML FAIM-Pure",
              "All secrets via environment variables: no hardcoded keys",
              "Entrypoint gating: refuses to start with a stale database schema",
              "Non-root container user: principle of least privilege",
              "Zero heavy document-ML daemon: pure deterministic layout parsing",
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
              "Historical plaintext raw blobs can be migrated through the guarded raw-reencryption execute/job routes before hard delete",
              "Tenant crypto rotation rewraps tenant DEKs under the active master key; encrypted payloads stay untouched",
              "Provenance: every node traces back to original file + page",
              "Download original: retrieve raw blob by raw_id at any time",
              "graph_version bump on every prune: audit trail preserved",
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
        <h2 className="text-2xl font-bold text-white mb-2">
          Deployment &amp; Configuration
        </h2>
        <p className="text-slate-400 leading-relaxed">
          Deployment uses a single root <code>docker-compose.yml</code> and root{" "}
          <code>.env</code> configuration across local CPU/GPU hosts and
          production VPS instances.
        </p>
      </div>

      <VisualDomainDiagram kind="deployment" />

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="Local Stack (CPU & GPU)" color="cyan">
          <ul className="space-y-2 text-sm text-slate-400">
            {[
              "Copy .env.example to .env as the single environment source of truth.",
              "docker compose up -d starts PostgreSQL, Redis, Qdrant, API, workers, and frontend.",
              "Set TORCH_INDEX_URL=https://download.pytorch.org/whl/cu124, FAIM_CONTAINER_RUNTIME=nvidia, NVIDIA_VISIBLE_DEVICES=all in .env for CUDA GPU passthrough.",
              "npm run faim:ps and /ready verify service health across all containers.",
            ].map((item) => (
              <li key={item} className="flex gap-2">
                <span className="text-cyan-400 shrink-0">→</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </Card>
        <Card title="VPS & Reverse Proxy" color="purple">
          <ul className="space-y-2 text-sm text-slate-400">
            {[
              "Use the same docker-compose.yml with --profile vps and keep host .env outside version control.",
              "deploy/Caddyfile.vps and deploy/nginx.conf provide ready-to-use reverse-proxy templates.",
              "scripts/vps_sync.sh excludes docs, tests, Runtime/ scratch folders, and secret env files.",
              "scripts/vps_deploy_ci.sh validates .env and pulls pre-built images cleanly without compose down.",
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
                "curl -fsS http://localhost:8000/health && curl -fsS http://localhost:8000/ready && curl -fsS http://localhost:8000/version",
                "Check FAIM_CONTAINER_RUNTIME / FAIM_FAST_ML_EMBEDDING / FAIM_EMBEDDING_DEVICE for CPU vs GPU profile",
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
          "240 n-gram dims + 16 text-stat dims (pure deterministic math)",
          "done",
        ],
        [
          "Hot / Warm / Cold tiers",
          "Auto-classified by last_access + touch_count at retrieval time",
          "done",
        ],
        [
          "Cold pruning",
          "90d configurable, dry-run preview available from Storage maintenance routes",
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
          "Cached repeat query hits bypass full graph rescoring",
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
          "PyMuPDF find_tables(): no double-extraction",
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
          "Structured query modes",
          "Direct, Timeline, Contradiction-aware, and Provenance-first evidence retrieval",
          "done",
        ],
        [
          "Conversational bypass",
          "Greetings skip FAIM retrieval: no false document retrievals",
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
          "Violet cluster X badge in node header: populated after running Topic Clustering",
          "done",
        ],
        [
          "Pulse-v2 reason ledger",
          "Backend graph/query events explain node glow, path motion, inspector proof, relation traces, and semantic-layer contributions",
          "done",
        ],
        [
          "Long-term toggle",
          "Per-node ♾ long-term protection toggle in inspector: immediate API write",
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
          Benchmarks &amp; Evaluation
        </h2>
        <p className="text-slate-400 leading-relaxed">
          Reproducible full-split BeIR (SciFact, NFCorpus, ArguAna) and LoCoMo
          evaluations across zero-ML FAIM-Pure CPU and Granite 97M hybrid
          profiles, paired with runtime graph scorecards and StressRunner load
          probes.
        </p>
      </div>

      <VisualBenchmarkChart />

      <BenchmarkResultsBoard compact showFullPageLink />

      <Card title="Runtime Evaluation & Stress Testing Surface" color="cyan">
        <div className="space-y-3 text-xs text-slate-400">
          <p className="leading-relaxed">
            Every reported figure comes from executed evaluation runs or live
            telemetry endpoints rather than synthetic approximations:
          </p>
          {[
            [
              "BeIR Retrieval Harness",
              "Evaluates SciFact (5,183 docs / 300 queries), NFCorpus (323 queries), and ArguAna against BM25 and standalone dense baselines under identical corpus splits.",
            ],
            [
              "Graph Topology Scorecard",
              "Exposed at GET /api/v1/metrics/scorecard, computing live Density D, Shannon Edge Entropy H, and Spectral Radius lambda directly from the persisted graph.",
            ],
            [
              "StressRunner Load Probes",
              "Executes progressive concurrency streams [1, 2, 5, 10] measuring ingest throughput, P50/P95/P99 latency, and plateau saturation detection while checking graph invariants.",
            ],
            [
              "Signed & Reproducible Reports",
              "Every benchmark run records active engine mode (FAIM_FAST_ML_EMBEDDING), hardware profile, and SHA-256 verification artifacts.",
            ],
          ].map(([k, v]) => (
            <div
              key={k}
              className="rounded-xl border border-slate-800 bg-slate-950/50 p-3"
            >
              <p className="font-mono text-cyan-300 font-semibold mb-1">{k}</p>
              <p className="text-slate-400 leading-relaxed">{v}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function SectionRoadmap() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">
          Architecture Milestones
        </h2>
        <p className="text-slate-400 leading-relaxed">
          Shipped capabilities across the memory core, retrieval engine,
          security hardening, and upcoming scale enhancements.
        </p>
      </div>

      <div className="space-y-3">
        {[
          {
            phase: "Core Engine",
            label: "Deterministic Memory + Knowledge Graph",
            status: "done",
            detail:
              "Opposition, inheritance, temporal, semantic edges, IDF weighting, Porter stemming, entity expansion, stop-word removal, graph diffusion, and deterministic core scoring: all complete and tested.",
          },
          {
            phase: "Storage",
            label: "Hot/Warm/Cold Tiers + Cold Pruning",
            status: "done",
            detail:
              "Automatic 3-tier memory temperature classification by last_access and touch_count. Dry-run + live pruning from Storage maintenance routes. FIG View shows temperature badge per node.",
          },
          {
            phase: "Structure",
            label: "Rich Block Anchors + FIG Structure Panel",
            status: "done",
            detail:
              "block_type, page, section, column, row ranges exposed per node in FIG View Inspector as a dedicated Structure section.",
          },
          {
            phase: "Context",
            label: "LLM Memory Inventory Context",
            status: "done",
            detail:
              "System prompt includes document inventory (file names, types, node counts, ingestion dates) so agents can answer meta-questions about indexed knowledge.",
          },
          {
            phase: "Explorer UI",
            label: "FIG Memory Signal Cards + Prev/Next Navigation",
            status: "done",
            detail:
              "Novelty, redundancy, recency signal cards with color coding per node. Deterministic Prev/Next navigation through relevant nodes.",
          },
          {
            phase: "Clustering",
            label: "Deterministic Topic Clustering",
            status: "done",
            detail:
              "Deterministic k-means++ on v_native vectors. Auto-selects K = sqrt(N/2), seeded from graph_id for reproducibility. cluster_id stored on every node. Query engine scopes recall to top-2 clusters before full scan.",
          },
          {
            phase: "Retention",
            label: "Long-term Memory Preservation",
            status: "done",
            detail:
              "long_term flag (BOOLEAN) on every node. Nodes marked long-term are never deleted by cold pruning regardless of age or access count. Toggle per-node from FIG View Inspector.",
          },
          {
            phase: "Security",
            label: "Historical Raw Re-encryption",
            status: "done",
            detail:
              "Guarded raw-reencryption execute/job routes migrate legacy plaintext raw blobs into encrypted storage, update references in place, and record maintenance history.",
          },
          {
            phase: "Multimodal",
            label: "Figure / Diagram Nodes",
            status: "done",
            detail:
              "PyMuPDF image blocks detected as inline figures on text pages. block_type=figure nodes created with spatial bbox anchor (x0/y0/x1/y1, area fraction, page), excluded from duplicate text extraction.",
          },
          {
            phase: "Hybrid Mode",
            label: "Dynamic CPU/GPU Embedding Routing + Fail-Open Fallbacks",
            status: "done",
            detail:
              "FAIM_FAST_ML_EMBEDDING=auto seamlessly toggles CPU zero-ML FAIM-Pure vs GPU Granite 97M Dense at zero downtime, while preserving cached graph lookup and fail-open embedding fallbacks.",
          },
          {
            phase: "Evaluation",
            label: "Multi-Harness Benchmark Suite",
            status: "done",
            detail:
              "Golden Signals (latency/traffic/errors/saturation), stress testing with saturation point detection, anomaly alerts, BEIR SciFact & NFCorpus, MuSiQue multi-hop, and exportable SHA-256 hashed reports.",
          },
          {
            phase: "Scale",
            label: "Block-Max WAND & Deterministic VP-Tree ANN",
            status: "done",
            detail:
              "Sparse Block-Max WAND shortlist combined with a graph-versioned deterministic VP-tree dense index for scalable retrieval.",
          },
          {
            phase: "Planned",
            label: "Self-organizing Cluster Entropy",
            status: "planned",
            detail:
              "When graph entropy exceeds a configured threshold, automatically trigger re-clustering of cold zones so graphs self-organize over time.",
          },
          {
            phase: "Planned",
            label: "Distributed Sharded Index Federation",
            status: "planned",
            detail:
              "Cross-shard WAND + federated graph diffusion across horizontally partitioned tenant clusters for multi-million-node deployments.",
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
        <h2 className="text-2xl font-bold text-white mb-2">
          Canonical Semantics Pipeline
        </h2>
        <p className="text-slate-400 leading-relaxed">
          FAIM matches concepts using deterministic lemmatization, alias
          canonicalization, and the 2,319,589-term Semantic Registry instead of
          relying on stochastic query rewriting.
        </p>
      </div>

      <VisualLexiconDistribution />

      <div className="grid md:grid-cols-3 gap-4">
        <Card title="Porter Stemmer & Lemmatization" color="cyan">
          <p className="text-sm text-slate-400 leading-relaxed">
            Every text node is normalized by reducing terms to their base roots
            via a deterministic, rule-based Porter Stemmer. This eliminates the
            need to run costly learned lemmatization engines on every search
            loop.
          </p>
        </Card>
        <Card title="Acronym Expansion Registry" color="purple">
          <p className="text-sm text-slate-400 leading-relaxed">
            Acronyms (like "ROI" or "CAGR") are expanded deterministically
            during text tokenization, matching their canonical form and ensuring
            exact search coverage.
          </p>
        </Card>
        <Card title="O(1) Stop Word Filtering" color="amber">
          <p className="text-sm text-slate-400 leading-relaxed">
            High-frequency, low-semantic-value words (e.g., "the", "is") are
            aggressively stripped out using a compiled <code>frozenset</code>{" "}
            dictionary before intent matching, preventing vector space dilution.
          </p>
        </Card>
      </div>

      <Card title="Distributional Synonyms & ConceptNet" color="amber">
        <p className="text-sm text-slate-400 leading-relaxed mb-4">
          Unsupervised synonyms are mined using Jaccard and PMI co-occurrence
          calculations from the active corpus. Broad semantic associations are
          linked using the local ConceptNet-derived lexical archive, the
          semantic registry runtime, and built-in multilingual embeddings.
        </p>
        <Code>{`PMI(w_1, w_2) = log_2 ( P(w_1, w_2) / (P(w_1) * P(w_2)) )
synonym_edge = PMI >= tau_pmi AND jaccard >= tau_jaccard`}</Code>
      </Card>

      <Card
        title="ConceptNet vs. Semantic Registry vs. Dense Embeddings"
        color="indigo"
      >
        <p className="text-sm text-slate-400 leading-relaxed mb-4">
          FAIM splits lexical broadening, semantic lookup, and task routing into
          separate deterministic layers.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-400 border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-slate-300 font-mono">
                <th className="py-2 px-3">Layer</th>
                <th className="py-2 px-3">Size</th>
                <th className="py-2 px-3">Purpose</th>
                <th className="py-2 px-3">Execution</th>
                <th className="py-2 px-3">Example</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/40">
              <tr>
                <td className="py-2 px-3 font-bold text-white">
                  ConceptNet Lexicon
                </td>
                <td className="py-2 px-3 text-cyan-400 font-mono">
                  2,172,991 terms
                </td>
                <td className="py-2 px-3">Global Lexical Flexibility</td>
                <td className="py-2 px-3">Pre-Processing</td>
                <td className="py-2 px-3 italic">
                  "residing" → ["dwelling", "living"]
                </td>
              </tr>
              <tr>
                <td className="py-2 px-3 font-bold text-white">
                  Semantic Registry Runtime
                </td>
                <td className="py-2 px-3 text-emerald-400 font-mono">
                  2.31M+ shipped term base
                </td>
                <td className="py-2 px-3">Combined semantic lookup</td>
                <td className="py-2 px-3">Query expansion</td>
                <td className="py-2 px-3 italic">
                  "rcp revenue latency" → graph-aware semantic broadening
                </td>
              </tr>
              <tr>
                <td className="py-2 px-3 font-bold text-white">
                  Multilingual Dense Embeddings
                </td>
                <td className="py-2 px-3 text-purple-400 font-mono">
                  Built-in multilingual
                </td>
                <td className="py-2 px-3">Semantic Recall</td>
                <td className="py-2 px-3">Dense Vector Scoring</td>
                <td className="py-2 px-3 italic">
                  "revenue latency" → cross-lingual dense match
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

function SectionGraphDiffusion() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">
          Graph Semantics and Diffusion
        </h2>
        <p className="text-slate-400 leading-relaxed">
          FAIM traverses active query paths using bounded multi-hop walks and
          deterministic diffusion equations to reward localized neighborhood
          coherence.
        </p>
      </div>

      <VisualGraphTopology />

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="Decaying Path Score" color="indigo">
          <p className="text-sm text-slate-400 leading-relaxed">
            Score weights decay geometrically with each traversal hop, ensuring
            that localized neighborhood connections are rewarded over distant
            semantic jumps.
          </p>
        </Card>
        <Card title="Temporal Opposition Suppression" color="red">
          <p className="text-sm text-slate-400 leading-relaxed">
            Chronological conflicts and contradictory properties are flagged
            during path traversal, suppressing the older candidate before
            re-ranking.
          </p>
        </Card>
      </div>

      <Card title="PageRank style Bounded Diffusion" color="purple">
        <p className="text-sm text-slate-400 leading-relaxed mb-4">
          Scores diffuse outward from seed nodes using a deterministic,
          PageRank-style matrix propagation across the active adjacency graph.
          The query runtime can then layer an exact traversal branch on top of
          that retrieval surface using the caller-selected{" "}
          <code className="text-purple-300">graph_max_hops</code> budget (1–24,
          default 2).
        </p>
        <Code>{`y^(k+1) = (1 - alpha) * y_seed + alpha * P^T * y^(k)
default_hops_max = 24
configurable_hops_max = 128
bounded_frontier_pruning = enabled`}</Code>
      </Card>
    </div>
  );
}

function SectionRerankerV2() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">
          Deterministic Reranker V2
        </h2>
        <p className="text-slate-400 leading-relaxed">
          Fuses sparse, dense, and graph components into a single multi-signal
          score for high precision without learned cross-encoders.
        </p>
      </div>

      <VisualScoreCalculator mode="scoring" />

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="Multi-Signal Score Blend" color="cyan">
          <p className="text-sm text-slate-400 leading-relaxed">
            Combines lexical term frequencies, graph path scores, matching
            entities, chronological times, and evidence density.
          </p>
        </Card>
        <Card title="Pairwise Dominance Suppression" color="emerald">
          <p className="text-sm text-slate-400 leading-relaxed">
            If two nodes assert contradicting values for the same entity and
            relation, the younger node suppresses the older candidate pairwise.
          </p>
        </Card>
      </div>

      <Card title="The V2 Reranker Equation" color="purple">
        <p className="text-sm text-slate-400 leading-relaxed mb-4">
          The final score is synthesized using a deterministic linear
          combination of structural and temporal components:
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
        <h2 className="text-2xl font-bold text-white mb-2">
          Indexing, WAND &amp; ANN
        </h2>
        <p className="text-slate-400 leading-relaxed">
          FAIM scales retrieval using graph-versioned cached artifacts,
          Block-Max WAND sparse pruning, and a deterministic VP-tree dense
          shortlist.
        </p>
      </div>

      <VisualBenchmarkChart />

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="Block-Max WAND Pruning" color="cyan">
          <p className="text-sm text-slate-400 leading-relaxed">
            Computes a dynamic score upper bound for term blocks, instantly
            skipping non-matching ranges to deliver sublinear candidate
            shortlist times.
          </p>
        </Card>
        <Card title="Deterministic VP-tree Dense Shortlist" color="purple">
          <p className="text-sm text-slate-400 leading-relaxed">
            Keeps dense retrieval deterministic by using a fixed VP-tree
            build/search order with cache reuse keyed by graph version.
          </p>
        </Card>
      </div>

      <Card title="The 4-Stage Progressive Retrieval Flow" color="amber">
        <div className="space-y-3 text-sm text-slate-400">
          {[
            {
              stage: "Stage 1",
              desc: "Sparse postings shortlist using Block-Max WAND upper bounds.",
            },
            {
              stage: "Stage 2",
              desc: "Native vector shortlist query using a deterministic VP-tree dense path and graph-versioned cache reuse.",
            },
            {
              stage: "Stage 3",
              desc: "Graph expansion and bounded multi-hop neighborhood diffusion.",
            },
            {
              stage: "Stage 4",
              desc: "Deterministic V2 reranking with pairwise dominance suppression.",
            },
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
        <h2 className="text-2xl font-bold text-white mb-2">
          Cross-Lingual Bridges
        </h2>
        <p className="text-slate-400 leading-relaxed">
          Bridges English, German, Spanish, French, Italian, Portuguese, and
          Dutch terms directly onto language-agnostic conceptual nodes using
          146,598 static multilingual lexicon entries alongside 2,172,991
          ConceptNet keys.
        </p>
      </div>

      <VisualLexiconDistribution />

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="German Transliteration" color="cyan">
          <p className="text-sm text-slate-400 leading-relaxed">
            Unifies spelling differences by standardizing German umlauts
            deterministically (ä → ae, ö → oe, ü → ue, ß → ss).
          </p>
        </Card>
        <Card title="Light German Stemmer" color="purple">
          <p className="text-sm text-slate-400 leading-relaxed">
            Stems German roots deterministically to handle inflections and
            plural variants perfectly without heavy dictionary runtimes.
          </p>
        </Card>
      </div>

      <Card title="Multilingual Concept Node Bridges" color="emerald">
        <p className="text-sm text-slate-400 leading-relaxed mb-4">
          English, German, Spanish, French, Italian, Portuguese, and Dutch
          surface forms map directly to a unified conceptual ID, resolving
          cross-lingual query matches in microseconds:
        </p>
        <Code>{`surface_form(EN) -> concept_key <- surface_form(DE)
surface_form(EN|DE|ES|FR|IT|PT|NL) -> concept_key
"sales" -> Concept: revenue <- "umsatz"`}</Code>
      </Card>
    </div>
  );
}

function SectionMultimodalNoML() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">
          Structural & Visual Indexing
        </h2>
        <p className="text-slate-400 leading-relaxed">
          Deterministic support for spreadsheet tables, page layout coordinates,
          and visual assets without heavy transformer models.
        </p>
      </div>

      <VisualDomainDiagram kind="extraction" />

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="Table Linearization" color="cyan">
          <p className="text-sm text-slate-400 leading-relaxed">
            Transforms pipe-delimited table rows into standardized,
            semicolon-delimited grids row-by-row, keeping cells grouped for
            keyword proximity queries.
          </p>
        </Card>
        <Card title="Image Perceptual Hash (pHash)" color="purple">
          <p className="text-sm text-slate-400 leading-relaxed">
            Generates a stable 16-character fingerprint proxy based on SHA-256
            to identify exact or near-duplicate visual assets instantly.
          </p>
        </Card>
      </div>

      <Card title="Layout Coordinates & Metadata" color="amber">
        <p className="text-sm text-slate-400 leading-relaxed mb-4">
          Saves and indexes physical layout boundaries (page numbers, slides,
          sections, block types) as easily queryable search tokens.
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
        <h2 className="text-2xl font-bold text-white mb-2">
          Domain Adaptation
        </h2>
        <p className="text-slate-400 leading-relaxed">
          Solves specialized domain jargon by ingesting curated corporate KB
          dumps and executing algebraic neighborhood walks.
        </p>
      </div>

      <VisualLexiconDistribution />

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="Deterministic Entity Linking" color="cyan">
          <p className="text-sm text-slate-400 leading-relaxed">
            Substring-matches input query words against the localized graph
            lexicon, resolving them directly to specific target seed node UUIDs.
          </p>
        </Card>
        <Card title="Multi-Relational Graph Walks" color="purple">
          <p className="text-sm text-slate-400 leading-relaxed">
            Starting at seed nodes, the engine executes neighborhood walks
            across adjacent entity relationships, fact values, and source
            citations.
          </p>
        </Card>
      </div>

      <Card title="Knowledge Base Edge-Scaling Multipliers" color="indigo">
        <p className="text-sm text-slate-400 leading-relaxed mb-4">
          Adjacent activated nodes receive relevance boosts scaled by normalized
          edge weights and connecting multipliers:
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
        <h2 className="text-2xl font-bold text-white mb-2">
          Extractive Answer Synthesis
        </h2>
        <p className="text-slate-400 leading-relaxed">
          Composes auditable, citation-first extractive prose and calibrated
          confidence intervals without generative LLM drift.
        </p>
      </div>

      <VisualScoreCalculator mode="confidence" />

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="Extractive Span Selector" color="cyan">
          <p className="text-sm text-slate-400 leading-relaxed">
            Splits text candidates into sentences and scores them based on term
            overlap, document rank, and temporal active/historical markers.
          </p>
        </Card>
        <Card title="Contradiction Warnings" color="red">
          <p className="text-sm text-slate-400 leading-relaxed">
            Automatically flags value conflicts asserting different figures for
            the same entity and relation in top retrieval candidates.
          </p>
        </Card>
      </div>

      <Card title="Evidence Confidence Interval Equation" color="purple">
        <p className="text-sm text-slate-400 leading-relaxed mb-4">
          Computes a bounded confidence score in [0, 1] based on evidence
          breadth, active span ratio, and contradiction penalties:
        </p>
        <Code>{`S_confidence = clamp( 0.45 * S_avg_span + 0.30 * S_breadth + 0.25 * S_active - S_penalty )
S_breadth = min( 1.0, unique_docs / 3.0 ), S_penalty = min( 0.5, 0.15 * conflicts )`}</Code>
      </Card>
    </div>
  );
}

function SectionHybridRouting() {
  const routingMatrix = [
    [
      "FAST + English",
      "FAIM_FAST_ML_EMBEDDING=auto",
      "FAIM-Pure (256-dim native)",
      "fast_pure_english: skips neural inference in favor of deterministic CPU math",
    ],
    [
      "FAST + Non-English",
      "FAIM_FAST_ML_EMBEDDING=auto",
      "Granite 97M Multilingual Dense",
      "fast_multilingual_embedding: auto-enables cross-lingual dense recall",
    ],
    [
      "STRICT / BALANCED / RELAXED",
      "FAIM_FAST_ML_EMBEDDING=auto",
      "Active ML Embedding + Native Core",
      "regular_embedding: blends semantic vectors with canonical graph recall",
    ],
    [
      "CPU-Only VPS Override",
      "FAIM_FAST_ML_EMBEDDING=false",
      "FAIM-Pure in FAST mode",
      "fast_pure_forced: guarantees zero GPU requirement for fast paths",
    ],
    [
      "Always Neural Fast Path",
      "FAIM_FAST_ML_EMBEDDING=true",
      "Active ML Embedding in FAST mode",
      "ml_embedding_forced: prioritizes neural vectors even on English FAST queries",
    ],
  ];

  const envVars = [
    [
      "FAIM_FAST_ML_EMBEDDING",
      "auto (default)",
      "Controls dynamic CPU FAIM-Pure vs ML embedding selection per query language and profile.",
    ],
    [
      "FAIM_EMBEDDING_DEVICE",
      "cpu | auto",
      "Selects CPU inference on standard VPS instances or CUDA GPU execution when NVIDIA runtime is available.",
    ],
    [
      "FAIM_CONTAINER_RUNTIME",
      "runc | nvidia",
      "Single compose knob switching containers between standard CPU (runc) and GPU passthrough (nvidia).",
    ],
    [
      "FAIM_EMBEDDING_PREWARM_REQUIRED",
      "false (default)",
      "Allows API & worker pods to start cleanly even if optional embedding prewarm times out.",
    ],
  ];

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-2 mb-2">
          <span className="text-[11px] font-mono uppercase tracking-wider px-2 py-0.5 rounded-md bg-emerald-500/10 border border-emerald-500/25 text-emerald-300">
            CPU VPS & GPU Cloud
          </span>
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">
          Dynamic CPU/GPU Hybrid Routing
        </h2>
        <p className="text-slate-400 leading-relaxed">
          FAIM automatically routes queries between ultra-fast zero-ML native
          vectors (<span className="text-white font-medium">FAIM-Pure</span>)
          and local multilingual neural embeddings (
          <span className="text-white font-medium">Granite 97M Dense</span>)
          based on query profile, language, and available compute hardware.
        </p>
      </div>

      <VisualHybridRouter />

      <div className="grid md:grid-cols-3 gap-4">
        <Card title="Zero-GPU VPS Ready" color="cyan">
          <p className="text-sm text-slate-400 leading-relaxed">
            Runs out of the box on commodity CPU servers using{" "}
            <code className="text-cyan-300">runc</code> and deterministic
            256-dim native vectors without GPU hardware requirements.
          </p>
        </Card>
        <Card title="Automatic GPU Acceleration" color="purple">
          <p className="text-sm text-slate-400 leading-relaxed">
            Flip{" "}
            <code className="text-purple-300">
              FAIM_CONTAINER_RUNTIME=nvidia
            </code>{" "}
            and{" "}
            <code className="text-purple-300">FAIM_EMBEDDING_DEVICE=auto</code>{" "}
            in one shared compose file to unlock CUDA inference.
          </p>
        </Card>
        <Card title="Fail-Open Resilience" color="emerald">
          <p className="text-sm text-slate-400 leading-relaxed">
            If an external or local embedding worker is unavailable or cold,
            FAIM falls back cleanly to cached dense vectors and FAIM-Pure
            without dropping requests.
          </p>
        </Card>
      </div>

      <Card title="Routing Policy Matrix" color="cyan">
        <p className="text-sm text-slate-400 leading-relaxed mb-4">
          Runtime selection executed inside{" "}
          <code className="text-cyan-300">resolve_fast_ml_embedding_mode</code>{" "}
          on every query and ingestion request:
        </p>
        <div className="overflow-x-auto rounded-xl border border-slate-800">
          <table className="w-full min-w-[680px] text-left text-xs">
            <thead className="bg-slate-950/70 text-slate-400 font-mono">
              <tr>
                <th className="px-3 py-2.5">Query Profile & Language</th>
                <th className="px-3 py-2.5">Policy Setting</th>
                <th className="px-3 py-2.5">Active Engine</th>
                <th className="px-3 py-2.5">Routing Reason</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {routingMatrix.map(([profile, setting, engine, reason]) => (
                <tr key={profile} className="align-top">
                  <td className="px-3 py-2.5 font-medium text-white">
                    {profile}
                  </td>
                  <td className="px-3 py-2.5 font-mono text-cyan-300">
                    {setting}
                  </td>
                  <td className="px-3 py-2.5 text-emerald-300">{engine}</td>
                  <td className="px-3 py-2.5 text-slate-400">{reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card title="Runtime Environment Switches" color="amber">
        <div className="space-y-2.5">
          {envVars.map(([name, def, desc]) => (
            <div
              key={name}
              className="rounded-lg border border-slate-800/80 bg-slate-950/60 p-3 flex flex-col sm:flex-row sm:items-center gap-2 justify-between"
            >
              <div>
                <p className="font-mono text-xs text-amber-300">{name}</p>
                <p className="text-xs text-slate-400 mt-0.5">{desc}</p>
              </div>
              <span className="shrink-0 text-[11px] font-mono px-2.5 py-1 rounded bg-slate-900 border border-slate-700 text-slate-300">
                {def}
              </span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function SectionApiReference() {
  const endpointGroups = [
    {
      title: "Health & Service Metadata",
      color: "emerald",
      routes: [
        [
          "GET",
          "/health",
          "Public",
          "Liveness probe returning service health status.",
        ],
        [
          "GET",
          "/ready",
          "Public",
          "Readiness check validating database, vector index, and queue readiness.",
        ],
        [
          "GET",
          "/version",
          "Public",
          "Returns active FAIM runtime build and schema compatibility version.",
        ],
        [
          "GET",
          "/pipeline/stats",
          "Auth",
          "Live ingestion & retrieval stage counters (also mounted under /api/v1).",
        ],
      ],
    },
    {
      title: "Retrieval, Query & Direct Memory",
      color: "cyan",
      routes: [
        [
          "POST",
          "/api/v1/query",
          "Bearer / Key",
          "Hybrid query execution with profile, graph_max_hops (1-24), and explain payload.",
        ],
        [
          "POST",
          "/api/v1/memory/search",
          "Bearer / Key",
          "Bounded memory node search across canonical, semantic, and graph channels.",
        ],
        [
          "POST",
          "/api/v1/memory/write",
          "Bearer / Key",
          "Idempotent memory node creation with SHA-256 content lineage.",
        ],
        [
          "GET",
          "/api/v1/memory/{node_id}/provenance",
          "Bearer / Key",
          "Returns immutable byte-offset source span and document lineage.",
        ],
      ],
    },
    {
      title: "Knowledge Graph, Ingestion & Evolution",
      color: "purple",
      routes: [
        [
          "POST",
          "/api/v1/ingest",
          "Bearer / Key",
          "Ingests raw text/structured payloads into deterministic nodes and edges.",
        ],
        [
          "POST",
          "/api/v1/ingest/upload",
          "Bearer / Key",
          "Multipart document ingestion for PDF, DOCX, PPTX, XLSX, HTML, MD, and code.",
        ],
        [
          "GET",
          "/api/v1/graph/surface",
          "Bearer / Key",
          "Retrieves typed nodes, edges, clusters, and coordinates for FIG View.",
        ],
        [
          "POST",
          "/api/v1/graph/paths/explain",
          "Bearer / Key",
          "Returns pulse-v2 reasoning chains and edge weights for explainability UI.",
        ],
        [
          "POST",
          "/api/v1/evolve",
          "Bearer / Key",
          "Explicitly triggers opt-in graph structural learning and hypothesis checks.",
        ],
        [
          "GET",
          "/api/v1/events/stream",
          "Bearer / Key",
          "Server-Sent Events stream of live ingestion, query, and maintenance events.",
        ],
      ],
    },
    {
      title: "Storage Maintenance, API Keys & Remote MCP",
      color: "amber",
      routes: [
        [
          "POST",
          "/api/v1/storage/uploads",
          "Bearer",
          "Tracked batch file upload & background ingestion queue.",
        ],
        [
          "GET",
          "/api/v1/storage/supported-types",
          "Public / Auth",
          "Lists active parser & OCR capabilities enabled on this runtime.",
        ],
        [
          "POST",
          "/api/v1/api-keys",
          "Bearer",
          "Issues scoped tenant API keys (shown once at creation time).",
        ],
        [
          "POST / SSE",
          "/mcp",
          "OAuth 2.1 / Key",
          "Remote MCP Streamable HTTP endpoint with PKCE for IDE & agent clients.",
        ],
      ],
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">
          REST API Reference
        </h2>
        <p className="text-slate-400 leading-relaxed">
          All operational endpoints are tenant-isolated by workspace scope and
          accept either session JWTs (
          <code className="text-cyan-300">Authorization: Bearer</code>) or
          scoped machine keys (<code className="text-cyan-300">X-API-Key</code>
          ).
        </p>
      </div>

      <VisualDomainDiagram kind="api" />

      <Card title="Quick Curl Example" color="indigo">
        <Code>{`# Check health & execute a hybrid bounded query
curl -fsS http://localhost:8000/health && curl -fsS http://localhost:8000/ready

curl -X POST http://localhost:8000/api/v1/query \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: $FAIM_API_KEY" \\
  -d '{
    "query": "What blocked database failover in Q3?",
    "profile": "BALANCED",
    "graph_max_hops": 4,
    "explain": true
  }'`}</Code>
      </Card>

      {endpointGroups.map((group) => (
        <Card key={group.title} title={group.title} color={group.color}>
          <div className="overflow-x-auto rounded-xl border border-slate-800">
            <table className="w-full min-w-[660px] text-left text-xs">
              <thead className="bg-slate-950/70 text-slate-400 font-mono">
                <tr>
                  <th className="px-3 py-2 w-24">Method</th>
                  <th className="px-3 py-2 w-64">Endpoint</th>
                  <th className="px-3 py-2 w-28">Auth</th>
                  <th className="px-3 py-2">Behavior</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {group.routes.map(([method, path, auth, desc]) => (
                  <tr key={path} className="align-top">
                    <td className="px-3 py-2.5 font-mono text-emerald-300">
                      {method}
                    </td>
                    <td className="px-3 py-2.5 font-mono text-cyan-300">
                      {path}
                    </td>
                    <td className="px-3 py-2.5 font-mono text-slate-400">
                      {auth}
                    </td>
                    <td className="px-3 py-2.5 text-slate-300 leading-relaxed">
                      {desc}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section renderer
// ---------------------------------------------------------------------------
const GROUP_ICONS: Record<
  string,
  React.ComponentType<{ className?: string }>
> = {
  Overview: BookOpen,
  "Core System": Cpu,
  "Retrieval & Semantics": Layers,
  "Documents & Extraction": FileText,
  "Platform & Operations": ShieldCheck,
};

const SECTION_COMPONENTS: Record<string, React.ComponentType> = {
  "what-is-faim": SectionWhatIsFaim,
  "current-state": SectionCurrentState,
  quickstart: SectionQuickStart,
  "why-faim": SectionWhyFaim,
  architecture: SectionArchitecture,
  memory: SectionMemory,
  graph: SectionGraph,
  retrieval: SectionRetrieval,
  "hybrid-routing": SectionHybridRouting,
  cortex: SectionCortex,
  "cortex-runtime": SectionCortexRuntime,
  "canonical-semantics": SectionCanonicalSemantics,
  "graph-diffusion": SectionGraphDiffusion,
  "reranker-v2": SectionRerankerV2,
  "scale-ann": SectionScaleANN,
  multilingual: SectionMultilingual,
  "multimodal-no-ml": SectionMultimodalNoML,
  "domain-adaptation": SectionDomainAdaptation,
  "answer-synthesis": SectionAnswerSynthesis,
  "document-intel": SectionDocIntel,
  ingestion: SectionIngestion,
  "fig-view": SectionFigView,
  "api-reference": SectionApiReference,
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
  const [query, setQuery] = useState("");
  const [mobileTocOpen, setMobileTocOpen] = useState(false);

  const allItems = useMemo(() => NAV_GROUPS.flatMap((g) => g.items), []);

  // Sync URL hash (#section-id) on mount and hashchange
  useEffect(() => {
    const applyHash = () => {
      const hash = window.location.hash.replace(/^#/, "");
      if (hash && SECTION_COMPONENTS[hash]) {
        setActive(hash);
      }
    };
    applyHash();
    window.addEventListener("hashchange", applyHash);
    return () => window.removeEventListener("hashchange", applyHash);
  }, []);

  const selectSection = (id: string) => {
    setActive(id);
    setMobileTocOpen(false);
    if (typeof window !== "undefined") {
      if (window.location.hash !== `#${id}`) {
        window.history.replaceState(null, "", `#${id}`);
      }
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  const filteredGroups = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return NAV_GROUPS;
    return NAV_GROUPS.map((g) => {
      const groupMatches = g.group.toLowerCase().includes(q);
      const items = groupMatches
        ? g.items
        : g.items.filter((item) => item.label.toLowerCase().includes(q));
      return { ...g, items };
    }).filter((g) => g.items.length > 0);
  }, [query]);

  const activeMeta = useMemo(() => {
    for (const g of NAV_GROUPS) {
      const found = g.items.find((i) => i.id === active);
      if (found) return { group: g.group, label: found.label };
    }
    return { group: "Overview", label: "What is FAIM?" };
  }, [active]);

  const activeIndex = Math.max(
    0,
    allItems.findIndex((i) => i.id === active),
  );

  const Content = SECTION_COMPONENTS[active] ?? SectionWhatIsFaim;

  const renderNavContent = () => (
    <div className="space-y-4">
      {filteredGroups.length === 0 ? (
        <div className="px-3 py-6 text-center text-xs text-slate-500">
          No matching topics for &ldquo;{query}&rdquo;
        </div>
      ) : (
        filteredGroups.map((group) => {
          const GroupIcon = GROUP_ICONS[group.group] ?? Sparkles;
          return (
            <div key={group.group} className="space-y-1">
              <div className="flex items-center justify-between px-2.5 pt-1 pb-1">
                <span className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                  <GroupIcon className="w-3.5 h-3.5 text-cyan-400/80" />
                  {group.group}
                </span>
                <span className="text-[10px] font-mono text-slate-600">
                  {group.items.length}
                </span>
              </div>
              <div className="space-y-0.5 pl-1 border-l border-slate-800/80 ml-2.5">
                {group.items.map((item) => {
                  const isActive = active === item.id;
                  return (
                    <button
                      key={item.id}
                      onClick={() => selectSection(item.id)}
                      className={`group w-full flex items-center justify-between text-left px-3 py-1.5 rounded-lg text-[13px] transition-all ${
                        isActive
                          ? "bg-gradient-to-r from-cyan-500/15 to-cyan-500/5 text-cyan-200 font-medium border-l-2 border-cyan-400 shadow-[inset_0_0_0_1px_rgba(34,211,238,0.18)]"
                          : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/50 border-l-2 border-transparent"
                      }`}
                    >
                      <span className="truncate">{item.label}</span>
                      {isActive && (
                        <ChevronRight className="w-3.5 h-3.5 shrink-0 text-cyan-400" />
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })
      )}
    </div>
  );

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
        <div className="max-w-7xl mx-auto flex flex-col lg:flex-row gap-8">
          {/* Mobile / Tablet Table of Contents Drawer */}
          <div className="lg:hidden">
            <button
              type="button"
              onClick={() => setMobileTocOpen((v) => !v)}
              className="w-full flex items-center justify-between px-4 py-3 rounded-2xl bg-slate-900/70 border border-slate-800 text-left"
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <Menu className="w-4 h-4 text-cyan-400 shrink-0" />
                <div className="min-w-0">
                  <p className="text-[10px] font-mono uppercase tracking-wider text-slate-500">
                    {activeMeta.group}
                  </p>
                  <p className="text-sm font-medium text-white truncate">
                    {activeMeta.label}
                  </p>
                </div>
              </div>
              <ChevronDown
                className={`w-4 h-4 text-slate-400 transition-transform ${
                  mobileTocOpen ? "rotate-180" : ""
                }`}
              />
            </button>

            {mobileTocOpen && (
              <div className="mt-2 rounded-2xl bg-slate-900/90 backdrop-blur-xl border border-slate-800 p-4 space-y-3">
                <div className="relative">
                  <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Filter documentation topics..."
                    className="w-full pl-8 pr-8 py-1.5 rounded-lg bg-slate-950/80 border border-slate-800 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-cyan-500/50"
                  />
                  {query && (
                    <button
                      type="button"
                      onClick={() => setQuery("")}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                      aria-label="Clear filter"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
                <div className="max-h-96 overflow-y-auto pr-1">
                  {renderNavContent()}
                </div>
              </div>
            )}
          </div>

          {/* Desktop Sidebar Table of Contents */}
          <aside className="hidden lg:block w-72 shrink-0">
            <div className="sticky top-24 rounded-2xl bg-slate-900/50 backdrop-blur-md border border-slate-800/80 p-4 flex flex-col max-h-[calc(100vh-7rem)] shadow-xl shadow-slate-950/40">
              {/* Header */}
              <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800/80">
                <div>
                  <p className="text-xs font-semibold text-white tracking-tight">
                    Documentation
                  </p>
                  <p className="text-[11px] font-mono text-slate-500">
                    {allItems.length} technical guides
                  </p>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-cyan-500/10 border border-cyan-500/25 text-cyan-300">
                  {APP_VERSION}
                </span>
              </div>

              {/* Filter Input */}
              <div className="relative mb-3">
                <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Filter topics..."
                  className="w-full pl-8 pr-8 py-1.5 rounded-lg bg-slate-950/80 border border-slate-800 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-cyan-500/50 transition-colors"
                />
                {query && (
                  <button
                    type="button"
                    onClick={() => setQuery("")}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                    aria-label="Clear filter"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>

              {/* Scrollable Navigation Groups */}
              <div className="overflow-y-auto pr-1 flex-1 scrollbar-thin scrollbar-thumb-slate-800 scrollbar-track-transparent">
                {renderNavContent()}
              </div>
            </div>
          </aside>

          {/* Content panel */}
          <div className="flex-1 min-w-0 max-w-4xl">
            <DocsBookBanner
              chapterNumber={activeIndex + 1}
              totalChapters={allItems.length}
              groupTitle={activeMeta.group}
              sectionTitle={activeMeta.label}
              version={APP_VERSION}
            />

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

            {/* Bottom prev/next pagination */}
            <div className="mt-12 pt-6 border-t border-slate-800/60 flex items-center justify-between gap-4">
              {(() => {
                const idx = allItems.findIndex((i) => i.id === active);
                const prev = allItems[idx - 1];
                const next = allItems[idx + 1];
                return (
                  <>
                    {prev ? (
                      <button
                        onClick={() => selectSection(prev.id)}
                        className="group flex flex-col items-start text-left px-4 py-2.5 rounded-xl border border-slate-800/80 bg-slate-900/30 hover:border-slate-700 hover:bg-slate-900/70 transition-all"
                      >
                        <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500">
                          ← Previous
                        </span>
                        <span className="text-sm text-slate-300 group-hover:text-white mt-0.5">
                          {prev.label}
                        </span>
                      </button>
                    ) : (
                      <span />
                    )}
                    {next ? (
                      <button
                        onClick={() => selectSection(next.id)}
                        className="group flex flex-col items-end text-right px-4 py-2.5 rounded-xl border border-slate-800/80 bg-slate-900/30 hover:border-cyan-500/40 hover:bg-slate-900/70 transition-all"
                      >
                        <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500">
                          Next →
                        </span>
                        <span className="text-sm text-slate-300 group-hover:text-cyan-300 mt-0.5">
                          {next.label}
                        </span>
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
