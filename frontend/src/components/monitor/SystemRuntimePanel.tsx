// src/components/SystemRuntimePanel.tsx
"use client";

/* =============================================================================
   SystemRuntimePanel (Redesigned - Compact & Unique)
   - Shows REAL Universe graph_id from SSE contract
   - Shows SSE connection status (unique to this panel)
   - Shows API base and backend version
   - Shows warnings (unique operational alerts)
   - NO health badge (already in TopBar)
   - NO placeholder paths (removed)
============================================================================= */

import React, { useEffect, useMemo, useRef, useState } from "react";
import { useSession } from "next-auth/react";
import { Radio, Server, AlertTriangle, Database, Wifi } from "lucide-react";
import {
  API_BASE_URL,
  fetchHealth,
  getUniverseGraphId,
  type HealthStatus,
} from "@/lib/api";
import { startFaimStream, type StreamContract } from "@/lib/realtime";
import { useUserIds } from "@/contexts/UserContext";

type SseState = "connecting" | "live" | "down";

function normBase(s: string): string {
  return (s || "").replace(/\/+$/, "");
}

const SystemRuntimePanel: React.FC = () => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [healthErr, setHealthErr] = useState<string | null>(null);

  const [sseState, setSseState] = useState<SseState>("connecting");
  const [universeGraphId, setUniverseGraphId] = useState<string | null>(null);
  const [lastPingAt, setLastPingAt] = useState<number | null>(null);
  const [streamErr, setStreamErr] = useState<string | null>(null);

  const { data: session } = useSession();
  const token = (session as any)?.accessToken;
  const { graphId: contextGraphId } = useUserIds();

  const mountedRef = useRef(true);

  // Health polling
  useEffect(() => {
    mountedRef.current = true;

    const run = async () => {
      try {
        const h = await fetchHealth();
        if (!mountedRef.current) return;
        setHealth(h);
        setHealthErr(null);
      } catch (e) {
        if (!mountedRef.current) return;
        setHealthErr(e instanceof Error ? e.message : String(e));
      }
    };

    void run();
    const id = window.setInterval(() => void run(), 15000);

    return () => {
      mountedRef.current = false;
      window.clearInterval(id);
    };
  }, []);

  // SSE stream
  useEffect(() => {
    setSseState("connecting");
    setStreamErr(null);

    const seedId =
      contextGraphId && contextGraphId.startsWith("U:")
        ? contextGraphId
        : getUniverseGraphId() || null;

    if (seedId) setUniverseGraphId(seedId);

    const stop = startFaimStream(
      seedId,
      {
        onContract: (c: StreamContract) => {
          const gid = c?.universe?.graph_id?.trim();
          if (gid) setUniverseGraphId(gid);
          setSseState("live");
        },
        onPing: (x: any) => {
          const now = Date.now();
          setLastPingAt(now);
          setSseState("live");

          const gid = (x?.graph_id || x?.graphId || "").toString().trim();
          if (gid && gid.startsWith("U:")) setUniverseGraphId(gid);
        },
        onError: (e) => {
          setSseState("down");
          setStreamErr(e instanceof Error ? e.message : String(e));
        },
      },
      token,
    );

    return () => stop();
  }, [token, contextGraphId]);

  // SSE staleness detector
  useEffect(() => {
    const id = window.setInterval(() => {
      if (!lastPingAt) return;
      const ageMs = Date.now() - lastPingAt;
      if (ageMs > 35000)
        setSseState((prev) => (prev === "down" ? prev : "connecting"));
    }, 5000);

    return () => window.clearInterval(id);
  }, [lastPingAt]);

  // Compute warnings
  const warnings = useMemo(() => {
    const w: string[] = [];
    if (healthErr) w.push(`Health fetch failed: ${healthErr}`);
    if (health && health.status !== "ok") w.push(`Backend health: ${health.status}`);
    if (!universeGraphId) w.push("Universe graph_id not received yet (waiting for SSE)");
    if (sseState === "connecting") w.push("SSE stream: connecting…");
    if (sseState === "down") w.push(`SSE stream: down${streamErr ? ` (${streamErr})` : ""}`);
    return w;
  }, [health, healthErr, sseState, streamErr, universeGraphId]);

  const apiBase = normBase(API_BASE_URL || "/api/v1");
  const backendVersion = health?.version || "—";

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Server size={14} className="text-cyan-400" />
        <h3 className="text-xs font-semibold text-slate-100">Runtime Status</h3>
      </div>

      {/* Status Grid */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {/* Universe Graph */}
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3">
          <div className="flex items-center gap-2 text-[10px] text-slate-500 mb-1">
            <Database size={12} />
            Universe Graph
          </div>
          <p className="text-sm font-mono text-cyan-300 truncate" title={universeGraphId || "—"}>
            {universeGraphId || "—"}
          </p>
        </div>

        {/* SSE Status */}
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3">
          <div className="flex items-center gap-2 text-[10px] text-slate-500 mb-1">
            <Wifi size={12} />
            Real-time Stream
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`h-2 w-2 rounded-full ${
                sseState === "live"
                  ? "bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.6)]"
                  : sseState === "down"
                  ? "bg-rose-400"
                  : "bg-amber-400 animate-pulse"
              }`}
            />
            <span
              className={`text-sm font-semibold ${
                sseState === "live"
                  ? "text-emerald-300"
                  : sseState === "down"
                  ? "text-rose-300"
                  : "text-amber-300"
              }`}
            >
              {sseState === "live" ? "LIVE" : sseState === "down" ? "DOWN" : "CONNECTING"}
            </span>
          </div>
        </div>

        {/* API Base */}
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3">
          <div className="flex items-center gap-2 text-[10px] text-slate-500 mb-1">
            <Radio size={12} />
            API Endpoint
          </div>
          <p className="text-sm font-mono text-slate-200">{apiBase}</p>
        </div>

        {/* Backend Version */}
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3">
          <div className="flex items-center gap-2 text-[10px] text-slate-500 mb-1">
            <Server size={12} />
            Backend Version
          </div>
          <p className="text-sm font-mono text-slate-200">{backendVersion}</p>
        </div>
      </div>

      {/* Warnings */}
      {warnings.length > 0 && (
        <div className="rounded-lg border border-amber-800/50 bg-amber-950/20 p-3">
          <div className="flex items-center gap-2 text-[10px] font-semibold text-amber-400 mb-2">
            <AlertTriangle size={12} />
            Warnings
          </div>
          <ul className="space-y-1">
            {warnings.map((w, idx) => (
              <li key={idx} className="text-[11px] text-amber-200">
                • {w}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default SystemRuntimePanel;
