"use client";

import { motion, useScroll, useSpring } from "framer-motion";
import { useEffect, useState } from "react";

const SECTIONS = [
  { id: "hero", label: "Hero" },
  { id: "stack", label: "Tech Stack" },
  { id: "highlights", label: "Highlights" },
  { id: "outcomes", label: "Outcomes" },
  { id: "architecture", label: "Architecture" },
  { id: "recall", label: "Hybrid Recall" },
  { id: "comparison", label: "RAG vs FAIM" },
  { id: "pillars", label: "Enterprise Pillars" },
  { id: "engine", label: "Core Engine" },
  { id: "graph-demo", label: "Knowledge Graph" },
  { id: "integrations", label: "Integration Map" },
  { id: "pipeline", label: "Ingestion Pipeline" },
  { id: "quickstart", label: "Quick Start" },
  { id: "docs-ops", label: "Docs & Ops" },
  { id: "math", label: "Math Proof" },
  { id: "query-logic", label: "Query Logic" },
  { id: "evolution", label: "Guardrailed Autonomy" },
  { id: "figview", label: "FIG View" },
  { id: "manifesto", label: "Manifesto" },
  { id: "benchmarks", label: "Benchmarks" },
  { id: "how-it-works", label: "How it Works" },
  { id: "api", label: "Developer API" },
  { id: "security", label: "Security Keys" },
  { id: "use-cases", label: "Use Cases" },
  { id: "roadmap", label: "Roadmap" },
  { id: "specs", label: "Technical Specs" },
  { id: "faq", label: "FAQ" },
  { id: "cta", label: "Get Started" },
];

export default function SectionTracker() {
  const [activeSection, setActiveSection] = useState("hero");
  const { scrollYProgress } = useScroll();
  const scaleY = useSpring(scrollYProgress, {
    stiffness: 100,
    damping: 30,
    restDelta: 0.001,
  });

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActiveSection(entry.target.id);
          }
        });
      },
      { threshold: 0.5 },
    );

    SECTIONS.forEach(({ id }) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, []);

  const scrollTo = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  const [mouseY, setMouseY] = useState<number | null>(null);

  const handleMouseMove = (e: React.MouseEvent) => {
    setMouseY(e.clientY);
  };

  const handleMouseLeave = () => {
    setMouseY(null);
  };

  return (
    <div
      className="fixed right-0 top-1/2 -translate-y-1/2 z-50 flex flex-col items-end px-1 sm:px-4 py-4 sm:py-8 gap-1 sm:gap-1.5 group h-fit max-h-[90vh] overflow-y-auto sm:overflow-visible custom-scrollbar"
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
    >
      {SECTIONS.map((section, i) => {
        const isActive = activeSection === section.id;

        // Liquid Proximity Calculation
        let proximityScale = 1;
        if (mouseY !== null) {
          const el = document.getElementById(`nav-dot-${section.id}`);
          if (el) {
            const rect = el.getBoundingClientRect();
            const centerY = rect.top + rect.height / 2;
            const dist = Math.abs(mouseY - centerY);
            // Gaussian-like falloff: max effect at dist=0, fades by 100px
            proximityScale = Math.max(1, 2.5 - dist / 60);
          }
        }

        return (
          <button
            key={section.id}
            id={`nav-dot-${section.id}`}
            onClick={() => scrollTo(section.id)}
            className="relative flex items-center justify-end h-3 w-8 sm:w-16 outline-none group/item"
          >
            {/* Label */}
            <span
              className={`absolute right-full mr-6 px-2 py-0.5 rounded-md bg-slate-900 border border-slate-800 text-[9px] font-bold uppercase tracking-widest whitespace-nowrap transition-all duration-200 pointer-events-none opacity-0 group-hover/item:opacity-100 translate-x-2 group-hover/item:translate-x-0 z-[60] ${
                isActive ? "text-cyan-400 border-cyan-500/30" : "text-slate-400"
              }`}
            >
              {section.label}
            </span>

            {/* Tactical Interactive Bar */}
            <motion.div
              animate={{
                width: isActive ? 32 * proximityScale : 12 * proximityScale,
                height: isActive ? 3 : 1.5,
                backgroundColor: isActive
                  ? "#22d3ee"
                  : mouseY !== null && proximityScale > 1.2
                    ? "#64748b"
                    : "#334155",
                x: proximityScale > 1 ? -(proximityScale - 1) * 10 : 0,
              }}
              transition={{ type: "spring", stiffness: 300, damping: 20 }}
              className={`rounded-full ${
                isActive ? "shadow-[0_0_12px_rgba(34,211,238,0.5)]" : ""
              }`}
            />

            {/* Hover Indicator Glow */}
            {mouseY !== null && proximityScale > 1.5 && (
              <div className="absolute right-0 w-4 h-4 bg-white/5 blur-md -z-10 rounded-full" />
            )}
          </button>
        );
      })}
    </div>
  );
}
