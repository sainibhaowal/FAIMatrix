"use client";

import { motion } from "framer-motion";
import { useState } from "react";

interface UseCase {
  id: string;
  title: string;
  icon: React.ReactNode;
  reason: string;
  features: string[];
  gradient: string;
  borderHover: string;
}

const USE_CASES: UseCase[] = [
  {
    id: "defense",
    title: "Defense & Intelligence",
    icon: (
      <svg viewBox="0 0 24 24" className="w-7 h-7" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m0-10.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
      </svg>
    ),
    reason: "Air-gapped operation. Zero cloud dependencies. Runs on 2 CPU + 1GB RAM.",
    features: [
      "Zero network required — runs fully offline",
      "Deterministic results for audit compliance",
      "Cryptographic integrity on every data point",
      "Tamper-evident immutable audit trail",
    ],
    gradient: "from-slate-500 to-slate-600",
    borderHover: "hover:border-slate-500/50",
  },
  {
    id: "healthcare",
    title: "Healthcare (HIPAA)",
    icon: (
      <svg viewBox="0 0 24 24" className="w-7 h-7" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z" />
      </svg>
    ),
    reason: "No patient data leaves the device. SHA-256 integrity for every record.",
    features: [
      "Data never sent to external APIs",
      "Per-tenant crypto isolation",
      "Verifiable data integrity (SHA-256)",
      "Complete audit trail for compliance",
    ],
    gradient: "from-rose-500 to-pink-500",
    borderHover: "hover:border-rose-500/50",
  },
  {
    id: "finance",
    title: "Financial Services (SOX)",
    icon: (
      <svg viewBox="0 0 24 24" className="w-7 h-7" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18.75a60.07 60.07 0 0115.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 013 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 00-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 01-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 003 15h-.75M15 10.5a3 3 0 11-6 0 3 3 0 016 0zm3 0h.008v.008H18V10.5zm-12 0h.008v.008H6V10.5z" />
      </svg>
    ),
    reason: "Mathematical stability proofs. Immutable audit trail. Deterministic outputs.",
    features: [
      "Provable stability bounds (E \u2264 2.0)",
      "Deterministic — same input, same output",
      "Immutable event journal for auditing",
      "Mathematical invariant verification",
    ],
    gradient: "from-emerald-500 to-teal-500",
    borderHover: "hover:border-emerald-500/50",
  },
  {
    id: "edge",
    title: "Edge & IoT",
    icon: (
      <svg viewBox="0 0 24 24" className="w-7 h-7" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M8.288 15.038a5.25 5.25 0 017.424 0M5.106 11.856c3.807-3.808 9.98-3.808 13.788 0M1.924 8.674c5.565-5.565 14.587-5.565 20.152 0M12.53 18.22l-.53.53-.53-.53a.75.75 0 011.06 0z" />
      </svg>
    ),
    reason: "Runs on minimal hardware. No cloud connectivity needed. No GPU required.",
    features: [
      "2 CPU + 1GB RAM (Docker proven)",
      "Zero GPU requirement (STRICT mode)",
      "No internet connection required",
      "Self-evolving without human intervention",
    ],
    gradient: "from-amber-500 to-orange-500",
    borderHover: "hover:border-amber-500/50",
  },
  {
    id: "regulated",
    title: "Regulated AI (EU AI Act)",
    icon: (
      <svg viewBox="0 0 24 24" className="w-7 h-7" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 21v-8.25M15.75 21v-8.25M8.25 21v-8.25M3 9l9-6 9 6m-1.5 12V10.332A48.36 48.36 0 0012 9.75c-2.551 0-5.056.2-7.5.582V21M3 21h18M12 6.75h.008v.008H12V6.75z" />
      </svg>
    ),
    reason: "Fully explainable. Deterministic. No black-box ML in the core engine.",
    features: [
      "7-component explainable scoring",
      "Complete decision audit trail",
      "No black-box neural components",
      "Reproducible results for any input",
    ],
    gradient: "from-blue-500 to-cyan-500",
    borderHover: "hover:border-blue-500/50",
  },
  {
    id: "research",
    title: "Research & Academic",
    icon: (
      <svg viewBox="0 0 24 24" className="w-7 h-7" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M4.26 10.147a60.436 60.436 0 00-.491 6.347A48.627 48.627 0 0112 20.904a48.627 48.627 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.57 50.57 0 00-2.658-.813A59.905 59.905 0 0112 3.493a59.902 59.902 0 0110.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.697 50.697 0 0112 13.489a50.702 50.702 0 017.74-3.342M6.75 15a.75.75 0 100-1.5.75.75 0 000 1.5zm0 0v-3.675A55.378 55.378 0 0112 8.443m-7.007 11.55A5.981 5.981 0 006.75 15.75v-1.5" />
      </svg>
    ),
    reason: "Reproducible experiments. Novel fractal physics framework. Publishable mathematics.",
    features: [
      "100% reproducible results",
      "Novel fractal dimension estimation",
      "Published mathematical framework",
      "Open for peer review and extension",
    ],
    gradient: "from-purple-500 to-violet-500",
    borderHover: "hover:border-purple-500/50",
  },
];

export default function UseCases() {
  const [activeCase, setActiveCase] = useState<string | null>(null);

  return (
    <section id="use-cases" className="py-28 px-4 bg-slate-950 relative">
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
          <span className="text-emerald-400 text-sm font-medium tracking-wider uppercase">
            Built For Trust
          </span>
          <h2 className="mt-4 text-4xl md:text-5xl font-bold text-white">
            Where Provable{" "}
            <span className="bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
              Trust Matters
            </span>
          </h2>
          <p className="mt-4 text-slate-400 max-w-2xl mx-auto text-lg">
            Industries where you can&apos;t say &ldquo;the AI decided.&rdquo;
            You need mathematical proof.
          </p>
        </motion.div>

        {/* Use Cases Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
          {USE_CASES.map((uc, i) => (
            <motion.div
              key={uc.id}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.08 }}
              onMouseEnter={() => setActiveCase(uc.id)}
              onMouseLeave={() => setActiveCase(null)}
              className={`group relative p-7 rounded-2xl border transition-all duration-500 ${
                activeCase === uc.id
                  ? "border-slate-600 bg-slate-900/60"
                  : `border-slate-800/60 bg-slate-900/20 ${uc.borderHover}`
              }`}
            >
              {/* Gradient glow */}
              <div className={`absolute inset-0 rounded-2xl bg-gradient-to-br ${uc.gradient} opacity-0 group-hover:opacity-[0.03] transition-opacity duration-500 pointer-events-none`} />

              <div className="relative z-10">
                {/* Icon */}
                <div className={`inline-flex p-3 rounded-xl bg-gradient-to-br ${uc.gradient} text-white mb-5`}>
                  {uc.icon}
                </div>

                <h3 className="text-lg font-bold text-white mb-2">{uc.title}</h3>
                <p className="text-sm text-slate-400 mb-5 leading-relaxed">{uc.reason}</p>

                {/* Features */}
                <ul className="space-y-2.5">
                  {uc.features.map((feat) => (
                    <li key={feat} className="flex items-start gap-2.5 text-sm text-slate-500">
                      <svg className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                      {feat}
                    </li>
                  ))}
                </ul>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
