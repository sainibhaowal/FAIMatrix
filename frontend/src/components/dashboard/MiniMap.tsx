"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { getSession } from "next-auth/react";

interface MiniMapProps {
  graphId?: string | null;
}

interface SurfaceNode {
  node_id: string;
  kind: string;
  display?: { title?: string };
  metrics?: { touch_count?: number };
}

interface SurfaceEdge {
  src_node_id: string;
  dst_node_id: string;
}

const KIND_COLORS: Record<string, string> = {
  concept: "#06b6d4",
  fact: "#10b981",
  event: "#a855f7",
  entity: "#fbbf24",
  procedure: "#34d399",
  macro: "#f472b6",
};

export const MiniMap: React.FC<MiniMapProps> = ({ graphId }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [mounted, setMounted] = useState(false);
  const [nodes, setNodes] = useState<Array<{ id: string; x: number; y: number; r: number; color: string; name: string }>>([]);
  const [links, setLinks] = useState<Array<{ source: number; target: number }>>([]);
  const [state, setState] = useState<"loading" | "ready" | "empty" | "error">("loading");
  const [dimensions, setDimensions] = useState({ width: 300, height: 200 });
  const animationRef = useRef<number | null>(null);

  useEffect(() => setMounted(true), []);

  const load = useMemo(
    () =>
      async () => {
        if (!graphId) {
          setState("empty");
          return;
        }
        setState((s) => (s === "ready" ? s : "loading"));
        try {
          const session = await getSession();
          const token = (session as { accessToken?: string } | null)?.accessToken;
          const headers: Record<string, string> = {};
          if (token) headers.Authorization = `Bearer ${token}`;

          const params = new URLSearchParams({
            graph_id: graphId,
            node_limit: "100",
            edge_limit: "200",
            timeline_limit: "0",
            include_topology: "false",
          });
          const res = await fetch(`/api/v1/graph/surface?${params.toString()}`, {
            headers,
            cache: "no-store",
          });
          if (!res.ok) throw new Error(`surface ${res.status}`);
          const data = await res.json();

          const rawNodes: SurfaceNode[] = Array.isArray(data?.nodes)
            ? (data.nodes as SurfaceNode[])
            : [];
          const rawEdges: SurfaceEdge[] = Array.isArray(data?.edges)
            ? (data.edges as SurfaceEdge[])
            : [];

          if (!rawNodes.length) {
            setNodes([]);
            setLinks([]);
            setState("empty");
            return;
          }

          const idSet = new Set(rawNodes.map((n) => n.node_id));
          const nodeIndex = new Map<string, number>();
          rawNodes.forEach((n, i) => nodeIndex.set(n.node_id, i));

          const layoutNodes = rawNodes.map((n, i) => {
            const angle = (i / rawNodes.length) * 2 * Math.PI;
            const radius = 0.35 + 0.35 * Math.random();
            return {
              id: n.node_id,
              name: n.display?.title?.slice(0, 40) || n.node_id.slice(0, 8),
              x: 0.5 + 0.4 * radius * Math.cos(angle),
              y: 0.5 + 0.4 * radius * Math.sin(angle),
              r: Math.min(4, Math.max(1.5, (n.metrics?.touch_count ?? 0) / 8 + 1.5)),
              color: KIND_COLORS[n.kind] ?? "#64748b",
            };
          });

          const layoutLinks = rawEdges
            .filter((e) => idSet.has(e.src_node_id) && idSet.has(e.dst_node_id))
            .map((e) => ({
              source: nodeIndex.get(e.src_node_id)!,
              target: nodeIndex.get(e.dst_node_id)!,
            }));

          setNodes(layoutNodes);
          setLinks(layoutLinks);
          setState("ready");
        } catch {
          setState("error");
        }
      },
    [graphId]
  );

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!graphId) return;
    const interval = setInterval(() => void load(), 30_000);
    return () => clearInterval(interval);
  }, [graphId, load]);

  // Simple force-directed animation for visual appeal
  useEffect(() => {
    if (state !== "ready" || nodes.length === 0) return;
    let frame = 0;
    const tick = () => {
      frame++;
      if (frame > 200) return; // run for ~3 seconds then stop
      setNodes((prev) =>
        prev.map((n, i) => {
          // Gentle drift toward center
          const dx = 0.5 - n.x;
          const dy = 0.5 - n.y;
          return {
            ...n,
            x: n.x + dx * 0.001,
            y: n.y + dy * 0.001,
          };
        }),
      );
      animationRef.current = requestAnimationFrame(tick);
    };
    animationRef.current = requestAnimationFrame(tick);
    return () => {
        if (animationRef.current) cancelAnimationFrame(animationRef.current);
      };
  }, [nodes.length, state]);

  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setDimensions({
          width: Math.max(250, entry.contentRect.width),
          height: Math.max(180, entry.contentRect.height),
        });
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, [mounted]);

  // Draw on canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || state !== "ready") return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = dimensions.width * dpr;
    canvas.height = dimensions.height * dpr;
    ctx.scale(dpr, dpr);

    ctx.clearRect(0, 0, dimensions.width, dimensions.height);
    // Links
    ctx.strokeStyle = "#1e293b";
    ctx.lineWidth = 0.5;
    ctx.beginPath();
    for (const link of links) {
      const s = nodes[link.source];
      const t = nodes[link.target];
      if (s && t) {
        ctx.moveTo(s.x * dimensions.width, s.y * dimensions.height);
        ctx.lineTo(t.x * dimensions.width, t.y * dimensions.height);
      }
    }
    ctx.stroke();
    // Nodes
    for (const node of nodes) {
      ctx.beginPath();
      ctx.arc(node.x * dimensions.width, node.y * dimensions.height, node.r, 0, 2 * Math.PI);
      ctx.fillStyle = node.color;
      ctx.fill();
    }
  }, [nodes, links, dimensions, state]);

  if (!mounted) {
    return (
      <div className="w-full h-full min-h-[180px] flex items-center justify-center bg-slate-950/60 rounded border border-slate-800">
        <span className="text-xs text-slate-500 font-mono animate-pulse">
          Initializing Mini-Map…
        </span>
      </div>
    );
  }

  const badgeLabel =
    state === "ready"
      ? `MINI-MAP — ${nodes.length} N · ${links.length} E`
      : state === "loading"
        ? "LOADING GRAPH…"
        : state === "error"
          ? "UNAVAILABLE"
          : "EMPTY GRAPH";

  return (
    <div
      ref={containerRef}
      className="w-full h-full min-h-[180px] relative overflow-hidden rounded bg-slate-950/80 border border-slate-800/80"
    >
      <div
        className={`absolute top-2 left-2 z-10 flex items-center space-x-2 px-2 py-1 rounded text-[9px] font-mono backdrop-blur-md ${
          state === "ready"
            ? "bg-slate-900/90 border border-emerald-400/30 text-emerald-300"
            : "bg-slate-900/90 border border-slate-700/40 text-slate-400"
        }`}
      >
        <span
          className={`w-1.5 h-1.5 rounded-full ${
            state === "ready" ? "bg-emerald-400 animate-pulse" : "bg-slate-600"
          }`}
        />
        <span>{badgeLabel}</span>
      </div>

      {(state === "loading" || state === "error") && nodes.length === 0 && (
        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-1 text-slate-500">
          <span className="text-[10px] font-mono animate-pulse">
            {state === "loading" ? "Fetching topology…" : "Failed to load"}
          </span>
        </div>
      )}

{state === "empty" && (
        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-2 px-4 text-center text-slate-500">
          <span className="text-[11px] font-mono">No graph data — ingest to populate</span>
        </div>
      )}

      <canvas
        ref={canvasRef}
        width={dimensions.width}
        height={dimensions.height}
        className="w-full h-full absolute inset-0"
        style={{ display: "block" }}
      />
</div>
  );
}