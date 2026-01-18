"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { FaimLogo } from "@/components";

const sections = [
  {
    title: "Getting Started",
    items: [
      {
        title: "Introduction to FAIMATRIX",
        href: "#intro",
        description: "Learn what FAIMATRIX is and how it works",
      },
      {
        title: "Quick Start Guide",
        href: "#quickstart",
        description: "Get up and running in 5 minutes",
      },
      {
        title: "Core Concepts",
        href: "#concepts",
        description: "Understanding the fractal memory engine",
      },
    ],
  },
  {
    title: "Features",
    items: [
      {
        title: "Knowledge Graph",
        href: "/features/knowledge-graph",
        description: "Visualize your knowledge connections",
      },

      {
        title: "Document Intelligence",
        href: "/features/document-intelligence",
        description: "Upload and process documents",
      },
    ],
  },
  {
    title: "API Reference",
    items: [
      {
        title: "REST API",
        href: "#api",
        description: "Full API documentation",
      },
      {
        title: "Webhooks",
        href: "#webhooks",
        description: "Real-time event notifications",
      },
      {
        title: "SDKs",
        href: "#sdks",
        description: "Client libraries for popular languages",
      },
    ],
  },
];

export default function DocsPage() {
  return (
    <main className="min-h-screen bg-slate-950">
      {/* Navbar */}
      <nav className="fixed top-0 left-0 right-0 z-50 pt-4 px-4">
        <div className="max-w-7xl mx-auto px-6 py-3 bg-slate-900/80 backdrop-blur-xl border border-slate-700/50 rounded-2xl">
          <div className="flex items-center justify-between">
            <Link href="/">
              <FaimLogo size={36} />
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

      <div className="pt-32 pb-20 px-4">
        <div className="max-w-5xl mx-auto">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center mb-16"
          >
            <span className="text-cyan-400 text-sm font-medium tracking-wide uppercase">
              Documentation
            </span>
            <h1 className="mt-4 text-4xl md:text-5xl font-bold text-white mb-4">
              Learn FAIMATRIX
            </h1>
            <p className="text-slate-400 text-lg max-w-2xl mx-auto">
              Everything you need to know about building with FAIMATRIX.
            </p>
          </motion.div>

          {/* Search */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="mb-12"
          >
            <div className="relative max-w-xl mx-auto">
              <input
                type="text"
                placeholder="Search documentation..."
                className="w-full px-5 py-4 pl-12 bg-slate-800/50 border border-slate-700 rounded-2xl text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition-colors"
              />
              <svg
                className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
            </div>
          </motion.div>

          {/* Documentation Sections */}
          <div className="grid md:grid-cols-3 gap-8">
            {sections.map((section, sectionIndex) => (
              <motion.div
                key={section.title}
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 + sectionIndex * 0.1 }}
              >
                <h2 className="text-lg font-semibold text-white mb-4">
                  {section.title}
                </h2>
                <div className="space-y-3">
                  {section.items.map((item) => (
                    <Link
                      key={item.title}
                      href={item.href}
                      className="block p-4 bg-slate-900/50 border border-slate-800 rounded-xl hover:border-cyan-500/50 hover:bg-slate-800/50 transition-all group"
                    >
                      <h3 className="text-white font-medium mb-1 group-hover:text-cyan-400 transition-colors">
                        {item.title}
                      </h3>
                      <p className="text-slate-500 text-sm">
                        {item.description}
                      </p>
                    </Link>
                  ))}
                </div>
              </motion.div>
            ))}
          </div>

          {/* Quick Start */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="mt-16 bg-gradient-to-br from-cyan-500/10 to-purple-500/10 border border-slate-700/50 rounded-2xl p-8"
          >
            <h2 id="quickstart" className="text-2xl font-bold text-white mb-6">
              Quick Start
            </h2>
            <div className="prose prose-invert max-w-none">
              <p className="text-slate-400 mb-4">
                Get started with FAIMATRIX in just a few steps:
              </p>
              <ol className="space-y-3 text-slate-300">
                <li className="flex items-start gap-3">
                  <span className="w-6 h-6 rounded-full bg-cyan-500/20 text-cyan-400 flex items-center justify-center text-sm shrink-0">
                    1
                  </span>
                  <span>Sign up for a free account at FAIMATRIX</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="w-6 h-6 rounded-full bg-cyan-500/20 text-cyan-400 flex items-center justify-center text-sm shrink-0">
                    2
                  </span>
                  <span>Upload your first document or paste text directly</span>
                </li>

                <li className="flex items-start gap-3">
                  <span className="w-6 h-6 rounded-full bg-cyan-500/20 text-cyan-400 flex items-center justify-center text-sm shrink-0">
                    3
                  </span>
                  <span>Explore your knowledge graph to find connections</span>
                </li>
              </ol>
            </div>
          </motion.div>
        </div>
      </div>
    </main>
  );
}
