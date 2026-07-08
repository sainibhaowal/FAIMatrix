"use client";

import { motion } from "framer-motion";
import { useState } from "react";

const LAYERS = [
  {
    id: "application",
    label: "Application Layer",
    sublabel: "LLM Optional. APIs First.",
    color: "purple",
    gradient: "from-purple-500/20 to-purple-500/5",
    borderColor: "border-purple-500/30",
    dotColor: "bg-purple-400",
    items: [
      {
        name: "App + LLM Integration",
        desc: "Use FAIM directly or add an LLM as a translator on top",
      },
      {
        name: "REST Query + Answer API",
        desc: "Deterministic retrieval, explain payloads, and citation-first answers",
      },
      {
        name: "API Keys + Tenant Isolation",
        desc: "Scoped access for multi-tenant production systems",
      },
      {
        name: "Dashboard + FIG View",
        desc: "Graph exploration, pulse-v2 reason ledgers, rebuild jobs, and operational visibility",
      },
    ],
  },
  {
    id: "engine",
    label: "FAIM Core Engine",
    sublabel: "Deterministic Core. Additive Retrieval Stack.",
    color: "cyan",
    gradient: "from-cyan-500/20 to-cyan-500/5",
    borderColor: "border-cyan-500/30",
    dotColor: "bg-cyan-400",
    items: [
      {
        name: "Native Core + Invariants",
        desc: "256-d vectors, inheritance, dedup, evolution, and 8 invariant checks",
      },
      {
        name: "Deterministic Semantic Router",
        desc: "Seeded alias mapping for intent routing (zero ML)",
      },
      {
        name: "Graph + Knowledge Layers",
        desc: "bounded multi-hop diffusion, semantic edges, domain knowledge, and pulse-v2 graph proof",
      },
      {
        name: "Answer-Ready Retrieval",
        desc: "Deterministic reranking, multimodal evidence, and extractive answer synthesis",
      },
    ],
  },
] as const;

export default function Architecture() {
  const [activeLayer, setActiveLayer] = useState<string>("engine");

  return (
    <section
      id="architecture"
      className="py-28 px-4 bg-slate-950 relative overflow-hidden"
    >
      <div className="absolute inset-0 faim-grid" />

      <div className="max-w-6xl mx-auto relative">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-20"
        >
          <span className="text-cyan-400 text-sm font-medium tracking-wider uppercase">
            Architecture
          </span>
          <h2 className="mt-4 text-4xl md:text-5xl font-bold text-white">
            Two Layers.{" "}
            <span className="bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
              One Deterministic Truth.
            </span>
          </h2>
          <p className="mt-4 text-slate-400 max-w-2xl mx-auto text-lg">
            The core engine still owns storage, retrieval, ranking, and answer
            composition. The application layer is where you add UI, workflow
            logic, or optional LLM translation.
          </p>
        </motion.div>

        <div className="grid lg:grid-cols-2 gap-8">
          {LAYERS.map((layer, idx) => (
            <motion.div
              key={layer.id}
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: idx * 0.15 }}
              onMouseEnter={() => setActiveLayer(layer.id)}
              className={`relative group rounded-2xl border p-8 transition-all duration-500 cursor-default ${
                activeLayer === layer.id
                  ? `${layer.borderColor} bg-gradient-to-b ${layer.gradient}`
                  : "border-slate-800 bg-slate-900/30 hover:border-slate-700"
              }`}
            >
              <div className="flex items-center gap-3 mb-2">
                <span
                  className={`w-3 h-3 rounded-full ${layer.dotColor} ${
                    activeLayer === layer.id ? "animate-pulse" : "opacity-60"
                  }`}
                />
                <h3 className="text-xl font-bold text-white">{layer.label}</h3>
              </div>
              <p
                className={`text-sm mb-8 ${
                  layer.id === "engine"
                    ? "text-cyan-400/80"
                    : "text-purple-400/80"
                } font-medium`}
              >
                {layer.sublabel}
              </p>

              <div className="space-y-4">
                {layer.items.map((item, i) => (
                  <motion.div
                    key={item.name}
                    initial={{ opacity: 0, x: -10 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.4, delay: 0.3 + i * 0.08 }}
                    className="flex items-start gap-3"
                  >
                    <div
                      className={`mt-1.5 w-1.5 h-1.5 rounded-full shrink-0 ${
                        layer.id === "engine" ? "bg-cyan-500" : "bg-purple-500"
                      }`}
                    />
                    <div>
                      <p className="text-white font-medium text-sm">
                        {item.name}
                      </p>
                      <p className="text-slate-500 text-xs">{item.desc}</p>
                    </div>
                  </motion.div>
                ))}
              </div>

              {layer.id === "engine" && (
                <div className="absolute top-4 right-4">
                  <span className="px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-[10px] font-bold tracking-wider uppercase">
                    Core
                  </span>
                </div>
              )}
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.5 }}
          className="flex justify-center my-8"
        >
          <div className="flex flex-col items-center gap-2 text-slate-600">
            <p className="text-xs font-medium tracking-wider uppercase text-slate-500">
              App layer changes. Core guarantees stay the same.
            </p>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="mt-4 p-6 rounded-xl border border-slate-800 bg-slate-900/40 text-center"
        >
          <p className="text-slate-400 text-sm leading-relaxed max-w-3xl mx-auto">
            <span className="text-white font-medium">
              The engine is the brain.
            </span>{" "}
            It stores, links, retrieves, ranks, and answers from deterministic
            graph-native memory.{" "}
            <span className="text-white font-medium">
              The application layer is optional orchestration.
            </span>{" "}
            Add an LLM, keep it out, or swap it later. FAIM still owns the
            memory truth, retrieval logic, and citation chain.
          </p>
        </motion.div>
      </div>
    </section>
  );
}
