"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState, useRef } from "react";

// Simulated FAIM graph nodes with real FAIM concepts
const NODES = [
  {
    id: 1,
    x: 50,
    y: 28,
    label: "Security Policy",
    color: "cyan",
    size: 18,
    residual: 0.08,
  },
  {
    id: 2,
    x: 28,
    y: 45,
    label: "Access Control",
    color: "cyan",
    size: 14,
    residual: 0.12,
  },
  {
    id: 3,
    x: 72,
    y: 42,
    label: "Encryption",
    color: "purple",
    size: 15,
    residual: 0.15,
  },
  {
    id: 4,
    x: 38,
    y: 68,
    label: "RBAC Rules",
    color: "blue",
    size: 12,
    residual: 0.31,
  },
  {
    id: 5,
    x: 62,
    y: 65,
    label: "TLS Config",
    color: "purple",
    size: 12,
    residual: 0.28,
  },
  {
    id: 6,
    x: 50,
    y: 50,
    label: "Auth Layer",
    color: "emerald",
    size: 16,
    residual: 0.06,
  },
  {
    id: 7,
    x: 18,
    y: 62,
    label: "JWT Tokens",
    color: "blue",
    size: 11,
    residual: 0.42,
  },
  {
    id: 8,
    x: 82,
    y: 58,
    label: "Certificates",
    color: "purple",
    size: 11,
    residual: 0.35,
  },
  {
    id: 9,
    x: 50,
    y: 82,
    label: "Audit Trail",
    color: "emerald",
    size: 13,
    residual: 0.09,
  },
  {
    id: 10,
    x: 30,
    y: 25,
    label: "Compliance",
    color: "cyan",
    size: 13,
    residual: 0.11,
  },
];

// Edges with inheritance fractions
const EDGES: { from: number; to: number; fraction: number }[] = [
  { from: 1, to: 2, fraction: 0.42 },
  { from: 1, to: 3, fraction: 0.31 },
  { from: 1, to: 6, fraction: 0.27 },
  { from: 2, to: 4, fraction: 0.58 },
  { from: 2, to: 7, fraction: 0.42 },
  { from: 3, to: 5, fraction: 0.55 },
  { from: 3, to: 8, fraction: 0.45 },
  { from: 6, to: 9, fraction: 0.63 },
  { from: 6, to: 4, fraction: 0.37 },
  { from: 10, to: 1, fraction: 0.48 },
  { from: 10, to: 2, fraction: 0.52 },
];

const COLOR_MAP: Record<string, string> = {
  cyan: "#22d3ee",
  purple: "#a855f7",
  blue: "#3b82f6",
  emerald: "#10b981",
};

const GRADIENT_MAP: Record<string, string> = {
  cyan: "from-cyan-400 to-cyan-500",
  purple: "from-purple-400 to-purple-500",
  blue: "from-blue-400 to-blue-500",
  emerald: "from-emerald-400 to-emerald-500",
};

