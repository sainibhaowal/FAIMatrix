"use client";

import React, { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";

const ForceGraph3D = dynamic(() => import("react-force-graph-3d"), {
  ssr: false,
});

interface NodeData {
  id: string;
  name: string;
  val: number;
  color: string;
}

interface LinkData {
  source: string;
  target: string;
}

interface MiniFigCanvasProps {
  nodeCount?: number;
  edgeCount?: number;
}

export const MiniFigCanvas: React.FC<MiniFigCanvasProps> = ({
  nodeCount = 12,
  edgeCount = 18,
}) => {
  const fgRef = useRef<any>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const graphData = React.useMemo(() => {
    const nodes: NodeData[] = [];
    const links: LinkData[] = [];
    const totalNodes = Math.max(8, Math.min(30, nodeCount || 12));

    for (let i = 0; i < totalNodes; i++) {
      nodes.push({
        id: `node-${i}`,
        name: i === 0 ? "Root Core" : `Memory Node #${i}`,
        val: i === 0 ? 12 : 5,
        color: i === 0 ? "#06b6d4" : i % 2 === 0 ? "#10b981" : "#a855f7",
      });
    }

    for (let i = 1; i < totalNodes; i++) {
      links.push({
        source: `node-0`,
        target: `node-${i}`,
      });
      if (i > 1 && i % 3 === 0) {
        links.push({
          source: `node-${i - 1}`,
          target: `node-${i}`,
        });
      }
    }

    return { nodes, links };
  }, [nodeCount, edgeCount]);

  useEffect(() => {
    if (fgRef.current) {
      fgRef.current.controls().autoRotate = true;
      fgRef.current.controls().autoRotateSpeed = 1.5;
    }
  }, [mounted]);

  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 400, height: 240 });

  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setDimensions({
          width: Math.max(300, entry.contentRect.width),
          height: Math.max(200, entry.contentRect.height),
        });
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, [mounted]);

  if (!mounted) {
    return (
      <div className="w-full h-full min-h-[240px] flex items-center justify-center bg-slate-950/60 rounded border border-slate-800">
        <span className="text-xs text-slate-500 font-mono animate-pulse">
          Initializing 3D Cortex FIG View...
        </span>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="w-full h-full min-h-[240px] relative overflow-hidden rounded bg-slate-950/80 border border-slate-800/80 group"
    >
      <div className="absolute top-2 left-2 z-10 flex items-center space-x-2 bg-slate-900/90 border border-cyan-500/30 px-2.5 py-1 rounded text-[10px] font-mono text-cyan-300 backdrop-blur-md">
        <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
        <span>LIVE CORTEX FIG VIEW</span>
      </div>

      <ForceGraph3D
        ref={fgRef}
        graphData={graphData}
        backgroundColor="#030712"
        nodeRelSize={4}
        nodeVal="val"
        nodeColor={(node: any) => node.color}
        nodeLabel={(node: any) => node.name}
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
