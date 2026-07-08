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
    description:
      "Browse the full knowledge graph in 3D. Pan, zoom, click any node to inspect its inheritance tree, vector hash, residual, and connections.",
    features: [
      "3D force-directed layout (WebGL)",
      "Click node \u2192 Inspector panel opens",
      "Hover for metadata tooltip",
      'Search nodes with "/" key (command palette)',
    ],
  },
  {
    id: "analyze",
    label: "Analyze",
    description:
      "Focus on topology statistics. See edge distribution by kind (inheritance vs opposition), node clustering, and graph health metrics at a glance.",
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
    description:
      "Trace ancestry chains. Select any memory and see its full inheritance tree \u2014 which parents contributed, what fractions, and how many hops to any other node.",
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
    response:
      "nodes[], edges[], timeline, topology { node_count, edge_counts_by_kind }",
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
    description: "Find shortest paths between two nodes with pulse-v2 explanation",
    response: "paths[], pulse_trace { events[], steps[] }, explanation",
  },
];

const FEATURES = [
  {
    title: "Pulse-v2 Reason Ledger",
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
      </svg>
    ),
    description:
      "Backend pulse events explain graph hops, semantic-registry signals, expansion sources, domain-memory links, reranker factors, and late-interaction matches. FIG View uses the same ledger for glow, path motion, inspector proof, and relation traces.",
  },
  {
    title: "GPU Stability Hardening",
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 17.25v1.007a3 3 0 01-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0115 18.257V17.25m6-12V15a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 15V5.25m18 0A2.25 2.25 0 0018.75 3H5.25A2.25 2.25 0 003 5.25m18 0V12a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 12V5.25" />
      </svg>
    ),
    description: "Zero-leak WebGL rendering with a static asset registry. Engineered for production stability across large-scale 3D cognitive constellations.",
  },
  {
    title: "Elastic Persistence",
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
      </svg>
    ),
    description: "100% native force-directed elasticity. Stretch and pull atoms with zero lag while the Gravitational Anchor keeps the globe tightly grouped.",
  },
  {
    title: "Event Timeline",
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    description: "Scrub through the graph's history: ingests, merges, prunes, and inventions. Every mutation recorded with SHA-256 integrity.",
  },
];

