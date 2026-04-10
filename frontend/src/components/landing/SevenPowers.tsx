"use client";

import { motion, useInView } from "framer-motion";
import { useRef, useState } from "react";

interface Power {
  number: string;
  title: string;
  headline: string;
  description: string;
  codeSnippet: string;
  codeFile: string;
  gradient: string;
  iconPath: string;
}

const POWERS: Power[] = [
  {
    number: "01",
    title: "Zero-LLM Engine",
    headline: "No API calls. No randomness. No cloud.",
    description:
      "The core engine imports zero ML libraries. 256-dimensional vectors are encoded with pure math. Fractal diagnostics computed with pure Python. When cloud APIs go down, FAIM keeps running — on a laptop, offline, air-gapped.",
    codeSnippet: `// engine_native.py — Zero ML imports
raw document → deterministic extraction
  → 256-dim encoding (NO ML)
  → inheritance computation
  → antisymmetric merge
  → fractal diagnostics → done`,
    codeFile: "engine_native.py",
    gradient: "from-cyan-500 to-blue-500",
    iconPath: "M13 10V3L4 14h7v7l9-11h-7z",
  },
  {
    number: "02",
    title: "Mathematical Inheritance",
    headline: "Fractions sum to exactly 1.0. Always.",
    description:
      "Every memory knows exactly where it came from. Parent fractions are computed by cosine similarity, normalized with stable rounding, and verified by invariant checks. The residual tells you exactly how novel each memory is.",
    codeSnippet: `// invariants.py — Inheritance invariant
fractions = [f for _, f in parents]
total = sum(fractions)
assert abs(total - 1.0) < 1e-9
// residual = 1 - cos(child, parent_mix)`,
    codeFile: "invariants.py",
    gradient: "from-blue-500 to-indigo-500",
    iconPath: "M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z",
  },
  {
    number: "03",
    title: "Deterministic Deduplication",
    headline: "Same input, same merge, same winner. Every time.",
    description:
      "When two vectors are >95% similar, they merge. The winner is selected by lexicographic comparison of SHA-256 hashes — not random, not by timestamp. Run the same ingest 1,000 times: identical results, provably.",
    codeSnippet: `// antisym.py — Deterministic winner
if a_hash < b_hash:
    return (a_id, b_id)   // a wins
elif b_hash < a_hash:
    return (b_id, a_id)   // b wins
// SHA-256 hash = determinism`,
    codeFile: "antisym.py",
    gradient: "from-indigo-500 to-purple-500",
    iconPath: "M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15",
  },
  {
    number: "04",
    title: "Fractal Physics",
    headline: "Your memory has a physics. Measurable. Bounded.",
    description:
      "D\u0302 (fractal dimension) measures structural complexity. H\u0302 (Shannon entropy) measures diversity. \u039B\u0302 (evolution pressure) signals when the graph needs to evolve. Energy E stays \u2264 2.0 — a mathematical stability bound scaled by the golden ratio.",
    codeSnippet: `// fractal_physics.py — Real physics
D = correlation_dimension(8 epsilons)
H = shannon_entropy(20 bins)
\u039B = 0.50*N + 0.30*(1-R) + 0.20*H
E = mean_L2_norm * (1/\u03C6)  // \u2264 2.0
// s = 1/PHI \u2248 0.618 (golden ratio)`,
    codeFile: "fractal_physics.py",
    gradient: "from-purple-500 to-pink-500",
    iconPath: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z",
  },
  {
    number: "05",
    title: "Cryptographic Integrity",
    headline: "Every vector. Every state. SHA-256 verified.",
    description:
      "Every vector has a vector_hash. Every graph state has a graph_hash. Every diagnostic has a diagnostics_hash. Tamper with a single float — the hash breaks. This is an immutable audit trail built into the core engine.",
    codeSnippet: `// vector_schema.py — Crypto integrity
canonical = json.dumps(data,
  sort_keys=True,
  separators=(",", ":"))
hash = sha256(canonical).hexdigest()
// verify_hash() on every read`,
    codeFile: "vector_schema.py",
    gradient: "from-emerald-500 to-cyan-500",
    iconPath: "M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z",
  },
  {
    number: "06",
    title: "Self-Evolution",
    headline: "The graph optimizes itself. No human intervention.",
    description:
      "Compute fractal diagnostics. If \u039B is high (lots of novelty) — loosen merge threshold, let the graph grow. If \u039B is low (high redundancy) — tighten, merge aggressively. Prune, self-invent macro nodes, re-verify all invariants. Automatically.",
    codeSnippet: `// evolution_native.py — Self-evolving
diagnostics = compute_diagnostics()
threshold = adapt_threshold(\u039B)
merges  = find_merge_candidates()
prunes  = prune_safe_nodes()
invents = self_invent_macros()
verify_all_invariants()  // always`,
    codeFile: "evolution_native.py",
    gradient: "from-amber-500 to-orange-500",
    iconPath: "M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15",
  },
  {
    number: "07",
    title: "Physics-Based Scoring",
    headline: "7 components. Fully explainable. No black box.",
    description:
      "Every query result comes with a complete breakdown: similarity, novelty, opposition penalty, redundancy penalty, recency boost, usage weight, and level penalty. Not a neural re-ranker — a transparent scoring function.",
    codeSnippet: `// query_engine.py — 7-component score
score =
  0.40 * similarity
+ 0.15 * novelty
- 0.10 * opposition
- 0.10 * redundancy
+ 0.10 * recency
+ 0.10 * usage
- 0.05 * level_penalty`,
    codeFile: "query_engine.py",
    gradient: "from-rose-500 to-red-500",
    iconPath: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4",
  },
];

