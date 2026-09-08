"use client";

import { motion, useReducedMotion } from "framer-motion";
import Link from "next/link";
import Image from "next/image";
import { ArrowDown, ArrowUpRight, Check, LockKeyhole, Network, ScanSearch } from "lucide-react";

const HERO_STATS = [
  { value: "Seeded", unit: "", label: "Semantic routing" },
  { value: "256", unit: "dim", label: "Deterministic vectors" },
  { value: "Hybrid", unit: "", label: "Retrieval stack" },
  { value: "SHA-256", unit: "", label: "Cryptographic lineage" },
];

const SPINE = [
  { label: "Deterministic semantic router", detail: "Seeded aliases and pattern overrides", icon: ScanSearch },
  { label: "Graph-native retrieval", detail: "Diffusion, reranking, and bounded hops", icon: Network },
  { label: "Guarded writeback safety", detail: "Durable, idempotent structural updates", icon: LockKeyhole },
];

export default function Hero() {
  const reduceMotion = useReducedMotion();

  return (
    <section className="faim-landing-hero relative min-h-[100svh] overflow-hidden bg-[#050a14] text-white">
      <div className="pointer-events-none absolute inset-0 faim-grid opacity-60" />
      <div className="pointer-events-none absolute -right-40 top-16 h-[34rem] w-[34rem] rounded-full bg-cyan-500/[0.06] blur-[140px]" />
      <div className="pointer-events-none absolute bottom-0 left-1/3 h-64 w-64 rounded-full bg-indigo-500/[0.05] blur-[120px]" />

      <div className="relative mx-auto flex min-h-[100svh] w-full max-w-[1480px] flex-col justify-center px-5 pb-14 pt-28 sm:px-8 lg:px-12 lg:py-16">
        <div className="faim-hero-brand mb-10 flex items-center justify-between gap-4 lg:mb-14">
          <div className="flex items-center gap-3">
            <Image src="/logo-coded.svg" alt="FAIMATRIX" width={42} height={42} className="h-10 w-10 rounded-xl border border-cyan-300/30 bg-cyan-300/[0.04] p-1" priority />
            <div>
              <p className="text-sm font-semibold tracking-[0.18em] text-white">FAIMATRIX</p>
              <p className="mt-1 font-mono text-[9px] uppercase tracking-[0.22em] text-slate-500">Public system atlas</p>
            </div>
          </div>
          <span className="hidden rounded-lg border border-emerald-300/20 bg-emerald-300/[0.07] px-3 py-2 font-mono text-[9px] uppercase tracking-[0.18em] text-emerald-200 sm:inline-flex">Deterministic core online</span>
        </div>

        <div className="grid items-center gap-10 lg:grid-cols-[minmax(0,1.08fr)_minmax(320px,0.72fr)] lg:gap-14">
          <motion.div
            initial={{ opacity: 0, y: reduceMotion ? 0 : 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: reduceMotion ? 0 : 0.45 }}
            className="max-w-3xl"
          >
            <div className="flex items-center gap-3 font-mono text-[10px] font-semibold uppercase tracking-[0.28em] text-cyan-300">
              <span className="h-2 w-2 rounded-full bg-cyan-300 shadow-[0_0_18px_rgba(103,232,249,0.8)]" />
              FAIMATRIX / Deterministic intelligence
            </div>

            <h1 className="mt-6 max-w-4xl text-[clamp(2.7rem,6vw,5.8rem)] font-semibold leading-[0.95] tracking-[-0.065em] text-slate-50">
              Deterministic intelligence
              <span className="block bg-gradient-to-r from-cyan-300 via-sky-400 to-indigo-400 bg-clip-text text-transparent">
                built on pure math.
              </span>
            </h1>

            <p className="mt-6 max-w-2xl text-[clamp(1rem,1.35vw,1.2rem)] leading-7 text-slate-400">
              FAIMATRIX is a structured knowledge engine powered by a
              deterministic semantic router. It combines 256-dim deterministic
              vectors with guarded memory writebacks, graph diffusion, and
              evidence-linked Cortex synthesis; optional model output remains
              an explicit application-layer dependency.
            </p>

            <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
              <Link
                href="/auth/signup"
                className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-cyan-300 px-6 text-sm font-semibold text-slate-950 shadow-[0_12px_36px_rgba(34,211,238,0.16)] transition-transform duration-200 hover:-translate-y-0.5 hover:bg-cyan-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-200 focus-visible:ring-offset-2 focus-visible:ring-offset-[#050a14]"
              >
                Start building <ArrowUpRight className="h-4 w-4" />
              </Link>
              <Link
                href="#platform"
                className="inline-flex min-h-12 items-center justify-center rounded-xl border border-white/[0.14] bg-white/[0.03] px-6 text-sm font-medium text-slate-200 transition-colors duration-200 hover:border-cyan-300/40 hover:bg-white/[0.06] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-200"
              >
                Explore the engine
              </Link>
              <Link
                href="/docs"
                className="inline-flex min-h-12 items-center justify-center rounded-xl px-4 text-sm font-medium text-cyan-200 transition-colors duration-200 hover:bg-cyan-300/[0.08] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-200"
              >
                Read docs <ArrowUpRight className="ml-1 h-4 w-4" />
              </Link>
            </div>
          </motion.div>

          <motion.aside
            initial={{ opacity: 0, y: reduceMotion ? 0 : 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: reduceMotion ? 0 : 0.45, delay: reduceMotion ? 0 : 0.08 }}
            aria-label="FAIM runtime spine"
            className="rounded-2xl border border-white/[0.1] bg-white/[0.035] p-4 shadow-[0_24px_80px_rgba(0,0,0,0.28)] backdrop-blur-sm sm:p-5"
          >
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-4">
              <div>
                <p className="font-mono text-[9px] uppercase tracking-[0.25em] text-slate-500">Runtime spine</p>
                <p className="mt-1 text-sm font-medium text-slate-100">Inspect every layer</p>
              </div>
              <span className="rounded-md border border-emerald-300/20 bg-emerald-300/[0.08] px-2 py-1 font-mono text-[9px] uppercase tracking-[0.12em] text-emerald-200">
                live
              </span>
            </div>

            <div className="divide-y divide-white/[0.07]">
              {SPINE.map((item) => {
                const Icon = item.icon;
                return (
                  <div key={item.label} className="flex gap-3 py-4 first:pt-5 last:pb-2">
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-cyan-300/15 bg-cyan-300/[0.06] text-cyan-200">
                      <Icon className="h-4 w-4" />
                    </span>
                    <div>
                      <p className="text-sm font-medium text-slate-100">{item.label}</p>
                      <p className="mt-1 text-xs leading-5 text-slate-500">{item.detail}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </motion.aside>
        </div>

        <motion.div
          initial={{ opacity: 0, y: reduceMotion ? 0 : 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: reduceMotion ? 0 : 0.4, delay: reduceMotion ? 0 : 0.16 }}
          className="mt-10 grid overflow-hidden rounded-2xl border border-white/[0.1] bg-white/[0.025] sm:grid-cols-2 lg:grid-cols-4"
        >
          {HERO_STATS.map((stat) => (
            <div key={stat.label} className="border-b border-white/[0.08] px-4 py-4 last:border-b-0 sm:px-5 lg:border-b-0 lg:border-r lg:last:border-r-0">
              <p className="text-xl font-semibold tracking-[-0.04em] text-slate-100 sm:text-2xl">
                {stat.value}
                {stat.unit && <span className="ml-1 text-xs font-normal text-cyan-300">{stat.unit}</span>}
              </p>
              <p className="mt-1 font-mono text-[9px] uppercase tracking-[0.16em] text-slate-500">{stat.label}</p>
            </div>
          ))}
        </motion.div>

        <div className="mt-4 grid gap-3 text-sm leading-6 text-slate-400 sm:grid-cols-2">
          <div className="rounded-xl border border-cyan-300/10 bg-cyan-300/[0.025] px-4 py-3">
            <p className="font-mono text-[9px] uppercase tracking-[0.18em] text-cyan-200/80">Deterministic semantic router</p>
            <p className="mt-1">Seeded alias and pattern classification with no LLM required for this path. Latency depends on deployment and is reported in the benchmark surface.</p>
          </div>
          <div className="rounded-xl border border-indigo-300/10 bg-indigo-300/[0.025] px-4 py-3">
            <p className="font-mono text-[9px] uppercase tracking-[0.18em] text-indigo-200/80">Guarded writeback safety</p>
            <p className="mt-1">Cortex still requires approval for structural updates, but approved writebacks now execute through a durable, idempotent backend path and appear with receipts in the FIG View.</p>
          </div>
        </div>

        <div className="mt-6 flex items-center gap-2 font-mono text-[9px] uppercase tracking-[0.2em] text-slate-600">
          <Check className="h-3.5 w-3.5 text-cyan-300" />
          Deterministic, inspectable, graph-native
        </div>

        <button type="button" onClick={() => { window.history.replaceState(null, "", "#core"); window.dispatchEvent(new HashChangeEvent("hashchange")); }} className="mx-auto mt-10 inline-flex cursor-pointer items-center gap-2 rounded-xl border border-white/[0.1] px-4 py-2.5 font-mono text-[9px] uppercase tracking-[0.2em] text-slate-500 transition-colors hover:border-cyan-300/30 hover:text-cyan-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300">
          Explore the atlas <ArrowDown className="h-3.5 w-3.5" />
        </button>
      </div>
    </section>
  );
}
