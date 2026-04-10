"use client";

import { motion } from "framer-motion";
import { useState } from "react";

type FigMode = "explore" | "analyze" | "lineage";

interface ModeInfo {
  id: FigMode;
  label: string;
  description: string;
  features: string[];
}

const MODES: ModeInfo[] = [
  {
    id: "explore",
    label: "Explore",
    description: "Browse the full knowledge graph in 3D. Pan, zoom, click any node to inspect its inheritance tree, vector hash, residual, and connections.",
    features: [
      "3D force-directed layout (WebGL)",
      "Click node \u2192 Inspector panel opens",
      "Hover for metadata tooltip",
      "Search nodes with \"/\" key (command palette)",
    ],
  },
  {
    id: "analyze",
    label: "Analyze",
    description: "Focus on topology statistics. See edge distribution by kind (inheritance vs opposition), node clustering, and graph health metrics at a glance.",
    features: [
      "Edge count by kind breakdown",
      "Node distribution by level",
      "Graph version and hash displayed",
      "Filter nodes/edges by kind (toggleable)",
    ],
  },
  {
    id: "lineage",
    label: "Lineage",
    description: "Trace ancestry chains. Select any memory and see its full inheritance tree \u2014 which parents contributed, what fractions, and how many hops to any other node.",
    features: [
      "Hierarchical top-down layout",
      "Path explanation between any 2 nodes",
      "Inheritance fraction labels on edges",
      "Multi-path discovery (up to 3 paths)",
    ],
  },
];

const API_ENDPOINTS = [
  {
    method: "GET",
    path: "/graph/surface",
    description: "Full graph snapshot: nodes, edges, timeline, topology stats",
    response: "nodes[], edges[], timeline, topology { node_count, edge_counts_by_kind }",
  },
  {
    method: "GET",
    path: "/graph/neighborhood",
    description: "BFS traversal from seed node with configurable depth",
    response: "nodes[], edges[], distances { node_id: hops_from_seed }",
  },
  {
    method: "POST",
    path: "/graph/paths/explain",
    description: "Find shortest paths between two nodes with explanation",
    response: "paths[], explanation { summary, hops, relation_distance }",
  },
];

const FEATURES = [
  {
    title: "Node Inspector",
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
      </svg>
    ),
    description: "Click any node to see: kind (atom/macro), level, residual, vector hash, touch count, inheritance edges in/out, creation date.",
  },
  {
    title: "Relation Explorer",
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
      </svg>
    ),
    description: "Pin two nodes and find all paths between them. See hop count, edge kinds traversed, and a natural language explanation of the relationship.",
  },
  {
    title: "Event Timeline",
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    description: "Scrub through the graph's history: ingests, merges, prunes, inventions, diagnostics snapshots \u2014 every mutation recorded in the event journal.",
  },
  {
    title: "Live Controls",
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 6h9.75M10.5 6a1.5 1.5 0 11-3 0m3 0a1.5 1.5 0 10-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-9.75 0h9.75" />
      </svg>
    ),
    description: "Zoom, pan, fit graph, center on node, lock/unlock physics simulation, toggle legend, show/hide edge kinds. Full camera control.",
  },
];

