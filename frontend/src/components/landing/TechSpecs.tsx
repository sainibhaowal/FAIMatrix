"use client";

import { motion } from "framer-motion";

const SPEC_GROUPS = [
  {
    title: "Vector Engine",
    color: "cyan",
    borderColor: "border-cyan-500/20",
    specs: [
      { label: "Vector Dimension", value: "256", unit: "fixed" },
      { label: "Encoding", value: "Deterministic", unit: "no ML" },
      { label: "Hash Algorithm", value: "SHA-256", unit: "" },
      { label: "Parent Top-K", value: "8", unit: "max" },
    ],
  },
  {
    title: "Fractal Physics",
    color: "purple",
    borderColor: "border-purple-500/20",
    specs: [
      { label: "D\u0302 Range", value: "[0, 10]", unit: "" },
      { label: "H\u0302 Range", value: "[0, 1]", unit: "" },
      { label: "\u039B\u0302 Formula", value: "0.5N+0.3(1-R)+0.2H", unit: "" },
      { label: "Energy Bound", value: "\u2264 2.0", unit: "" },
    ],
  },
  {
    title: "Query Scoring",
    color: "blue",
    borderColor: "border-blue-500/20",
    specs: [
      { label: "Similarity Weight", value: "0.40", unit: "" },
      { label: "Novelty Weight", value: "0.15", unit: "" },
      { label: "Opposition Penalty", value: "0.10", unit: "" },
      { label: "Components Total", value: "7", unit: "" },
    ],
  },
  {
    title: "Infrastructure",
    color: "emerald",
    borderColor: "border-emerald-500/20",
    specs: [
      { label: "Min CPU", value: "2", unit: "cores" },
      { label: "Min RAM", value: "1", unit: "GB" },
      { label: "GPU Required", value: "No", unit: "(STRICT)" },
      { label: "Network Required", value: "No", unit: "" },
    ],
  },
];

const SPEED_PROFILES = [
  { name: "STRICT", nodes: "1M", p95: "10ms", qps: "50", gpu: "No", color: "text-emerald-400" },
  { name: "FAST", nodes: "10M", p95: "2ms", qps: "200", gpu: "Yes", color: "text-blue-400" },
  { name: "RELAXED", nodes: "50M", p95: "2ms", qps: "500", gpu: "Yes", color: "text-purple-400" },
  { name: "SCALE", nodes: "80M", p95: "2ms", qps: "500", gpu: "Yes", color: "text-amber-400" },
];

const colorMap: Record<string, string> = {
  cyan: "text-cyan-400",
  purple: "text-purple-400",
  blue: "text-blue-400",
  emerald: "text-emerald-400",
};

const bgMap: Record<string, string> = {
  cyan: "bg-cyan-500/10",
  purple: "bg-purple-500/10",
  blue: "bg-blue-500/10",
  emerald: "bg-emerald-500/10",
};

export default function TechSpecs() {
  return (
    <section id="specs" className="py-28 px-4 bg-gradient-to-b from-slate-950 to-[#070a18]">
      <div className="max-w-6xl mx-auto">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-20"
        >
          <span className="text-amber-400 text-sm font-medium tracking-wider uppercase">
            Specifications
          </span>
          <h2 className="mt-4 text-4xl md:text-5xl font-bold text-white">
            Real Numbers.{" "}
            <span className="bg-gradient-to-r from-amber-400 to-orange-400 bg-clip-text text-transparent">
              From Real Code.
            </span>
          </h2>
          <p className="mt-4 text-slate-400 max-w-2xl mx-auto">
            Every number on this page comes directly from the source code.
            Nothing estimated. Nothing inflated.
          </p>
        </motion.div>

        {/* Spec Groups */}
        <div className="grid md:grid-cols-2 gap-5 mb-16">
          {SPEC_GROUPS.map((group, gi) => (
            <motion.div
              key={group.title}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: gi * 0.1 }}
              className={`p-6 rounded-2xl border ${group.borderColor} bg-slate-900/30`}
            >
              <div className="flex items-center gap-3 mb-5">
                <div className={`w-2 h-2 rounded-full ${bgMap[group.color]}`}>
                  <div className={`w-2 h-2 rounded-full ${colorMap[group.color]} animate-pulse`} style={{ opacity: 0.8 }} />
                </div>
                <h3 className={`text-sm font-bold tracking-wider uppercase ${colorMap[group.color]}`}>
                  {group.title}
                </h3>
              </div>

              <div className="space-y-3">
                {group.specs.map((spec) => (
                  <div key={spec.label} className="flex items-center justify-between py-2 border-b border-slate-800/50 last:border-0">
                    <span className="text-slate-500 text-sm">{spec.label}</span>
                    <span className="text-white font-mono text-sm font-medium">
                      {spec.value}
                      {spec.unit && (
                        <span className="text-slate-600 text-xs ml-1.5">{spec.unit}</span>
                      )}
                    </span>
                  </div>
                ))}
              </div>
            </motion.div>
          ))}
        </div>

        {/* Speed Profiles Table */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <h3 className="text-xl font-bold text-white text-center mb-8">
            Speed Budget Profiles
            <span className="block text-sm font-normal text-slate-500 mt-1">
              from spec.py — SpeedBudget dataclass
            </span>
          </h3>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/30 overflow-hidden">
            {/* Table Header */}
            <div className="grid grid-cols-5 gap-4 px-6 py-4 border-b border-slate-800 bg-slate-900/50">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Profile</span>
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Max Nodes</span>
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">p95 Retrieve</span>
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Min QPS</span>
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">GPU</span>
            </div>

            {/* Table Rows */}
            {SPEED_PROFILES.map((profile, i) => (
              <motion.div
                key={profile.name}
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.3, delay: i * 0.08 }}
                className="grid grid-cols-5 gap-4 px-6 py-4 border-b border-slate-800/50 last:border-0 hover:bg-slate-800/20 transition-colors"
              >
                <span className={`font-mono text-sm font-bold ${profile.color}`}>
                  {profile.name}
                </span>
                <span className="text-white font-mono text-sm">{profile.nodes}</span>
                <span className="text-white font-mono text-sm">{profile.p95}</span>
                <span className="text-white font-mono text-sm">{profile.qps}</span>
                <span className={`font-mono text-sm ${profile.gpu === "No" ? "text-emerald-400" : "text-slate-400"}`}>
                  {profile.gpu}
                </span>
              </motion.div>
            ))}
          </div>

          <p className="text-center text-slate-600 text-xs mt-4 font-mono">
            Source: faim_native/orchestration/perf/spec.py
          </p>
        </motion.div>
      </div>
    </section>
  );
}
