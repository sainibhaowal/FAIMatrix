"use client";

import React from "react";

function clamp01(x: number) {
  return Math.max(0, Math.min(1, x));
}

const SPOT_SIZE = 240;
const SPOT_GAIN = 0.1;
const SPOT_FADE = 64;

export function GlowPanel({
  children,
  className = "",
  intensity = 0.26,
}: {
  children: React.ReactNode;
  className?: string;
  intensity?: number;
}) {
  const o = String(clamp01(intensity));

  return (
    <div
      onMouseMove={(e) => {
        const el = e.currentTarget as HTMLDivElement;
        const r = el.getBoundingClientRect();
        const x = ((e.clientX - r.left) / r.width) * 100;
        const y = ((e.clientY - r.top) / r.height) * 100;
        el.style.setProperty("--gx", `${x.toFixed(2)}%`);
        el.style.setProperty("--gy", `${y.toFixed(2)}%`);
      }}
      style={
        {
          ["--gx" as any]: "50%",
          ["--gy" as any]: "50%",
          ["--go" as any]: o,
        } as React.CSSProperties
      }
      className={[
        "relative overflow-hidden rounded-2xl border",
        "border-cyan-300/10 bg-slate-950/55",
        "shadow-[0_0_0_1px_rgba(34,211,238,0.10),0_0_30px_rgba(34,211,238,0.05)]",
        "before:absolute before:inset-0 before:pointer-events-none",
        "before:bg-[linear-gradient(180deg,rgba(34,211,238,0.10),transparent_45%,transparent)]",
        "after:absolute after:inset-0 after:pointer-events-none",
        `after:bg-[radial-gradient(${SPOT_SIZE}px_circle_at_var(--gx)_var(--gy),rgba(34,211,238,calc(var(--go)*${SPOT_GAIN})),transparent_${SPOT_FADE}%)]`,
        className,
      ].join(" ")}
    >
      <div className="pointer-events-none absolute inset-0 rounded-2xl border border-cyan-400/10" />
      <div className="relative h-full min-h-0">{children}</div>
    </div>
  );
}
