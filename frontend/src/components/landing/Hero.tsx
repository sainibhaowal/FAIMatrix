"use client";

import { motion, useScroll, useTransform } from "framer-motion";
import Link from "next/link";
import { useRef } from "react";

const HERO_STATS = [
  { value: "256", unit: "dim", label: "Deterministic Vectors" },
  { value: "Hybrid", unit: "", label: "Retrieval Stack" },
  { value: "EN/DE", unit: "", label: "Cross-Lingual Support" },
  { value: "SHA-256", unit: "", label: "Cryptographic Lineage" },
];

export default function Hero() {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start start", "end start"],
  });
  const bgY = useTransform(scrollYProgress, [0, 1], ["0%", "30%"]);
  const opacity = useTransform(scrollYProgress, [0, 0.8], [1, 0]);

  return (
    <section
      ref={ref}
      className="relative min-h-screen flex items-center justify-center overflow-hidden"
    >
      <motion.div
        style={{ y: bgY }}
        className="absolute inset-0 bg-gradient-to-br from-slate-950 via-[#070a18] to-cyan-950/30"
      />

      <div className="absolute inset-0 faim-grid" />

      <div className="absolute top-1/4 left-1/6 w-[500px] h-[500px] bg-cyan-500/8 rounded-full blur-[120px] animate-pulse" />
      <div
        className="absolute bottom-1/3 right-1/5 w-[400px] h-[400px] bg-purple-500/6 rounded-full blur-[100px] animate-pulse"
        style={{ animationDelay: "2s" }}
      />
      <div
        className="absolute top-2/3 left-1/2 w-[300px] h-[300px] bg-blue-500/5 rounded-full blur-[80px] animate-pulse"
        style={{ animationDelay: "4s" }}
      />

      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {["D\u0302", "H\u0302", "\u039B\u0302", "\u03C6\u207B\u00B9", "\u2211=1", "E\u22642.0"].map((sym, i) => (
          <motion.span
            key={sym}
            className="absolute text-cyan-500/[0.07] font-mono select-none"
            style={{
              fontSize: `${18 + i * 4}px`,
              left: `${12 + i * 15}%`,
              top: `${20 + (i % 3) * 25}%`,
            }}
            animate={{
              y: [0, -20, 0],
              opacity: [0.04, 0.08, 0.04],
            }}
            transition={{
              duration: 6 + i,
              repeat: Infinity,
              ease: "easeInOut",
              delay: i * 0.8,
            }}
          >
            {sym}
          </motion.span>
        ))}
      </div>

      <motion.div style={{ opacity }} className="relative z-10 text-center px-4 max-w-5xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <span className="inline-flex items-center gap-2.5 px-5 py-2 rounded-full border border-cyan-500/20 bg-cyan-500/[0.06] text-cyan-300 text-xs font-medium tracking-wider uppercase">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-400" />
            </span>
            Deterministic Memory + Retrieval Engine
          </span>
        </motion.div>

        <motion.h2
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.15 }}
          className="mt-8 text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-bold text-white leading-[1.05] tracking-tight"
        >
          Memory That Thinks
          <br />
          <span className="bg-gradient-to-r from-cyan-400 via-blue-400 to-purple-500 bg-clip-text text-transparent">
            With Pure Math
          </span>
        </motion.h2>

        <motion.p
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.3 }}
          className="mt-6 text-lg md:text-xl text-slate-400 max-w-2xl mx-auto leading-relaxed"
        >
          FAIMATRIX is a deterministic memory, retrieval, and answer engine.
          It combines native 256-dimensional vectors, sparse lexical sidecars,
          graph diffusion, proposition-aware reranking, multilingual concept links,
          multimodal indexing, domain knowledge, and citation-first answers
          without giving up FAIM&apos;s core invariants.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.45 }}
          className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4"
        >
          <Link
            href="/auth/signup"
            className="group relative px-8 py-4 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-xl text-white font-semibold text-lg shadow-lg shadow-cyan-500/25 hover:shadow-cyan-500/40 transition-all duration-300 hover:scale-[1.03]"
          >
            <span className="relative z-10 flex items-center gap-2">
              Start Building
              <svg className="w-5 h-5 group-hover:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </span>
            <div className="absolute inset-0 bg-gradient-to-r from-cyan-400 to-blue-400 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
          </Link>

          <Link
            href="#architecture"
            className="px-8 py-4 border border-slate-700/80 rounded-xl text-slate-300 font-medium text-lg hover:border-slate-500 hover:bg-white/[0.03] transition-all duration-300"
          >
            Explore the Engine
          </Link>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.7 }}
          className="mt-20 grid grid-cols-2 md:grid-cols-4 gap-6 md:gap-0 md:divide-x md:divide-slate-800"
        >
          {HERO_STATS.map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.8 + i * 0.1 }}
              className="flex flex-col items-center px-6"
            >
              <p className="text-2xl md:text-3xl font-bold text-white font-mono tracking-tight">
                {stat.value}
                {stat.unit && (
                  <span className="text-sm md:text-base text-cyan-400 ml-1 font-sans font-medium">
                    {stat.unit}
                  </span>
                )}
              </p>
              <p className="text-xs md:text-sm text-slate-500 mt-1">{stat.label}</p>
            </motion.div>
          ))}
        </motion.div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1, delay: 1.5 }}
        className="absolute bottom-8 left-1/2 -translate-x-1/2"
      >
        <div className="w-6 h-10 border-2 border-slate-700 rounded-full flex justify-center pt-2">
          <motion.div
            animate={{ y: [0, 8, 0] }}
            transition={{ duration: 1.5, repeat: Infinity }}
            className="w-1.5 h-1.5 bg-slate-500 rounded-full"
          />
        </div>
      </motion.div>
    </section>
  );
}
