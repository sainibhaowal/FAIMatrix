// src/components/FaimHeader.tsx
"use client";

import * as React from "react";

function clamp(n: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, n));
}

function useGlow() {
  const ref = React.useRef<HTMLDivElement | null>(null);

  const onMouseMove = (e: React.MouseEvent) => {
    const el = ref.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const x = clamp((e.clientX - r.left) / Math.max(1, r.width), 0, 1) * 100;
    const y = clamp((e.clientY - r.top) / Math.max(1, r.height), 0, 1) * 100;
    el.style.setProperty("--mx", `${x.toFixed(2)}%`);
    el.style.setProperty("--my", `${y.toFixed(2)}%`);
    el.style.setProperty("--gvis", `1`);
  };

  // keep subtle (not sticky) for header
  const onMouseLeave = () => {
    const el = ref.current;
    if (!el) return;
    el.style.setProperty("--gvis", `0`);
  };

  return { ref, onMouseMove, onMouseLeave };
}

export function FaimHeader() {
  const g = useGlow();

  return (
    <div
      ref={g.ref}
      onMouseMove={g.onMouseMove}
      onMouseLeave={g.onMouseLeave}
      style={
        {
          "--mx": "55%",
          "--my": "25%",
          "--gvis": "0",
        } as React.CSSProperties
      }
      className={[
        "group relative overflow-hidden rounded-2xl border border-slate-800/70 bg-slate-950/55 p-4",
        "before:pointer-events-none before:absolute before:inset-0 before:opacity-0 before:transition-opacity before:duration-200",
        "before:[background:radial-gradient(420px_circle_at_var(--mx)_var(--my),rgba(34,211,238,0.14),transparent_62%)]",
        "before:opacity-[var(--gvis)]",
        "after:pointer-events-none after:absolute after:inset-0 after:opacity-0 after:transition-opacity after:duration-200",
        "after:[background:radial-gradient(360px_circle_at_var(--mx)_var(--my),rgba(168,85,247,0.10),transparent_66%)]",
        "after:opacity-[var(--gvis)]",
        "hover:border-cyan-500/35",
      ].join(" ")}
    >
      <div className="relative z-[1] space-y-1">
        <div className="text-[10px] uppercase tracking-[0.24em] text-cyan-400/80">
          FAIM LAB
        </div>
        <div className="text-lg font-semibold text-slate-50">
          Fractal Antisymmetric Inheritance Memory
        </div>
        <div className="text-[11px] text-slate-400">
          FIG · Antisym · Evolution · CR · R · Drift
        </div>
      </div>
    </div>
  );
}
