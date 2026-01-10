"use client";

import React, { useEffect, useRef, useState } from "react";
import { 
  Plus, 
  Minus, 
  Maximize, 
  Compass, 
  Layers, 
  Activity, 
  Minimize2,
  Map as MapIcon 
} from "lucide-react";
import { format } from "path";

// ----------------------------------------------------------------------------
// Types
// ----------------------------------------------------------------------------

export type ZoomHandlers = {
  onZoomIn: () => void;
  onZoomOut: () => void;
  onFit: () => void;
};

// ----------------------------------------------------------------------------
// Zoom Controls
// ----------------------------------------------------------------------------

export function ZoomControls({ onZoomIn, onZoomOut, onFit }: ZoomHandlers) {
  return (
    <div className="flex flex-col gap-1 rounded-lg border border-slate-800 bg-slate-950/80 p-1 backdrop-blur pointer-events-auto">
      <button
        onClick={onZoomIn}
        className="flex h-7 w-7 items-center justify-center rounded hover:bg-slate-800 text-slate-300 hover:text-cyan-300 transition-colors"
        title="Zoom In"
      >
        <Plus size={16} />
      </button>
      <button
        onClick={onZoomOut}
        className="flex h-7 w-7 items-center justify-center rounded hover:bg-slate-800 text-slate-300 hover:text-cyan-300 transition-colors"
        title="Zoom Out"
      >
        <Minus size={16} />
      </button>
      <div className="my-0.5 h-px bg-slate-800" />
      <button
        onClick={onFit}
        className="flex h-7 w-7 items-center justify-center rounded hover:bg-slate-800 text-slate-300 hover:text-emerald-300 transition-colors"
        title="Fit to Screen"
      >
        <Maximize size={14} />
      </button>
    </div>
  );
}

// ----------------------------------------------------------------------------
// Graph Overview
// ----------------------------------------------------------------------------

export function GraphOverview({ 
  nodeCount, 
  edgeCount, 
  compressionRatio 
}: { 
  nodeCount: number; 
  edgeCount: number; 
  compressionRatio?: number 
}) {
  return (
    <div className="flex items-center gap-4 rounded-lg border border-slate-800 bg-slate-950/80 px-3 py-2 backdrop-blur text-xs text-slate-300 pointer-events-auto shadow-lg">
      <div className="flex items-center gap-2">
        <Activity size={14} className="text-cyan-500" />
        <span className="font-mono text-cyan-200">{nodeCount}</span>
        <span className="text-[10px] text-slate-500 uppercase tracking-wide">Nodes</span>
      </div>
      <div className="h-3 w-px bg-slate-800" />
      <div className="flex items-center gap-2">
        <span className="font-mono text-violet-200">{edgeCount}</span>
        <span className="text-[10px] text-slate-500 uppercase tracking-wide">Edges</span>
      </div>
      {compressionRatio !== undefined && (
        <>
          <div className="h-3 w-px bg-slate-800" />
          <div className="flex items-center gap-2" title="Compression Ratio">
            <Layers size={14} className="text-emerald-500" />
            <span className="font-mono text-emerald-200">{compressionRatio.toFixed(1)}x</span>
            <span className="text-[10px] text-slate-500 uppercase tracking-wide">CR</span>
          </div>
        </>
      )}
    </div>
  );
}

// ----------------------------------------------------------------------------
// Graph Legend
// ----------------------------------------------------------------------------

type LegendItem = { color: string; label: string };

export function GraphLegend({ items }: { items: LegendItem[] }) {
  const [minimized, setMinimized] = useState(false);

  if (items.length === 0) return null;

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-slate-800 bg-slate-950/80 p-2 backdrop-blur pointer-events-auto transition-all max-w-[200px]">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-1.5 text-[10px] font-semibold text-slate-400 uppercase tracking-wide px-1">
          <Compass size={12} />
          <span>Legend</span>
        </div>
        <button 
          onClick={() => setMinimized(!minimized)}
          className="text-slate-500 hover:text-slate-200"
        >
          {minimized ? <Maximize size={10} /> : <Minimize2 size={10} />}
        </button>
      </div>
      
      {!minimized && (
        <div className="flex flex-col gap-1 mt-1">
          {items.map((item) => (
            <div key={item.label} className="flex items-center gap-2 px-1">
              <span 
                className="h-2 w-2 rounded-full ring-1 ring-inset ring-white/10" 
                style={{ backgroundColor: item.color }} 
              />
              <span className="text-[11px] text-slate-300 truncate" title={item.label}>
                {item.label}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ----------------------------------------------------------------------------
// Minimap (Placeholder for now)
// ----------------------------------------------------------------------------

export function GraphMinimap({ visible }: { visible: boolean }) {
  if (!visible) return null;

  return (
    <div className="w-48 h-32 rounded-lg border border-slate-800 bg-slate-950/90 p-2 backdrop-blur pointer-events-auto flex flex-col items-center justify-center gap-2 text-slate-500">
       <MapIcon size={24} className="opacity-20" />
       <span className="text-[10px]">Minimap (Coming Soon)</span>
    </div>
  );
}
