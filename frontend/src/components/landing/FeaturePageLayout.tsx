"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import FaimLogo from "@/components/landing/FaimLogo";

interface FeaturePageLayoutProps {
  title: string;
  subtitle: string;
  gradient: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  benefits: string[];
}

export default function FeaturePageLayout({
  title,
  subtitle,
  gradient,
  icon,
  children,
  benefits,
}: FeaturePageLayoutProps) {
  return (
    <main className="min-h-screen bg-slate-950">
      {/* Navbar */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-slate-950/80 backdrop-blur-xl border-b border-slate-800/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link href="/">
              <FaimLogo size={36} />
            </Link>
            <div className="flex items-center gap-4">
              <Link
                href="/"
                className="text-sm text-slate-400 hover:text-white transition-colors"
              >
                ← Back to Home
              </Link>
              <Link
                href="/dashboard"
                className="px-4 py-2 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-lg text-white text-sm font-medium"
              >
                Get Started
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-32 pb-20 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className={`inline-flex p-4 rounded-2xl bg-gradient-to-br ${gradient} text-white mb-8`}
          >
            {icon}
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-4xl md:text-6xl font-bold text-white mb-6"
          >
            {title}
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="text-xl text-slate-400 max-w-2xl mx-auto"
          >
            {subtitle}
          </motion.p>
        </div>
      </section>

      {/* Content */}
      <section className="py-16 px-4">
        <div className="max-w-4xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="prose prose-invert prose-lg max-w-none"
          >
            {children}
          </motion.div>
        </div>
      </section>

      {/* Benefits */}
      <section className="py-16 px-4 bg-slate-900/50">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold text-white mb-8 text-center">
            Key Benefits
          </h2>
          <div className="grid md:grid-cols-2 gap-4">
            {benefits.map((benefit, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.4 + index * 0.1 }}
                className="flex items-start gap-3 p-4 rounded-xl bg-slate-800/50 border border-slate-700/50"
              >
                <svg
                  className="w-5 h-5 text-cyan-400 shrink-0 mt-0.5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
                <span className="text-slate-300">{benefit}</span>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-4">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-3xl font-bold text-white mb-4">
            Ready to Get Started?
          </h2>
          <p className="text-slate-400 mb-8">
            Experience the power of FAIM Lab today.
          </p>
          <Link
            href="/dashboard"
            className="inline-flex px-8 py-4 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-xl text-white font-semibold hover:scale-105 transition-transform"
          >
            Start Free Trial →
          </Link>
        </div>
      </section>
    </main>
  );
}
