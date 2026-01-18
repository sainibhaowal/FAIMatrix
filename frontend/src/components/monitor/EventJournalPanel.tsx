"use client";

/**
 * EventJournalPanel - Real-time FAIM event stream visualization
 * 
 * Shows: node_added, node_merged, edge_created, evolution_cycle events
 * Connects to /api/v1/stream (SSE)
 */

import React, { useState, useEffect, useRef } from "react";
import { useFaimStream } from "@/lib/realtime";
import { useUserIds } from "@/contexts/UserContext";
import clsx from "clsx";

interface JournalEvent {
  id: string;
  type: string;
  timestamp: number;
  data: any;
}

const EVENT_ICONS: Record<string, string> = {
  node_added: "➕",
  node_merged: "🔀",
  node_pruned: "✂️",
  edge_created: "🔗",
  evolution_cycle: "🔄",
  invention_created: "✨",
  fig_delta: "📊",
  default: "📝",
};

const EVENT_COLORS: Record<string, string> = {
  node_added: "border-cyan-500/30 bg-cyan-500/5",
  node_merged: "border-purple-500/30 bg-purple-500/5",
  node_pruned: "border-amber-500/30 bg-amber-500/5",
  edge_created: "border-blue-500/30 bg-blue-500/5",
  evolution_cycle: "border-emerald-500/30 bg-emerald-500/5",
  invention_created: "border-yellow-500/30 bg-yellow-500/5",
  fig_delta: "border-slate-500/30 bg-slate-500/5",
  default: "border-slate-700 bg-slate-900/50",
};

function formatTime(ts: number): string {
  const d = new Date(ts);
  return d.toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function EventJournalPanel() {
  const { graphId } = useUserIds();
  const [events, setEvents] = useState<JournalEvent[]>([]);
  const [paused, setPaused] = useState(false);
  const [connected, setConnected] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Stream handler
  useFaimStream(graphId, {
    onFigDelta: (d) => {
      if (paused) return;
      const newEvent: JournalEvent = {
        id: `${Date.now()}-${Math.random()}`,
        type: d.delta?.kind || "fig_delta",
        timestamp: d.ts || Date.now(),
        data: d.delta,
      };
      setEvents((prev) => [newEvent, ...prev].slice(0, 100));
    },
    onPing: () => setConnected(true),
    onError: () => setConnected(false),
  });

  // Auto-scroll to top on new events
  useEffect(() => {
    if (scrollRef.current && !paused) {
      scrollRef.current.scrollTop = 0;
    }
  }, [events, paused]);

  return (
    <div className="h-full flex flex-col rounded-2xl border border-slate-800 bg-slate-950/60 overflow-hidden">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-100">Event Journal</span>
          <span
            className={clsx(
              "h-2 w-2 rounded-full",
              connected ? "bg-emerald-400 animate-pulse" : "bg-slate-600"
            )}
          />
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setPaused(!paused)}
            className={clsx(
              "px-2 py-1 text-[10px] rounded-full transition",
              paused
                ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                : "bg-slate-800 text-slate-300 border border-slate-700"
            )}
          >
            {paused ? "▶ Resume" : "⏸ Pause"}
          </button>
          <button
            onClick={() => setEvents([])}
            className="px-2 py-1 text-[10px] rounded-full bg-slate-800 text-slate-400 border border-slate-700 hover:text-slate-200"
          >
            Clear
          </button>
        </div>
      </header>

      {/* Event list */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-2 space-y-1.5">
        {events.length === 0 ? (
          <div className="flex items-center justify-center h-full text-[11px] text-slate-500">
            {connected ? "Waiting for events..." : "Connecting to stream..."}
          </div>
        ) : (
          events.map((evt) => {
            const icon = EVENT_ICONS[evt.type] || EVENT_ICONS.default;
            const colorClass = EVENT_COLORS[evt.type] || EVENT_COLORS.default;
            return (
              <div
                key={evt.id}
                className={clsx(
                  "flex items-start gap-2 px-2 py-1.5 rounded-lg border text-[11px]",
                  colorClass
                )}
              >
                <span className="text-sm">{icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium text-slate-200">{evt.type}</span>
                    <span className="text-[9px] text-slate-500 shrink-0">
                      {formatTime(evt.timestamp)}
                    </span>
                  </div>
                  {evt.data && (
                    <div className="mt-0.5 text-[10px] text-slate-400 truncate">
                      {evt.data.nodes_added?.length && `+${evt.data.nodes_added.length} nodes`}
                      {evt.data.nodes_removed?.length && ` -${evt.data.nodes_removed.length} nodes`}
                      {evt.data.links_added?.length && ` +${evt.data.links_added.length} edges`}
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Footer stats */}
      <footer className="px-3 py-2 border-t border-slate-800 text-[10px] text-slate-500 flex items-center justify-between">
        <span>{events.length} events</span>
        <span className="text-slate-600">Graph: {graphId?.slice(0, 16) || "—"}</span>
      </footer>
    </div>
  );
}

export default EventJournalPanel;
