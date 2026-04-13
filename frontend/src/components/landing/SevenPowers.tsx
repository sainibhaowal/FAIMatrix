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
    title: "Deterministic Core",
    headline: "The original FAIM engine is still the source of truth.",
    description:
      "FAIM still writes 256-dimensional native vectors, computes inheritance fractions, verifies 8 invariants, hashes graph state, and evolves without randomness. Everything else was added around this core, not in place of it.",
    codeSnippet: `// engine_native.py — deterministic core
raw document → deterministic extraction
  → 256-dim encoding
  → inheritance computation
  → antisymmetric merge
  → invariant verification
  → graph hash + diagnostics`,
    codeFile: "engine_native.py",
    gradient: "from-cyan-500 to-blue-500",
    iconPath: "M13 10V3L4 14h7v7l9-11h-7z",
  },
  {
    number: "02",
    title: "Representation V2",
    headline: "Dense native vectors plus deterministic sparse retrieval.",
    description:
      "FAIM now stores additive sidecars for words, phrases, skip-grams, entities, time, and layout signals. Query-time lexical fusion adds BM25-style sparse scoring without touching v_native or base hashes.",
    codeSnippet: `// representation_v2.py — additive sidecar
channels = {
  "word": word_terms,
  "phrase": phrase_terms,
  "entity": entity_terms,
  "time": time_terms,
  "layout": layout_terms,
}
score = native_score + lexical_score`,
    codeFile: "representation_v2.py",
    gradient: "from-blue-500 to-indigo-500",
    iconPath: "M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 2 0 01-1-1v-6z",
  },
  {
    number: "03",
    title: "Canonical Semantics",
    headline: "Aliases, lemmas, phrases, and corpus-derived meaning.",
    description:
      "WordNet is no longer the only semantic layer. FAIM mines aliases, rewrites phrase variants, induces paraphrase-style edges, and rebuilds graph-local canonical lexicons from corpus statistics.",
    codeSnippet: `// canonical_semantics.py — graph-local adaptation
if pmi >= tau_pmi and overlap >= tau_ctx:
    add_semantic_edge("distributional_synonym")
if phrase_rule.matches(text):
    add_semantic_edge("paraphrase")`,
    codeFile: "canonical_semantics.py",
    gradient: "from-indigo-500 to-purple-500",
    iconPath: "M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15",
  },
  {
    number: "04",
    title: "Graph Semantics + Diffusion",
    headline: "The graph now contributes retrieval value, not just structure.",
    description:
      "Bounded multi-hop traversal, semantic path scoring, concept neighborhood scoring, and deterministic diffusion now influence recall and ranking. Contradictions and opposition are handled during path expansion instead of only after the fact.",
    codeSnippet: `// diffusion.py — bounded graph semantics
S_graph(d|q) =
  Σ paths(lambda ** hops * product(edge_weight))
y_next = (1 - alpha) * seed + alpha * P^T * y
// fixed hops, fixed iterations, deterministic ordering`,
    codeFile: "diffusion.py",
    gradient: "from-purple-500 to-pink-500",
    iconPath: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z",
  },
  {
    number: "05",
    title: "Deterministic Reranker V2",
    headline: "Structured relevance without a learned cross-encoder.",
    description:
      "FAIM now extracts propositions, scores evidence spans, matches entity-relation-value-time structure, and suppresses weaker competing candidates pairwise. Relevance improved without giving up auditability.",
    codeSnippet: `// reranker_v2.py — structured relevance
score =
  lexical + graph + entity + time
  + evidence_span + proposition_match
  - contradiction - redundancy
dominance = suppress_weaker_conflicts(top_n)`,
    codeFile: "reranker_v2.py",
    gradient: "from-emerald-500 to-cyan-500",
    iconPath: "M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z",
  },
  {
    number: "06",
    title: "Scale, Multilingual, Multimodal",
    headline: "Production-oriented retrieval paths beyond plain brute force.",
    description:
      "FAIM now includes sparse inverted indexes, deterministic ANN shortlist generation, English/German concept linking, layout/table/image sidecars, and modality-aware reranking. It scales better and handles richer evidence types.",
    codeSnippet: `// query_flow.py — staged candidate generation
sparse = inverted_index.shortlist(query)
dense = deterministic_ann.shortlist(v_native)
candidates = stable_union(sparse, dense)
// multilingual + multimodal boosts stay additive`,
    codeFile: "query_flow.py",
    gradient: "from-amber-500 to-orange-500",
    iconPath: "M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15",
  },
  {
    number: "07",
    title: "Domain Knowledge + Answers",
    headline: "FAIM now links facts and returns grounded answers.",
    description:
      "Offline KB imports, domain profile packs, entity linking, terminology mining, and extractive answer synthesis make FAIM application-ready. It can now traverse text to entities and facts, then return citation-first answers with contradiction notes.",
    codeSnippet: `// answer_synthesis.py — citation-first output
answer = {
  "direct_answer": best_span,
  "citations": supporting_sources,
  "contradiction_notes": conflicts,
  "confidence": support_score,
}`,
    codeFile: "answer_synthesis.py",
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
        <div
          className={`absolute inset-0 rounded-2xl bg-gradient-to-br ${power.gradient} opacity-0 group-hover:opacity-[0.04] transition-opacity duration-500 pointer-events-none`}
        />

        <div className="relative z-10">
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

          <p className={`text-sm font-medium mb-3 bg-gradient-to-r ${power.gradient} bg-clip-text text-transparent`}>
            {power.headline}
          </p>

          <p className="text-slate-400 text-sm leading-relaxed">
            {power.description}
          </p>

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
            7 Production Layers.{" "}
            <span className="bg-gradient-to-r from-cyan-400 via-blue-400 to-purple-400 bg-clip-text text-transparent">
              One Deterministic System.
            </span>
          </h2>
          <p className="mt-4 text-slate-400 max-w-2xl mx-auto text-lg">
            The original FAIM core is still intact. These cards show how the
            retrieval, knowledge, and answer stack now work together in production.
          </p>
        </motion.div>

        <div className="grid gap-5">
          {POWERS.map((power, i) => (
            <PowerCard key={power.number} power={power} index={i} />
          ))}
        </div>
      </div>
    </section>
  );
}
