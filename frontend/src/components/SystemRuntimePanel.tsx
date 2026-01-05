// src/components/SystemRuntimePanel.tsx
"use client";

/* ========================================================================== */
/*  SystemRuntimePanel (Production-safe)                                      */
/*  - Shows REAL per-user Universe graph_id from SSE contract (authoritative) */
/*  - Treats MAIN/DEFAULT_GRAPH_ID as UX entry only (never displayed as truth)*/
/*  - Does not call non-existent endpoints                                    */
/* ========================================================================== */

import React, { useEffect, useMemo, useRef, useState } from "react";
import { useSession } from "next-auth/react";
import {
  API_BASE_URL,
  fetchHealth,
  getUniverseGraphId,
  type HealthStatus,
} from "@/lib/api";
import { startFaimStream, type StreamContract } from "@/lib/realtime";
import { useUserIds } from "@/contexts/UserContext";

type RuntimeInfo = {
  current_graph: string; // REAL Universe graph id (U:xxxx) once known
  api_base: string;
  backend_version: string;
  runtime_paths: {
    cache: string;
    benchmarks: string;
    logs: string;
  };
  warnings: string[];
};

type SseState = "connecting" | "live" | "down";

/** Defensive normalize (no trailing slashes) */
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

  // -------------------- Health polling (safe, low frequency) --------------------
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
    const id = window.setInterval(() => void run(), 15000); // 15s

    return () => {
      mountedRef.current = false;
      window.clearInterval(id);
    };
  }, []);

  // -------------------- SSE stream (authoritative contract) --------------------
  useEffect(() => {
    // We MUST connect even if we don't know Universe id yet.
    // ENTRY_GRAPH_ID is just an entry/alias; backend maps to per-user Universe.
    setSseState("connecting");
    setStreamErr(null);

    // Prefer Context ID (auth) over localStorage (maybe stale)
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
          setSseState("live"); // contract arrived => stream works
        },
        onPing: (x: any) => {
          // ping proves liveness; contract remains authoritative for graph_id
          const now = Date.now();
          setLastPingAt(now);
          setSseState("live");

          // If backend includes graph_id in ping, we can accept it as consistent hint
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

  // -------------------- SSE staleness detector --------------------
  useEffect(() => {
    const id = window.setInterval(() => {
      if (!lastPingAt) return;
      const ageMs = Date.now() - lastPingAt;
      // If no ping for > 35s, treat as connecting (maybe reconnecting)
      if (ageMs > 35000)
        setSseState((prev) => (prev === "down" ? prev : "connecting"));
    }, 5000);

    return () => window.clearInterval(id);
  }, [lastPingAt]);

  // -------------------- Derived Runtime Info --------------------
  const info: RuntimeInfo = useMemo(() => {
    const apiBase = normBase(API_BASE_URL || "/api/v1");

    const warnings: string[] = [];
    if (healthErr) warnings.push(`Health fetch failed: ${healthErr}`);
    if (health && health.status !== "ok")
      warnings.push(`Backend health: ${health.status}`);

    if (!universeGraphId)
      warnings.push(
        "Universe graph_id not received yet (waiting for SSE contract).",
      );

    if (sseState === "connecting") warnings.push("SSE stream: connecting…");
    if (sseState === "down")
      warnings.push(`SSE stream: down${streamErr ? ` (${streamErr})` : ""}`);

    return {
      current_graph: universeGraphId || "—",
      api_base: apiBase,
      backend_version: health?.version || "unknown",
      runtime_paths: {
        cache: "Runtime/Cache",
        benchmarks: "Runtime/Benchmarks",
        logs: "Runtime/Logs",
      },
      warnings,
    };
  }, [health, healthErr, sseState, streamErr, universeGraphId]);

  const healthy = (health?.status || "down") === "ok";

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-950/60 p-6">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-slate-100">
            System / Runtime
          </h2>
          <p className="text-xs text-slate-400">
            Live view of real Universe graph id, API base, paths and backend
            health.
          </p>
        </div>
        <div
          className={[
            "rounded-full px-3 py-1 text-xs font-medium",
            healthy
              ? "bg-emerald-500/15 text-emerald-200"
              : "bg-amber-500/15 text-amber-200",
          ].join(" ")}
          title={healthy ? "Backend health OK" : "Backend not OK"}
        >
          {healthy ? "Healthy" : "Degraded"}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4">
          <p className="mb-1 text-xs text-slate-400">
            Current graph (Universe)
          </p>
          <p className="text-sm font-semibold text-slate-100">
            {info.current_graph}
          </p>

          <div className="mt-3 grid grid-cols-2 gap-3 text-xs">
            <div>
              <p className="text-slate-400">API base</p>
              <p className="font-medium text-slate-100">{info.api_base}</p>
            </div>
            <div>
              <p className="text-slate-400">Backend version</p>
              <p className="font-medium text-slate-100">
                {info.backend_version}
              </p>
            </div>
          </div>

          <div className="mt-3 text-xs">
            <p className="text-slate-400">SSE</p>
            <p
              className={[
                "font-medium",
                sseState === "live"
                  ? "text-emerald-200"
                  : sseState === "down"
                    ? "text-red-200"
                    : "text-slate-200",
              ].join(" ")}
            >
              {sseState === "live"
                ? "LIVE"
                : sseState === "down"
                  ? "DOWN"
                  : "CONNECTING"}
            </p>
          </div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4">
          <p className="mb-2 text-xs text-slate-400">Runtime paths (logical)</p>
          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Cache</span>
              <span className="font-medium text-slate-100">
                {info.runtime_paths.cache}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Benchmarks</span>
              <span className="font-medium text-slate-100">
                {info.runtime_paths.benchmarks}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Logs</span>
              <span className="font-medium text-slate-100">
                {info.runtime_paths.logs}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-5">
        <p className="mb-1 text-slate-400">Warnings</p>
        {info.warnings.length > 0 ? (
          <ul className="space-y-1">
            {info.warnings.map((w, idx) => (
              <li
                key={idx}
                className="rounded border border-amber-900/50 bg-amber-950/40 px-2 py-1 text-[11px] text-amber-100"
              >
                {w}
              </li>
            ))}
          </ul>
        ) : (
          <p className="rounded border border-slate-800 bg-slate-950/80 px-2 py-1 text-[11px] text-slate-400">
            No runtime warnings reported.
          </p>
        )}
      </div>
    </section>
  );
};

export default SystemRuntimePanel;
