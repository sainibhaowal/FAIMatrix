"use client";

import { motion } from "framer-motion";
import { useState } from "react";

const STEPS = [
  {
    title: "1. Install Core",
    code: "pip install faim-native",
    desc: "Single binary engine. No external vector DB required.",
  },
  {
    title: "2. Boot Engine",
    code: "faim server start --port 8080",
    desc: "Initializes local deterministic graph and API layer.",
  },
  {
    title: "3. Ingest & Query",
    code: `from faim import FaimClient

client = FaimClient("http://localhost:8080")
client.ingest("./legal_report.pdf")
answer = client.query("When is the deadline?")`,
    desc: "Automatic layout analysis, graph expansion, and answer synthesis.",
  },
];

export default function QuickStart() {
  const [activeStep, setActiveStep] = useState(0);

  return (
    <section className="py-28 px-4 bg-slate-950 relative overflow-hidden">
      <div className="max-w-6xl mx-auto relative">
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
          >
            <span className="text-purple-400 text-sm font-medium tracking-wider uppercase">
              Developer Experience
            </span>
            <h2 className="mt-4 text-4xl font-bold text-white mb-6">
              Production-Ready in{" "}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-400">
                60 Seconds.
              </span>
            </h2>
            <p className="text-slate-400 mb-10 text-lg">
              FAIM is built for engineers who need to ship accurate AI features
              without managing complex infrastructure stacks.
            </p>

            <div className="space-y-4">
              {STEPS.map((step, i) => (
                <button
                  key={step.title}
                  onClick={() => setActiveStep(i)}
                  className={`w-full text-left p-6 rounded-2xl border transition-all duration-300 ${
                    activeStep === i
                      ? "border-purple-500/50 bg-purple-500/10"
                      : "border-slate-800 bg-slate-900/20 hover:border-slate-700"
                  }`}
                >
                  <div className="flex items-center gap-4">
                    <span className={`text-sm font-bold ${activeStep === i ? "text-purple-400" : "text-slate-600"}`}>
                      0{i + 1}
                    </span>
                    <h3 className="text-white font-bold">{step.title}</h3>
                  </div>
                  {activeStep === i && (
                    <motion.p
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      className="mt-2 text-sm text-slate-400 pl-9"
                    >
                      {step.desc}
                    </motion.p>
                  )}
                </button>
              ))}
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            className="relative"
          >
            <div className="absolute inset-0 bg-purple-500/20 blur-3xl rounded-full" />
            <div className="relative rounded-2xl border border-slate-800 bg-slate-900/80 p-1 backdrop-blur-xl shadow-2xl overflow-hidden">
              <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-800 bg-slate-950/50">
                <div className="flex gap-1.5">
                  <div className="w-2.5 h-2.5 rounded-full bg-rose-500/20" />
                  <div className="w-2.5 h-2.5 rounded-full bg-amber-500/20" />
                  <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/20" />
                </div>
                <span className="text-[10px] font-mono text-slate-600 ml-2 uppercase tracking-widest">
                  Terminal — bash
                </span>
              </div>
              <div className="p-6 font-mono text-sm">
                <pre className="text-purple-400">
                  <code>{STEPS[activeStep].code}</code>
                </pre>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
