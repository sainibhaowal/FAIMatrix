// src/components/ContextSidebar.tsx
"use client";

import * as React from "react";
import clsx from "clsx";
import type { UsedNodeSummary } from "@/lib/realtime";

type UsedNodeSummaryUI = UsedNodeSummary &
  Partial<{
    label: string;
    preview: string;
    kind: string;
    region: string;
    score: number;
  }> & {
    id: string;
  };

interface ContextSidebarProps {
  nodes?: UsedNodeSummaryUI[];


  usedNodes?: UsedNodeSummaryUI[];
  graphId?: string;

  className?: string;
  onNodeClick?: (id: string) => void;
}

function clamp(n: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, n));
}

/**
 * Sticky glow:
 * - sets --mx/--my and turns --gvis to 1 on first move
 * - does NOT turn it off on mouse leave (so the glow stays)
 */
function useGlowSticky() {
  const ref = React.useRef<HTMLDivElement | null>(null);

  const onMouseMove = (e: React.MouseEvent) => {
    const el = ref.current;
    if (!el) return;

    const r = el.getBoundingClientRect();
    const x = clamp((e.clientX - r.left) / Math.max(1, r.width), 0, 1) * 100;
    const y = clamp((e.clientY - r.top) / Math.max(1, r.height), 0, 1) * 100;

    el.style.setProperty("--gx", `${x.toFixed(2)}%`);
    el.style.setProperty("--gy", `${y.toFixed(2)}%`);
    el.style.setProperty("--mx", `${x.toFixed(2)}%`);
    el.style.setProperty("--my", `${y.toFixed(2)}%`);

    // ✅ once on, keep it on
    el.style.setProperty("--gvis", `0.35`);
  };

  // ✅ no-op: do NOT disable glow on leave
  const onMouseLeave = () => {};

  return { ref, onMouseMove, onMouseLeave };
}

function GlowItem({
  className,
  children,
  onClick,
}: {
  className?: string;
  children: React.ReactNode;
  onClick?: () => void;
}) {
  const g = useGlowSticky();

  return (
    <div
      ref={g.ref}
      onMouseMove={g.onMouseMove}
      onMouseLeave={g.onMouseLeave}
      onClick={onClick}
      style={
        {
          "--gx": "45%",
          "--gy": "20%",
          "--mx": "45%",
          "--my": "20%",
          "--gvis": "0", // starts off, becomes 1 after first hover/move, then stays
        } as React.CSSProperties
      }
      className={clsx(
        "relative cursor-pointer overflow-hidden rounded-xl border border-slate-800/70 bg-slate-950/45 p-3",
        "transition hover:-translate-y-[1px] hover:border-cyan-500/50",
        "before:pointer-events-none before:absolute before:inset-0 before:opacity-0 before:transition-opacity before:duration-200",
        "before:[background:radial-gradient(520px_circle_at_var(--gx)_var(--gy),rgba(34,211,238,0.18),transparent_60%)]",
        // ✅ sticky opacity (NOT hover-gated)
        "before:opacity-[var(--gvis)]",
        className,
      )}
    >
      <div className="relative z-[1]">{children}</div>
    </div>
  );
}

export function ContextSidebar({
  nodes,
  usedNodes,
  graphId: _graphId,
  className,
  onNodeClick,
}: ContextSidebarProps) {
  const list = (nodes ?? usedNodes ?? []) as UsedNodeSummaryUI[];

  const g = useGlowSticky();

  return (
    <section
      ref={g.ref}
      onMouseMove={g.onMouseMove}
      onMouseLeave={g.onMouseLeave}
      style={
        {
          "--mx": "50%",
          "--my": "30%",
          "--gvis": "0", // becomes 1 on first move and stays
        } as React.CSSProperties
      }
      className={clsx(
        "h-full overflow-hidden rounded-2xl border border-slate-800/70 bg-slate-950/50 p-4",
        "group relative transition hover:border-cyan-500/40",
        "before:pointer-events-none before:absolute before:inset-0 before:opacity-0 before:transition-opacity before:duration-200",
        "before:[background:radial-gradient(720px_circle_at_var(--mx)_var(--my),rgba(34,211,238,0.14),transparent_58%)]",
        // ✅ sticky opacity (NOT hover-gated)
        "before:opacity-[var(--gvis)]",
        "after:pointer-events-none after:absolute after:inset-0 after:opacity-0 after:transition-opacity after:duration-200",
        "after:[background:radial-gradient(520px_circle_at_var(--mx)_var(--my),rgba(168,85,247,0.12),transparent_62%)]",
        // ✅ sticky opacity (NOT hover-gated)
        "after:opacity-[var(--gvis)]",
        className,
      )}
    >
      <div className="relative z-[1]">
        <header className="mb-3">
          <div className="text-xs font-semibold text-slate-100">Context</div>
          <div className="text-[11px] text-slate-400">
            Nodes used by FAIM to answer your last request.
          </div>
        </header>

        {list.length === 0 ? (
          <div className="text-xs text-slate-500">
            Ask a question first. As FAIM feeds the LLM, you&apos;ll see exactly
            which nodes influenced the answer.
          </div>
        ) : (
          <ol className="space-y-3 overflow-y-auto pr-1 text-xs">
            {list.map((n) => (
              <li key={n.id}>
                <GlowItem onClick={() => onNodeClick?.(n.id)}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="truncate text-[11px] font-semibold text-slate-100">
                        {n.label ?? n.id}
                      </div>

                      {n.preview ? (
                        <div className="mt-1 line-clamp-2 text-[11px] text-slate-400">
                          {n.preview}
                        </div>
                      ) : null}
                    </div>

                    {typeof n.score === "number" ? (
                      <div className="shrink-0 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-2 py-[2px] text-[10px] text-cyan-200">
                        {n.score.toFixed(3)}
                      </div>
                    ) : null}
                  </div>

                  <div className="mt-2 flex flex-wrap gap-2">
                    {n.kind ? (
                      <span className="rounded-full border border-slate-800 bg-slate-950/50 px-2 py-[2px] text-[10px] text-slate-300">
                        {n.kind}
                      </span>
                    ) : null}
                    {n.region ? (
                      <span className="rounded-full border border-slate-800 bg-slate-950/50 px-2 py-[2px] text-[10px] text-slate-300">
                        {n.region}
                      </span>
                    ) : null}
                  </div>
                </GlowItem>
              </li>
            ))}
          </ol>
        )}
      </div>
    </section>
  );
}
