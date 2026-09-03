"use client";

import React, { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { getSession } from "next-auth/react";

const ForceGraph3D = dynamic(() => import("react-force-graph-3d"), {
  ssr: false,
});

interface NodeData {
  id: string;
  name: string;
  val: number;
  color: string;
  kind?: string;
}

interface LinkData {
  source: string;
  target: string;
}

interface MiniFigCanvasProps {
  graphId?: string | null;
  nodeCount?: number;
  edgeCount?: number;
}

const KIND_COLORS: Record<string, string> = {
  chunk: "#38bdf8", // cyan-400
  entity: "#a78bfa", // violet-400
  event: "#34d399", // emerald-400
  claim: "#fbbf24", // amber-400
  topic: "#f472b6", // pink-400
  summary: "#60a5fa", // blue-400
  default: "#94a3b8", // slate-400
};

export const MiniFigCanvas: React.FC<MiniFigCanvasProps> = ({
  graphId = "default",
  nodeCount = 0,
  edgeCount = 0,
}) => {
  const fgRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [mounted, setMounted] = useState(false);
  const [realNodes, setRealNodes] = useState<NodeData[]>([]);
  const [realLinks, setRealLinks] = useState<LinkData[]>([]);
  const [loading, setLoading] = useState(false);
  const [dimensions, setDimensions] = useState({ width: 400, height: 280 });

  useEffect(() => {
    setMounted(true);
  }, []);

  // Fetch real graph surface to mirror the actual FIG View
  useEffect(() => {
    let cancelled = false;
    async function loadSurface() {
      if (!graphId) return;
      try {
        setLoading(true);
        const session = await getSession();
        const token = (session as { accessToken?: string } | null)?.accessToken;
        const tenantId = (session as { tenantId?: string } | null)?.tenantId;
        const headers: Record<string, string> = {};
        if (token) headers.Authorization = `Bearer ${token}`;
        if (tenantId) headers["X-Tenant-Id"] = tenantId;

        const params = new URLSearchParams({
          graph_id: graphId,
          node_limit: "60",
          edge_limit: "120",
          timeline_limit: "0",
          include_topology: "false",
        });

        const res = await fetch(`/api/v1/graph/surface?${params.toString()}`, {
          headers,
          cache: "no-store",
        });

        if (!res.ok) return;
        const data = await res.json();
        if (cancelled) return;

        if (Array.isArray(data?.nodes) && data.nodes.length > 0) {
          const rawNodes = data.nodes;
          const rawEdges = Array.isArray(data?.edges) ? data.edges : [];
          const idSet = new Set(rawNodes.map((n: any) => n.node_id));

          const nodes: NodeData[] = rawNodes.map((n: any) => {
            const kind = (n.kind || "default").toLowerCase();
            const color = KIND_COLORS[kind] || KIND_COLORS.default;
            return {
              id: n.node_id,
              name: n.display?.title || n.node_id.slice(0, 10),
              val: Math.max(3, Math.min(10, (n.metrics?.touch_count ?? 1) * 1.5)),
              color,
              kind,
            };
          });

          const links: LinkData[] = rawEdges
            .filter((e: any) => idSet.has(e.src_node_id) && idSet.has(e.dst_node_id))
            .map((e: any) => ({
              source: e.src_node_id,
              target: e.dst_node_id,
            }));

          setRealNodes(nodes);
          setRealLinks(links);
        } else {
          setRealNodes([]);
          setRealLinks([]);
        }
      } catch {
        // Fallback gracefully on network issues
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadSurface();
    return () => {
      cancelled = true;
    };
  }, [graphId, nodeCount]);

  // Set up auto-rotation
  useEffect(() => {
    if (fgRef.current) {
      fgRef.current.controls().autoRotate = true;
      fgRef.current.controls().autoRotateSpeed = 1.2;
    }
  }, [mounted, realNodes.length]);

  // Measure container dimensions
  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setDimensions({
          width: Math.max(260, Math.floor(entry.contentRect.width)),
          height: Math.max(240, Math.floor(entry.contentRect.height)),
        });
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, [mounted]);

  if (!mounted) {
    return (
      <div className="w-full h-full min-h-[280px] flex items-center justify-center bg-slate-950/60 rounded-[14px] border border-slate-800">
        <span className="text-xs text-slate-500 font-mono animate-pulse">
          Initializing 3D Cortex FIG View...
        </span>
      </div>
    );
  }

  // If real graph has 0 nodes, display genuine empty state with clean design
  if (realNodes.length === 0 && (nodeCount === 0 || !nodeCount)) {
    return (
      <div
        ref={containerRef}
        className="w-full h-full min-h-[280px] relative overflow-hidden rounded-[14px] bg-slate-950/80 border border-slate-800/80 flex flex-col items-center justify-center p-6 text-center"
      >
        <div className="absolute top-2 left-2 z-10 flex items-center space-x-2 bg-slate-900/90 border border-cyan-500/30 px-2.5 py-1 rounded text-[10px] font-mono text-cyan-300 backdrop-blur-md">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
          <span>CORTEX FIG VIEW · LIVE MIRROR</span>
        </div>
        <div className="flex flex-col items-center justify-center gap-2.5 max-w-[260px]">
          <div className="w-10 h-10 rounded-xl bg-cyan-950/40 border border-cyan-800/40 flex items-center justify-center text-cyan-400">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <p className="text-xs font-semibold text-slate-300">Graph is currently empty</p>
          <p className="text-[10px] text-slate-500 font-mono leading-relaxed">
            Ingest files to generate real nodes and mirror spatial 3D clusters.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="w-full h-full min-h-[280px] relative overflow-hidden rounded-[14px] bg-slate-950/80 border border-slate-800/80 group"
    >
      <div className="absolute top-2 left-2 z-10 flex items-center space-x-2 bg-slate-900/90 border border-cyan-500/30 px-2.5 py-1 rounded text-[10px] font-mono text-cyan-300 backdrop-blur-md">
        <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
        <span>LIVE CORTEX FIG MIRROR ({realNodes.length} NODES)</span>
      </div>

      <ForceGraph3D
        ref={fgRef}
        graphData={{ nodes: realNodes, links: realLinks }}
        backgroundColor="#030712"
        nodeRelSize={4}
        nodeVal="val"
        nodeColor={(node: any) => node.color}
        nodeLabel={(node: any) => `${node.name} (${node.kind || "node"})`}
        linkColor={() => "#1e293b"}
        linkWidth={1.5}
        linkDirectionalParticles={2}
        linkDirectionalParticleWidth={2}
        linkDirectionalParticleSpeed={0.005}
        showNavInfo={false}
        width={dimensions.width}
        height={dimensions.height}
      />
    </div>
  );
};
