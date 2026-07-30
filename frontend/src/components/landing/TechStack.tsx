"use client";

import { motion, useReducedMotion } from "framer-motion";
import {
  Activity,
  Braces,
  BrainCircuit,
  Box,
  Boxes,
  CheckCircle2,
  CircleDot,
  Cloud,
  Code2,
  Database,
  FileCode2,
  FileScan,
  Fingerprint,
  Globe2,
  KeyRound,
  Layers3,
  LockKeyhole,
  Network,
  Orbit,
  PanelTop,
  ScanText,
  ServerCog,
  ShieldCheck,
  Sparkles,
  TerminalSquare,
  TestTube2,
  type LucideIcon,
} from "lucide-react";

type StackItem = {
  name: string;
  role: string;
  icon: LucideIcon;
  tone: "cyan" | "violet" | "emerald" | "amber";
  status?: string;
};

type StackLayer = {
  number: string;
  name: string;
  description: string;
  icon: LucideIcon;
  tone: StackItem["tone"];
  items: StackItem[];
};

const TONE = {
  cyan: {
    text: "text-cyan-200",
    icon: "text-cyan-200",
    surface: "hover:text-white",
  },
  violet: {
    text: "text-violet-200",
    icon: "text-violet-200",
    surface: "hover:text-white",
  },
  emerald: {
    text: "text-emerald-200",
    icon: "text-emerald-200",
    surface: "hover:text-white",
  },
  amber: {
    text: "text-amber-200",
    icon: "text-amber-200",
    surface: "hover:text-white",
  },
} as const;

const STACK_LAYERS: StackLayer[] = [
  {
    number: "01",
    name: "FAIM native intelligence",
    description: "The deterministic reasoning spine built inside FAIM.",
    icon: BrainCircuit,
    tone: "cyan",
    items: [
      { name: "v_native", role: "256-dim deterministic vector", icon: Orbit, tone: "cyan" },
      { name: "Cortex", role: "task routing + bounded reasoning", icon: BrainCircuit, tone: "cyan" },
      { name: "Semantic Registry", role: "lexical and concept broadening", icon: Layers3, tone: "cyan" },
      { name: "Graph + Diffusion", role: "typed edges + adaptive hops", icon: Network, tone: "cyan" },
      { name: "Reranker V2", role: "deterministic score fusion", icon: Activity, tone: "cyan" },
      { name: "Pulse-v2", role: "reason-source event ledger", icon: Sparkles, tone: "cyan" },
      { name: "NumPy", role: "numeric validation and acceleration", icon: Braces, tone: "cyan" },
      { name: "PyTorch", role: "optional GPU acceleration path", icon: Orbit, tone: "cyan", status: "optional" },
    ],
  },
  {
    number: "02",
    name: "Data and retrieval substrate",
    description: "Durable graph truth with acceleration layers around it.",
    icon: Database,
    tone: "violet",
    items: [
      { name: "PostgreSQL", role: "graph, memory, auth, events", icon: Database, tone: "violet" },
      { name: "Qdrant", role: "optional vector acceleration", icon: Boxes, tone: "violet" },
      { name: "Redis", role: "cache, locks, rate limits", icon: Cloud, tone: "violet" },
      { name: "SQLAlchemy", role: "typed persistence boundary", icon: Braces, tone: "violet" },
      { name: "psycopg2", role: "PostgreSQL driver", icon: ServerCog, tone: "violet" },
      { name: "orjson", role: "fast API serialization", icon: Braces, tone: "violet" },
      { name: "Native ANN", role: "versioned deterministic shortlist", icon: ScanText, tone: "violet" },
      { name: "SHA-256", role: "content and lineage fingerprints", icon: Fingerprint, tone: "violet" },
    ],
  },
  {
    number: "03",
    name: "Perception and security",
    description: "Evidence extraction, multimodal sidecars, and fail-closed trust.",
    icon: ShieldCheck,
    tone: "emerald",
    items: [
      { name: "PyMuPDF", role: "PDF layout and block extraction", icon: FileScan, tone: "emerald" },
      { name: "pdfplumber + pypdf", role: "PDF text and page utilities", icon: FileScan, tone: "emerald" },
      { name: "Tesseract OCR", role: "scanned document perception", icon: ScanText, tone: "emerald" },
      { name: "python-docx", role: "DOCX structure extraction", icon: FileCode2, tone: "emerald" },
      { name: "openpyxl", role: "XLSX cells and tables", icon: FileCode2, tone: "emerald" },
      { name: "python-pptx", role: "PPTX slide structure", icon: FileCode2, tone: "emerald" },
      { name: "Pillow", role: "image normalization and features", icon: PanelTop, tone: "emerald" },
      { name: "Argon2id", role: "credential and API-key hashing", icon: KeyRound, tone: "emerald" },
      { name: "AES-GCM", role: "encrypted raw payload envelope", icon: LockKeyhole, tone: "emerald" },
    ],
  },
  {
    number: "04",
    name: "Application and operations",
    description: "The production surface developers and operators use every day.",
    icon: ServerCog,
    tone: "amber",
    items: [
      { name: "Python", role: "FAIM native runtime", icon: Code2, tone: "amber" },
      { name: "FastAPI", role: "REST and health surfaces", icon: TerminalSquare, tone: "amber" },
      { name: "Uvicorn", role: "ASGI application server", icon: Activity, tone: "amber" },
      { name: "Pydantic", role: "strict request contracts", icon: Braces, tone: "amber" },
      { name: "PyJWT + Argon2id", role: "session and key auth", icon: KeyRound, tone: "amber" },
      { name: "HTTPX", role: "service and provider calls", icon: Globe2, tone: "amber" },
      { name: "Docker", role: "repeatable local deployment", icon: Box, tone: "amber" },
      { name: "Next.js + React", role: "product and marketing UI", icon: Globe2, tone: "amber" },
      { name: "Tailwind + Framer", role: "responsive styling + motion", icon: Sparkles, tone: "amber" },
      { name: "Pytest + Playwright", role: "backend and UI validation", icon: TestTube2, tone: "amber" },
    ],
  },
];

