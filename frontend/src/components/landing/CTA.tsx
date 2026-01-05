"use client";

import { motion } from "framer-motion";
import Link from "next/link";

export default function CTA() {
  return (
    <section className="py-24 px-4 bg-slate-950 relative overflow-hidden">
      {/* Background Effects */}
      <div className="absolute inset-0">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-cyan-500/10 rounded-full blur-3xl" />
        <div className="absolute top-1/4 right-1/4 w-[400px] h-[400px] bg-purple-500/10 rounded-full blur-3xl" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 40 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6 }}
        className="relative z-10 max-w-4xl mx-auto text-center"
      >
        <h2 className="text-4xl md:text-6xl font-bold text-white leading-tight">
          Ready to Transform
          <br />
          <span className="bg-gradient-to-r from-cyan-400 via-blue-400 to-purple-400 bg-clip-text text-transparent">
            Your Knowledge?
          </span>
        </h2>

        <p className="mt-6 text-lg text-slate-400 max-w-xl mx-auto">
          Join the future of memory. Start building your infinite knowledge base
          today.
        </p>

        <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            href="/dashboard"
            className="group relative px-10 py-4 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-xl text-white font-semibold text-lg shadow-lg shadow-cyan-500/25 hover:shadow-cyan-500/40 transition-all duration-300 hover:scale-105"
          >
            Get Started Free
            <span className="ml-2 inline-block group-hover:translate-x-1 transition-transform">
              →
            </span>
          </Link>
        </div>

        <p className="mt-6 text-sm text-slate-500">
          No credit card required • Free forever tier
        </p>
      </motion.div>
    </section>
  );
}
