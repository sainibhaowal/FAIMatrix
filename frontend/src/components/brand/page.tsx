"use client";

import React, { useCallback, useState } from "react";
import { Activity, Pause, Play, Sparkles } from "lucide-react";

import Logo from "./Logo";

function clamp(n: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, n));
}

function useGlow() {
  return useCallback((e: React.MouseEvent<HTMLElement>) => {
    const el = e.currentTarget as HTMLElement;
    const r = el.getBoundingClientRect();
    const x = clamp((e.clientX - r.left) / Math.max(r.width, 1), 0, 1);
    const y = clamp((e.clientY - r.top) / Math.max(r.height, 1), 0, 1);
    el.style.setProperty("--mx", `${x * 100}%`);
    el.style.setProperty("--my", `${y * 100}%`);
  }, []);
}

function GlassButton(props: {
  label: string;
  icon: React.ReactNode;
  active?: boolean;
  onClick?: () => void;
  tone?: "cyan" | "violet" | "amber";
}) {
  const onMove = useGlow();
  const tone = props.tone ?? "cyan";
  const glow =
    tone === "violet"
      ? "rgba(168,85,247,0.20)"
      : tone === "amber"
        ? "rgba(245,158,11,0.18)"
        : "rgba(34,211,238,0.18)";

  return (
    <button
      type="button"
      onClick={props.onClick}
      onMouseMove={onMove}
      className={[
        "group relative inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm transition-all duration-300",
        "border border-white/10 bg-white/5 text-white/80 hover:text-white hover:bg-white/10",
        "active:scale-[0.98]",
        props.active ? "ring-1 ring-white/10" : "",
      ].join(" ")}
      style={{
        backgroundImage: `radial-gradient(180px 90px at var(--mx, 50%) var(--my, 50%), ${glow}, transparent 60%)`,
      }}
    >
      <span className="opacity-90">{props.icon}</span>
      <span className="font-medium">{props.label}</span>
      <span className="pointer-events-none absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity">
        <span className="absolute inset-0 rounded-xl bg-gradient-to-r from-cyan-400/10 via-white/0 to-purple-400/10" />
      </span>
    </button>
  );
}

export default function BrandPage() {
  const [monitorOn, setMonitorOn] = useState(true);
  const [paused, setPaused] = useState(false);

  const toggleMonitor = () => setMonitorOn((v) => !v);
  const togglePause = () => setPaused((v) => !v);

  const handlePulse = useCallback(() => {
    setPaused(true);
    window.setTimeout(() => setPaused(false), 110);
  }, []);

  return (
    <div className="min-h-screen bg-[#050b14] text-white">
      <div className="pointer-events-none fixed inset-0">
        <div className="absolute -top-40 left-1/3 h-[520px] w-[520px] rounded-full bg-cyan-500/10 blur-[110px]" />
        <div className="absolute -bottom-48 right-1/4 h-[560px] w-[560px] rounded-full bg-purple-500/10 blur-[120px]" />
      </div>

      <div className="relative mx-auto max-w-6xl px-6 py-8">
        <div className="flex flex-col gap-4 rounded-2xl border border-white/10 bg-white/5 p-5 shadow-[0_0_0_1px_rgba(255,255,255,0.04)]">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <Logo size="medium" />
              <div>
                <div className="text-xl font-semibold leading-tight">
                  {monitorOn ? "FAIM Monitor" : "FAIM Brand"}
                </div>
                <div className="text-sm text-white/60">
                  UI-only layer: hover glow · glass nav · safe wiring
                </div>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <GlassButton
                label="Monitor"
                icon={<Activity size={16} />}
                active={monitorOn}
                onClick={toggleMonitor}
                tone="cyan"
              />
              <GlassButton
                label={paused ? "Resume" : "Pause"}
                icon={paused ? <Play size={16} /> : <Pause size={16} />}
                active={paused}
                onClick={togglePause}
                tone="violet"
              />
              <GlassButton
                label="Pulse"
                icon={<Sparkles size={16} />}
                onClick={handlePulse}
                tone="amber"
              />
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            {[
              "Fractal Inheritance",
              "Antisymmetric Opposition",
              "Pruning / Cold Data",
              "Evolution Gradients",
              "Metrics: CR · D · Drift",
            ].map((t) => (
              <span
                key={t}
                className="rounded-full border border-white/10 bg-black/30 px-3 py-1 text-xs text-white/70"
              >
                {t}
              </span>
            ))}
          </div>
        </div>

        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <div className="text-sm font-semibold text-white/90">
                  Visual Core
                </div>
                <div className="text-xs text-white/50">
                  hover the logo · smooth parallax
                </div>
              </div>
              <span className="rounded-full border border-white/10 bg-black/30 px-2 py-1 text-[11px] text-white/60">
                {monitorOn ? (paused ? "paused" : "live") : "brand"}
              </span>
            </div>

            <div className="flex items-center justify-center rounded-2xl border border-white/10 bg-black/30 p-4">
              <Logo size="large" px={420} />
            </div>
          </div>

          <div className="space-y-6">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
              <div className="text-sm font-semibold text-white/90">Status</div>
              <div className="mt-3 space-y-2 text-sm text-white/70">
                <div className="flex items-center justify-between">
                  <span>Backend</span>
                  <span className="text-emerald-300">connected*</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>FIG Stream</span>
                  <span className="text-white/70">idle</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Pruning</span>
                  <span className="text-white/70">scheduled</span>
                </div>
              </div>
              <div className="mt-3 text-xs text-white/45">
                *UI placeholder: wire real signals later via your existing API
                slice.
              </div>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
              <div className="text-sm font-semibold text-white/90">Notes</div>
              <ul className="mt-3 list-disc pl-5 text-sm text-white/70 space-y-2">
                <li>This page only changes styling + local UI toggles.</li>
                <li>No other module imports were changed.</li>
                <li>
                  Use <span className="text-white/90">/monitor</span> as a
                  dedicated route.
                </li>
              </ul>
            </div>
          </div>
        </div>

        <div className="mt-8 text-xs text-white/40">
          Tip: Sidebar “Monitor” points to “/”. If you want it to point to
          “/monitor”, tell me and I’ll change only that href.
        </div>
      </div>
    </div>
  );
}
