"use client";

import { motion } from "framer-motion";
import Link from "next/link";

const features = [
  {
    id: "memory-engine",
    icon: (
      <svg viewBox="0 0 24 24" className="w-8 h-8" fill="none" stroke="currentColor" strokeWidth="1.5">
        <circle cx="12" cy="12" r="3" />
        <path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83" />
      </svg>
    ),
    title: "Native Semantic Matching",
    description:
      "FAIM now combines a 2.31M+ term semantic registry runtime, semantic-signature channels, a weighted query expansion engine, broader cross-lingual concept bridges across EN, DE, ES, FR, IT, PT, and NL, and a FAIM-native late-interaction scorer across tokens, phrases, concepts, multilingual surfaces, and graph-learned domain terms. The result is stronger fuzzy matching without turning the engine into a black-box ML system.",
    gradient: "from-cyan-500 to-blue-500",
    link: "/features/memory-engine",
  },
  {
    id: "knowledge-graph",
    icon: (
      <svg viewBox="0 0 24 24" className="w-8 h-8" fill="none" stroke="currentColor" strokeWidth="1.5">
        <circle cx="12" cy="12" r="2" />
        <circle cx="6" cy="6" r="2" />
        <circle cx="18" cy="6" r="2" />
        <circle cx="6" cy="18" r="2" />
        <circle cx="18" cy="18" r="2" />
        <path d="M12 10V8M8 8l2-2M14 8l2-2M12 14v2M8 16l2 2M14 16l2 2" />
      </svg>
    ),
    title: "Bounded Graph Reasoning",
    description:
      "Trace evidence chains through a real planner-driven Cortex runtime. FAIM runs adaptive 1-24 hop reasoning by default, supports higher bounded ceilings up to 128 when configured, and visualizes exact path traces in FIG View with citation integrity preserved.",
    gradient: "from-purple-500 to-pink-500",
    link: "/features/knowledge-graph",
  },
  {
    id: "cognitive-pulse-engine",
    icon: (
      <svg viewBox="0 0 24 24" className="w-8 h-8" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M4 12h3l2-6 4 12 2-6h5" />
        <circle cx="7" cy="12" r="1.5" />
        <circle cx="15" cy="12" r="1.5" />
      </svg>
    ),
    title: "Cognitive Pulse Engine",
    description:
      "FIG View now reads a formal pulse-v2 reason ledger from the backend. Node glow, path motion, inspector proof, relation traces, and legends are backed by graph hops, semantic-registry signals, weighted expansion sources, domain-memory links, reranker factors, and late-interaction matches.",
    gradient: "from-fuchsia-500 to-cyan-500",
    link: "/docs#fig-view",
  },

  {
    id: "document-intelligence",
    icon: (
      <svg
        viewBox="0 0 24 24"
        className="w-8 h-8"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
      >
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z" />
        <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" />
      </svg>
    ),
    title: "Document Intelligence",
    description:
      "FAIM Native extractor handles multi-column PDFs, complex tables, scanned-page OCR when enabled, DOCX, PPTX, XLSX, images, and code. Core extraction is local; OCR and model-assisted paths are optional and can vary by provider and configuration.",
    gradient: "from-orange-500 to-amber-500",
    link: "/features/document-intelligence",
  },
  {
    id: "deterministic-security",
    icon: (
      <svg
        viewBox="0 0 24 24"
        className="w-8 h-8"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
      >
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        <path d="M9 12l2 2 4-4" />
      </svg>
    ),
    title: "Deterministic Security",
    description:
      "Identity anchoring, tenant-scoped access, encryption controls, and auditable data lifecycle operations support privacy-aware deployments.",
    gradient: "from-green-500 to-emerald-500",
    link: "/features/security",
  },
  {
    id: "autonomous-domain-memory",
    icon: (
      <svg viewBox="0 0 24 24" className="w-8 h-8" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M4 6h16M4 12h10M4 18h16" />
      </svg>
    ),
    title: "Autonomous Domain Memory",
    description:
      "Uploaded data teaches FAIM its own terminology, aliases, entities, and facts. No manual domain pack selection is required for the normal path.",
    gradient: "from-amber-500 to-orange-500",
    link: "/dashboard/domain",
  },
];

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.15,
    },
  },
};

const item = {
  hidden: { opacity: 0, y: 40 },
  show: { opacity: 1, y: 0, transition: { duration: 0.6 } },
};

export default function Features() {
  return (
    <section id="features" className="py-24 px-4 bg-slate-950">
      <div className="max-w-6xl mx-auto">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <span className="text-cyan-400 text-sm font-medium tracking-wide uppercase">
            Features
          </span>
          <h2 className="mt-4 text-4xl md:text-5xl font-bold text-white">
            Everything You Need to
            <br />
            <span className="bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
              Master Your Knowledge
            </span>
          </h2>
        </motion.div>

        {/* Feature Cards */}
        <motion.div
          variants={container}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true }}
          className="grid md:grid-cols-2 gap-6"
        >
          {features.map((feature, index) => (
            <motion.div
              key={index}
              variants={item}
              className="group relative p-8 rounded-2xl border border-slate-800 bg-slate-900/50 hover:bg-slate-900/80 transition-all duration-500 hover:border-slate-700"
            >
              {/* Gradient Glow on Hover - pointer-events-none so it doesn't block clicks */}
              <div
                className={`absolute inset-0 rounded-2xl bg-gradient-to-br ${feature.gradient} opacity-0 group-hover:opacity-5 transition-opacity duration-500 pointer-events-none`}
              />

              {/* Content - relative z-10 to be above the gradient */}
              <div className="relative z-10">
                {/* Icon */}
                <div
                  className={`inline-flex p-3 rounded-xl bg-gradient-to-br ${feature.gradient} text-white mb-6`}
                >
                  {feature.icon}
                </div>

                {/* Content */}
                <h3 className="text-xl font-semibold text-white mb-3">
                  {feature.title}
                </h3>
                <p className="text-slate-400 leading-relaxed mb-6">
                  {feature.description}
                </p>

                {/* Learn More Link */}
                <Link
                  href={feature.link}
                  className="inline-flex items-center text-cyan-400 text-sm font-medium hover:text-cyan-300 transition-colors group/link"
                >
                  Learn more
                  <svg
                    className="w-4 h-4 ml-2 group-hover/link:translate-x-1 transition-transform"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 5l7 7-7 7"
                    />
                  </svg>
                </Link>
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
