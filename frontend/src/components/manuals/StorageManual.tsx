"use client";

import React, { useState } from "react";
import {
  ManualShell,
  SectionHeading,
  SubHeading,
  Callout,
  DTable,
  type TocItem,
} from "@/components/manuals/ManualShell";
import {
  Database,
  HardDrive,
  Cpu,
  Layers,
  ShieldCheck,
  Zap,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Binary,
  RotateCcw,
  Scale,
  HelpCircle,
  Server,
  Lock,
  Search,
  ScanText,
  Activity,
  Workflow,
  Sparkles,
  Key,
  ArrowRight,
  ArrowDown,
  RefreshCw,
  GitCommit,
  GitBranch,
  Network,
  Share2,
  Eye,
  Check,
  Terminal,
  Shield,
  FileCode,
  Compass,
  Globe,
} from "lucide-react";

const TOC: TocItem[] = [
  {
    id: "overview",
    label: "1. System Overview & Architecture",
    children: [
      { id: "arch-visual-blueprint", label: "Visual System Topology Blueprint" },
      { id: "core-principles", label: "Core Storage Invariants" },
      { id: "dual-store-visual", label: "Dual-Store Relational & Vector Sync" },
    ],
  },
  {
    id: "pipeline",
    label: "2. End-to-End Ingestion Pipeline",
    children: [
      { id: "pipeline-visual-flow", label: "9-Step Visual Ingest Flowchart" },
      { id: "pipeline-sidecars-visual", label: "8 Sidecars Fan-Out Architecture" },
      { id: "pipeline-atom-commit", label: "Knowledge Atomization & Commit" },
    ],
  },
  {
    id: "engines",
    label: "3. Storage Engine Topology & Layers",
    children: [
      { id: "engine-stack-visual", label: "4-Tier Storage Engine Stack" },
      { id: "engine-cas", label: "CAS Blob Disk Store (/var/lib/faim/raw)" },
      { id: "engine-postgres", label: "PostgreSQL Relational Spine" },
      { id: "engine-qdrant", label: "Qdrant HNSW Vector Engine" },
      { id: "engine-redis", label: "Redis Queue & Lock Accelerator" },
    ],
  },
  {
    id: "profiles",
    label: "4. Upload Profiles & Persist Policies",
    children: [
      { id: "profile-modes", label: "Profile Comparison (STRICT, BALANCED, RELAXED, FAST)" },
      { id: "persist-modes", label: "Persist Validation Modes" },
      { id: "policy-engine-visual", label: "UI Mode Policy Decision Tree" },
    ],
  },
  {
    id: "ocr",
    label: "5. OCR Perception & Document Extraction",
    children: [
      { id: "ocr-pipeline-visual", label: "PaddleOCR v6 Pipeline Architecture" },
      { id: "ocr-formats", label: "Supported Formats & Limits" },
      { id: "ocr-config", label: "Runtime OCR Environment Config" },
    ],
  },
  {
    id: "catalog",
    label: "6. Cryptographic Provenance & Proofs",
    children: [
      { id: "provenance-chain-visual", label: "Visual SHA-256 & Packet Hash Chain" },
      { id: "catalog-fields", label: "Catalog Metadata Schema" },
      { id: "catalog-immutability", label: "Append-Only Immutability Rule" },
    ],
  },
  {
    id: "statemachine",
    label: "7. Ingest State Machine & Crash Recovery",
    children: [
      { id: "statemachine-visual", label: "Visual State Transition Graph" },
      { id: "state-recovery", label: "Worker Idempotency & Crash Recovery" },
      { id: "state-dedup", label: "Content-Addressed Deduplication" },
    ],
  },
  {
    id: "governance",
    label: "8. Governance, Orphan Scans & HITL",
    children: [
      { id: "gov-workflow-visual", label: "HITL Approval Queue Workflow" },
      { id: "gov-orphans-visual", label: "Orphan Artifact Scanner & GC" },
      { id: "gov-isolation", label: "Multi-Tenant Crypto-Sharding" },
    ],
  },
  {
    id: "api",
    label: "9. Operations & Storage REST API",
    children: [
      { id: "api-endpoints", label: "REST & Cortex Storage Endpoints" },
      { id: "api-cli", label: "CLI & Diagnostic Inspection Commands" },
      { id: "api-metrics", label: "Storage Health & Throughput Metrics" },
    ],
  },
  {
    id: "troubleshoot",
    label: "10. Troubleshooting & Enterprise FAQ",
    children: [
      { id: "troubleshoot-matrix", label: "Storage Diagnostics Matrix" },
      { id: "troubleshoot-faq", label: "Enterprise Storage FAQ" },
    ],
  },
];

