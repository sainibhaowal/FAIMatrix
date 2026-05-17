"use client";

import { motion } from "framer-motion";
import { useState } from "react";

type Tab = "ingest" | "query" | "evolve" | "keys";

interface CodeExample {
  id: Tab;
  label: string;
  language: string;
  code: string;
  description: string;
}

const CODE_EXAMPLES: CodeExample[] = [
  {
    id: "ingest",
    label: "Ingest Memory",
    language: "bash",
    code: `curl -X POST https://api.faimatrix.com/api/v1/memories \\
  -H "X-Tenant-Id: your-tenant" \\
  -H "X-API-Key: faim_sk_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "graph_id": "my-project",
    "content": "Kubernetes pods should not run as root...",
    "metadata": { "source": "security-docs" }
  }'

# Response:
# {
#   "node_id": "n_8f3a...",
#   "vector_hash": "sha256:a4c1e...",
#   "parents": [
#     { "id": "n_2b1c...", "fraction": 0.42 },
#     { "id": "n_9d4f...", "fraction": 0.31 },
#     { "id": "n_1a7e...", "fraction": 0.27 }
#   ],
#   "residual": 0.12,
#   "invariants_passed": 8
# }`,
    description:
      "Every ingest returns parent lineage, inheritance fractions, novelty residual, and invariant verification. Not just an ID.",
  },
  {
    id: "query",
    label: "Deep Query",
    language: "bash",
    code: `curl -X POST https://api.faimatrix.com/api/v1/query \\
  -H "X-Tenant-Id: your-tenant" \\
  -H "X-API-Key: faim_sk_..." \\
  -d '{
    "graph_id": "my-project",
    "query": "container security best practices",
    "hop_depth": 24,
    "explain": true
  }'
 
# Response includes 24-hop reasoning path:
# {
#   "answer": {
#     "direct_answer": "Pods should not run as root.",
#     "confidence": 0.83,
#     "reasoning_path": ["n_8f3a", "n_2b1c", "n_9d4f", "..."],
#     "citations": [{ "node_id": "n_8f3a..." }]
#   },
#   "intent": {
#     "classification": "BestPractices",
#     "confidence": 1.0,
#     "registry_match": "security-protocol-v2"
#   }
# }`,
    description:
      "Query returns deterministic ranking with 24-hop deep graph reasoning. The 1M+ Semantic Registry maps intent in <10ms, providing full explainability for every retrieval signal.",
  },
  {
    id: "evolve",
    label: "Evolve Graph",
    language: "bash",
    code: `curl -X POST https://api.faimatrix.com/api/v1/evolve \\
  -H "X-Tenant-Id: your-tenant" \\
  -H "X-API-Key: faim_sk_..." \\
  -d '{
    "graph_id": "my-project"
  }'

# Response:
# {
#   "merges": 3,
#   "prunes": 1,
#   "inventions": 1,
#   "diagnostics": {
#     "D_hat": 2.34,
#     "H_hat": 0.67,
#     "Lambda_hat": 0.52,
#     "energy": 1.41,
#     "redundancy": 0.18,
#     "novelty": 0.31
#   },
#   "graph_hash": "sha256:b7f2e...",
#   "invariants_passed": 8
# }`,
    description:
      "Trigger self-evolution. The graph merges redundancy, prunes dead nodes, self-invents macro concepts, and re-verifies all invariants.",
  },
  {
    id: "keys",
    label: "API Keys",
    language: "bash",
    code: `# Generate API key from dashboard or CLI
curl -X POST https://api.faimatrix.com/api/v1/keys \\
  -H "Authorization: Bearer your-jwt" \\
  -d '{
    "name": "production-app",
    "scopes": ["memories:write", "query:read", "evolve:write"]
  }'

# Use in any application:
# Python
from faimatrix import FAIMClient
client = FAIMClient(api_key="faim_sk_...")
result = client.query("my-project", "security policies")

# JavaScript / TypeScript
const faim = new FAIMClient({ apiKey: "faim_sk_..." });
const results = await faim.query("my-project", "security policies");

# Any HTTP client — it's a REST API
# Works with LangChain, LlamaIndex, or raw HTTP`,
    description:
      "Scoped API keys with granular permissions. Connect from Python, JavaScript, or any HTTP client. Works with any LLM framework.",
  },
];

