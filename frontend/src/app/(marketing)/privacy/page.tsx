"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { FaimLogo } from "@/components";

export default function PrivacyPage() {
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
        <div className="max-w-3xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <h1 className="text-4xl font-bold text-white mb-4">
              Privacy Policy
            </h1>
            <p className="text-slate-400 mb-8">Last updated: January 2026</p>

            <div className="prose prose-invert max-w-none space-y-8">
              <section>
                <h2 className="text-2xl font-semibold text-white mb-4">
                  1. Introduction
                </h2>
                <p className="text-slate-400 leading-relaxed">
                  FAIM Lab (&quot;we&quot;, &quot;our&quot;, or &quot;us&quot;), operated by Ravinder Singh,
                  is committed to protecting your privacy. This Privacy Policy
                  explains how we collect, use, disclose, and safeguard your
                  information when you use our service.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-white mb-4">
                  2. Information We Collect
                </h2>
                <p className="text-slate-400 leading-relaxed mb-4">
                  We may collect the following types of information:
                </p>
                <ul className="list-disc list-inside text-slate-400 space-y-2">
                  <li>Account information (email, name)</li>
                  <li>Usage data and analytics</li>
                  <li>Documents and content you upload</li>
                  <li>Communication preferences</li>
                </ul>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-white mb-4">
                  3. How We Use Your Information
                </h2>
                <p className="text-slate-400 leading-relaxed mb-4">
                  We use collected information to:
                </p>
                <ul className="list-disc list-inside text-slate-400 space-y-2">
                  <li>Provide and maintain our service</li>
                  <li>Improve and personalize your experience</li>
                  <li>Process transactions and send notifications</li>
                  <li>Analyze usage patterns to improve our product</li>
                </ul>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-white mb-4">
                  4. Data Security
                </h2>
                <p className="text-slate-400 leading-relaxed">
                  We implement industry-standard security measures to protect
                  your data. Your uploaded content is encrypted at rest and in
                  transit. However, no method of transmission over the Internet
                  is 100% secure.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-white mb-4">
                  5. Your Rights (GDPR)
                </h2>
                <p className="text-slate-400 leading-relaxed mb-4">
                  If you are in the EU, you have the right to:
                </p>
                <ul className="list-disc list-inside text-slate-400 space-y-2">
                  <li>Access your personal data</li>
                  <li>Rectify inaccurate data</li>
                  <li>Request deletion of your data</li>
                  <li>Object to processing of your data</li>
                  <li>Data portability</li>
                </ul>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-white mb-4">
                  6. Contact Us
                </h2>
                <p className="text-slate-400 leading-relaxed">
                  If you have questions about this Privacy Policy, please
                  contact us at{" "}
                  <a
                    href="mailto:privacy@faimlab.com"
                    className="text-cyan-400 hover:underline"
                  >
                    privacy@faimlab.com
                  </a>
                  .
                </p>
              </section>
            </div>
          </motion.div>
        </div>
      </div>
    </main>
  );
}
