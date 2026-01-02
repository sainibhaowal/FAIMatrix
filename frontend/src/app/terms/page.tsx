'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';
import FaimLogo from '@/components/landing/FaimLogo';

export default function TermsPage() {
  return (
    <main className="min-h-screen bg-slate-950">
      {/* Navbar */}
      <nav className="fixed top-0 left-0 right-0 z-50 pt-4 px-4">
        <div className="max-w-7xl mx-auto px-6 py-3 bg-slate-900/80 backdrop-blur-xl border border-slate-700/50 rounded-2xl">
          <div className="flex items-center justify-between">
            <Link href="/">
              <FaimLogo size={36} />
            </Link>
            <Link href="/" className="text-sm text-slate-400 hover:text-white transition-colors">
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
            <h1 className="text-4xl font-bold text-white mb-4">Terms of Service</h1>
            <p className="text-slate-400 mb-8">Last updated: January 2026</p>

            <div className="prose prose-invert max-w-none space-y-8">
              <section>
                <h2 className="text-2xl font-semibold text-white mb-4">1. Acceptance of Terms</h2>
                <p className="text-slate-400 leading-relaxed">
                  By accessing or using FAIM Lab, a service operated by Ravinder Singh, you agree to be bound by these Terms of Service. If you do not agree to these terms, please do not use our service.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-white mb-4">2. Description of Service</h2>
                <p className="text-slate-400 leading-relaxed">
                  FAIM Lab provides AI-powered knowledge management services, including document processing, knowledge graph visualization, and natural language querying of your data.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-white mb-4">3. User Accounts</h2>
                <p className="text-slate-400 leading-relaxed mb-4">When creating an account, you agree to:</p>
                <ul className="list-disc list-inside text-slate-400 space-y-2">
                  <li>Provide accurate and complete information</li>
                  <li>Maintain the security of your account credentials</li>
                  <li>Notify us immediately of any unauthorized access</li>
                  <li>Be responsible for all activities under your account</li>
                </ul>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-white mb-4">4. Acceptable Use</h2>
                <p className="text-slate-400 leading-relaxed mb-4">You agree not to:</p>
                <ul className="list-disc list-inside text-slate-400 space-y-2">
                  <li>Upload illegal or harmful content</li>
                  <li>Attempt to gain unauthorized access to our systems</li>
                  <li>Use the service to infringe on intellectual property rights</li>
                  <li>Resell or redistribute the service without permission</li>
                </ul>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-white mb-4">5. Intellectual Property</h2>
                <p className="text-slate-400 leading-relaxed">
                  You retain ownership of all content you upload to FAIM Lab. By uploading content, you grant us a license to process and store it for the purpose of providing our services.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-white mb-4">6. Limitation of Liability</h2>
                <p className="text-slate-400 leading-relaxed">
                  FAIM Lab is provided "as is" without warranties of any kind. We are not liable for any indirect, incidental, or consequential damages arising from your use of the service.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-white mb-4">7. Contact</h2>
                <p className="text-slate-400 leading-relaxed">
                  For questions about these Terms, contact us at{' '}
                  <a href="mailto:legal@faimlab.com" className="text-cyan-400 hover:underline">legal@faimlab.com</a>.
                </p>
              </section>
            </div>
          </motion.div>
        </div>
      </div>
    </main>
  );
}
