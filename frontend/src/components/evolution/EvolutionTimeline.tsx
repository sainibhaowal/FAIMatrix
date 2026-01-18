"use client";

import React from "react";
import { GitMerge, Scissors, TrendingUp, Dna, Clock, RefreshCw } from "lucide-react";
import { GlowCard } from "@/components/ui/GlowCard";

type EvolutionEvent = {
  id: string;
  event_type: "merge" | "prune" | "promotion" | "evolution";
  timestamp: string;
  details?: {
    nodes_affected?: number;
    redundancy_reduced?: number;
    message?: string;
  };
};

interface EvolutionTimelineProps {
  events: EvolutionEvent[];
  loading: boolean;
}

export function EvolutionTimeline({ events, loading }: EvolutionTimelineProps) {
  const eventIcon = (type: string) => {
    switch (type) {
      case "merge":
        return <GitMerge size={14} className="text-blue-400" />;
      case "prune":
        return <Scissors size={14} className="text-amber-400" />;
      case "promotion":
        return <TrendingUp size={14} className="text-emerald-400" />;
      default:
        return <Dna size={14} className="text-purple-400" />;
    }
  };

  const eventColor = (type: string) => {
    switch (type) {
      case "merge":
        return "border-blue-400/20 bg-blue-500/5";
      case "prune":
        return "border-amber-400/20 bg-amber-500/5";
      case "promotion":
        return "border-emerald-400/20 bg-emerald-500/5";
      default:
        return "border-purple-400/20 bg-purple-500/5";
    }
  };

  return (
    <GlowCard className="p-0 overflow-hidden">
      <div className="p-5 border-b border-slate-800/50">
        <h3 className="text-base font-medium text-slate-50 flex items-center gap-2">
          <Clock size={16} className="text-slate-400" />
          Event History
        </h3>
      </div>
      <div className="p-5 max-h-[500px] overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-12 text-slate-500">
            <RefreshCw size={20} className="animate-spin mr-2" />
            Loading evolution history...
          </div>
        ) : events.length === 0 ? (
          <div className="text-center py-12 text-slate-500">
            <Dna size={32} className="mx-auto mb-3 opacity-50" />
            <div className="text-sm">No evolution events yet</div>
            <div className="text-xs mt-1">Trigger an evolution cycle to see events here</div>
          </div>
        ) : (
          <div className="space-y-3">
            {events.map((event) => (
              <div
                key={event.id}
                className={`rounded-xl border p-4 transition-all hover:border-opacity-40 ${eventColor(
                  event.event_type
                )}`}
              >
                <div className="flex items-start gap-3">
                  <div className="mt-0.5">{eventIcon(event.event_type)}</div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-medium text-slate-200 capitalize">
                        {event.event_type} Event
                      </span>
                      <span className="text-xs text-slate-500">
                        {formatRelativeTime(event.timestamp)}
                      </span>
                    </div>
                    {event.details?.message && (
                      <div className="text-xs text-slate-400 mt-1">{event.details.message}</div>
                    )}
                    {event.details?.nodes_affected && (
                      <div className="text-xs text-slate-500 mt-1">
                        {event.details.nodes_affected} nodes affected
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </GlowCard>
  );
}

function formatRelativeTime(timestamp: string): string {
  const now = Date.now();
  const then = new Date(timestamp).getTime();
  const diff = now - then;

  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes} min ago`;
  if (hours < 24) return `${hours} hour${hours > 1 ? "s" : ""} ago`;
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days} days ago`;
  return new Date(timestamp).toLocaleDateString();
}
