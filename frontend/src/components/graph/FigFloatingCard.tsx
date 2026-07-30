"use client";

/**
 * FIG View — Floating Hover Card
 *
 * A lightweight card that appears near the cursor when hovering a node.
 * Uses createPortal so it renders over the canvas without z-index conflicts.
 *
 * Safety:
 *   - No secrets exposed (no v_native, no raw credentials)
 *   - display.title comes from backend (safe fallback chain)
 *   - No tenant data in visible content
 */

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

import { Badge } from "@/components/ui";
import { nodeColorByState } from "@/lib/figViewLayout";
import { nodeStateClass, safeNodeTitle } from "@/lib/figViewSafety";
import type { FigNode, FigNodeDisplayState } from "@/types/figView";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type FigFloatingCardProps = {
  node: FigNode | null;
  x: number;
  y: number;
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const STATE_LABELS: Record<FigNodeDisplayState, string> = {
  active: "Active",
  warm: "Warm",
  cold: "Cold",
  historical: "Historical",
  compressed: "Compressed",
  deduplicated: "Deduplicated",
  pruned: "Pruned",
  deactivated: "Deactivated",
  unknown: "Unknown",
};

const STATE_BADGE_VARIANT: Record<
  string,
  "default" | "secondary" | "outline" | "success" | "warning" | "error"
> = {
  active: "success",
  cold: "secondary",
  historical: "warning",
  compressed: "default",
  deduplicated: "secondary",
  pruned: "error",
  deactivated: "outline",
  unknown: "outline",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function FigFloatingCard({ node, x, y }: FigFloatingCardProps) {
  const [mounted, setMounted] = useState(false);

  // Portal requires document.body — only available client-side after mount
  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted || !node) return null;

  // Position card to avoid viewport edges
  const CARD_W = 224; // w-56
  const CARD_H = 180;
  const OFFSET_X = 16;
  const OFFSET_Y = 16;

  const vw = typeof window !== "undefined" ? window.innerWidth : 1200;
  const vh = typeof window !== "undefined" ? window.innerHeight : 800;

  let left = x + OFFSET_X;
  let top = y + OFFSET_Y;
  if (left + CARD_W > vw - 8) left = x - CARD_W - OFFSET_X;
  if (top + CARD_H > vh - 8) top = y - CARD_H - OFFSET_Y;
  left = Math.max(8, left);
  top = Math.max(8, top);

  const title = safeNodeTitle(node);
  const stateKey = nodeStateClass(node) as FigNodeDisplayState;
  const stateColor = nodeColorByState(stateKey, false);
  const stateLabel = STATE_LABELS[stateKey] ?? "Unknown";
  const badgeVariant = STATE_BADGE_VARIANT[stateKey] ?? "outline";
  const shortId = node.node_id.slice(0, 8);
  const levelLabel = `L${node.level}`;

  const cardContent = (
    <div
      className="pointer-events-none fixed z-50 w-56 rounded-xl border border-slate-700/70 bg-slate-950/95 shadow-[0_8px_32px_rgba(0,0,0,0.6)] backdrop-blur-md"
      style={{ left, top }}
    >
      {/* State color strip */}
      <div
        className="h-0.5 w-full rounded-t-xl"
        style={{ backgroundColor: stateColor }}
      />

      <div className="px-3 py-2.5 space-y-2">
        {/* Title */}
        <div className="flex items-start justify-between gap-2">
          <p
            className="text-[11px] font-semibold text-slate-100 leading-tight truncate max-w-[160px]"
            title={title}
          >
            {title}
          </p>
          <span className="text-[9px] font-mono text-slate-500 shrink-0">
            {levelLabel}
          </span>
        </div>

        {/* Kind + State row */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <Badge size="sm" variant="outline">
            {node.kind}
          </Badge>
          <Badge size="sm" variant={badgeVariant}>
            {stateLabel}
          </Badge>
        </div>

        {/* Metrics if available */}
        {node.metrics && (
          <div className="grid grid-cols-2 gap-1 text-[9px] text-slate-500">
            <span>
              touches:{" "}
              <span className="text-slate-300 font-mono">
                {node.metrics.touch_count}
              </span>
            </span>
            <span>
              residual:{" "}
              <span className="text-slate-300 font-mono">
                {typeof node.metrics.residual === "number"
                  ? node.metrics.residual.toFixed(3)
                  : "—"}
              </span>
            </span>
          </div>
        )}

        {/* Provenance hint */}
        {node.provenance?.block_id && (
          <p className="text-[9px] text-slate-600 font-mono truncate">
            block: {node.provenance.block_id.slice(0, 20)}
          </p>
        )}

        {/* Node ID footer */}
        <div className="pt-0.5 border-t border-slate-800/60">
          <p className="text-[9px] font-mono text-slate-600">{shortId}…</p>
        </div>
      </div>
    </div>
  );

  return createPortal(cardContent, document.body);
}