export default function FigViewShowcase() {
  const [activeMode, setActiveMode] = useState<FigMode>("explore");
  const mode = MODES.find((m) => m.id === activeMode)!;

  return (
    <section
      id="fig-view"
      className="py-28 px-4 bg-slate-950 relative overflow-hidden"
    >
      <div className="absolute inset-0 faim-grid opacity-30" />

      {/* Background Radar Scanning Effect */}
      <motion.div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] border border-purple-500/5 rounded-full pointer-events-none"
        animate={{ scale: [1, 1.2, 1], opacity: [0.1, 0.2, 0.1] }}
        transition={{ duration: 10, repeat: Infinity }}
      />

      <div className="max-w-6xl mx-auto relative">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7 }}
          className="text-center mb-16"
        >
          <span className="text-purple-400 text-[10px] font-bold tracking-[0.3em] uppercase mb-4 block">
            FIG View &mdash; Graph Visualization
          </span>
          <h2 className="text-3xl md:text-5xl font-bold text-white tracking-tight leading-tight">
            See Your Memory <br className="hidden md:block" />
            <span className="bg-gradient-to-r from-purple-400 via-blue-400 to-cyan-400 bg-clip-text text-transparent">
              In Immersive 3D
            </span>
          </h2>
          <p className="mt-6 text-slate-400 max-w-2xl mx-auto text-lg leading-relaxed">
            Interactive 3D force-directed graph visualization. Explore, analyze,
            and trace inheritance lineage across your entire knowledge graph.
          </p>
        </motion.div>

        <div className="grid lg:grid-cols-3 gap-8 mb-16">
          {/* Tactical Mode Selector */}
          <div className="flex flex-col gap-3">
            {MODES.map((m) => {
              const isActive = m.id === activeMode;
              return (
                <button
                  key={m.id}
                  onClick={() => setActiveMode(m.id)}
                  className={`group relative text-left p-6 rounded-2xl border transition-all duration-300 overflow-hidden ${
                    isActive
                      ? "border-purple-500/40 bg-purple-500/10"
                      : "border-slate-800 bg-slate-900/30 hover:border-slate-700"
                  }`}
                >
                  <div
                    className={`absolute left-0 top-0 w-1 h-full bg-purple-500 transition-transform ${isActive ? "scale-y-100" : "scale-y-0"}`}
                  />
                  <h3
                    className={`font-bold text-sm tracking-wide ${isActive ? "text-purple-400" : "text-slate-400 group-hover:text-slate-300"}`}
                  >
                    {m.label} Mode
                  </h3>
                  <p className="text-slate-500 text-xs mt-2 leading-relaxed">
                    {m.description}
                  </p>
                </button>
              );
            })}
          </div>

          {/* Immersive Canvas Preview */}
          <div className="lg:col-span-2">
            <motion.div
              key={mode.id}
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5 }}
              className="relative h-[300px] sm:h-[400px] md:h-[480px] rounded-3xl border border-slate-800 bg-slate-950 overflow-hidden shadow-2xl"
            >
              {/* Starry Grid Background */}
              <div
                className="absolute inset-0 opacity-40 pointer-events-none"
                style={{
                  backgroundImage:
                    "radial-gradient(circle at 1px 1px, rgba(168,85,247,0.15) 1px, transparent 0)",
                  backgroundSize: "32px 32px",
                }}
              />

              {/* Radar Line - Behind Nodes */}
              <motion.div
                className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-purple-500/50 to-transparent z-0 pointer-events-none"
                animate={{ top: ["0%", "100%", "0%"] }}
                transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
              />

              {/* Mode-Specific Graph Simulation */}
              <svg className="absolute inset-0 w-full h-full p-12 overflow-visible z-10 pointer-events-none">
                <defs>
                  <filter
                    id="glow"
                    x="-20%"
                    y="-20%"
                    width="140%"
                    height="140%"
                  >
                    <feGaussianBlur stdDeviation="3" result="blur" />
                    <feComposite
                      in="SourceGraphic"
                      in2="blur"
                      operator="over"
                    />
                  </filter>
                </defs>

                {/* Dynamic Edges */}
                {activeMode === "explore" &&
                  [
                    [30, 25, 55, 40],
                    [55, 40, 75, 30],
                    [55, 40, 50, 65],
                    [30, 25, 20, 50],
                    [20, 50, 50, 65],
                    [75, 30, 80, 55],
                    [80, 55, 50, 65],
                    [50, 65, 35, 80],
                    [35, 80, 20, 50],
                    [75, 30, 60, 15],
                  ].map(([x1, y1, x2, y2], i) => (
                    <motion.line
                      key={`e-exp-${i}`}
                      x1={`${x1}%`}
                      y1={`${y1}%`}
                      x2={`${x2}%`}
                      y2={`${y2}%`}
                      stroke="#475569"
                      strokeWidth="0.8"
                      opacity="0.3"
                    />
                  ))}

                {activeMode === "analyze" &&
                  [
                    [20, 20, 50, 50],
                    [80, 20, 50, 50],
                    [50, 80, 50, 50],
                    [20, 20, 80, 20],
                    [80, 20, 80, 80],
                    [80, 80, 20, 80],
                    [20, 80, 20, 20],
                  ].map(([x1, y1, x2, y2], i) => (
                    <motion.line
                      key={`e-ana-${i}`}
                      x1={`${x1}%`}
                      y1={`${y1}%`}
                      x2={`${x2}%`}
                      y2={`${y2}%`}
                      stroke="#a855f7"
                      strokeWidth="1"
                      strokeDasharray="4 4"
                      opacity="0.4"
                    />
                  ))}

                {activeMode === "lineage" &&
                  [
                    [50, 15, 30, 40],
                    [50, 15, 70, 40],
                    [30, 40, 15, 75],
                    [30, 40, 45, 75],
                    [70, 40, 85, 75],
                  ].map(([x1, y1, x2, y2], i) => (
                    <motion.line
                      key={`e-lin-${i}`}
                      x1={`${x1}%`}
                      y1={`${y1}%`}
                      x2={`${x2}%`}
                      y2={`${y2}%`}
                      stroke="#3b82f6"
                      strokeWidth="1.5"
                      opacity="0.5"
                    />
                  ))}

                {/* Dynamic Nodes */}
                {activeMode === "explore" &&
                  [
                    { cx: 30, cy: 25, r: 6, fill: "#22d3ee" },
                    { cx: 55, cy: 40, r: 10, fill: "#a855f7" },
                    { cx: 75, cy: 30, r: 7, fill: "#3b82f6" },
                    { cx: 50, cy: 65, r: 9, fill: "#22d3ee" },
                    { cx: 20, cy: 50, r: 6, fill: "#10b981" },
                    { cx: 80, cy: 55, r: 5, fill: "#3b82f6" },
                    { cx: 35, cy: 80, r: 7, fill: "#a855f7" },
                    { cx: 60, cy: 15, r: 5, fill: "#10b981" },
                  ].map((n, i) => (
                    <g key={`n-exp-${i}`}>
                      <circle
                        cx={`${n.cx}%`}
                        cy={`${n.cy}%`}
                        r={n.r}
                        fill={n.fill}
                        filter="url(#glow)"
                      />
                      <circle
                        cx={`${n.cx}%`}
                        cy={`${n.cy}%`}
                        r={n.r + 4}
                        fill={n.fill}
                        opacity="0.1"
                      />
                    </g>
                  ))}

                {activeMode === "analyze" &&
                  [
                    { cx: 50, cy: 50, r: 14, fill: "#a855f7" },
                    { cx: 20, cy: 20, r: 8, fill: "#22d3ee" },
                    { cx: 80, cy: 20, r: 8, fill: "#22d3ee" },
                    { cx: 80, cy: 80, r: 8, fill: "#22d3ee" },
                    { cx: 20, cy: 80, r: 8, fill: "#22d3ee" },
                  ].map((n, i) => (
                    <g key={`n-ana-${i}`}>
                      <circle
                        cx={`${n.cx}%`}
                        cy={`${n.cy}%`}
                        r={n.r}
                        fill={n.fill}
                        filter="url(#glow)"
                      />
                      <motion.circle
                        cx={`${n.cx}%`}
                        cy={`${n.cy}%`}
                        r={n.r + 8}
                        fill={n.fill}
                        opacity="0.05"
                        animate={{ scale: [1, 1.2, 1] }}
                        transition={{ duration: 2, repeat: Infinity }}
                      />
                    </g>
                  ))}

                {activeMode === "lineage" &&
                  [
                    { cx: 50, cy: 15, r: 12, fill: "#a855f7" },
                    { cx: 30, cy: 40, r: 9, fill: "#3b82f6" },
                    { cx: 70, cy: 40, r: 9, fill: "#3b82f6" },
                    { cx: 15, cy: 75, r: 7, fill: "#22d3ee" },
                    { cx: 45, cy: 75, r: 7, fill: "#22d3ee" },
                    { cx: 85, cy: 75, r: 7, fill: "#22d3ee" },
                  ].map((n, i) => (
                    <g key={`n-lin-${i}`}>
                      <circle
                        cx={`${n.cx}%`}
                        cy={`${n.cy}%`}
                        r={n.r}
                        fill={n.fill}
                        filter="url(#glow)"
                      />
                      <path
                        d={`M ${n.cx}% ${n.cy}% l 0 15`}
                        stroke="#334155"
                        strokeWidth="1"
                        strokeDasharray="2 2"
                      />
                    </g>
                  ))}
              </svg>

              <div className="absolute top-6 left-6 flex items-center gap-3">
                <div className="flex h-2 w-2 relative">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-purple-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-purple-500"></span>
                </div>
                <span className="text-[10px] font-bold text-purple-400 uppercase tracking-widest">
                  Live View Port &mdash; {mode.label}
                </span>
              </div>

              <div className="absolute bottom-6 right-6 flex flex-col items-end gap-1">
                <div className="px-3 py-1 bg-slate-900/80 border border-slate-800 rounded-lg text-[9px] font-mono text-slate-400 backdrop-blur-sm">
                  STATUS: STABLE (E=1.618)
                </div>
                <div className="px-3 py-1 bg-slate-900/80 border border-slate-800 rounded-lg text-[9px] font-mono text-slate-400 backdrop-blur-sm">
                  NODES: 142 | EDGES: 384
                </div>
              </div>
            </motion.div>
          </div>
        </div>

        {/* Tactical Feature Cards */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          {FEATURES.map((feat, i) => (
            <motion.div
              key={feat.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              whileHover={{ y: -5 }}
              className="p-8 rounded-3xl border border-slate-800/60 bg-slate-900/20 hover:border-purple-500/30 hover:bg-slate-900/40 transition-all"
            >
              <div className="inline-flex p-3 rounded-2xl bg-purple-500/10 text-purple-400 mb-6">
                {feat.icon}
              </div>
              <h4 className="text-white font-bold text-sm mb-3">
                {feat.title}
              </h4>
              <p className="text-slate-500 text-xs leading-relaxed">
                {feat.description}
              </p>
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
            <h3 className="text-sm font-bold text-white">
              Graph API Endpoints
            </h3>
          </div>
          {API_ENDPOINTS.map((ep, i) => (
            <div
              key={ep.path}
              className={`px-6 py-4 flex flex-col md:flex-row md:items-center gap-3 ${
                i < API_ENDPOINTS.length - 1
                  ? "border-b border-slate-800/50"
                  : ""
              }`}
            >
              <div className="flex items-center gap-2 shrink-0">
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    ep.method === "GET"
                      ? "bg-emerald-500/10 text-emerald-400"
                      : "bg-blue-500/10 text-blue-400"
                  }`}
                >
                  {ep.method}
                </span>
                <code className="text-cyan-400 text-xs font-mono">
                  {ep.path}
                </code>
              </div>
              <p className="text-slate-500 text-xs flex-1">{ep.description}</p>
              <code className="text-slate-600 text-[10px] font-mono hidden lg:block">
                {ep.response}
              </code>
            </div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
