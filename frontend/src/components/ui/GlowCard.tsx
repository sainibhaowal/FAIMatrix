"use client";

import React from "react";

function clamp01(x: number) {
  return Math.max(0, Math.min(1, x));
}

/**
 * Neon “spotlight” card:
 * - cursor-follow spotlight on hover
 * - DOES NOT reset on mouse leave (stays at last position)
 * - subtle cyan border + glow
 */
export function GlowCard({
  children,
  className = "",
  intensity = 0.35,
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
        // Smooth + no re-render: write CSS vars directly
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
        "group relative overflow-hidden rounded-3xl border",
        // Deep Ocean: Dark Slate with subtle Cyan tint linked to FAIM identity
        "border-cyan-500/10 bg-slate-950/40",
        "backdrop-blur-2xl",
        // Depth: Cyan/Teal top highlight
        "shadow-[inset_0_1px_0_0_rgba(34,211,238,0.1)]",
        // Transition
        "transition-all duration-300",
        // Hover: Brighter border + Deep Cyan glow
        "hover:border-cyan-400/20 hover:shadow-2xl hover:shadow-cyan-500/10",
        // Spotlight gradient layer
        "after:absolute after:inset-0 after:pointer-events-none",
        "after:opacity-0 after:transition-opacity after:duration-500 group-hover:after:opacity-100",
        // Spotlight: Soft Teal/Cyan Nebula (Matches Sidebar)
        "after:bg-[radial-gradient(500px_circle_at_var(--gx)_var(--gy),rgba(34,211,238,0.08),transparent_60%)]",
        className,
      ].join(" ")}
    >
      {/* Noise Texture (Keep for realism) */}
      <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-[0.03] pointer-events-none mix-blend-overlay"></div>

      {/* Deep Ocean Gradient subtle bottom fade */}
      <div className="absolute inset-0 bg-gradient-to-t from-cyan-950/10 to-transparent pointer-events-none" />

      {/* Inner Content Container */}
      <div className="relative p-6 z-10">{children}</div>
    </div>
  );
}
