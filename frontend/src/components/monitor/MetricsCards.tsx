"use client";

import type { GraphMetrics } from "@/lib/api";
import React from "react";

function clamp(n: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, n));
}

/**
 * Sticky glow updater:
 * - updates --mx/--my on pointer move
 * - sets --gvis to a soft value
 * - does NOT reset on leave (so glow stays)
 */
function useStickyGlow(intensity = 0.22) {
  return React.useCallback(
    (e: React.PointerEvent<HTMLElement>) => {
      const el = e.currentTarget as HTMLElement;
      const r = el.getBoundingClientRect();
      const x = clamp((e.clientX - r.left) / Math.max(r.width, 1), 0, 1);
      const y = clamp((e.clientY - r.top) / Math.max(r.height, 1), 0, 1);
      el.style.setProperty("--mx", `${(x * 100).toFixed(2)}%`);
      el.style.setProperty("--my", `${(y * 100).toFixed(2)}%`);
      el.style.setProperty("--gvis", String(intensity));
    },
    [intensity],
  );
}

export function MetricsCards({ metrics }: { metrics: GraphMetrics }) {
  const onMove = useStickyGlow(0.22);

  const { node_count, compression_ratio, redundancy, drift } = metrics;
  const flat = metrics as unknown as {
    retrieve_p50_ms?: number;
    retrieve_p95_ms?: number;
  };

  const rawBytes = metrics.raw_bytes ?? 0;
  const faimBytes = metrics.faim_bytes ?? 0;
  const p50 = metrics.latency?.retrieve_p50_ms ?? flat.retrieve_p50_ms ?? 0;
  const p95 = metrics.latency?.retrieve_p95_ms ?? flat.retrieve_p95_ms ?? 0;

  const cards = [
    {
      title: "Nodes",
      value: node_count.toLocaleString(),
      hint: "Active memory nodes in FIG",
    },
    {
      title: "Compression Ratio (CR)",
      value: `${compression_ratio.toFixed(1)}×`,
      hint: "Raw vs FAIM storage (higher is better)",
    },
    {
      title: "Redundancy (R)",
      value: `${(redundancy * 100).toFixed(2)}%`,
      hint: "Local overlap between nodes (lower is better)",
    },
    {
      title: "Drift",
      value: `${(drift * 100).toFixed(2)}%`,
      hint: "Recall degradation (lower is better)",
    },
    {
      title: "Raw bytes",
      value: `${rawBytes}`,
      hint: "Approx raw payload bytes (baseline).",
    },
    {
      title: "FAIM bytes",
      value: `${faimBytes}`,
      hint: "Approx compressed FAIM footprint.",
    },
    {
      title: "Retrieve p50 / p95",
      value: `${p50.toFixed(1)} / ${p95.toFixed(1)} ms`,
      hint: "Latency for memory lookup",
    },
    {
      title: "Storage (raw → FAIM)",
      value: `${(rawBytes / 1_048_576).toFixed(1)} MB → ${(faimBytes / 1_048_576).toFixed(2)} MB`,
      hint: "Actual disk footprint before/after FAIM",
    },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-3">
      {cards.map((c) => (
        <div
          key={c.title}
          // ✅ Capture phase makes it resilient (even if inner elements stop propagation)
          onPointerMoveCapture={onMove}
          // ✅ sticky: do nothing on leave (keeps last glow position)
          onPointerLeave={() => {}}
          style={
            {
              "--mx": "50%",
              "--my": "35%",
              "--gvis": "0",
            } as React.CSSProperties
          }
          className={[
            "group relative overflow-hidden rounded-2xl border border-slate-800/70 bg-slate-950/55 p-4",
            // neon cyan frame line
            "ring-1 ring-inset ring-cyan-500/10",
            // depth
            "shadow-[0_0_0_1px_rgba(15,23,42,0.55),0_18px_60px_-38px_rgba(0,0,0,0.85)]",
            "transition duration-200 hover:-translate-y-0.5 hover:border-cyan-500/35",
            // sticky glow layers (controlled intensity)
            "before:pointer-events-none before:absolute before:inset-0 before:opacity-0 before:transition-opacity before:duration-200",
            "before:[background:radial-gradient(560px_260px_at_var(--mx)_var(--my),rgba(34,211,238,0.12),transparent_66%)]",
            "before:opacity-[var(--gvis)]",
            "after:pointer-events-none after:absolute after:inset-0 after:opacity-0 after:transition-opacity after:duration-200",
            "after:[background:radial-gradient(440px_220px_at_var(--mx)_var(--my),rgba(168,85,247,0.10),transparent_70%)]",
            "after:opacity-[var(--gvis)]",
          ].join(" ")}
        >
          {/* extra neon edge line (subtle) */}
          <div className="pointer-events-none absolute inset-0 rounded-2xl border border-cyan-400/10" />
          <div className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100">
            <div className="absolute inset-0 bg-gradient-to-r from-cyan-400/6 via-transparent to-purple-400/6" />
          </div>

          {/* inner glass layer */}
          <article
            className={[
              "relative z-[1] rounded-xl border border-slate-800 bg-slate-950/70 p-3",
              "transition duration-200 group-hover:border-cyan-500/25",
            ].join(" ")}
          >
            <div className="text-xs uppercase tracking-wide text-slate-400">
              {c.title}
            </div>
            <div className="mt-2 text-2xl font-semibold text-cyan-300">
              {c.value}
            </div>
            <div className="mt-1 text-[11px] text-slate-400">{c.hint}</div>
          </article>
        </div>
      ))}
    </div>
  );
}
