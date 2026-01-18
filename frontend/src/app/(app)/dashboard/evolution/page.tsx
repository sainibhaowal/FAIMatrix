"use client";

import { useEffect, useState, useCallback } from "react";
import { useUserIds } from "@/contexts/UserContext";
import { GlowCard } from "@/components/ui/GlowCard";
import {
  EvolutionPanel,
  EvolutionStats,
  EvolutionTimeline,
} from "@/components";
import { Dna, Activity } from "lucide-react";
import { API_BASE_URL, buildFaimHeaders, getUniverseGraphId } from "@/lib/api-client";

/* =============================================================================
   Types
============================================================================= */

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

/* =============================================================================
   Evolution Page
============================================================================= */

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
      const logRes = await fetch(
        `${API_BASE_URL}/evolution/${encodeURIComponent(graphId)}/log?limit=50`,
        {
          headers: buildFaimHeaders(),
        }
      );

      if (logRes.ok) {
        const logData = await logRes.json();
        const realEvents: EvolutionEvent[] = (logData.events || []).map((e: any) => ({
          id: e.id || `evt-${Math.random()}`,
          event_type: e.event_type || "evolution",
          timestamp: e.timestamp || new Date().toISOString(),
          details: e.details || {},
        }));
        setEvents(realEvents);

        const summary = logData.summary || {};
        setEvolutionCount(
          (summary.merges || 0) + (summary.prunes || 0) + (summary.promotions || 0)
        );
      }
    } catch (err) {
      console.warn("Failed to fetch evolution data:", err);
    } finally {
      setLoading(false);
    }
  }, [graphId]);

  useEffect(() => {
    fetchEvolutionData();
  }, [fetchEvolutionData]);

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
            Self-optimization events for{" "}
            <span className="text-cyan-300 font-mono">{graphId?.slice(0, 8)}...</span>
          </div>
        </div>
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <Activity size={14} className="text-purple-400" />
          <span>{evolutionCount} evolution cycles</span>
        </div>
      </div>

      {/* Stats Summary */}
      <EvolutionStats evolutionCount={evolutionCount} events={events} />

      {/* Main Content: Timeline + Control Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <EvolutionTimeline events={events} loading={loading} />
        </div>

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
