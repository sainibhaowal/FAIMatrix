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
  {
    name: "Char / Native",
    weight: "0.12",
    value: 0.86,
    type: "positive",
    color: "bg-cyan-500",
    description: "Deterministic VP-Tree vector and character-level match",
  },
  {
    name: "Word / Phrase",
    weight: "0.20",
    value: 0.91,
    type: "positive",
    color: "bg-blue-500",
    description: "WAND-based sparse lexical and Representation V2 score",
  },
  {
    name: "Entity / Concept",
    weight: "0.14",
    value: 0.77,
    type: "positive",
    color: "bg-indigo-500",
    description: "Entity, alias, concept, and domain linking support",
  },
  {
    name: "Graph",
    weight: "0.16",
    value: 0.74,
    type: "positive",
    color: "bg-purple-500",
    description: "Semantic traversal, diffusion, and neighborhood score",
  },
  {
    name: "Temporal",
    weight: "0.08",
    value: 0.82,
    type: "positive",
    color: "bg-emerald-500",
    description: "Recency and temporal consistency weighting",
  },
  {
    name: "Evidence",
    weight: "0.14",
    value: 0.88,
    type: "positive",
    color: "bg-fuchsia-500",
    description: "Evidence density, proposition overlap, and span quality",
  },
  {
    name: "Opposition",
    weight: "0.09",
    value: 0.06,
    type: "negative",
    color: "bg-red-500",
    description: "Contradiction-aware suppression during traversal and rerank",
  },
  {
    name: "Redundancy",
    weight: "0.07",
    value: 0.11,
    type: "negative",
    color: "bg-orange-500",
    description: "Duplicate or already-covered information penalty",
  },
  {
    name: "Modality",
    weight: "0.05",
    value: 0.53,
    type: "positive",
    color: "bg-amber-500",
    description: "OCR, table, layout, and metadata-aware boost",
  },
  {
    name: "Domain",
    weight: "0.05",
    value: 0.79,
    type: "positive",
    color: "bg-rose-500",
    description: "KB, terminology, and profile-pack support",
  },
];

function AnimatedBar({
  value,
  color,
  delay,
  isInView,
}: {
  value: number;
  color: string;
  delay: number;
  isInView: boolean;
}) {
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
      const score =
        0.12 * 0.86 +
        0.2 * 0.91 +
        0.14 * 0.77 +
        0.16 * 0.74 +
        0.08 * 0.82 +
        0.14 * 0.88 -
        0.09 * 0.06 -
        0.07 * 0.11 +
        0.05 * 0.53 +
        0.05 * 0.79;
      setFinalScore(Math.round(score * 1000) / 1000);
    }, 1200);
    return () => clearTimeout(timer);
  }, [isInView]);

  return (
    <section className="py-28 px-4 bg-slate-950 relative overflow-hidden">
      <div className="absolute inset-0 faim-grid" />

      <div className="max-w-6xl mx-auto relative">
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
            Not a black-box confidence score. The Hybrid Physics-Based Graph
            Recall stack exposes the signals that actually produced the result.
          </p>
        </motion.div>

        <div ref={ref} className="grid lg:grid-cols-2 gap-10 items-start">
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
                      <span
                        className={`text-xs font-mono px-1.5 py-0.5 rounded ${
                          comp.type === "positive"
                            ? "bg-emerald-500/10 text-emerald-400"
                            : "bg-red-500/10 text-red-400"
                        }`}
                      >
                        {comp.type === "positive" ? "+" : "\u2212"}
                        {comp.weight}
                      </span>
                      <span className="text-sm text-white font-medium">
                        {comp.name}
                      </span>
                    </div>
                    <span className="text-sm font-mono text-slate-400">
                      {comp.value.toFixed(2)}
                    </span>
                  </div>
                  <AnimatedBar
                    value={comp.value}
                    color={comp.color}
                    delay={0.15 + i * 0.1}
                    isInView={isInView}
                  />
                  <p className="text-[11px] text-slate-600 mt-1">
                    {comp.description}
                  </p>
                </div>
              ))}
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.15 }}
            className="space-y-6"
          >
            <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/40">
              <h4 className="text-sm font-bold text-slate-500 uppercase tracking-wider mb-4">
                The Formula
              </h4>
              <div className="p-4 rounded-lg bg-slate-950 border border-slate-800">
                <pre className="text-sm font-mono text-slate-300 leading-loose whitespace-pre-wrap">{`score =
  w1 × char/native
+ w2 × word/phrase
+ w3 × entity/concept
+ w4 × graph
+ w5 × temporal
+ w6 × evidence
+ w7 × modality
+ w8 × domain
− w9 × opposition
− w10 × redundancy`}</pre>
              </div>
              <p className="text-xs text-slate-600 mt-3 font-mono">
                Source: query_flow.py + query_engine.py + reranker_v2.py
              </p>
            </div>

            <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/40">
              <h4 className="text-sm font-bold text-slate-500 uppercase tracking-wider mb-4">
                What This Means
              </h4>
              <div className="space-y-4">
                <ExplainPoint
                  title="Fully Transparent"
                  text="Lexical, graph, proposition, modality, and domain signals are all surfaced as measurable components."
                />
                <ExplainPoint
                  title="Reproducible"
                  text="Same query plus the same graph state produces the same shortlist, the same rerank, and the same answer block."
                />
                <ExplainPoint
                  title="Auditable"
                  text='For regulated systems: "This result ranked first because lexical=0.91, graph=0.74, evidence=0.88, with contradiction penalty 0.06."'
                />
                <ExplainPoint
                  title="Citation-First"
                  text="The same stack feeds extractive answer synthesis, so the answer stays tied to spans, sources, and contradiction notes."
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