function StackCard({ item, index, reduceMotion }: { item: StackItem; index: number; reduceMotion: boolean }) {
  const tone = TONE[item.tone];
  const Icon = item.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: reduceMotion ? 0 : 10 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.2 }}
      transition={{ duration: reduceMotion ? 0 : 0.35, delay: reduceMotion ? 0 : index * 0.035 }}
      whileHover={reduceMotion ? undefined : { y: -3 }}
      className={`group relative flex min-h-[86px] items-center gap-3 rounded-xl p-3 transition-colors duration-200 ${tone.surface}`}
    >
      <span className={`relative flex h-10 w-10 shrink-0 items-center justify-center ${tone.icon}`}>
        <Icon className="h-[18px] w-[18px]" strokeWidth={1.7} aria-hidden="true" />
      </span>
      <span className="min-w-0">
        <span className="block truncate text-sm font-semibold text-slate-200 group-hover:text-white">{item.name}</span>
        <span className="mt-1 flex items-center gap-2 text-[10px] leading-4 text-slate-500">
          {item.role}
          {item.status && <span className={`font-mono text-[8px] uppercase tracking-wider ${tone.text}`}>({item.status})</span>}
        </span>
      </span>
    </motion.div>
  );
}

export default function TechStack() {
  const reduceMotion = Boolean(useReducedMotion());

  return (
    <section className="relative overflow-hidden bg-transparent px-4 py-12 sm:px-6 sm:py-16">
      <div className="relative mx-auto max-w-6xl">
        <div className="mb-10 flex flex-col justify-between gap-5 pb-7 sm:flex-row sm:items-end">
          <div>
            <div className="mb-3 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.24em] text-cyan-200">
              <CircleDot className="h-3.5 w-3.5" aria-hidden="true" />
              Runtime foundation
            </div>
            <h2 className="text-2xl font-semibold tracking-[-0.04em] text-white sm:text-3xl">
              The stack behind the memory engine
            </h2>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">
              Not a logo wall. This is the actual execution surface: FAIM-native
              intelligence, durable storage, evidence perception, security, and
              the application layer that connects them.
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2 px-1 py-2 font-mono text-[9px] uppercase tracking-[0.16em] text-emerald-200">
            <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
            4 runtime layers
          </div>
        </div>

        <div className="space-y-5">
          {STACK_LAYERS.map((layer) => {
            const tone = TONE[layer.tone];
            const LayerIcon = layer.icon;
            return (
              <motion.div
                key={layer.name}
                initial={{ opacity: 0, y: reduceMotion ? 0 : 14 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.12 }}
                transition={{ duration: reduceMotion ? 0 : 0.4 }}
                className="grid gap-4 p-4 sm:p-5 lg:grid-cols-[220px_minmax(0,1fr)]"
              >
                <div className="relative flex gap-3 lg:block">
                  <span className={`flex h-11 w-11 shrink-0 items-center justify-center lg:mb-5 lg:ml-4 ${tone.icon}`}>
                    <LayerIcon className="h-5 w-5" strokeWidth={1.6} aria-hidden="true" />
                  </span>
                  <div className="lg:ml-4">
                    <p className={`font-mono text-[9px] uppercase tracking-[0.2em] ${tone.text}`}>Layer {layer.number}</p>
                    <h3 className="mt-1 text-base font-semibold text-white">{layer.name}</h3>
                    <p className="mt-1 max-w-xs text-xs leading-5 text-slate-500">{layer.description}</p>
                  </div>
                </div>
                <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
                  {layer.items.map((item, index) => (
                    <StackCard key={item.name} item={item} index={index} reduceMotion={reduceMotion} />
                  ))}
                </div>
              </motion.div>
            );
          })}
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-2 pt-5 font-mono text-[9px] uppercase tracking-[0.16em] text-slate-600">
          <span className="flex items-center gap-2"><ShieldCheck className="h-3.5 w-3.5 text-emerald-300" /> core path is auditable</span>
          <span className="flex items-center gap-2"><Activity className="h-3.5 w-3.5 text-cyan-300" /> accelerators stay additive</span>
          <span className="flex items-center gap-2"><LockKeyhole className="h-3.5 w-3.5 text-violet-300" /> security boundaries stay explicit</span>
        </div>
      </div>
    </section>
  );
}
