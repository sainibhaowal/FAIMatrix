"use client";

import { motion } from "framer-motion";
import { useState } from "react";

const KEY_LIFECYCLE = [
  {
    step: "Create",
    icon: (
      <svg
        viewBox="0 0 24 24"
        className="w-5 h-5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z"
        />
      </svg>
    ),
    description: "Generate scoped key with Argon2id hashing",
    detail: "Plaintext shown once. Never stored. Only hash kept in DB.",
    color: "cyan",
  },
  {
    step: "Authenticate",
    icon: (
      <svg
        viewBox="0 0 24 24"
        className="w-5 h-5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"
        />
      </svg>
    ),
    description: "Middleware validates key + tenant + scopes per request",
    detail: "AuthDecision: valid, method, key_id, scopes, reason.",
    color: "emerald",
  },
  {
    step: "Authorize",
    icon: (
      <svg
        viewBox="0 0 24 24"
        className="w-5 h-5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z"
        />
      </svg>
    ),
    description: 'Route-level scope check: require_scopes(["memory.write"])',
    detail: "Missing scope \u2192 403 + audit event. No silent failures.",
    color: "purple",
  },
  {
    step: "Audit",
    icon: (
      <svg
        viewBox="0 0 24 24"
        className="w-5 h-5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
        />
      </svg>
    ),
    description: "Every key action logged to append-only audit trail",
    detail: "used, denied(scope), denied(expired), denied(revoked).",
    color: "amber",
  },
];

const SCOPES = [
  { name: "keys.read", desc: "List own API keys", level: "basic" },
  { name: "keys.write", desc: "Create, rotate, revoke keys", level: "admin" },
  { name: "memory.read", desc: "Query memories from graph", level: "basic" },
  { name: "memory.write", desc: "Ingest memories to graph", level: "standard" },
  {
    name: "memory.admin",
    desc: "Evolve, prune, admin operations",
    level: "admin",
  },
];

const SECURITY_LAYERS = [
  {
    name: "Tenant Isolation",
    desc: "Mandatory tenant_id scoping across every DB query",
    icon: "\uD83D\uDD12",
  },
  {
    name: "JWT + API Key",
    desc: "Dual auth: session tokens or scoped API keys",
    icon: "\uD83D\uDDDD\uFE0F",
  },
  {
    name: "Rate Limiting",
    desc: "Per-tenant, per-route rate limits enforced",
    icon: "\u26A1",
  },
  {
    name: "Security Headers",
    desc: "HSTS, CSP, X-Frame-Options, X-Content-Type",
    icon: "\uD83D\uDEE1\uFE0F",
  },
  {
    name: "Request Tracing",
    desc: "Every request gets a unique X-Request-Id",
    icon: "\uD83D\uDD0D",
  },
  {
    name: "CORS Policy",
    desc: "Strict origin whitelist, no wildcard",
    icon: "\uD83C\uDF10",
  },
];

const colorMap: Record<string, { bg: string; text: string; border: string }> = {
  cyan: {
    bg: "bg-cyan-500/10",
    text: "text-cyan-400",
    border: "border-cyan-500/30",
  },
  emerald: {
    bg: "bg-emerald-500/10",
    text: "text-emerald-400",
    border: "border-emerald-500/30",
  },
  purple: {
    bg: "bg-purple-500/10",
    text: "text-purple-400",
    border: "border-purple-500/30",
  },
  amber: {
    bg: "bg-amber-500/10",
    text: "text-amber-400",
    border: "border-amber-500/30",
  },
};

