"use client";

import { motion } from "framer-motion";

const PILLARS = [
  {
    title: "Layout-Aware Perception",
    subtitle: "The End of Context Blindness",
    desc: "Standard RAG treats PDFs as flat text. FAIM understands multi-column scientific papers, detects table headers, and preserves logical reading order.",
    tech: "extractors_faim.py",
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
    color: "blue",
  },
  {
    title: "Conflict-Aware Retrieval",
    subtitle: "Detecting Evidence Gaps",
    desc: "FAIM doesn't just average results. It analyzes entity-relation-value signatures to identify and surface contradictory evidence automatically.",
    tech: "answer_synthesis.py",
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    ),
    color: "rose",
  },
  {
    title: "Spatial Anchoring",
    subtitle: "Precise Provenance",
    desc: "Citations aren't just 'Page 5'. FAIM stores exact (x,y) bounding boxes for every table, figure, and evidence block extracted from your data.",
    tech: "perception/extract",
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    ),
    color: "amber",
  },
  {
    title: "Tenant Isolation",
    subtitle: "SaaS-Ready Security",
    desc: "Every graph, node, and edge is crypto-isolated via mandatory tenant_id scoping. Built for production-scale multi-tenancy from day one.",
    tech: "tenant_id scoping",
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
      </svg>
    ),
    color: "emerald",
  },
];

export default function EnterprisePillars() {
  return (
    <section className="py-28 px-4 bg-slate-950 relative overflow-hidden border-y border-slate-900">
      <div className="max-w-6xl mx-auto relative">
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          {PILLARS.map((pillar, idx) => (
            <motion.div
              key={pillar.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: idx * 0.1 }}
              className="p-6 rounded-2xl border border-slate-800 bg-slate-900/10 hover:border-slate-700 hover:bg-slate-900/30 transition-all group"
            >
              <div className={`w-12 h-12 rounded-xl bg-${pillar.color}-500/10 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform`}>
                <div className={`text-${pillar.color}-400`}>{pillar.icon}</div>
              </div>
              <h3 className="text-white font-bold mb-1">{pillar.title}</h3>
              <p className={`text-[10px] font-bold uppercase tracking-widest text-${pillar.color}-500/80 mb-3`}>
                {pillar.subtitle}
              </p>
              <p className="text-slate-500 text-xs leading-relaxed mb-6">
                {pillar.desc}
              </p>
              <div className="pt-4 border-t border-slate-800/50">
                <span className="text-[10px] font-mono text-slate-700 uppercase">
                  {pillar.tech}
                </span>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
