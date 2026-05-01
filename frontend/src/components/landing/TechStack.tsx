"use client";

import { motion } from "framer-motion";

const TECH_ITEMS = [
  { name: "PostgreSQL", desc: "Core Graph Storage", icon: "🐘" },
  { name: "Qdrant", desc: "Vector Index Layer", icon: "🌌" },
  { name: "Redis", desc: "Global Lock & Cache", icon: "⚡" },
  { name: "Docker", desc: "Cloud Orchestration", icon: "🐳" },
  { name: "FastAPI", desc: "Engine API Layer", icon: "🚀" },
  { name: "Argon2", desc: "Secure Key Hashing", icon: "🔐" },
  { name: "PyMuPDF", desc: "Layout Perception", icon: "📄" },
  { name: "Tesseract", desc: "Scanned OCR Core", icon: "👁️" },
  { name: "SQLAlchemy", desc: "ORM Orchestration", icon: "🔗" },
  { name: "Pydantic", desc: "Strict Logic Schema", icon: "✅" },
  { name: "Pytest", desc: "Engine Validation", icon: "🧪" },
  { name: "Python", desc: "Native Logic Core", icon: "🐍" },
];

export default function TechStack() {
  return (
    <section className="py-16 px-4 bg-slate-950 border-y border-slate-900/50">
      <div className="max-w-6xl mx-auto">
        <motion.p
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="text-center text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500 mb-10"
        >
          Built on the Foundations of Modern Infrastructure
        </motion.p>

        <div className="flex flex-wrap items-center justify-center gap-6 sm:gap-8 md:gap-12">
          {TECH_ITEMS.map((tech, index) => (
            <motion.div
              key={tech.name}
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: index * 0.05 }}
              className="flex items-center gap-3 group min-w-[140px]"
            >
              <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center text-lg sm:text-xl group-hover:border-slate-700 transition-colors shrink-0">
                {tech.icon}
              </div>
              <div className="flex flex-col min-w-0">
                <span className="text-xs sm:text-sm font-bold text-slate-300 group-hover:text-white transition-colors truncate">
                  {tech.name}
                </span>
                <span className="text-[9px] sm:text-[10px] text-slate-600 font-medium">
                  {tech.desc}
                </span>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