export default function FigViewShowcase() {
  const [activeMode, setActiveMode] = useState<FigMode>("explore");
  const mode = MODES.find((m) => m.id === activeMode)!;

  return (
    <section id="fig-view" className="py-28 px-4 bg-slate-950 relative overflow-hidden">
      <div className="absolute inset-0 faim-grid" />

      <div className="max-w-6xl mx-auto relative">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <span className="text-purple-400 text-sm font-medium tracking-wider uppercase">
            FIG View \u2014 Graph Visualization
          </span>
          <h2 className="mt-4 text-4xl md:text-5xl font-bold text-white">
            See Your Memory{" "}
            <span className="bg-gradient-to-r from-purple-400 via-blue-400 to-cyan-400 bg-clip-text text-transparent">
              In 3D
            </span>
          </h2>
          <p className="mt-4 text-slate-400 max-w-2xl mx-auto">
            Interactive 3D force-directed graph visualization.
            Explore, analyze, and trace inheritance lineage across your entire knowledge graph.
          </p>
        </motion.div>

        {/* Mode Selector + Preview */}
        <div className="grid lg:grid-cols-3 gap-6 mb-16">
          {/* Mode tabs */}
          <div className="space-y-3">
            {MODES.map((m) => {
              const isActive = m.id === activeMode;
              return (
                <button
                  key={m.id}
                  onClick={() => setActiveMode(m.id)}
                  className={`w-full text-left p-5 rounded-xl border transition-all duration-300 ${
                    isActive
                      ? "border-purple-500/30 bg-purple-500/[0.06]"
                      : "border-slate-800/50 bg-slate-900/20 hover:border-slate-700"
                  }`}
                >
                  <h3 className={`font-bold text-sm ${isActive ? "text-purple-400" : "text-slate-400"}`}>
                    {m.label} Mode
                  </h3>
                  <p className="text-slate-500 text-xs mt-1 leading-relaxed">
                    {m.description.slice(0, 80)}...
                  </p>
                </button>
              );
            })}
          </div>

          {/* Canvas Preview */}
          <div className="lg:col-span-2">
            <motion.div
              key={mode.id}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.3 }}
              className="relative h-[360px] rounded-2xl border border-slate-800 bg-slate-900/30 overflow-hidden"
            >
              {/* Simulated 3D graph preview */}
              <div
                className="absolute inset-0"
                style={{
                  backgroundImage: "radial-gradient(circle at 1px 1px, rgba(255,255,255,0.06) 1px, transparent 0)",
                  backgroundSize: "24px 24px",
                }}
              />

              {/* Simulated nodes */}
              <svg className="absolute inset-0 w-full h-full">
                {/* Edges */}
                {[
                  [30, 25, 55, 40], [55, 40, 75, 30], [55, 40, 50, 65],
                  [30, 25, 20, 50], [20, 50, 50, 65], [75, 30, 80, 55],
                  [80, 55, 50, 65], [50, 65, 35, 80], [35, 80, 20, 50],
                  [75, 30, 60, 15],
                ].map(([x1, y1, x2, y2], i) => (
                  <line
                    key={i}
                    x1={`${x1}%`} y1={`${y1}%`}
                    x2={`${x2}%`} y2={`${y2}%`}
                    stroke={i % 3 === 0 ? "#a855f7" : "#1e293b"}
                    strokeWidth={i % 3 === 0 ? 1.2 : 0.6}
                    strokeDasharray={i % 5 === 0 ? "4 3" : "none"}
                    opacity={0.5}
                  />
                ))}

                {/* Nodes */}
                {[
                  { cx: 30, cy: 25, r: 6, fill: "#22d3ee" },
                  { cx: 55, cy: 40, r: 8, fill: "#a855f7" },
                  { cx: 75, cy: 30, r: 5, fill: "#3b82f6" },
                  { cx: 50, cy: 65, r: 7, fill: "#22d3ee" },
                  { cx: 20, cy: 50, r: 5, fill: "#10b981" },
                  { cx: 80, cy: 55, r: 4, fill: "#3b82f6" },
                  { cx: 35, cy: 80, r: 5, fill: "#a855f7" },
                  { cx: 60, cy: 15, r: 4, fill: "#10b981" },
                ].map((n, i) => (
                  <g key={i}>
                    <circle
                      cx={`${n.cx}%`} cy={`${n.cy}%`} r={n.r}
                      fill={n.fill} opacity={0.8}
                    />
                    <circle
                      cx={`${n.cx}%`} cy={`${n.cy}%`} r={n.r + 4}
                      fill={n.fill} opacity={0.1}
                    />
                  </g>
                ))}
              </svg>

              {/* Mode label */}
              <div className="absolute top-4 left-4 flex items-center gap-2">
                <span className="px-3 py-1 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-400 text-[10px] font-bold uppercase tracking-wider">
                  {mode.label}
                </span>
              </div>

              {/* Stats */}
              <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between text-[10px] font-mono text-slate-600">
                <span>8 nodes &middot; 10 edges</span>
                <span>3D Force-Directed &middot; WebGL</span>
              </div>
            </motion.div>

            {/* Mode features */}
            <div className="mt-4 grid grid-cols-2 gap-2">
              {mode.features.map((feat) => (
                <div key={feat} className="flex items-center gap-2 text-xs text-slate-500">
                  <svg className="w-3 h-3 text-purple-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                  {feat}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Features Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-5 mb-16">
          {FEATURES.map((feat, i) => (
            <motion.div
              key={feat.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: i * 0.08 }}
              className="p-6 rounded-xl border border-slate-800/60 bg-slate-900/20 hover:border-slate-700 transition-all"
            >
              <div className="inline-flex p-2.5 rounded-lg bg-purple-500/10 text-purple-400 mb-4">
                {feat.icon}
              </div>
              <h4 className="text-white font-semibold text-sm mb-2">{feat.title}</h4>
              <p className="text-slate-500 text-xs leading-relaxed">{feat.description}</p>
            </motion.div>
          ))}
        </div>

        {/* API Endpoints */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="rounded-2xl border border-slate-800 bg-slate-900/30 overflow-hidden"
        >
          <div className="px-6 py-4 border-b border-slate-800">
            <h3 className="text-sm font-bold text-white">Graph API Endpoints</h3>
          </div>
          {API_ENDPOINTS.map((ep, i) => (
            <div
              key={ep.path}
              className={`px-6 py-4 flex flex-col md:flex-row md:items-center gap-3 ${
                i < API_ENDPOINTS.length - 1 ? "border-b border-slate-800/50" : ""
              }`}
            >
              <div className="flex items-center gap-2 shrink-0">
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                  ep.method === "GET"
                    ? "bg-emerald-500/10 text-emerald-400"
                    : "bg-blue-500/10 text-blue-400"
                }`}>
                  {ep.method}
                </span>
                <code className="text-cyan-400 text-xs font-mono">{ep.path}</code>
              </div>
              <p className="text-slate-500 text-xs flex-1">{ep.description}</p>
              <code className="text-slate-600 text-[10px] font-mono hidden lg:block">{ep.response}</code>
            </div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
