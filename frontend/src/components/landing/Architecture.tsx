"use client";

import { motion } from "framer-motion";
import { useState } from "react";

const LAYERS = [
  {
    id: "application",
    label: "Application Layer",
    sublabel: "Natural Language Interface",
    color: "purple",
    gradient: "from-purple-500/20 to-purple-500/5",
    borderColor: "border-purple-500/30",
    dotColor: "bg-purple-400",
    items: [
      { name: "LLM Integration", desc: "Natural language queries and explanations" },
      { name: "API Gateway", desc: "Universal REST API with tenant isolation" },
      { name: "API Keys", desc: "Connect any application to FAIM power" },
      { name: "Dashboard", desc: "Visual graph exploration and monitoring" },
    ],
  },
  {
    id: "engine",
    label: "FAIM Core Engine",
    sublabel: "Zero-LLM. Pure Mathematics.",
    color: "cyan",
    gradient: "from-cyan-500/20 to-cyan-500/5",
    borderColor: "border-cyan-500/30",
    dotColor: "bg-cyan-400",
    items: [
      { name: "Fractal Physics", desc: "D\u0302, H\u0302, \u039B\u0302, Energy \u2264 2.0" },
      { name: "Inheritance Model", desc: "Fractions sum to exactly 1.0" },
      { name: "Antisymmetric Merge", desc: "Deterministic dedup via SHA-256" },
      { name: "8 Invariant Checks", desc: "Mathematical proof every cycle" },
    ],
  },
] as const;

export default function Architecture() {
  const [activeLayer, setActiveLayer] = useState<string>("engine");

  return (
    <section id="architecture" className="py-28 px-4 bg-slate-950 relative overflow-hidden">
      {/* Subtle background */}
      <div className="absolute inset-0 faim-grid" />

      <div className="max-w-6xl mx-auto relative">
        {/* Section Header */}
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
              One Truth.
            </span>
          </h2>
          <p className="mt-4 text-slate-400 max-w-2xl mx-auto text-lg">
            The core engine runs on pure mathematics — no LLM, no randomness,
            no cloud dependency. The application layer adds natural language on top.
          </p>
        </motion.div>

        {/* Architecture Diagram */}
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
              {/* Layer Header */}
              <div className="flex items-center gap-3 mb-2">
                <span className={`w-3 h-3 rounded-full ${layer.dotColor} ${
                  activeLayer === layer.id ? "animate-pulse" : "opacity-60"
                }`} />
                <h3 className="text-xl font-bold text-white">{layer.label}</h3>
              </div>
              <p className={`text-sm mb-8 ${
                layer.id === "engine" ? "text-cyan-400/80" : "text-purple-400/80"
              } font-medium`}>
                {layer.sublabel}
              </p>

              {/* Items */}
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
                    <div className={`mt-1.5 w-1.5 h-1.5 rounded-full shrink-0 ${
                      layer.id === "engine" ? "bg-cyan-500" : "bg-purple-500"
                    }`} />
                    <div>
                      <p className="text-white font-medium text-sm">{item.name}</p>
                      <p className="text-slate-500 text-xs">{item.desc}</p>
                    </div>
                  </motion.div>
                ))}
              </div>

              {/* Badge */}
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

        {/* Connection Arrow */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.5 }}
          className="flex justify-center my-8"
        >
          <div className="flex flex-col items-center gap-2 text-slate-600">
            <p className="text-xs font-medium tracking-wider uppercase text-slate-500">
              LLM goes down? Engine keeps running.
            </p>
          </div>
        </motion.div>

        {/* Key Differentiator */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="mt-4 p-6 rounded-xl border border-slate-800 bg-slate-900/40 text-center"
        >
          <p className="text-slate-400 text-sm leading-relaxed max-w-3xl mx-auto">
            <span className="text-white font-medium">The engine is the brain.</span>{" "}
            It stores, retrieves, merges, and evolves memories using pure mathematics.{" "}
            <span className="text-white font-medium">The LLM is the translator.</span>{" "}
            It converts engine output into natural human language. Remove the translator —
            the brain keeps working. That&apos;s what makes FAIM fundamentally different.
          </p>
        </motion.div>
      </div>
    </section>
  );
}