export default function DeveloperAPI() {
  const [activeTab, setActiveTab] = useState<Tab>("ingest");
  const activeExample = CODE_EXAMPLES.find((e) => e.id === activeTab)!;

  return (
    <section
      id="api"
      className="py-28 px-4 bg-gradient-to-b from-[#070a18] to-slate-950"
    >
      <div className="max-w-6xl mx-auto">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <span className="text-blue-400 text-sm font-medium tracking-wider uppercase">
            Developer Experience
          </span>
          <h2 className="mt-4 text-4xl md:text-5xl font-bold text-white">
            One API.{" "}
            <span className="bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
              Infinite Power.
            </span>
          </h2>
          <p className="mt-4 text-slate-400 max-w-2xl mx-auto text-lg">
            Universal REST API. Generate API keys, connect from any application,
            and let FAIM power your memory with mathematical precision.
          </p>
        </motion.div>

        {/* Code Explorer */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.15 }}
          className="rounded-2xl border border-slate-800 bg-slate-900/50 overflow-hidden"
        >
          {/* Tabs */}
          <div className="flex border-b border-slate-800 overflow-x-auto">
            {CODE_EXAMPLES.map((example) => (
              <button
                key={example.id}
                onClick={() => setActiveTab(example.id)}
                className={`relative px-6 py-4 text-sm font-medium whitespace-nowrap transition-colors ${
                  activeTab === example.id
                    ? "text-cyan-400"
                    : "text-slate-500 hover:text-slate-300"
                }`}
              >
                {example.label}
                {activeTab === example.id && (
                  <motion.div
                    layoutId="api-tab-indicator"
                    className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-cyan-500 to-blue-500"
                    transition={{ duration: 0.25 }}
                  />
                )}
              </button>
            ))}
          </div>

          <div className="grid lg:grid-cols-5">
            {/* Code Block */}
            <div className="lg:col-span-3 p-6 border-r border-slate-800/50">
              <div className="rounded-lg bg-slate-950 border border-slate-800 p-5 overflow-x-auto">
                {/* Window dots */}
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-3 h-3 rounded-full bg-red-500/60" />
                  <div className="w-3 h-3 rounded-full bg-yellow-500/60" />
                  <div className="w-3 h-3 rounded-full bg-green-500/60" />
                  <span className="text-slate-600 text-[10px] font-mono ml-2">
                    {activeExample.language}
                  </span>
                </div>
                <pre className="text-xs md:text-sm font-mono text-slate-300 leading-relaxed whitespace-pre overflow-x-auto">
                  {activeExample.code}
                </pre>
              </div>
            </div>

            {/* Description */}
            <div className="lg:col-span-2 p-6 flex flex-col justify-center">
              <h3 className="text-lg font-bold text-white mb-3">
                {activeExample.label}
              </h3>
              <p className="text-slate-400 text-sm leading-relaxed">
                {activeExample.description}
              </p>

              {/* Feature highlights */}
              <div className="mt-6 space-y-3">
                {activeTab === "ingest" && (
                  <>
                    <Highlight text="Parent lineage returned on every write" />
                    <Highlight text="SHA-256 vector hash for verification" />
                    <Highlight text="8 invariants checked per operation" />
                  </>
                )}
                {activeTab === "query" && (
                  <>
                    <Highlight text="24-hop deep graph reasoning path" />
                    <Highlight text="1M+ Semantic Registry intent classification" />
                    <Highlight text="Deterministic ranking with full explainability" />
                  </>
                )}
                {activeTab === "evolve" && (
                  <>
                    <Highlight text="Autonomous merge, prune, self-invent" />
                    <Highlight text="Fractal diagnostics in response" />
                    <Highlight text="Graph hash for state verification" />
                  </>
                )}
                {activeTab === "keys" && (
                  <>
                    <Highlight text="Scoped permissions per key" />
                    <Highlight text="Works with any HTTP client" />
                    <Highlight text="Multi-tenant isolation built in" />
                  </>
                )}
              </div>
            </div>
          </div>
        </motion.div>

        {/* Integration badges */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="mt-10 flex flex-wrap items-center justify-center gap-4"
        >
          {[
            "REST API",
            "Python SDK",
            "TypeScript SDK",
            "LangChain",
            "LlamaIndex",
            "Any LLM",
          ].map((badge) => (
            <span
              key={badge}
              className="px-4 py-2 rounded-full border border-slate-800 bg-slate-900/30 text-slate-500 text-xs font-medium"
            >
              {badge}
            </span>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

function Highlight({ text }: { text: string }) {
  return (
    <div className="flex items-center gap-2.5 text-sm text-slate-500">
      <svg
        className="w-4 h-4 text-cyan-500 shrink-0"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2}
      >
        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
      </svg>
      {text}
    </div>
  );
}
