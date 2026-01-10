// /home/sephi-asi/FAIM/frontend/src/app/dashboard/evolution/page.tsx
"use client";

/* =============================================================================
   FAIM LAB — Evolution Timeline Page
   
   Surfaces the FAIM Self-Evolution concept:
   - Live evolution events (merges, prunes, promotions)
   - Historical timeline of autonomous optimizations
   - Evolution stats and metrics
============================================================================= */

import { useEffect, useState, useCallback } from "react";
import { useUserIds } from "@/contexts/UserContext";
import { GlowCard } from "@/components/ui/GlowCard";
import { EvolutionPanel } from "@/components/features/evolution";
import {
  Dna,
  GitMerge,
  Scissors,
  TrendingUp,
  Activity,
  Clock,
  RefreshCw,
} from "lucide-react";
import { API_BASE_URL, buildFaimHeaders, getUniverseGraphId } from "@/lib/api";

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

function fmt(n?: number | null, digits = 2) {
  if (typeof n !== "number" || !Number.isFinite(n)) return "—";
  return n.toFixed(digits);
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

export default function EvolutionPage() {
  const { graphId: contextGraphId } = useUserIds();
  const [graphId, setGraphId] = useState<string>("");
  const [events, setEvents] = useState<EvolutionEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [evolutionCount, setEvolutionCount] = useState(0);

  // Sync graph ID
  useEffect(() => {
    if (contextGraphId && contextGraphId.startsWith("U:")) {
      setGraphId(contextGraphId);
    } else {
      const u = getUniverseGraphId();
      if (u && u.startsWith("U:")) setGraphId(u);
    }
  }, [contextGraphId]);

  // Fetch evolution log and status from REAL backend
  const fetchEvolutionData = useCallback(async () => {
    if (!graphId) return;
    
    setLoading(true);
    try {
      // Fetch real event log from backend
      const logRes = await fetch(`${API_BASE_URL}/evolution/${encodeURIComponent(graphId)}/log?limit=50`, {
        headers: buildFaimHeaders(),
      });
      
      if (logRes.ok) {
        const logData = await logRes.json();
        // Map backend events to our type
        const realEvents: EvolutionEvent[] = (logData.events || []).map((e: any) => ({
          id: e.id || `evt-${Math.random()}`,
          event_type: e.event_type || "evolution",
          timestamp: e.timestamp || new Date().toISOString(),
          details: e.details || {},
        }));
        setEvents(realEvents);
        
        // Update count from summary
        const summary = logData.summary || {};
        setEvolutionCount((summary.merges || 0) + (summary.prunes || 0) + (summary.promotions || 0));
      }
      
      // Leave evolution count at 0 if no events - don't confuse with node count
    
    } catch (err) {
      console.warn("Failed to fetch evolution data:", err);
    } finally {
      setLoading(false);
    }
  }, [graphId]);

  // Fetch on mount and when graphId changes
  useEffect(() => {
    fetchEvolutionData();
  }, [fetchEvolutionData]);


  const eventIcon = (type: string) => {
    switch (type) {
      case "merge": return <GitMerge size={14} className="text-blue-400" />;
      case "prune": return <Scissors size={14} className="text-amber-400" />;
      case "promotion": return <TrendingUp size={14} className="text-emerald-400" />;
      default: return <Dna size={14} className="text-purple-400" />;
    }
  };

  const eventColor = (type: string) => {
    switch (type) {
      case "merge": return "border-blue-400/20 bg-blue-500/5";
      case "prune": return "border-amber-400/20 bg-amber-500/5";
      case "promotion": return "border-emerald-400/20 bg-emerald-500/5";
      default: return "border-purple-400/20 bg-purple-500/5";
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-50 flex items-center gap-2">
            <Dna className="w-6 h-6 text-purple-400" />
            Evolution Timeline
          </h1>
          <div className="text-sm text-slate-400">
            Self-optimization events for <span className="text-cyan-300 font-mono">{graphId?.slice(0,8)}...</span>
          </div>
        </div>
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <Activity size={14} className="text-purple-400" />
          <span>{evolutionCount} evolution cycles</span>
        </div>
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <GlowCard className="border-purple-400/10">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-500/10 rounded-xl">
              <Dna className="w-5 h-5 text-purple-400" />
            </div>
            <div>
              <div className="text-[11px] uppercase tracking-widest text-slate-400 font-semibold">Total Evolutions</div>
              <div className="text-2xl font-bold text-purple-300">{evolutionCount}</div>
            </div>
          </div>
        </GlowCard>

        <GlowCard className="border-blue-400/10">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/10 rounded-xl">
              <GitMerge className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <div className="text-[11px] uppercase tracking-widest text-slate-400 font-semibold">Merge Events</div>
              <div className="text-2xl font-bold text-blue-300">{events.filter(e => e.event_type === "merge").length}</div>
            </div>
          </div>
        </GlowCard>

        <GlowCard className="border-amber-400/10">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-amber-500/10 rounded-xl">
              <Scissors className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <div className="text-[11px] uppercase tracking-widest text-slate-400 font-semibold">Prune Events</div>
              <div className="text-2xl font-bold text-amber-300">{events.filter(e => e.event_type === "prune").length}</div>
            </div>
          </div>
        </GlowCard>

        <GlowCard className="border-emerald-400/10">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-emerald-500/10 rounded-xl">
              <TrendingUp className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <div className="text-[11px] uppercase tracking-widest text-slate-400 font-semibold">Promotions</div>
              <div className="text-2xl font-bold text-emerald-300">{events.filter(e => e.event_type === "promotion").length}</div>
            </div>
          </div>
        </GlowCard>
      </div>

      {/* Main Content: Timeline + Control Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Timeline */}
        <div className="lg:col-span-2">
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
                      className={`rounded-xl border p-4 transition-all hover:border-opacity-40 ${eventColor(event.event_type)}`}
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
        </div>

        {/* Evolution Control Panel */}
        <div className="lg:col-span-1">
          <GlowCard className="border-purple-400/10">
            <h3 className="text-sm font-semibold text-slate-100 mb-4 flex items-center gap-2">
              <Activity size={14} className="text-purple-400" />
              Evolution Control
            </h3>
            {graphId && (
              <EvolutionPanel 
                graphId={graphId} 
                onEvolutionComplete={() => {
                  // Refresh entire event log to show new events
                  fetchEvolutionData();
                }}
              />
            )}
          </GlowCard>
        </div>
      </div>
    </div>
  );
}