export default function GraphDemo() {
  const [activeNode, setActiveNode] = useState<number | null>(null);
  const [pulsingEdge, setPulsingEdge] = useState(0);
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  useEffect(() => {
    const interval = setInterval(() => {
      setPulsingEdge((prev) => (prev + 1) % EDGES.length);
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  const activeNodeData = activeNode
    ? NODES.find((n) => n.id === activeNode)
    : null;
  const activeEdges = activeNode
    ? EDGES.filter((e) => e.from === activeNode || e.to === activeNode)
    : [];

  return (
    <section className="py-28 px-4 bg-gradient-to-b from-slate-950 to-[#070a18] overflow-hidden">
      <div className="max-w-6xl mx-auto">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          {/* Left: Description */}
          <motion.div
            initial={{ opacity: 0, x: -40 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <span className="text-cyan-400 text-sm font-medium tracking-wider uppercase">
              Knowledge Graph
            </span>
            <h2 className="mt-4 text-4xl md:text-5xl font-bold text-white leading-tight">
              See Inheritance{" "}
              <span className="bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
                Come Alive
              </span>
            </h2>
            <p className="mt-6 text-slate-400 leading-relaxed">
              Every edge is a mathematical relationship — not an LLM guess.
              Hover a node to see its parents, inheritance fractions, and
              novelty residual. This is real graph structure, not a
              visualization trick.
            </p>

            {/* Active node info — Fixed height to prevent layout jumps on mobile */}
            <div className="mt-6 sm:mt-8 min-h-[180px] sm:min-h-[160px] relative">
              <AnimatePresence mode="wait">
                {activeNodeData ? (
                  <motion.div
                    key={activeNodeData.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ duration: 0.2 }}
                    className="p-5 rounded-xl border border-slate-800 bg-slate-900/60"
                  >
                    <div className="flex items-center gap-3 mb-3">
                      <div
                        className={`w-3 h-3 rounded-full bg-gradient-to-br ${GRADIENT_MAP[activeNodeData.color]}`}
                      />
                      <span className="text-white font-semibold">
                        {activeNodeData.label}
                      </span>
                      <span className="text-slate-600 text-xs font-mono">
                        node_{activeNodeData.id}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div>
                        <span className="text-slate-500 text-xs">
                          Residual (Novelty)
                        </span>
                        <p className="text-white font-mono">
                          {(activeNodeData.residual * 100).toFixed(0)}%
                        </p>
                      </div>
                      <div>
                        <span className="text-slate-500 text-xs">
                          Connections
                        </span>
                        <p className="text-white font-mono">
                          {activeEdges.length}
                        </p>
                      </div>
                    </div>
                    {activeEdges.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-slate-800">
                        <span className="text-slate-500 text-xs">
                          Inheritance Fractions
                        </span>
                        <div className="flex flex-wrap gap-2 mt-1">
                          {activeEdges.slice(0, 3).map((edge, i) => {
                            const otherNodeId =
                              edge.from === activeNode ? edge.to : edge.from;
                            const otherNode = NODES.find(
                              (n) => n.id === otherNodeId,
                            );
                            return (
                              <span
                                key={i}
                                className="px-2 py-1 rounded bg-slate-800 text-xs font-mono text-slate-300"
                              >
                                {otherNode?.label}:{" "}
                                {(edge.fraction * 100).toFixed(0)}%
                              </span>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </motion.div>
                ) : (
                  <motion.div
                    key="empty"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="p-5 rounded-xl border border-dashed border-slate-800 bg-slate-900/20 text-center"
                  >
                    <p className="text-slate-600 text-sm">
                      Hover a node to inspect inheritance fractions and novelty
                    </p>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </motion.div>

          {/* Right: Interactive Graph */}
          <motion.div
            initial={{ opacity: 0, x: 40 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="relative h-[350px] sm:h-[450px] rounded-2xl border border-slate-800 bg-slate-900/30 overflow-hidden touch-none"
          >
            {/* Dot grid */}
            <div
              className="absolute inset-0 opacity-20"
              style={{
                backgroundImage:
                  "radial-gradient(circle at 1px 1px, rgba(255,255,255,0.08) 1px, transparent 0)",
                backgroundSize: "28px 28px",
              }}
            />

            {/* SVG edges */}
            <svg className="absolute inset-0 w-full h-full">
              {EDGES.map((edge, index) => {
                const fromNode = NODES.find((n) => n.id === edge.from)!;
                const toNode = NODES.find((n) => n.id === edge.to)!;
                const isPulsing = index === pulsingEdge;
                const isActive =
                  activeNode !== null &&
                  (edge.from === activeNode || edge.to === activeNode);

                return (
                  <motion.line
                    key={`${edge.from}-${edge.to}`}
                    x1={`${fromNode.x}%`}
                    y1={`${fromNode.y}%`}
                    x2={`${toNode.x}%`}
                    y2={`${toNode.y}%`}
                    stroke={
                      isActive ? "#22d3ee" : isPulsing ? "#3b82f6" : "#1e293b"
                    }
                    strokeWidth={isActive ? 2 : isPulsing ? 1.5 : 0.8}
                    strokeDasharray={isPulsing ? "6 4" : "none"}
                    initial={{ pathLength: 0, opacity: 0.4 }}
                    animate={{
                      pathLength: 1,
                      opacity: isActive ? 0.9 : isPulsing ? 0.7 : 0.3,
                    }}
                    transition={{ duration: 0.4 }}
                  />
                );
              })}
            </svg>

            {/* Nodes */}
            {NODES.map((node) => {
              const isActive = activeNode === node.id;
              const isConnected =
                activeNode !== null &&
                EDGES.some(
                  (e) =>
                    (e.from === activeNode && e.to === node.id) ||
                    (e.to === activeNode && e.from === node.id),
                );

              return (
                <motion.div
                  key={node.id}
                  initial={{ scale: 0, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{
                    delay: node.id * 0.08,
                    type: "tween",
                    ease: "easeOut",
                  }}
                  onMouseEnter={() => setActiveNode(node.id)}
                  onMouseLeave={() => setActiveNode(null)}
                  onPointerDown={() => setActiveNode(node.id)}
                  className="absolute transform -translate-x-1/2 -translate-y-1/2 cursor-pointer group p-2"
                  style={{ left: `${node.x}%`, top: `${node.y}%` }}
                >
                  <motion.div
                    animate={{
                      scale: isActive ? 1.2 : isConnected ? 1.1 : 1,
                      boxShadow: isActive
                        ? `0 0 20px ${COLOR_MAP[node.color]}40`
                        : isConnected
                          ? `0 0 10px ${COLOR_MAP[node.color]}20`
                          : "0 0 0px transparent",
                    }}
                    transition={{
                      type: "tween",
                      ease: "easeOut",
                      duration: 0.2,
                    }}
                    style={{ width: node.size, height: node.size }}
                    className={`rounded-full bg-gradient-to-br ${GRADIENT_MAP[node.color]} shadow-md`}
                  />

                  {/* Label on hover */}
                  <AnimatePresence>
                    {(isActive || isConnected) && (
                      <motion.div
                        initial={{ opacity: 0, y: 4 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 4 }}
                        className="absolute top-full mt-2 left-1/2 -translate-x-1/2 px-2.5 py-1 bg-slate-800/90 backdrop-blur-sm rounded-md text-[10px] text-white whitespace-nowrap border border-slate-700/50"
                      >
                        {node.label}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              );
            })}

            {/* Corner label */}
            <div className="absolute top-4 right-4 text-[10px] font-mono text-slate-600">
              {NODES.length} nodes &middot; {EDGES.length} edges
            </div>

            {/* Floating particles */}
            {mounted &&
              [
                { left: 20, top: 35 },
                { left: 55, top: 20 },
                { left: 75, top: 75 },
                { left: 35, top: 80 },
              ].map((pos, i) => (
                <motion.div
                  key={i}
                  className="absolute w-1 h-1 bg-cyan-400/20 rounded-full"
                  animate={{
                    x: [0, 20 - i * 8],
                    y: [0, 15 - i * 6],
                    opacity: [0.2, 0.5, 0.2],
                  }}
                  transition={{
                    duration: 4 + i * 0.8,
                    repeat: Infinity,
                    repeatType: "reverse",
                  }}
                  style={{ left: `${pos.left}%`, top: `${pos.top}%` }}
                />
              ))}
          </motion.div>
        </div>
      </div>
    </section>
  );
}
