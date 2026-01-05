import React from "react";

/* =============================================================================
   OmniSync Theme Components
   Neo-Glass Dark (Cyan/Violet)
   ============================================================================= */

// A) Background glow (drop behind any page)
export function OmniGlowBG() {
  return (
    <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
      <div className="absolute -top-24 left-[-10%] h-[420px] w-[420px] rounded-full bg-cyan-500/15 blur-3xl animate-pulse-glow" />
      <div className="absolute top-10 right-[-8%] h-[420px] w-[420px] rounded-full bg-violet-500/15 blur-3xl animate-pulse-glow" style={{ animationDelay: "1s" }} />
      <div className="absolute bottom-[-20%] left-[20%] h-[520px] w-[520px] rounded-full bg-sky-500/10 blur-3xl animate-pulse-glow" style={{ animationDelay: "2s" }} />
    </div>
  );
}

// B) Glass panel wrapper
export function GlassPanel({ className = "", children }: { className?: string; children: React.ReactNode }) {
  return (
    <div className={`os-surface os-glass ${className}`}>
      {children}
    </div>
  );
}

// C) Glass card wrapper
export function GlassCard({ className = "", children }: { className?: string; children: React.ReactNode }) {
  return (
    <div className={`os-card ${className}`}>
      {children}
    </div>
  );
}