export default function SecurityKeys() {
  const [activeScope, setActiveScope] = useState<string | null>(null);

  return (
    <section
      id="security"
      className="py-28 px-4 bg-slate-950 relative overflow-hidden"
    >
      <div className="absolute inset-0 faim-grid" />

      <div className="max-w-6xl mx-auto relative">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-20"
        >
          <span className="text-emerald-400 text-sm font-medium tracking-wider uppercase">
            Security & API Keys
          </span>
          <h2 className="mt-4 text-4xl md:text-5xl font-bold text-white">
            Enterprise Security.{" "}
            <span className="bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
              Every Layer.
            </span>
          </h2>
          <p className="mt-4 text-slate-400 max-w-2xl mx-auto">
            Scoped API keys with Argon2id hashing, complete audit trail,
            multi-tenant isolation, and 6 middleware security layers.
          </p>
        </motion.div>

        {/* Key Lifecycle Flow */}
        <div className="grid md:grid-cols-4 gap-4 mb-16">
          {KEY_LIFECYCLE.map((item, i) => {
            const c = colorMap[item.color];
            return (
              <motion.div
                key={item.step}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.1 }}
                className={`relative p-6 rounded-xl border ${c.border} ${c.bg}`}
              >
                {/* Step number */}
                <span className="text-slate-600 text-[10px] font-mono font-bold absolute top-3 right-3">
                  {String(i + 1).padStart(2, "0")}
                </span>

                <div
                  className={`inline-flex p-2 rounded-lg ${c.bg} ${c.text} mb-3`}
                >
                  {item.icon}
                </div>
                <h3 className="text-white font-bold text-sm mb-1">
                  {item.step}
                </h3>
                <p className="text-slate-400 text-xs mb-2">
                  {item.description}
                </p>
                <p className="text-slate-600 text-[11px] font-mono">
                  {item.detail}
                </p>

                {/* Connector arrow */}
                {i < KEY_LIFECYCLE.length - 1 && (
                  <div className="absolute -right-2.5 top-1/2 -translate-y-1/2 text-slate-700 hidden md:block z-10">
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M9 5l7 7-7 7"
                      />
                    </svg>
                  </div>
                )}
              </motion.div>
            );
          })}
        </div>

        <div className="grid lg:grid-cols-2 gap-8">
          {/* Scopes */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="p-8 rounded-2xl border border-slate-800 bg-slate-900/30"
          >
            <h3 className="text-lg font-bold text-white mb-6">
              Granular Scopes
            </h3>

            <div className="space-y-3">
              {SCOPES.map((scope) => (
                <div
                  key={scope.name}
                  onMouseEnter={() => setActiveScope(scope.name)}
                  onMouseLeave={() => setActiveScope(null)}
                  className={`flex items-center justify-between p-3 rounded-lg border transition-all duration-200 ${
                    activeScope === scope.name
                      ? "border-cyan-500/30 bg-cyan-500/[0.04]"
                      : "border-slate-800/50 bg-slate-900/20"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <code className="text-cyan-400 text-xs font-mono bg-slate-800/60 px-2 py-1 rounded">
                      {scope.name}
                    </code>
                    <span className="text-slate-400 text-sm">{scope.desc}</span>
                  </div>
                  <span
                    className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${
                      scope.level === "admin"
                        ? "text-amber-400 bg-amber-500/10"
                        : scope.level === "standard"
                          ? "text-blue-400 bg-blue-500/10"
                          : "text-slate-500 bg-slate-800/50"
                    }`}
                  >
                    {scope.level}
                  </span>
                </div>
              ))}
            </div>

            <p className="text-slate-600 text-xs mt-4 font-mono">
              Source: api/routers/api_keys.py, api/deps.py
            </p>
          </motion.div>

          {/* Security Middleware Stack */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="p-8 rounded-2xl border border-slate-800 bg-slate-900/30"
          >
            <h3 className="text-lg font-bold text-white mb-6">
              6-Layer Middleware Stack
            </h3>

            <div className="space-y-3">
              {SECURITY_LAYERS.map((layer, i) => (
                <motion.div
                  key={layer.name}
                  initial={{ opacity: 0, x: 10 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.3, delay: i * 0.06 }}
                  className="flex items-start gap-3 p-3 rounded-lg border border-slate-800/30 hover:border-slate-700/50 hover:bg-slate-900/40 transition-all"
                >
                  <span className="text-lg mt-0.5">{layer.icon}</span>
                  <div>
                    <p className="text-white text-sm font-medium">
                      {layer.name}
                    </p>
                    <p className="text-slate-500 text-xs">{layer.desc}</p>
                  </div>
                </motion.div>
              ))}
            </div>

            <div className="mt-6 p-4 rounded-lg bg-slate-950 border border-slate-800">
              <p className="text-[10px] text-slate-600 font-mono uppercase tracking-wider mb-2">
                Middleware Order
              </p>
              <p className="text-xs font-mono text-slate-400">
                SecurityHeaders \u2192 JWT \u2192 TenantAuth \u2192 RateLimit
                \u2192 RequestId \u2192 CORS
              </p>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