function PowerCard({ power, index }: { power: Power; index: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-50px" });
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 50 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.6, delay: index * 0.08 }}
      className="group relative"
    >
      <div
        onClick={() => setIsExpanded(!isExpanded)}
        className={`relative rounded-2xl border p-8 transition-all duration-500 cursor-pointer ${
          isExpanded
            ? "border-slate-600 bg-slate-900/80"
            : "border-slate-800/60 bg-slate-900/30 hover:border-slate-700 hover:bg-slate-900/50"
        }`}
      >
        {/* Gradient glow on hover */}
        <div
          className={`absolute inset-0 rounded-2xl bg-gradient-to-br ${power.gradient} opacity-0 group-hover:opacity-[0.04] transition-opacity duration-500 pointer-events-none`}
        />

        <div className="relative z-10">
          {/* Header */}
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center gap-4">
              <div className={`flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-br ${power.gradient} bg-opacity-10`}>
                <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d={power.iconPath} />
                </svg>
              </div>
              <div>
                <span className="text-slate-600 text-xs font-mono font-bold tracking-wider">
                  {power.number}
                </span>
                <h3 className="text-xl font-bold text-white">{power.title}</h3>
              </div>
            </div>
            <motion.svg
              animate={{ rotate: isExpanded ? 180 : 0 }}
              transition={{ duration: 0.3 }}
              className="w-5 h-5 text-slate-500 shrink-0 mt-2"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </motion.svg>
          </div>

          {/* Headline */}
          <p className={`text-sm font-medium mb-3 bg-gradient-to-r ${power.gradient} bg-clip-text text-transparent`}>
            {power.headline}
          </p>

          {/* Description */}
          <p className="text-slate-400 text-sm leading-relaxed">
            {power.description}
          </p>

          {/* Code Snippet (expandable) */}
          <motion.div
            initial={false}
            animate={{
              height: isExpanded ? "auto" : 0,
              opacity: isExpanded ? 1 : 0,
              marginTop: isExpanded ? 24 : 0,
            }}
            transition={{ duration: 0.3, ease: "easeOut" }}
            className="overflow-hidden"
          >
            <div className="relative rounded-lg bg-slate-950 border border-slate-800 p-4 overflow-x-auto">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-red-500/60" />
                  <div className="w-3 h-3 rounded-full bg-yellow-500/60" />
                  <div className="w-3 h-3 rounded-full bg-green-500/60" />
                </div>
                <span className="text-slate-600 text-[10px] font-mono">{power.codeFile}</span>
              </div>
              <pre className="text-xs font-mono text-slate-300 leading-relaxed whitespace-pre-wrap">
                {power.codeSnippet}
              </pre>
            </div>
          </motion.div>
        </div>
      </div>
    </motion.div>
  );
}

export default function SevenPowers() {
  return (
    <section id="powers" className="py-28 px-4 bg-gradient-to-b from-slate-950 to-[#070a18]">
      <div className="max-w-5xl mx-auto">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-20"
        >
          <span className="text-cyan-400 text-sm font-medium tracking-wider uppercase">
            The Engine
          </span>
          <h2 className="mt-4 text-4xl md:text-5xl font-bold text-white">
            7 Capabilities.{" "}
            <span className="bg-gradient-to-r from-cyan-400 via-blue-400 to-purple-400 bg-clip-text text-transparent">
              Zero Compromise.
            </span>
          </h2>
          <p className="mt-4 text-slate-400 max-w-2xl mx-auto text-lg">
            Every claim backed by real code. Click any card to see the implementation.
          </p>
        </motion.div>

        {/* Powers Grid */}
        <div className="grid gap-5">
          {POWERS.map((power, i) => (
            <PowerCard key={power.number} power={power} index={i} />
          ))}
        </div>
      </div>
    </section>
  );
}