export function StorageManual({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [activeTab, setActiveTab] = useState<"blueprint" | "dataflow" | "engines">("blueprint");

  return (
    <ManualShell
      open={open}
      onClose={onClose}
      title="FAIM Storage — Master Architecture & Operations Manual"
      subtitle="Immutable CAS Blobs · Dual-Store Relational & Vector Pipeline · Cryptographic Provenance"
      toc={TOC}
      accent="#06b6d4"
    >
      {/* ── Chapter 1: System Overview & Architecture ─────────────────────────── */}
      <SectionHeading id="overview" kicker="Chapter 01" title="System Overview & Storage Architecture Topology">
        <p>
          <strong>FAIM Storage</strong> is the immutable knowledge ingestion engine and persistent data foundation of the
          FAIM platform. It provides cryptographic provenance, deterministic sidecar generation, and zero-loss multi-modal
          data persistence for enterprise knowledge graphs.
        </p>

        <SubHeading id="arch-visual-blueprint">Visual System Topology Blueprint</SubHeading>
        <p className="text-xs text-slate-300 leading-relaxed">
          The storage subsystem decouples raw physical file persistence from relational knowledge representation and dense vector indexing.
          The interactive architecture diagram below illustrates how client uploads traverse API gateways, worker queues, and the 4 persistent storage tiers:
        </p>

        {/* ── VISUAL ARCHITECTURE BLUEPRINT (Interactive Canvas) ───────────────── */}
        <div className="my-5 overflow-hidden rounded-[18px] border border-cyan-500/30 bg-[#050811] p-5 shadow-[0_0_50px_rgba(6,182,212,0.08)]">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/8 pb-3 mb-4">
            <div className="flex items-center gap-2">
              <div className="flex h-6 w-6 items-center justify-center rounded-lg border border-cyan-500/40 bg-cyan-500/10 text-cyan-300">
                <Network size={14} />
              </div>
              <span className="text-xs font-bold uppercase tracking-wider text-white">
                FAIM Storage Multi-Tier System Blueprint
              </span>
            </div>
            <div className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-black/40 p-1">
              <span className="px-2 py-0.5 text-[10px] font-mono text-cyan-300 bg-cyan-500/15 rounded">
                Tier-1 CAS
              </span>
              <span className="px-2 py-0.5 text-[10px] font-mono text-indigo-300 bg-indigo-500/15 rounded">
                Tier-2 Postgres
              </span>
              <span className="px-2 py-0.5 text-[10px] font-mono text-purple-300 bg-purple-500/15 rounded">
                Tier-3 Qdrant
              </span>
              <span className="px-2 py-0.5 text-[10px] font-mono text-emerald-300 bg-emerald-500/15 rounded">
                Tier-4 Redis
              </span>
            </div>
          </div>

          {/* SVG Diagram Canvas */}
          <div className="relative w-full overflow-x-auto custom-scrollbar py-2">
            <div className="min-w-[760px] flex flex-col gap-4">
              
              {/* TOP: Client Intake Tier */}
              <div className="flex items-center justify-between rounded-xl border border-white/10 bg-white/[0.02] p-3">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-cyan-400/40 bg-cyan-500/10 text-cyan-300">
                    <FileText size={20} />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-white">Client / Cortex Ingest Gateway</h4>
                    <p className="text-[10px] text-slate-400">
                      Multi-file upload (PDF, DOCX, Markdown, Images, JSON) · Pre-flight MIME validation · Tenant Key Auth
                    </p>
                  </div>
                </div>
                <span className="rounded-md border border-cyan-500/30 bg-cyan-500/10 px-2 py-1 font-mono text-[10px] text-cyan-300">
                  HTTP POST /api/v1/storage/upload
                </span>
              </div>

              {/* CONNECTING FLOW ARROWS */}
              <div className="flex items-center justify-around px-8">
                <div className="flex flex-col items-center">
                  <div className="h-4 w-[2px] bg-gradient-to-b from-cyan-400 to-indigo-500" />
                  <span className="text-[9px] font-mono text-cyan-400">1. SHA-256 Stream</span>
                </div>
                <div className="flex flex-col items-center">
                  <div className="h-4 w-[2px] bg-gradient-to-b from-cyan-400 to-emerald-500" />
                  <span className="text-[9px] font-mono text-emerald-400">2. Enqueue Job</span>
                </div>
              </div>

              {/* MIDDLE: Worker & Processing Hub */}
              <div className="grid grid-cols-2 gap-4">
                {/* Left: Raw Store & Integrity */}
                <div className="rounded-xl border border-cyan-500/30 bg-cyan-950/20 p-3.5 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-1.5 text-xs font-bold text-cyan-200">
                      <HardDrive size={14} className="text-cyan-400" /> Tier 1: Raw Blob Store (CAS)
                    </span>
                    <span className="text-[9px] font-mono text-cyan-400 bg-cyan-500/10 px-1.5 py-0.5 rounded">
                      /var/lib/faim/raw/blobs
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-300 leading-relaxed">
                    Content-Addressable Storage keyed by cryptographic <code className="text-cyan-300">SHA-256</code> digest.
                    Guarantees immutable raw byte preservation, zero in-place overwrites, and automatic deduplication.
                  </p>
                  <div className="rounded-lg border border-white/6 bg-black/40 p-2 font-mono text-[10px] text-slate-400">
                    File: <span className="text-cyan-300">blobs/8f4c2e...a9b1</span> (4.2 MB, Immutable)
                  </div>
                </div>

                {/* Right: Background Ingestion Worker */}
                <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-3.5 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-1.5 text-xs font-bold text-emerald-200">
                      <Cpu size={14} className="text-emerald-400" /> Tier 4: Redis Task Pipeline
                    </span>
                    <span className="text-[9px] font-mono text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded">
                      orchestration.jobs.worker
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-300 leading-relaxed">
                    Redis coordinates concurrent worker tasks, manages distributed locks (<code className="text-emerald-300">faim:lock:*</code>),
                    and executes PaddleOCR v6 perception + 8 sidecar generation.
                  </p>
                  <div className="flex gap-2">
                    <span className="rounded bg-emerald-500/15 px-2 py-0.5 text-[9px] font-mono text-emerald-300 border border-emerald-500/30">
                      Profile: RELAXED
                    </span>
                    <span className="rounded bg-emerald-500/15 px-2 py-0.5 text-[9px] font-mono text-emerald-300 border border-emerald-500/30">
                      OCR: paddleocr_v6
                    </span>
                  </div>
                </div>
              </div>

              {/* CONNECTING FLOW ARROWS */}
              <div className="flex items-center justify-around px-8">
                <div className="flex flex-col items-center">
                  <div className="h-4 w-[2px] bg-gradient-to-b from-indigo-500 to-indigo-400" />
                  <span className="text-[9px] font-mono text-indigo-400">3. Symbolic Atoms & Triples</span>
                </div>
                <div className="flex flex-col items-center">
                  <div className="h-4 w-[2px] bg-gradient-to-b from-purple-500 to-purple-400" />
                  <span className="text-[9px] font-mono text-purple-400">4. Dense Embeddings</span>
                </div>
              </div>

              {/* BOTTOM: Dual-Store Relational & Vector Persistence */}
              <div className="grid grid-cols-2 gap-4">
                {/* Relational Truth Spine */}
                <div className="rounded-xl border border-indigo-500/30 bg-indigo-950/20 p-3.5 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-1.5 text-xs font-bold text-indigo-200">
                      <Database size={14} className="text-indigo-400" /> Tier 2: Relational Spine (Postgres)
                    </span>
                    <span className="text-[9px] font-mono text-indigo-400 bg-indigo-500/10 px-1.5 py-0.5 rounded">
                      PostgreSQL 15 (pgvector)
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-300 leading-relaxed">
                    Single source of truth managing metadata catalogs, knowledge atoms, typed graph relations, and audit ledgers:
                  </p>
                  <div className="grid grid-cols-2 gap-1.5 font-mono text-[9px] text-indigo-300">
                    <div className="bg-black/30 p-1.5 rounded border border-white/5">storage_files</div>
                    <div className="bg-black/30 p-1.5 rounded border border-white/5">nodes & edges</div>
                    <div className="bg-black/30 p-1.5 rounded border border-white/5">events & versions</div>
                    <div className="bg-black/30 p-1.5 rounded border border-white/5">cortex_approvals</div>
                  </div>
                </div>

                {/* Vector Engine */}
                <div className="rounded-xl border border-purple-500/30 bg-purple-950/20 p-3.5 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-1.5 text-xs font-bold text-purple-200">
                      <Zap size={14} className="text-purple-400" /> Tier 3: Vector Engine (Qdrant)
                    </span>
                    <span className="text-[9px] font-mono text-purple-400 bg-purple-500/10 px-1.5 py-0.5 rounded">
                      Qdrant HNSW Core
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-300 leading-relaxed">
                    HNSW vector graph index executing sub-millisecond approximate nearest neighbor searches:
                  </p>
                  <div className="grid grid-cols-2 gap-1.5 font-mono text-[9px] text-purple-300">
                    <div className="bg-black/30 p-1.5 rounded border border-white/5">Metric: Cosine</div>
                    <div className="bg-black/30 p-1.5 rounded border border-white/5">Tenant Sharding</div>
                    <div className="bg-black/30 p-1.5 rounded border border-white/5">Payload Filter</div>
                    <div className="bg-black/30 p-1.5 rounded border border-white/5">HNSW M=16, ef=100</div>
                  </div>
                </div>
              </div>

            </div>
          </div>
        </div>

        <SubHeading id="core-principles">Core Storage Invariants</SubHeading>
        <div className="grid gap-3 sm:grid-cols-2 my-3">
          <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4 space-y-2">
            <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-cyan-400" />
            <h4 className="text-xs font-bold text-cyan-200 flex items-center gap-1.5">
              <ShieldCheck size={14} /> Immutable & Append-Only Invariant
            </h4>
            <p className="text-xs text-slate-300 leading-relaxed">
              Storage never performs in-place overwrites. Modifications to documents generate new version records
              chained by cryptographically verified packet hashes.
            </p>
          </div>

          <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4 space-y-2">
            <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-purple-400" />
            <h4 className="text-xs font-bold text-purple-200 flex items-center gap-1.5">
              <Lock size={14} /> Cryptographic Tenant Sharding
            </h4>
            <p className="text-xs text-slate-300 leading-relaxed">
              Every raw blob, relational row, and vector embedding is strictly bound to its owning <span className="font-mono text-cyan-300">tenant_id</span> and <span className="font-mono text-cyan-300">graph_id</span>.
            </p>
          </div>
        </div>

        <SubHeading id="dual-store-visual">Dual-Store Relational & Vector Sync</SubHeading>
        <Callout tone="info" title="Dual-Store Synchronization Guarantee">
          FAIM enforces simultaneous synchronization between PostgreSQL (which holds discrete symbolic facts, relations, and provenance records)
          and Qdrant (which holds vector embeddings). A document is only marked <span className="font-mono text-emerald-300">committed</span> when both engines complete transactionally.
        </Callout>
      </SectionHeading>

      {/* ── Chapter 2: End-to-End Ingestion Pipeline ─────────────────────────── */}
      <SectionHeading id="pipeline" kicker="Chapter 02" title="End-to-End Ingestion Pipeline & Data Flow">
        <p>
          When a file is uploaded via the UI or proposed by Cortex, it flows through a deterministic 9-step ingestion pipeline:
        </p>

        <SubHeading id="pipeline-visual-flow">9-Step Visual Ingest Flowchart</SubHeading>
        
        {/* ── VISUAL FLOWCHART CONDUIT ────────────────────────────────────────── */}
        <div className="my-4 overflow-hidden rounded-[16px] border border-white/10 bg-[#060913] p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-white/6 pb-2">
            <span className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
              <Workflow size={14} className="text-cyan-400" /> Ingest Pipeline Execution Track
            </span>
            <span className="text-[10px] font-mono text-slate-400">Deterministic · Zero Loss</span>
          </div>

          <div className="grid gap-2.5 sm:grid-cols-3">
            {[
              {
                step: "01",
                name: "Pre-Flight Validation",
                desc: "Sanitizes filename, checks MIME headers against allowed extension matrix.",
                badge: "MIME / Ext",
                color: "text-cyan-300 border-cyan-500/30 bg-cyan-500/10",
              },
              {
                step: "02",
                name: "CAS SHA-256 Write",
                desc: "Streams file to disk /var/lib/faim/raw/blobs/<sha256> with hash deduplication.",
                badge: "CAS Stream",
                color: "text-cyan-300 border-cyan-500/30 bg-cyan-500/10",
              },
              {
                step: "03",
                name: "PostgreSQL Pending",
                desc: "Inserts initial storage_file row with status 'pending' and registers file size.",
                badge: "SQL Insert",
                color: "text-indigo-300 border-indigo-500/30 bg-indigo-500/10",
              },
              {
                step: "04",
                name: "Redis Queue Dispatch",
                desc: "Enqueues background task for ingestion worker with selected profile.",
                badge: "Redis Pub",
                color: "text-emerald-300 border-emerald-500/30 bg-emerald-500/10",
              },
              {
                step: "05",
                name: "Perception & OCR",
                desc: "Parses PDF/MD/TXT or runs PaddleOCR v6 for scanned document pages.",
                badge: "PaddleOCR",
                color: "text-amber-300 border-amber-500/30 bg-amber-500/10",
              },
              {
                step: "06",
                name: "8 Sidecars Extraction",
                desc: "Generates lemmata, n-gram shingles, aliases, transliterations, and relation cues.",
                badge: "8 Sidecars",
                color: "text-purple-300 border-purple-500/30 bg-purple-500/10",
              },
              {
                step: "07",
                name: "Knowledge Atomization",
                desc: "Extracts atomic triples (subject-predicate-object) mapped to line numbers.",
                badge: "Triples",
                color: "text-purple-300 border-purple-500/30 bg-purple-500/10",
              },
              {
                step: "08",
                name: "Dual-Store Commit",
                desc: "Inserts nodes into Postgres and HNSW vector points into Qdrant in lockstep.",
                badge: "2-Phase Sync",
                color: "text-sky-300 border-sky-500/30 bg-sky-500/10",
              },
              {
                step: "09",
                name: "Packet Hash & Evolve",
                desc: "Chains packet hash, marks status 'committed', and triggers domain memory learning.",
                badge: "Committed",
                color: "text-emerald-400 border-emerald-500/40 bg-emerald-500/15",
              },
            ].map((p) => (
              <div key={p.step} className="rounded-xl border border-white/6 bg-white/[0.02] p-3 flex flex-col justify-between space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-slate-400">Step {p.step}</span>
                  <span className={`px-1.5 py-0.5 rounded text-[9px] font-mono border ${p.color}`}>
                    {p.badge}
                  </span>
                </div>
                <div>
                  <h5 className="text-xs font-bold text-white">{p.name}</h5>
                  <p className="text-[10px] text-slate-400 mt-0.5 leading-relaxed">{p.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <SubHeading id="pipeline-sidecars-visual">8 Sidecars Fan-Out Architecture</SubHeading>
        <p className="text-xs text-slate-300 leading-relaxed">
          During document ingestion, FAIM builds 8 additive, deterministic sidecar channels alongside the canonical dense vector.
          The visual matrix below shows how raw text is deterministically decomposed into specialized semantic channels:
        </p>

        {/* ── VISUAL SIDECARS FAN-OUT MATRIX ─────────────────────────────────── */}
        <div className="my-4 grid gap-2.5 sm:grid-cols-2 text-xs">
          {[
            { num: "01", name: "Phrase Shingles (N-Grams)", desc: "Captures multi-word sequence signatures (bigrams, trigrams) to prevent semantic fragmentation of domain terminology.", icon: Binary },
            { num: "02", name: "Concept Keys & Lemmata", desc: "Extracts canonical dictionary lemmata to bridge variations in verb tenses and noun plurals deterministically.", icon: Search },
            { num: "03", name: "Alias Families", desc: "Maps acronyms, abbreviations, and organizational aliases (e.g., 'FAIM' ↔ 'Fractal Antisymmetric Inheritance Memory').", icon: Share2 },
            { num: "04", name: "Transliterated Tokens", desc: "Standardizes phonetic variations and non-Latin character sets for cross-script retrieval consistency.", icon: Globe },
            { num: "05", name: "Stem Families", desc: "Groups morphological root stems to ensure query matching across derivative word forms.", icon: GitBranch },
            { num: "06", name: "Morphology Buckets", desc: "Categorizes syntactic parts of speech and structural sentence roles for exact grammatical alignment.", icon: Layers },
            { num: "07", name: "Relation Cues", desc: "Identifies subject-predicate-object assertion markers (e.g., 'depends_on', 'supersedes', 'located_in').", icon: GitCommit },
            { num: "08", name: "Temporal & Numerical Cues", desc: "Indexes ISO timestamps, version numbers, and numerical constraints for precise temporal ordering.", icon: Activity },
          ].map((s) => {
            const Icon = s.icon;
            return (
              <div key={s.num} className="rounded-xl border border-white/8 bg-white/[0.02] p-3 flex gap-3 items-start">
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-cyan-500/30 bg-cyan-500/10 text-cyan-300 font-mono text-xs font-bold">
                  {s.num}
                </div>
                <div>
                  <h5 className="text-xs font-bold text-cyan-200 flex items-center gap-1.5">
                    <Icon size={12} className="text-cyan-400" /> {s.name}
                  </h5>
                  <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">{s.desc}</p>
                </div>
              </div>
            );
          })}
        </div>

        <SubHeading id="pipeline-atom-commit">Knowledge Atomization & Commit</SubHeading>
        <Callout tone="success" title="Atomic Commit Guarantee">
          If vector insertion into Qdrant fails due to a network glitch, PostgreSQL rolls back the relational atom transaction
          and marks the file with an explicit diagnostic error message, allowing single-click retry.
        </Callout>
      </SectionHeading>

      {/* ── Chapter 3: Storage Engine Topology & Layers ───────────────────────── */}
      <SectionHeading id="engines" kicker="Chapter 03" title="Storage Engine Topology & Multi-Store Layers">
        <p>
          FAIM utilizes a purpose-built 4-tier storage architecture designed for speed, resilience, and cryptographic auditability:
        </p>

        <SubHeading id="engine-stack-visual">4-Tier Storage Engine Stack</SubHeading>
        
        {/* Visual Engine Stack Diagram */}
        <div className="my-4 overflow-hidden rounded-[16px] border border-white/10 bg-[#050711] p-4 space-y-3">
          <div className="grid gap-3 sm:grid-cols-4 text-xs font-mono">
            <div className="rounded-xl border border-cyan-500/30 bg-cyan-500/[0.04] p-3 space-y-2">
              <span className="text-[10px] text-cyan-400 font-bold uppercase">Tier 1: Physical Bytes</span>
              <h5 className="text-xs font-bold text-white flex items-center gap-1.5">
                <HardDrive size={13} className="text-cyan-400" /> CAS Disk Store
              </h5>
              <p className="text-[10px] font-sans text-slate-400 leading-relaxed">
                Physical files stored at <code className="text-cyan-300">/var/lib/faim/raw/blobs/&lt;sha256&gt;</code>.
              </p>
            </div>

            <div className="rounded-xl border border-indigo-500/30 bg-indigo-500/[0.04] p-3 space-y-2">
              <span className="text-[10px] text-indigo-400 font-bold uppercase">Tier 2: Relational Atoms</span>
              <h5 className="text-xs font-bold text-white flex items-center gap-1.5">
                <Database size={13} className="text-indigo-400" /> PostgreSQL 15
              </h5>
              <p className="text-[10px] font-sans text-slate-400 leading-relaxed">
                Nodes, edges, properties, version trees, audit ledgers, and pgvector fallbacks.
              </p>
            </div>

            <div className="rounded-xl border border-purple-500/30 bg-purple-500/[0.04] p-3 space-y-2">
              <span className="text-[10px] text-purple-400 font-bold uppercase">Tier 3: Vector Indices</span>
              <h5 className="text-xs font-bold text-white flex items-center gap-1.5">
                <Zap size={13} className="text-purple-400" /> Qdrant HNSW
              </h5>
              <p className="text-[10px] font-sans text-slate-400 leading-relaxed">
                Multi-tenant collection partitions, Cosine metric, sub-ms similarity search.
              </p>
            </div>

            <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/[0.04] p-3 space-y-2">
              <span className="text-[10px] text-emerald-400 font-bold uppercase">Tier 4: Acceleration</span>
              <h5 className="text-xs font-bold text-white flex items-center gap-1.5">
                <Activity size={13} className="text-emerald-400" /> Redis 7
              </h5>
              <p className="text-[10px] font-sans text-slate-400 leading-relaxed">
                Distributed locks, worker queues, and real-time query acceleration caching.
              </p>
            </div>
          </div>
        </div>

        <SubHeading id="engine-cas">Layer 1: Content-Addressed Blob Store (CAS)</SubHeading>
        <p className="text-xs text-slate-300 leading-relaxed">
          Raw file contents are stored strictly by their SHA-256 cryptographic digest. This guarantees that files with identical contents
          never consume redundant disk space, and physical bytes can never be tampered with undetected.
        </p>

        <SubHeading id="engine-postgres">Layer 2: Relational Spine (PostgreSQL + pgvector)</SubHeading>
        <p className="text-xs text-slate-300 leading-relaxed">
          PostgreSQL 15 serves as the single source of truth, managing <code className="text-indigo-300">storage_files</code>,
          <code className="text-indigo-300">nodes</code>, <code className="text-indigo-300">edges</code>,
          <code className="text-indigo-300">events</code>, and <code className="text-indigo-300">cortex_tool_approvals</code>.
        </p>

        <SubHeading id="engine-qdrant">Layer 3: Vector Engine (Qdrant HNSW)</SubHeading>
        <p className="text-xs text-slate-300 leading-relaxed">
          Qdrant clusters knowledge vectors using Hierarchical Navigable Small World (HNSW) graphs, executing cosine similarity queries across multi-million node tenant graphs.
        </p>

        <SubHeading id="engine-redis">Layer 4: Cache & Queue Layer (Redis)</SubHeading>
        <p className="text-xs text-slate-300 leading-relaxed">
          Redis coordinates background ingestion workers, locks concurrent mutation jobs (<code className="text-emerald-300">faim:lock:*</code>),
          and caches frequent query results for ultra-low latency response times.
        </p>
      </SectionHeading>

      {/* ── Chapter 4: Upload Profiles & Persist Policies ──────────────────────── */}
      <SectionHeading id="profiles" kicker="Chapter 04" title="Upload Profiles & Persist Policies">
        <p>
          FAIM provides configurable extraction profiles and persist modes to optimize processing depth based on file complexity and domain requirements.
        </p>

        <SubHeading id="profile-modes">Profiles: STRICT, BALANCED, RELAXED, FAST</SubHeading>
        <DTable
          head={["Profile", "Extraction Depth", "Sidecar Level", "Recommended Use Case"]}
          rows={[
            {
              cells: [
                <span key="1" className="font-mono font-bold text-emerald-300">FAST</span>,
                "Lightweight paragraph chunking + direct dense vector generation",
                "Basic n-grams + Lemmata",
                "High-throughput bulk ingestion & simple text documents",
              ],
            },
            {
              cells: [
                <span key="2" className="font-mono font-bold text-cyan-300">RELAXED (Default)</span>,
                "Standard entity & relation extraction with full sidecar generation",
                "All 8 Semantic Sidecars + ConceptNet expansion",
                "Enterprise knowledge bases, manuals, and technical docs",
              ],
            },
            {
              cells: [
                <span key="3" className="font-mono font-bold text-sky-300">BALANCED</span>,
                "Standard extraction with bounded acceleration and adaptive safeguards",
                "Core sidecars + deterministic semantic expansion",
                "General research and knowledge-base ingestion",
              ],
            },
            {
              cells: [
                <span key="4" className="font-mono font-bold text-purple-300">STRICT</span>,
                "Deep hierarchical entity extraction + deep contradiction checking",
                "Complete 8 Sidecars + Multi-lingual bridges + full validation",
                "Legal policies, compliance standards, and medical assertions",
              ],
            },
          ]}
        />

        <SubHeading id="persist-modes">Persist Validation Modes</SubHeading>
        <div className="grid gap-3 sm:grid-cols-2 my-3">
          <div className="rounded-[14px] border border-white/8 bg-white/[0.03] p-4 space-y-1.5">
            <span className="font-mono text-[10px] font-bold text-emerald-300 uppercase">Relaxed Mode</span>
            <h4 className="text-xs font-bold text-white">Tolerant Persistence</h4>
            <p className="text-xs text-slate-400 leading-relaxed">
              Allows files to commit even if non-critical warnings occur during extraction (e.g. minor OCR confidence dips or partial entity parse warnings).
            </p>
          </div>

          <div className="rounded-[14px] border border-white/8 bg-white/[0.03] p-4 space-y-1.5">
            <span className="font-mono text-[10px] font-bold text-amber-300 uppercase">Strict Mode</span>
            <h4 className="text-xs font-bold text-white">Zero-Warning Gatekeeping</h4>
            <p className="text-xs text-slate-400 leading-relaxed">
              Requires 100% validation pass. If any extraction invariant fails, the ingest rolls back and logs the failure in the catalog.
            </p>
          </div>
        </div>

        <SubHeading id="policy-engine-visual">UI Mode Policy Decision Tree</SubHeading>
        <p className="text-xs text-slate-300 leading-relaxed">
          The storage header displays the <strong>Effective UI Mode Policy</strong> badge resolved from your tenant session,
          ensuring operators always have clear visibility into active write permissions.
        </p>
      </SectionHeading>

      {/* ── Chapter 5: OCR Perception & Document Extraction ───────────────────── */}
      <SectionHeading id="ocr" kicker="Chapter 05" title="OCR Perception & Document Extraction">
        <p>
          Scanned PDFs, technical diagrams, and document images pass through the built-in Optical Character Recognition (OCR) perception pipeline.
        </p>

        <SubHeading id="ocr-pipeline-visual">PaddleOCR v6 Pipeline Architecture</SubHeading>
        
        {/* Visual OCR Pipeline Diagram */}
        <div className="my-4 overflow-hidden rounded-[16px] border border-white/10 bg-[#060813] p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-white/6 pb-2">
            <span className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
              <ScanText size={14} className="text-amber-400" /> OCR Multi-Stage Perception Engine
            </span>
            <span className="text-[10px] font-mono text-amber-400">PaddleOCR v6 · Local CPU/GPU</span>
          </div>

          <div className="grid gap-2 sm:grid-cols-4 text-xs font-mono">
            <div className="rounded-xl border border-white/8 bg-white/[0.02] p-3 space-y-1">
              <span className="text-[10px] text-amber-400 font-bold">1. Pre-Processing</span>
              <p className="text-[10px] font-sans text-slate-400">Binarization, deskewing, DPI normalization &gt;= 150.</p>
            </div>
            <div className="rounded-xl border border-white/8 bg-white/[0.02] p-3 space-y-1">
              <span className="text-[10px] text-amber-400 font-bold">2. Text Detection</span>
              <p className="text-[10px] font-sans text-slate-400">DBNet text box polygon boundary detection.</p>
            </div>
            <div className="rounded-xl border border-white/8 bg-white/[0.02] p-3 space-y-1">
              <span className="text-[10px] text-amber-400 font-bold">3. Direction Angle</span>
              <p className="text-[10px] font-sans text-slate-400">Orientation classification (0°, 90°, 180°, 270°).</p>
            </div>
            <div className="rounded-xl border border-white/8 bg-white/[0.02] p-3 space-y-1">
              <span className="text-[10px] text-amber-400 font-bold">4. Recognition</span>
              <p className="text-[10px] font-sans text-slate-400">SVTR text recognition with confidence scores.</p>
            </div>
          </div>
        </div>

        <SubHeading id="ocr-formats">Supported Formats & Limits</SubHeading>
        <div className="grid gap-2.5 sm:grid-cols-2 my-3 text-xs">
          <div className="rounded-xl border border-white/8 bg-white/[0.02] p-3">
            <span className="font-bold text-cyan-300">Text & Structured Documents:</span>
            <p className="text-slate-400 mt-1"><code className="text-slate-200">.pdf</code>, <code className="text-slate-200">.docx</code>, <code className="text-slate-200">.md</code>, <code className="text-slate-200">.txt</code>, <code className="text-slate-200">.json</code></p>
          </div>
          <div className="rounded-xl border border-white/8 bg-white/[0.02] p-3">
            <span className="font-bold text-cyan-300">Images & Scanned Pages:</span>
            <p className="text-slate-400 mt-1"><code className="text-slate-200">.png</code>, <code className="text-slate-200">.jpg</code>, <code className="text-slate-200">.jpeg</code>, <code className="text-slate-200">.tiff</code></p>
          </div>
        </div>

        <SubHeading id="ocr-config">Runtime OCR Environment Config</SubHeading>
        <DTable
          head={["Environment Variable", "Default", "Description"]}
          rows={[
            { cells: [<code key="1">FAIM_OCR_ENABLED</code>, "true", "Enables / disables OCR extraction for images and scanned PDFs"] },
            { cells: [<code key="2">FAIM_OCR_ENGINE</code>, "paddleocr_v6", "OCR engine selection (PaddleOCR v6 / fallback parser)"] },
            { cells: [<code key="3">FAIM_OCR_FAIL_CLOSED</code>, "false", "Whether to reject file on OCR error (true) or fallback gracefully (false)"] },
            { cells: [<code key="4">FAIM_OCR_LANGS</code>, "eng", "Comma-separated language models (eng, deu, fra, spa)"] },
          ]}
        />
      </SectionHeading>

      {/* ── Chapter 6: Cryptographic Provenance & Proofs ──────────────────────── */}
      <SectionHeading id="catalog" kicker="Chapter 06" title="Cryptographic Provenance & Proofs">
        <p>
          The Storage File Catalog provides complete transparency into all persisted knowledge artifacts and their cryptographic lineage.
        </p>

        <SubHeading id="provenance-chain-visual">Visual SHA-256 & Packet Hash Chain</SubHeading>
        
        {/* Visual Hash Chain Box */}
        <div className="my-4 overflow-hidden rounded-[16px] border border-cyan-500/30 bg-[#050711] p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-white/6 pb-2">
            <span className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
              <ShieldCheck size={14} className="text-cyan-400" /> Cryptographic Provenance Hash Chain
            </span>
            <span className="text-[10px] font-mono text-cyan-300">100% Grounded Auditing</span>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 text-xs font-mono">
            <div className="flex-1 rounded-xl border border-cyan-500/20 bg-cyan-950/20 p-3 space-y-1">
              <span className="text-[10px] text-cyan-400 font-bold">1. Raw Byte Digest</span>
              <p className="text-[11px] text-white">SHA-256 Fingerprint</p>
              <p className="text-[9px] text-slate-400 truncate">sha256:4a8b...9f2c (Physical Disk)</p>
            </div>

            <ArrowRight size={18} className="text-cyan-400 shrink-0 hidden sm:block" />
            <ArrowDown size={18} className="text-cyan-400 shrink-0 sm:hidden" />

            <div className="flex-1 rounded-xl border border-indigo-500/20 bg-indigo-950/20 p-3 space-y-1">
              <span className="text-[10px] text-indigo-400 font-bold">2. Atom Representation</span>
              <p className="text-[11px] text-white">Packet Hash</p>
              <p className="text-[9px] text-slate-400 truncate">packet:7d1e...3b8a (Relational)</p>
            </div>

            <ArrowRight size={18} className="text-indigo-400 shrink-0 hidden sm:block" />
            <ArrowDown size={18} className="text-indigo-400 shrink-0 sm:hidden" />

            <div className="flex-1 rounded-xl border border-emerald-500/20 bg-emerald-950/20 p-3 space-y-1">
              <span className="text-[10px] text-emerald-400 font-bold">3. 3D FIG Proof</span>
              <p className="text-[11px] text-white">Verified Glow Receipt</p>
              <p className="text-[9px] text-slate-400 truncate">pulse_id: v2_pulse_9901</p>
            </div>
          </div>
        </div>

        <SubHeading id="catalog-fields">Catalog Metadata Schema</SubHeading>
        <p className="text-xs text-slate-300 leading-relaxed">
          Each file record in the catalog surfaces granular metrics:
        </p>
        <ul className="list-disc space-y-1 pl-5 text-xs text-slate-300 font-mono">
          <li><strong>raw_id:</strong> Unique internal identifier for the file ingest record.</li>
          <li><strong>filename & mime_type:</strong> Original file name and sanitized content type.</li>
          <li><strong>size_bytes:</strong> Exact byte length stored on disk.</li>
          <li><strong>sha256:</strong> Cryptographic SHA-256 fingerprint of the raw file.</li>
          <li><strong>packet_hash:</strong> Hash chain of the parsed and committed knowledge atoms.</li>
          <li><strong>node_count & vector_count:</strong> Exact number of graph entities and embeddings created.</li>
          <li><strong>ingest_status:</strong> Current lifecycle status (<span className="text-emerald-300">committed</span>, <span className="text-cyan-300">processing</span>, <span className="text-amber-300">pending</span>, <span className="text-rose-300">error</span>).</li>
        </ul>

        <SubHeading id="catalog-immutability">Append-Only Immutability Rule</SubHeading>
        <Callout tone="success" title="Zero-Hallucination Evidence Trail">
          When FAIM Cortex cites a source, it links the answer directly to the file&apos;s SHA-256 raw digest and packet hash,
          guaranteeing that every output is 100% verified against original source documents.
        </Callout>
      </SectionHeading>

      {/* ── Chapter 7: Ingest State Machine & Crash Recovery ─────────────────── */}
      <SectionHeading id="statemachine" kicker="Chapter 07" title="Ingest State Machine & Crash Recovery">
        <p>
          The ingestion lifecycle follows a strictly ordered finite state machine with automatic crash recovery and idempotency guarantees.
        </p>

        <SubHeading id="statemachine-visual">Visual State Transition Graph</SubHeading>
        
        {/* Visual State Machine Box */}
        <div className="my-4 overflow-hidden rounded-[16px] border border-white/10 bg-[#060813] p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-white/6 pb-2">
            <span className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
              <RotateCcw size={14} className="text-cyan-400" /> Finite State Machine & Rollback Graph
            </span>
            <span className="text-[10px] font-mono text-emerald-400">Deterministic Recovery</span>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
            <div className="rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-3 py-2 text-center">
              <span className="text-[9px] text-slate-400">State 1</span>
              <p className="text-cyan-300 font-bold">received</p>
            </div>
            <ArrowRight size={14} className="text-slate-500 shrink-0" />
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-center">
              <span className="text-[9px] text-slate-400">State 2</span>
              <p className="text-amber-300 font-bold">pending</p>
            </div>
            <ArrowRight size={14} className="text-slate-500 shrink-0" />
            <div className="rounded-lg border border-sky-500/30 bg-sky-500/10 px-3 py-2 text-center">
              <span className="text-[9px] text-slate-400">State 3</span>
              <p className="text-sky-300 font-bold">processing</p>
            </div>
            <ArrowRight size={14} className="text-slate-500 shrink-0" />
            <div className="rounded-lg border border-indigo-500/30 bg-indigo-500/10 px-3 py-2 text-center">
              <span className="text-[9px] text-slate-400">State 4</span>
              <p className="text-indigo-300 font-bold">embedding</p>
            </div>
            <ArrowRight size={14} className="text-slate-500 shrink-0" />
            <div className="rounded-lg border border-emerald-500/40 bg-emerald-500/15 px-3 py-2 text-center shadow-[0_0_15px_rgba(16,185,129,0.2)]">
              <span className="text-[9px] text-slate-400">Final</span>
              <p className="text-emerald-300 font-bold">committed</p>
            </div>
          </div>
        </div>

        <DTable
          head={["State", "Phase", "System Action", "Next State"]}
          rows={[
            {
              cells: [
                <span key="1" className="font-mono text-cyan-300">received</span>,
                "Intake",
                "File uploaded, written to CAS, initial DB record inserted",
                <span key="1b" className="font-mono text-cyan-300">pending</span>,
              ],
            },
            {
              cells: [
                <span key="2" className="font-mono text-amber-300">pending</span>,
                "Queued",
                "Job enqueued in Redis waiting for background worker pick-up",
                <span key="2b" className="font-mono text-sky-300">processing</span>,
              ],
            },
            {
              cells: [
                <span key="3" className="font-mono text-sky-300">processing</span>,
                "Extract & OCR",
                "Worker extracts text, runs OCR, builds 8 sidecars and knowledge triples",
                <span key="3b" className="font-mono text-indigo-300">embedding</span>,
              ],
            },
            {
              cells: [
                <span key="4" className="font-mono text-indigo-300">embedding</span>,
                "Vectorization",
                "Generating dense embeddings and inserting HNSW vectors into Qdrant",
                <span key="4b" className="font-mono text-emerald-300">committed</span>,
              ],
            },
            {
              cells: [
                <span key="5" className="font-mono text-emerald-300">committed</span>,
                "Live in Graph",
                "Relational & vector stores synchronized; graph version incremented",
                "—",
              ],
            },
            {
              cells: [
                <span key="6" className="font-mono text-rose-300">error</span>,
                "Failed",
                "Failure logged with explicit error reason; transaction rolled back",
                <span key="6b" className="font-mono text-cyan-300">pending (on retry)</span>,
              ],
            },
          ]}
        />

        <SubHeading id="state-recovery">Worker Idempotency & Crash Recovery</SubHeading>
        <p className="text-xs text-slate-300 leading-relaxed">
          If a worker process restarts mid-pipeline, stale in-progress jobs are detected via heartbeat timeouts and safely requeued.
          Because all graph entity creation operations are idempotent based on packet hash, no duplicate nodes are generated.
        </p>

        <SubHeading id="state-dedup">Content-Addressed Deduplication</SubHeading>
        <p className="text-xs text-slate-300 leading-relaxed">
          Uploading the same identical file twice automatically matches the existing SHA-256 digest in the CAS store,
          bypassing re-upload bandwidth and referencing the verified raw blob directly.
        </p>
      </SectionHeading>

      {/* ── Chapter 8: Governance, Orphan Scans & HITL ─────────────────────────── */}
      <SectionHeading id="governance" kicker="Chapter 08" title="Storage Governance, Orphan Scans & HITL Approvals">
        <p>
          To maintain pristine knowledge base integrity, FAIM provides automated orphan detection and mandatory human-in-the-loop approvals for mutating actions.
        </p>

        <SubHeading id="gov-workflow-visual">HITL Approval Queue Workflow</SubHeading>
        
        {/* Visual HITL Workflow Box */}
        <div className="my-4 overflow-hidden rounded-[16px] border border-amber-500/30 bg-[#0a0812] p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-white/6 pb-2">
            <span className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
              <Lock size={14} className="text-amber-400" /> Human-in-the-Loop Storage Governance
            </span>
            <span className="text-[10px] font-mono text-amber-300">Zero Unauthorized Mutations</span>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 text-xs font-mono">
            <div className="flex-1 rounded-xl border border-white/8 bg-white/[0.02] p-3 space-y-1">
              <span className="text-[10px] text-cyan-300 font-bold">1. Mutation Propose</span>
              <p className="text-[11px] text-white">Agent / User Request</p>
              <p className="text-[9px] text-slate-400">upload / delete / reingest</p>
            </div>

            <ArrowRight size={16} className="text-amber-400 shrink-0 hidden sm:block" />
            <ArrowDown size={16} className="text-amber-400 shrink-0 sm:hidden" />

            <div className="flex-1 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 space-y-1">
              <span className="text-[10px] text-amber-300 font-bold">2. HITL Approval Queue</span>
              <p className="text-[11px] text-white">Operator Decision</p>
              <p className="text-[9px] text-amber-200/80">Approve / Reject + Note</p>
            </div>

            <ArrowRight size={16} className="text-amber-400 shrink-0 hidden sm:block" />
            <ArrowDown size={16} className="text-amber-400 shrink-0 sm:hidden" />

            <div className="flex-1 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 space-y-1">
              <span className="text-[10px] text-emerald-300 font-bold">3. Idempotent Execute</span>
              <p className="text-[11px] text-white">Durable Execution</p>
              <p className="text-[9px] text-emerald-200/80">Ledger audit receipt logged</p>
            </div>
          </div>
        </div>

        <SubHeading id="gov-orphans-visual">Orphan Artifact Scanner & GC</SubHeading>
        <p className="text-xs text-slate-300 leading-relaxed">
          The <strong>Orphan Scanner</strong> inspects the storage layer to discover:
        </p>
        <ul className="list-disc space-y-1 pl-5 text-xs text-slate-300">
          <li>Database records whose backing CAS raw blob is missing from disk.</li>
          <li>Raw blobs on disk that are no longer referenced by any graph node.</li>
          <li>Partially failed historical ingest artifacts.</li>
        </ul>

        <SubHeading id="gov-isolation">Multi-Tenant Crypto-Sharding</SubHeading>
        <Callout tone="warn" title="Approval Gatekeeping">
          Destructive storage actions (hard deletes, purge, re-ingest) proposed by Cortex or operators are placed in the
          <strong>Approval Queue</strong>. No mutations execute until explicitly approved by an authorized administrator.
        </Callout>
      </SectionHeading>

      {/* ── Chapter 9: Operations & Storage REST API ──────────────────────────── */}
      <SectionHeading id="api" kicker="Chapter 09" title="Storage Operations & REST API Reference">
        <SubHeading id="api-endpoints">REST & Cortex Storage Endpoints</SubHeading>
        <DTable
          head={["Method", "Endpoint", "Description", "Auth Required"]}
          rows={[
            {
              cells: [
                <span key="1" className="font-mono font-bold text-cyan-300">POST</span>,
                <code key="2">/api/v1/storage/upload</code>,
                "Batch file upload and ingest initiation",
                "Tenant API Key",
              ],
            },
            {
              cells: [
                <span key="3" className="font-mono font-bold text-sky-300">GET</span>,
                <code key="4">/api/v1/storage/catalog</code>,
                "Paginated catalog of stored files with filters & search",
                "Tenant API Key",
              ],
            },
            {
              cells: [
                <span key="5" className="font-mono font-bold text-sky-300">GET</span>,
                <code key="6">/api/v1/cortex/storage/status</code>,
                "Live graph storage summary (nodes, edges, ingest counts)",
                "Tenant API Key",
              ],
            },
            {
              cells: [
                <span key="7" className="font-mono font-bold text-sky-300">GET</span>,
                <code key="8">/api/v1/cortex/storage/orphan-scan</code>,
                "Scans for orphaned graph and storage artifacts",
                "Tenant API Key",
              ],
            },
            {
              cells: [
                <span key="9" className="font-mono font-bold text-amber-300">POST</span>,
                <code key="10">/api/v1/cortex/tool-approvals/propose</code>,
                "Propose mutating action (upload/delete/reingest) to queue",
                "Tenant API Key",
              ],
            },
            {
              cells: [
                <span key="11" className="font-mono font-bold text-rose-300">DELETE</span>,
                <code key="12">/api/v1/storage/files/{`{raw_id}`}</code>,
                "Soft delete or request purge of a stored file",
                "Admin Key",
              ],
            },
          ]}
        />

        <SubHeading id="api-cli">CLI & Diagnostic Inspection Commands</SubHeading>
        <div className="rounded-[14px] border border-white/8 bg-black/40 p-3 font-mono text-xs text-slate-300 space-y-2">
          <p className="text-slate-500"># Check live storage health summary</p>
          <p className="text-cyan-300">curl -H &quot;X-Tenant-Id: default&quot; -H &quot;X-Api-Key: test-key&quot; http://localhost:8000/api/v1/cortex/storage/status</p>
          <p className="text-slate-500 mt-2"># Run an orphan artifact scan</p>
          <p className="text-cyan-300">curl -H &quot;X-Tenant-Id: default&quot; -H &quot;X-Api-Key: test-key&quot; http://localhost:8000/api/v1/cortex/storage/orphan-scan</p>
        </div>

        <SubHeading id="api-metrics">Storage Health & Throughput Metrics</SubHeading>
        <p className="text-xs text-slate-300 leading-relaxed">
          Storage telemetry streams real-time health metrics including ingest throughput (MB/s), active worker concurrency,
          Qdrant vector density, and PostgreSQL transaction latencies.
        </p>
      </SectionHeading>

      {/* ── Chapter 10: Troubleshooting & Enterprise FAQ ───────────────────────── */}
      <SectionHeading id="troubleshoot" kicker="Chapter 10" title="Troubleshooting & Enterprise FAQ">
        <SubHeading id="troubleshoot-matrix">Storage Diagnostics Matrix</SubHeading>
        <DTable
          head={["Observed Symptom", "Probable Root Cause", "Recommended Resolution"]}
          rows={[
            {
              cells: [
                "Upload button disabled in UI",
                "Effective mode policy forbids uploads or tenant is read-only",
                "Check the Mode Policy Banner at top of page or elevate tenant permissions",
              ],
            },
            {
              cells: [
                "File stuck in 'processing' state",
                "Worker container offline or Redis queue worker stalled",
                "Verify faim-worker container status via `docker compose ps` and restart worker if needed",
              ],
            },
            {
              cells: [
                "OCR produced empty text on scan",
                "Scanned resolution too low or language mismatch in config",
                "Check `FAIM_OCR_LANGS` runtime config and ensure image DPI >= 150",
              ],
            },
            {
              cells: [
                "Orphan count > 0 in Health Scan",
                "Aborted historical upload or deleted source file",
                "Review the Orphan Scan findings and click 'Reconcile' to clean up orphaned references",
              ],
            },
            {
              cells: [
                "HTTP 401 on storage upload",
                "Missing or invalid X-Tenant-Id or X-Api-Key headers",
                "Check API key configuration in Dashboard -> API Keys or authenticate session",
              ],
            },
          ]}
        />

        <SubHeading id="troubleshoot-faq">Enterprise Storage FAQ</SubHeading>
        <div className="space-y-3 my-3">
          {[
            {
              q: "Q1: Where are the physical raw files stored?",
              a: "Raw files are stored locally in the Content-Addressed Store at /var/lib/faim/raw/blobs/<sha256>, mounted via the raw_data Docker volume.",
            },
            {
              q: "Q2: Does FAIM store confidential files in external cloud services?",
              a: "No. All storage layers (CAS disk store, PostgreSQL, Qdrant vector engine, and PaddleOCR v6) run 100% locally on-premises or in your self-hosted Docker containers without external cloud data leakage.",
            },
            {
              q: "Q3: What happens if an upload fails mid-way?",
              a: "FAIM uses atomic transactions. If an error occurs during extraction or vectorization, the relational transaction rolls back, preventing corrupt or half-committed nodes from contaminating the knowledge graph.",
            },
            {
              q: "Q4: How does deduplication work across uploads?",
              a: "Files are fingerprinted by SHA-256 immediately upon arrival. If an identical file is uploaded again, FAIM recognizes the existing blob and avoids duplicating physical disk storage.",
            },
            {
              q: "Q5: Can I delete or re-ingest a single document from the graph?",
              a: "Yes. From the Storage catalog, you can propose a Re-Ingest or Delete action. Once approved in the Approval Queue, the file and all associated graph nodes are cleanly updated or purged.",
            },
            {
              q: "Q6: How does FAIM guarantee auditability for compliance?",
              a: "Every document commit records a cryptographic SHA-256 hash, packet hash, operator ID, and timestamp. Every Cortex answer cites exact source line numbers and verifiable evidence hashes.",
            },
          ].map((item, idx) => (
            <div key={idx} className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4 space-y-1.5">
              <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-cyan-400/80 via-cyan-400/30 to-transparent" />
              <h4 className="text-xs font-bold text-cyan-200">{item.q}</h4>
              <p className="text-xs text-slate-300 leading-relaxed">{item.a}</p>
            </div>
          ))}
        </div>
      </SectionHeading>
    </ManualShell>
  );
}

export default StorageManual;
