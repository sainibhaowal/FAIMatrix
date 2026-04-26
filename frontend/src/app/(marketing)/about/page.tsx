"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import Logo from "@/components/brand/Logo";

const timeline = [
  {
    year: "2024",
    title: "The Vision",
    description:
      "The idea of FAIMATRIX was born - a system that remembers, connects, and evolves like the human mind.",
  },
  {
    year: "2025",
    title: "Development Begins",
    description:
      "Building the fractal memory engine from the ground up. Every line of code crafted with purpose.",
  },
  {
    year: "2026",
    title: "FAIMATRIX Launch",
    description:
      "FAIMATRIX goes live - transforming how people store and retrieve knowledge.",
  },
];

const values = [
  {
    icon: (
      <svg
        className="w-6 h-6"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
        />
      </svg>
    ),
    title: "Innovation First",
    description:
      "Pushing the boundaries of what AI-powered knowledge management can achieve.",
  },
  {
    icon: (
      <svg
        className="w-6 h-6"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
        />
      </svg>
    ),
    title: "Privacy by Design",
    description:
      "Your data is yours. We build with security and privacy as core principles.",
  },
  {
    icon: (
      <svg
        className="w-6 h-6"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M13 10V3L4 14h7v7l9-11h-7z"
        />
      </svg>
    ),
    title: "Performance",
    description:
      "Sub-millisecond retrieval at any scale. Speed without compromise.",
  },
];

export default function AboutPage() {
  return (
    <main className="min-h-screen bg-slate-950">
      {/* Navbar */}
      <nav className="fixed top-0 left-0 right-0 z-50 pt-4 px-4">
        <div className="max-w-7xl mx-auto px-6 py-3 bg-slate-900/80 backdrop-blur-xl border border-slate-700/50 rounded-2xl">
          <div className="flex items-center justify-between">
            <Link href="/">
              <Logo px={36} />
            </Link>
            <Link
              href="/"
              className="text-sm text-slate-400 hover:text-white transition-colors"
            >
              ← Back to Home
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-32 pb-20 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <span className="text-cyan-400 text-sm font-medium tracking-wide uppercase">
              About FAIMATRIX
            </span>
            <h1 className="mt-4 text-4xl md:text-6xl font-bold text-white leading-tight">
              Building the Future of
              <br />
              <span className="bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
                Intelligent Memory
              </span>
            </h1>
            <p className="mt-6 text-xl text-slate-400 max-w-2xl mx-auto">
              FAIMATRIX is on a mission to transform how humans interact with
              their knowledge. We&apos;re building an AI that remembers,
              connects, and evolves alongside you.
            </p>
          </motion.div>
        </div>
      </section>

      {/* Founder Section */}
      <section className="py-20 px-4">
        <div className="max-w-4xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="bg-gradient-to-br from-cyan-500/10 to-purple-500/10 border border-slate-700/50 rounded-3xl p-8 md:p-12"
          >
            <div className="flex flex-col md:flex-row items-center gap-8">
              {/* Avatar */}
              <div className="shrink-0">
                <div className="w-32 h-32 rounded-2xl bg-gradient-to-br from-cyan-500 to-purple-500 flex items-center justify-center text-white text-4xl font-bold shadow-lg shadow-cyan-500/20">
                  RS
                </div>
              </div>

              {/* Bio */}
              <div className="text-center md:text-left">
                <h2 className="text-2xl font-bold text-white mb-2">
                  Ravinder Singh
                </h2>
                <p className="text-cyan-400 font-medium mb-4">
                  Founder, CEO & Developer
                </p>
                <p className="text-slate-400 leading-relaxed mb-6">
                  I started FAIMATRIX because I believed there had to be a
                  better way to manage knowledge. Traditional tools force rigid
                  structures on fluid thoughts. FAIM is different — it adapts to
                  how you think, not the other way around.
                </p>
                <p className="text-slate-400 leading-relaxed">
                  As the sole developer and founder, I&apos;ve built every
                  component of FAIMATRIX from the ground up. The fractal memory
                  engine, the knowledge graph — all crafted with one goal: to
                  make your knowledge truly intelligent.
                </p>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Vision */}
      <section className="py-20 px-4 bg-slate-900/30">
        <div className="max-w-4xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-12"
          >
            <h2 className="text-3xl font-bold text-white mb-4">The Vision</h2>
            <p className="text-slate-400 max-w-2xl mx-auto">
              Imagine a world where your knowledge never gets lost. Where every
              idea, document, and thought is connected in a living, breathing
              network that grows smarter over time.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-6">
            {values.map((value, index) => (
              <motion.div
                key={value.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 text-center"
              >
                <div className="w-12 h-12 rounded-xl bg-cyan-500/10 text-cyan-400 flex items-center justify-center mx-auto mb-4">
                  {value.icon}
                </div>
                <h3 className="text-white font-semibold mb-2">{value.title}</h3>
                <p className="text-slate-400 text-sm">{value.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Timeline */}
      <section className="py-20 px-4">
        <div className="max-w-4xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-12"
          >
            <h2 className="text-3xl font-bold text-white mb-4">Our Journey</h2>
          </motion.div>

          <div className="relative">
            {/* Timeline Line */}
            <div className="absolute left-4 md:left-1/2 top-0 bottom-0 w-px bg-gradient-to-b from-cyan-500 via-purple-500 to-transparent" />

            {timeline.map((item, index) => (
              <motion.div
                key={item.year}
                initial={{ opacity: 0, x: index % 2 === 0 ? -30 : 30 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                className={`relative flex items-center gap-8 mb-12 ${
                  index % 2 === 0 ? "md:flex-row" : "md:flex-row-reverse"
                }`}
              >
                {/* Dot */}
                <div className="absolute left-4 md:left-1/2 w-3 h-3 rounded-full bg-cyan-500 -translate-x-1/2 shadow-lg shadow-cyan-500/50" />

                {/* Content */}
                <div
                  className={`ml-12 md:ml-0 md:w-1/2 ${index % 2 === 0 ? "md:pr-12 md:text-right" : "md:pl-12"}`}
                >
                  <span className="text-cyan-400 font-bold text-lg">
                    {item.year}
                  </span>
                  <h3 className="text-white font-semibold text-xl mt-1">
                    {item.title}
                  </h3>
                  <p className="text-slate-400 mt-2">{item.description}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-4">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-3xl font-bold text-white mb-4">
            Join the Journey
          </h2>
          <p className="text-slate-400 mb-8">
            FAIMATRIX is just getting started. Be part of the future of
            knowledge management.
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link
              href="/dashboard"
              className="px-8 py-4 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-xl text-white font-semibold hover:scale-105 transition-transform"
            >
              Get Started Free
            </Link>
            <Link
              href="/contact"
              className="px-8 py-4 bg-slate-800 rounded-xl text-white font-semibold hover:bg-slate-700 transition-colors"
            >
              Contact
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}
