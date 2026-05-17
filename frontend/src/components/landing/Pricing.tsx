"use client";

import { motion } from "framer-motion";
import Link from "next/link";

const plans = [
  {
    name: "Explorer",
    price: "$0",
    period: "forever",
    description: "Personal cognitive mapping",
    features: [
      "1,000 Nodes",
      "1-Hop Reasoning",
      "Standard 3D Globe",
      "Basic Semantic Search"
    ],
    cta: "Start Explorer",
    popular: false,
    gradient: "from-slate-600 to-slate-700",
  },
  {
    name: "Architect",
    price: "$29",
    period: "/month",
    description: "Deep structured knowledge",
    features: [
      "10,000 Nodes",
      "4-Hop Reasoning",
      "Semantic Alias Engine",
      "Graph Snapshots",
      "API Access"
    ],
    cta: "Start Architect",
    popular: true,
    gradient: "from-cyan-500 to-blue-500",
  },
  {
    name: "Neural",
    price: "$99",
    period: "/month",
    description: "Elite intelligence synthesis",
    features: [
      "100,000 Nodes",
      "24-Hop Reasoning",
      "Cross-Graph Synthesis",
      "Real-time Evolution",
      "Priority Workers"
    ],
    cta: "Go Neural",
    popular: false,
    gradient: "from-purple-500 to-blue-500",
  },
  {
    name: "Matrix",
    price: "Custom",
    period: "",
    description: "Enterprise sovereign memory",
    features: [
      "Unlimited Nodes/Hops",
      "Private Memory Shards",
      "Dedicated GPU Workers",
      "SSO & 24/7 Support",
      "On-premise Option"
    ],
    cta: "Contact Sales",
    popular: false,
    gradient: "from-purple-600 to-pink-600",
  },
];

export default function Pricing() {
  return (
    <section id="pricing" className="py-24 px-4 bg-slate-950">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <span className="text-cyan-400 text-sm font-medium tracking-wide uppercase">
            Pricing
          </span>
          <h2 className="mt-4 text-4xl md:text-5xl font-bold text-white">
            Simple, Transparent Pricing
          </h2>
          <p className="mt-4 text-slate-400 max-w-2xl mx-auto">
            Start free and scale as your knowledge grows. No hidden fees.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          {plans.map((plan, index) => (
            <motion.div
              key={plan.name}
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.1 }}
              className={`relative rounded-2xl border ${
                plan.popular
                  ? "border-cyan-500/50 bg-gradient-to-b from-cyan-950/50 to-slate-900"
                  : "border-slate-800 bg-slate-900/50"
              } p-8`}
            >
              {/* Popular Badge */}
              {plan.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="px-4 py-1 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full text-white text-xs font-medium">
                    Most Popular
                  </span>
                </div>
              )}

              {/* Plan Header */}
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-white">
                  {plan.name}
                </h3>
                <div className="mt-2 flex items-baseline gap-1">
                  <span className="text-4xl font-bold text-white">
                    {plan.price}
                  </span>
                  <span className="text-slate-400 text-sm">{plan.period}</span>
                </div>
                <p className="mt-2 text-slate-400 text-sm">
                  {plan.description}
                </p>
              </div>

              {/* Features */}
              <ul className="space-y-3 mb-8">
                {plan.features.map((feature) => (
                  <li
                    key={feature}
                    className="flex items-start gap-3 text-sm text-slate-300"
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
                    {feature}
                  </li>
                ))}
              </ul>

              {/* CTA */}
              <Link
                href="/dashboard"
                className={`block w-full py-3 text-center rounded-xl font-medium transition-all duration-300 ${
                  plan.popular
                    ? "bg-gradient-to-r from-cyan-500 to-blue-500 text-white shadow-lg shadow-cyan-500/25 hover:shadow-cyan-500/40 hover:scale-105"
                    : "bg-slate-800 text-slate-200 hover:bg-slate-700"
                }`}
              >
                {plan.cta}
              </Link>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
