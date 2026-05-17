"use client";

import { motion } from "framer-motion";
import Link from "next/link";

const CARDS = [
  {
    title: "1M+ Semantic Registry",
    tag: "Deterministic Intel",
    text: "Deterministic classification of 100k+ professional concepts. No black-boxes, just structured knowledge at scale.",
    href: "/docs",
    cta: "Read Spec",
    accent: "cyan",
  },
  {
    title: "FAIM Cortex",
    tag: "Memory synthesis",
    text: "Multi-hop reasoning (up to 24 hops) with real-time neural pulse tracing and memory writeback proposals.",
    href: "/dashboard/memory-query",
    cta: "Open Cortex",
    accent: "purple",
  },
  {
    title: "Matrix Billing",
    tag: "Scale-Ready",
    text: "4-tier professional subscription matrix metered by cognitive capacity (Nodes & Hops). Transparent resource allocation.",
    href: "/docs",
    cta: "View Tiers",
    accent: "emerald",
  },
] as const;

const ACCENT_STYLES: Record<
  (typeof CARDS)[number]["accent"],
  { border: string; bg: string; text: string; button: string }
> = {
  cyan: {
    border: "border-cyan-500/20",
    bg: "bg-cyan-500/[0.04]",
    text: "text-cyan-300/70",
    button:
      "border-cyan-500/30 bg-cyan-500/10 text-cyan-200 hover:bg-cyan-500/20",
  },
  purple: {
    border: "border-purple-500/20",
    bg: "bg-purple-500/[0.04]",
    text: "text-purple-300/70",
    button:
      "border-purple-500/30 bg-purple-500/10 text-purple-200 hover:bg-purple-500/20",
  },
  emerald: {
    border: "border-emerald-500/20",
    bg: "bg-emerald-500/[0.04]",
    text: "text-emerald-300/70",
    button:
      "border-emerald-500/30 bg-emerald-500/10 text-emerald-200 hover:bg-emerald-500/20",
  },
};

export default function DocsOperations() {
  return (
    <section
      id="docs-ops"
      className="py-28 px-4 bg-gradient-to-b from-slate-950 to-[#070a18]"
    >
      <div className="max-w-6xl mx-auto relative">
        <motion.div
          initial={{ opacity: 0, y: 26 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-14"
        >
          <span className="text-cyan-400 text-sm font-medium tracking-wider uppercase">
            Docs & Operations
          </span>
          <h2 className="mt-4 text-4xl md:text-5xl font-bold text-white">
            One docs surface for{" "}
            <span className="bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
              product, query, and deploy
            </span>
          </h2>
          <p className="mt-4 text-slate-400 max-w-3xl mx-auto text-lg">
            The public site now exposes the current FAIM system, the memory
            synthesis layer, and the production deploy flow in one place so
            operators do not have to hunt through scattered notes.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-6">
          {CARDS.map((card, index) => {
            const styles = ACCENT_STYLES[card.accent];
            return (
              <motion.div
                key={card.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.08 }}
                className={`rounded-3xl border ${styles.border} ${styles.bg} p-6 sm:p-7`}
              >
                <p
                  className={`text-[10px] font-bold uppercase tracking-[0.2em] ${styles.text}`}
                >
                  {card.tag}
                </p>
                <h3 className="mt-3 text-2xl font-bold text-white">
                  {card.title}
                </h3>
                <p className="mt-4 text-sm leading-relaxed text-slate-400">
                  {card.text}
                </p>
                <Link
                  href={card.href}
                  className={`mt-6 inline-flex items-center gap-2 rounded-xl border px-4 py-2 text-sm font-medium transition-all ${styles.button}`}
                >
                  {card.cta}
                  <span aria-hidden="true">→</span>
                </Link>
              </motion.div>
            );
          })}
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.15 }}
          className="mt-8 grid gap-3 md:grid-cols-4"
        >
          {[
            "Local prod uses .env.localprod",
            "VPS prod uses deploy/env.vpsprod",
            "Selective rebuilds avoid full image churn",
            "Benchmark and smoke checks stay explicit",
          ].map((line) => (
            <div
              key={line}
              className="rounded-2xl border border-slate-800/70 bg-slate-900/30 px-4 py-3 text-[11px] font-medium text-slate-400"
            >
              {line}
            </div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
