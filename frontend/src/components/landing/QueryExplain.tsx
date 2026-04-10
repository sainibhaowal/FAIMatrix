"use client";

import { motion, useInView } from "framer-motion";
import { useRef, useState, useEffect } from "react";

interface ScoreComponent {
  name: string;
  weight: string;
  value: number;
  type: "positive" | "negative";
  color: string;
  description: string;
}

const SCORE_COMPONENTS: ScoreComponent[] = [
  { name: "Similarity", weight: "0.40", value: 0.92, type: "positive", color: "bg-cyan-500", description: "Cosine similarity to query vector" },
  { name: "Novelty", weight: "0.15", value: 0.68, type: "positive", color: "bg-blue-500", description: "Residual from parent mix — how unique" },
  { name: "Opposition", weight: "0.10", value: 0.05, type: "negative", color: "bg-red-500", description: "Contradiction penalty" },
  { name: "Redundancy", weight: "0.10", value: 0.12, type: "negative", color: "bg-orange-500", description: "Information already covered" },
  { name: "Recency", weight: "0.10", value: 0.85, type: "positive", color: "bg-emerald-500", description: "How recently accessed" },
  { name: "Usage", weight: "0.10", value: 0.45, type: "positive", color: "bg-purple-500", description: "log1p(access_count) normalized" },
  { name: "Level", weight: "0.05", value: 0.08, type: "negative", color: "bg-amber-500", description: "Depth penalty in hierarchy" },
];

function AnimatedBar({ value, color, delay, isInView }: { value: number; color: string; delay: number; isInView: boolean }) {
  return (
    <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
      <motion.div
        initial={{ width: 0 }}
        animate={isInView ? { width: `${value * 100}%` } : {}}
        transition={{ duration: 0.8, delay, ease: "easeOut" }}
        className={`h-full rounded-full ${color}`}
      />
    </div>
  );
}

export default function QueryExplain() {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-80px" });
  const [finalScore, setFinalScore] = useState(0);

  useEffect(() => {
    if (!isInView) return;
    const timer = setTimeout(() => {
      // Calculate: 0.40*0.92 + 0.15*0.68 - 0.10*0.05 - 0.10*0.12 + 0.10*0.85 + 0.10*0.45 - 0.05*0.08
      const score = 0.40 * 0.92 + 0.15 * 0.68 - 0.10 * 0.05 - 0.10 * 0.12 + 0.10 * 0.85 + 0.10 * 0.45 - 0.05 * 0.08;
      setFinalScore(Math.round(score * 1000) / 1000);
    }, 1200);
    return () => clearTimeout(timer);
  }, [isInView]);

  return (
    <section className="py-28 px-4 bg-slate-950 relative overflow-hidden">
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
          <span className="text-rose-400 text-sm font-medium tracking-wider uppercase">
            Explainability
          </span>
          <h2 className="mt-4 text-4xl md:text-5xl font-bold text-white">
            Ask &ldquo;Why?&rdquo; and{" "}
            <span className="bg-gradient-to-r from-rose-400 to-purple-400 bg-clip-text text-transparent">
              Get Math.
            </span>
          </h2>
          <p className="mt-4 text-slate-400 max-w-2xl mx-auto text-lg">
            Every query result includes a full scoring breakdown.
            Not &ldquo;confidence: 0.87&rdquo; — the actual formula, the actual values.
          </p>
        </motion.div>

        <div ref={ref} className="grid lg:grid-cols-2 gap-10 items-start">
          {/* Left: Score Breakdown */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="p-8 rounded-2xl border border-slate-800 bg-slate-900/40"
          >
            <div className="flex items-center justify-between mb-8">
              <h3 className="text-lg font-bold text-white">Score Breakdown</h3>
              <div className="flex items-center gap-3">
                <span className="text-slate-500 text-xs">Final Score</span>
                <motion.span
                  initial={{ opacity: 0 }}
                  animate={isInView ? { opacity: 1 } : {}}
                  transition={{ duration: 0.5, delay: 1.2 }}
                  className="text-2xl font-bold font-mono text-cyan-400"
                >
                  {finalScore || "..."}
                </motion.span>
              </div>
            </div>

            <div className="space-y-5">
              {SCORE_COMPONENTS.map((comp, i) => (
                <div key={comp.name}>
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-mono px-1.5 py-0.5 rounded ${
                        comp.type === "positive"
                          ? "bg-emerald-500/10 text-emerald-400"
                          : "bg-red-500/10 text-red-400"
                      }`}>
                        {comp.type === "positive" ? "+" : "\u2212"}{comp.weight}
                      </span>
                      <span className="text-sm text-white font-medium">{comp.name}</span>
                    </div>
                    <span className="text-sm font-mono text-slate-400">{comp.value.toFixed(2)}</span>
                  </div>
                  <AnimatedBar
                    value={comp.value}
                    color={comp.color}
                    delay={0.15 + i * 0.1}
                    isInView={isInView}
                  />
                  <p className="text-[11px] text-slate-600 mt-1">{comp.description}</p>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Right: Explain Payload */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.15 }}
            className="space-y-6"
          >
            {/* Formula */}
            <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/40">
              <h4 className="text-sm font-bold text-slate-500 uppercase tracking-wider mb-4">
                The Formula
              </h4>
              <div className="p-4 rounded-lg bg-slate-950 border border-slate-800">
                <pre className="text-sm font-mono text-slate-300 leading-loose whitespace-pre-wrap">{`score =
  0.40 × similarity
+ 0.15 × novelty
− 0.10 × opposition
− 0.10 × redundancy
+ 0.10 × recency
+ 0.10 × usage
− 0.05 × level`}</pre>
              </div>
              <p className="text-xs text-slate-600 mt-3 font-mono">
                Source: query_engine.py — ScoringWeights dataclass
              </p>
            </div>

            {/* Key points */}
            <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/40">
              <h4 className="text-sm font-bold text-slate-500 uppercase tracking-wider mb-4">
                What This Means
              </h4>
              <div className="space-y-4">
                <ExplainPoint
                  title="Fully Transparent"
                  text="Every score is a weighted sum of measurable components. No hidden layers, no learned weights."
                />
                <ExplainPoint
                  title="Reproducible"
                  text="Same query, same graph state = same scores. Every time. Deterministically."
                />
                <ExplainPoint
                  title="Auditable"
                  text='For regulated industries: "This memory ranked #1 because similarity=0.92, novelty=0.68, with 0.05 opposition penalty."'
                />
                <ExplainPoint
                  title="Tunable"
                  text="Weights are configurable per use case. Prioritize novelty for research, recency for real-time, similarity for precision."
                />
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}

function ExplainPoint({ title, text }: { title: string; text: string }) {
  return (
    <div className="flex items-start gap-3">
      <div className="mt-1 w-1.5 h-1.5 rounded-full bg-cyan-500 shrink-0" />
      <div>
        <p className="text-white text-sm font-medium">{title}</p>
        <p className="text-slate-500 text-xs mt-0.5">{text}</p>
      </div>
    </div>
  );
}
