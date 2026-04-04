"use client";

import {
  Clock3,
  Crosshair,
  Eye,
  GitFork,
  Lock,
  Maximize2,
  Minus,
  Network,
  Plus,
  RotateCcw,
  Unlock,
} from "lucide-react";

import { Badge, Button } from "@/components/ui";
import type { LayoutMode } from "@/lib/figViewLayout";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type FigControlsProps = {
  layoutMode: LayoutMode;
  onLayoutChange: (mode: LayoutMode) => void;
  locked: boolean;
  onLockToggle: () => void;
  selectedNodeId: string | null;
  onFit: () => void;
  onCenter: () => void;
  onResetCamera: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  timelineVisible: boolean;
  onTimelineToggle: () => void;
  similarityMode: string;
};

// ---------------------------------------------------------------------------
// Layout mode config
// ---------------------------------------------------------------------------

const MODES: Array<{ key: LayoutMode; label: string; icon: React.ReactNode }> = [
  { key: "explore", label: "Explore", icon: <Eye className="h-3.5 w-3.5" /> },
  { key: "analyze", label: "Analyze", icon: <Network className="h-3.5 w-3.5" /> },
  { key: "lineage", label: "Lineage", icon: <GitFork className="h-3.5 w-3.5" /> },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function FigControls({
  layoutMode,
  onLayoutChange,
  locked,
  onLockToggle,
  selectedNodeId,
  onFit,
  onCenter,
  onResetCamera,
  onZoomIn,
  onZoomOut,
  timelineVisible,
  onTimelineToggle,
  similarityMode,
}: FigControlsProps) {
  return (
    <div className="flex flex-wrap items-center gap-1.5 rounded-xl bg-slate-900/70 border border-slate-800 px-3 py-2">
      {/* Layout mode toggle */}
      <div className="flex items-center rounded-lg bg-slate-800/60 p-0.5">
        {MODES.map((m) => (
          <button
            key={m.key}
            onClick={() => onLayoutChange(m.key)}
            className={`flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
              layoutMode === m.key
                ? "bg-cyan-900/60 text-cyan-300"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-700/50"
            }`}
            title={`${m.label} layout`}
          >
            {m.icon}
            <span className="hidden sm:inline">{m.label}</span>
          </button>
        ))}
      </div>

      <Separator />

      {/* Camera controls */}
      <ControlButton onClick={onFit} title="Fit graph to view" icon={<Maximize2 />} />
      <ControlButton
        onClick={onCenter}
        title={selectedNodeId ? "Center on selection" : "No node selected"}
        icon={<Crosshair />}
        disabled={!selectedNodeId}
      />
      <ControlButton onClick={onResetCamera} title="Reset camera" icon={<RotateCcw />} />

      <Separator />

      {/* Zoom */}
      <ControlButton onClick={onZoomIn} title="Zoom in" icon={<Plus />} />
      <ControlButton onClick={onZoomOut} title="Zoom out" icon={<Minus />} />

      <Separator />

      {/* Lock / Unlock */}
      <button
        onClick={onLockToggle}
        className={`flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium transition-colors ${
          locked
            ? "bg-amber-900/40 text-amber-300"
            : "text-slate-400 hover:text-slate-200 hover:bg-slate-700/50"
        }`}
        title={locked ? "Unlock simulation" : "Lock simulation"}
      >
        {locked ? <Lock className="h-3.5 w-3.5" /> : <Unlock className="h-3.5 w-3.5" />}
        <span className="hidden sm:inline">{locked ? "Locked" : "Unlock"}</span>
      </button>

      <Separator />

      {/* Timeline toggle */}
      <button
        onClick={onTimelineToggle}
        className={`flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium transition-colors ${
          timelineVisible
            ? "bg-cyan-900/40 text-cyan-300"
            : "text-slate-400 hover:text-slate-200 hover:bg-slate-700/50"
        }`}
        title={timelineVisible ? "Hide timeline" : "Show timeline"}
      >
        <Clock3 className="h-3.5 w-3.5" />
        <span className="hidden sm:inline">Timeline</span>
      </button>

      {/* Similarity control (v1 placeholder) */}
      <div className="ml-auto flex items-center gap-1">
        <Badge size="sm" variant="outline">
          similarity: {similarityMode}
        </Badge>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ControlButton({
  onClick,
  title,
  icon,
  disabled = false,
}: {
  onClick: () => void;
  title: string;
  icon: React.ReactNode;
  disabled?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="flex items-center justify-center h-7 w-7 rounded-md text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors [&>svg]:h-3.5 [&>svg]:w-3.5"
      title={title}
    >
      {icon}
    </button>
  );
}

function Separator() {
  return <div className="h-5 w-px bg-slate-700/60 mx-0.5" />;
}
