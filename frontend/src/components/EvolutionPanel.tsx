'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Activity, Zap, GitMerge, Trash2, TrendingUp, RefreshCw } from 'lucide-react';

interface EvolutionStats {
  regions: number;
  merges: number;
  prunes: number;
  promotions: number;
  redundancy_before: number;
  redundancy_after: number;
  objective_before: number;
  objective_after: number;
}

interface EvolutionEvent {
  event_type: string;
  graph_id: string;
  timestamp: string;
  stats?: EvolutionStats;
  message?: string;
}

interface Props {
  graphId: string;
  onEvolutionComplete?: () => void;
}

export default function EvolutionPanel({ graphId, onEvolutionComplete }: Props) {
  const [isConnected, setIsConnected] = useState(false);
  const [isEvolving, setIsEvolving] = useState(false);
  const [lastEvent, setLastEvent] = useState<EvolutionEvent | null>(null);
  const [events, setEvents] = useState<EvolutionEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Manual evolution trigger
  const triggerEvolution = useCallback(async () => {
    setIsEvolving(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/evolution/${graphId}/evolve`, {
        method: 'POST',
      });
      const data = await res.json();
      if (data.success && data.stats) {
        const event: EvolutionEvent = {
          event_type: 'evolution_completed',
          graph_id: graphId,
          timestamp: new Date().toISOString(),
          stats: data.stats,
        };
        setLastEvent(event);
        setEvents((prev) => [event, ...prev].slice(0, 10));
        // Notify parent to refresh graph
        if (onEvolutionComplete) {
          onEvolutionComplete();
        }
      } else if (data.error) {
        setError(data.error);
      }
    } catch (e: any) {
      setError(e.message || 'Evolution failed');
    } finally {
      setIsEvolving(false);
    }
  }, [graphId, onEvolutionComplete]);

  // Connect to SSE stream
  const connectStream = useCallback(() => {
    if (typeof window === 'undefined') return;
    
    const evtSource = new EventSource(
      `/api/v1/evolution/${graphId}/stream?interval=60`
    );

    evtSource.addEventListener('connected', (e) => {
      setIsConnected(true);
      setError(null);
    });

    evtSource.addEventListener('evolution_started', (e) => {
      setIsEvolving(true);
    });

    evtSource.addEventListener('evolution_completed', (e) => {
      try {
        const data = JSON.parse(e.data) as EvolutionEvent;
        setLastEvent(data);
        setEvents((prev) => [data, ...prev].slice(0, 10));
        setIsEvolving(false);
      } catch {}
    });

    evtSource.addEventListener('evolution_error', (e) => {
      try {
        const data = JSON.parse(e.data);
        setError(data.message || 'Evolution error');
        setIsEvolving(false);
      } catch {}
    });

    evtSource.onerror = () => {
      setIsConnected(false);
      evtSource.close();
    };

    return () => {
      evtSource.close();
      setIsConnected(false);
    };
  }, [graphId]);

  return (
    <div className="space-y-4 p-2">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold text-slate-100 flex items-center gap-2">
          <Activity size={14} className="text-cyan-400" />
          Self-Evolution
        </h3>
        <div className="flex items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-emerald-400' : 'bg-slate-600'
            }`}
            title={isConnected ? 'Connected' : 'Disconnected'}
          />
          <button
            onClick={isConnected ? undefined : connectStream}
            className="text-[10px] text-slate-400 hover:text-cyan-300"
            title="Connect to live stream"
          >
            {isConnected ? 'Live' : 'Connect'}
          </button>
        </div>
      </div>

      {/* Evolution Trigger */}
      <button
        onClick={triggerEvolution}
        disabled={isEvolving}
        className={`w-full flex items-center justify-center gap-2 rounded-lg border px-4 py-2 text-xs font-medium transition-all ${
          isEvolving
            ? 'border-amber-500/30 bg-amber-500/10 text-amber-300 cursor-wait'
            : 'border-cyan-500/30 bg-cyan-500/10 text-cyan-300 hover:bg-cyan-500/20'
        }`}
      >
        {isEvolving ? (
          <>
            <RefreshCw size={14} className="animate-spin" />
            Evolving...
          </>
        ) : (
          <>
            <Zap size={14} />
            Trigger Evolution
          </>
        )}
      </button>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-2 text-[10px] text-red-300">
          {error}
        </div>
      )}

      {/* Last Stats */}
      {lastEvent?.stats && (
        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-2">
            <StatCard
              icon={<GitMerge size={12} />}
              label="Merges"
              value={lastEvent.stats.merges}
              color="cyan"
            />
            <StatCard
              icon={<Trash2 size={12} />}
              label="Prunes"
              value={lastEvent.stats.prunes}
              color="amber"
            />
            <StatCard
              icon={<TrendingUp size={12} />}
              label="Promotes"
              value={lastEvent.stats.promotions}
              color="emerald"
            />
          </div>

          <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-3 space-y-2">
            <div className="flex justify-between text-[10px]">
              <span className="text-slate-400">Redundancy</span>
              <span className="font-mono">
                <span className="text-slate-500">
                  {(lastEvent.stats.redundancy_before * 100).toFixed(1)}%
                </span>
                <span className="text-slate-600 mx-1">→</span>
                <span
                  className={
                    lastEvent.stats.redundancy_after <
                    lastEvent.stats.redundancy_before
                      ? 'text-emerald-400'
                      : 'text-slate-300'
                  }
                >
                  {(lastEvent.stats.redundancy_after * 100).toFixed(1)}%
                </span>
              </span>
            </div>
            <div className="flex justify-between text-[10px]">
              <span className="text-slate-400">Objective J</span>
              <span className="font-mono">
                <span className="text-slate-500">
                  {lastEvent.stats.objective_before.toFixed(3)}
                </span>
                <span className="text-slate-600 mx-1">→</span>
                <span
                  className={
                    lastEvent.stats.objective_after <
                    lastEvent.stats.objective_before
                      ? 'text-emerald-400'
                      : 'text-slate-300'
                  }
                >
                  {lastEvent.stats.objective_after.toFixed(3)}
                </span>
              </span>
            </div>
            <div className="flex justify-between text-[10px]">
              <span className="text-slate-400">Regions</span>
              <span className="text-slate-300 font-mono">
                {lastEvent.stats.regions}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Event History */}
      {events.length > 0 && (
        <div className="space-y-1">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider">
            History
          </div>
          <div className="max-h-32 overflow-auto space-y-1">
            {events.slice(0, 5).map((evt, i) => (
              <div
                key={i}
                className="flex items-center justify-between text-[10px] py-1 border-b border-slate-800/50"
              >
                <span className="text-slate-400">
                  {new Date(evt.timestamp).toLocaleTimeString()}
                </span>
                <span className="text-slate-300">
                  {evt.stats
                    ? `+${evt.stats.merges}m -${evt.stats.prunes}p`
                    : evt.event_type}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  color: 'cyan' | 'amber' | 'emerald';
}) {
  const colors = {
    cyan: 'border-cyan-500/30 bg-cyan-500/10 text-cyan-300',
    amber: 'border-amber-500/30 bg-amber-500/10 text-amber-300',
    emerald: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
  };

  return (
    <div
      className={`rounded-lg border p-2 text-center ${colors[color]}`}
    >
      <div className="flex items-center justify-center gap-1 text-[10px] opacity-70">
        {icon}
        {label}
      </div>
      <div className="text-lg font-bold">{value}</div>
    </div>
  );
}
