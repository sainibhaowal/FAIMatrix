"use client";

import { motion } from "framer-motion";
import {
  ArrowUpRight,
  BookOpenCheck,
  Check,
  CircleDashed,
  ExternalLink,
  Minus,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";

type CapabilityStatus = "native" | "optional" | "partial" | "compose" | "na";

type Capability = {
  status: CapabilityStatus;
  text: string;
};

type System = {
  key: string;
  name: string;
  kind: string;
  href: string;
  source: string;
  summary: string;
};

const SYSTEMS: System[] = [
  {
    key: "faim",
    name: "FAIM",
    kind: "Memory + retrieval engine",
    href: "https://github.com/sainibhaowal/FAIMatrix",
    source: "FAIM source",
    summary:
      "Graph-native memory with a deterministic core and optional model adapters.",
  },
  {
    key: "pgvector",
    name: "pgvector",
    kind: "PostgreSQL extension",
    href: "https://github.com/pgvector/pgvector",
    source: "pgvector docs",
    summary:
      "Vector types and exact or approximate nearest-neighbor search inside Postgres.",
  },
  {
    key: "qdrant",
    name: "Qdrant",
    kind: "Vector database",
    href: "https://qdrant.tech/documentation/search/hybrid-queries/",
    source: "Qdrant docs",
    summary:
      "Dense, sparse, multivector, filtering, and staged retrieval primitives.",
  },
  {
    key: "weaviate",
    name: "Weaviate",
    kind: "Vector database",
    href: "https://docs.weaviate.io/weaviate/search/hybrid",
    source: "Weaviate docs",
    summary:
      "Vector-first objects with keyword, vector, hybrid search, and filters.",
  },
  {
    key: "pinecone",
    name: "Pinecone",
    kind: "Managed vector database",
    href: "https://docs.pinecone.io/guides/search/hybrid-search",
    source: "Pinecone docs",
    summary:
      "Managed vector retrieval with dense/sparse hybrid patterns and metadata filters.",
  },
  {
    key: "milvus",
    name: "Milvus",
    kind: "Vector database",
    href: "https://milvus.io/docs/hybrid_search_with_milvus.md",
    source: "Milvus docs",
    summary:
      "Distributed vector search with dense, sparse, hybrid, and multi-vector APIs.",
  },
  {
    key: "elastic",
    name: "Elasticsearch",
    kind: "Search engine",
    href: "https://www.elastic.co/docs/solutions/search/hybrid-search",
    source: "Elastic docs",
    summary:
      "Full-text BM25 and vector retrieval with declarative hybrid rank fusion.",
  },
  {
    key: "chroma",
    name: "Chroma",
    kind: "AI data infrastructure",
    href: "https://docs.trychroma.com/docs/overview/introduction",
    source: "Chroma docs",
    summary:
      "Embeddings, metadata, dense/sparse/hybrid search, and multimodal retrieval.",
  },
  {
    key: "graphiti",
    name: "Graphiti / Zep",
    kind: "Temporal context graph",
    href: "https://help.getzep.com/graphiti/getting-started/welcome",
    source: "Graphiti docs",
    summary:
      "Incremental temporal graphs combining semantic, keyword, and graph retrieval.",
  },
  {
    key: "mem0",
    name: "Mem0",
    kind: "LLM memory layer",
    href: "https://docs.mem0.ai/platform/features/graph-memory",
    source: "Mem0 docs",
    summary:
      "Scoped long-term memory with automatic entity linking and retrieval boosts.",
  },
  {
    key: "letta",
    name: "Letta",
    kind: "Stateful agent runtime",
    href: "https://docs.letta.com/",
    source: "Letta docs",
    summary: "Stateful agents with editable memory blocks and archival memory.",
  },
  {
    key: "langgraph",
    name: "LangGraph",
    kind: "Agent workflow runtime",
    href: "https://docs.langchain.com/oss/python/langgraph/persistence",
    source: "LangGraph docs",
    summary:
      "Checkpointed graph execution, durable state, interrupts, and time travel.",
  },
];

const cap = (status: CapabilityStatus, text: string): Capability => ({
  status,
  text,
});

const ROWS: Array<{
  label: string;
  detail: string;
  values: Record<string, Capability>;
}> = [
  {
    label: "Primary role",
    detail: "What the system is designed to be",
    values: {
      faim: cap("native", "Memory + retrieval engine"),
      pgvector: cap("native", "Postgres vector extension"),
      qdrant: cap("native", "Vector database"),
      weaviate: cap("native", "Vector database"),
      pinecone: cap("native", "Managed vector database"),
      milvus: cap("native", "Vector database"),
      elastic: cap("native", "Search engine"),
      chroma: cap("native", "AI data infrastructure"),
      graphiti: cap("native", "Temporal context graph"),
      mem0: cap("native", "LLM memory layer"),
      letta: cap("native", "Stateful agent runtime"),
      langgraph: cap("native", "Agent workflow runtime"),
    },
  },
  {
    label: "Dense vector search",
    detail: "Similarity search over embeddings",
    values: {
      faim: cap("native", "Native shortlist + optional Qdrant"),
      pgvector: cap("native", "Exact, HNSW, IVFFlat"),
      qdrant: cap("native", "HNSW"),
      weaviate: cap("native", "HNSW, flat, dynamic"),
      pinecone: cap("native", "Managed dense indexes"),
      milvus: cap("native", "HNSW, IVF, FLAT, DiskANN"),
      elastic: cap("native", "Dense vector kNN"),
      chroma: cap("native", "HNSW / SPANN by deployment"),
      graphiti: cap("optional", "Vector component in hybrid retrieval"),
      mem0: cap("native", "Embedding-backed memory search"),
      letta: cap("optional", "Provider-backed archival search"),
      langgraph: cap("compose", "Add a checkpointer or store"),
    },
  },
  {
    label: "Lexical + hybrid retrieval",
    detail: "Exact terms combined with semantic signals",
    values: {
      faim: cap("native", "Sparse, dense, aliases, graph signals"),
      pgvector: cap("compose", "Postgres full-text + vector SQL"),
      qdrant: cap("native", "Sparse/dense fusion + multistage"),
      weaviate: cap("native", "BM25F + vector fusion"),
      pinecone: cap("native", "Dense/sparse hybrid patterns"),
      milvus: cap("native", "Dense/sparse hybrid search"),
      elastic: cap("native", "BM25 + vector + RRF"),
      chroma: cap("native", "Dense, sparse, full-text"),
      graphiti: cap("native", "Semantic + keyword + graph"),
      mem0: cap("native", "Semantic + keyword + graph boost"),
      letta: cap("compose", "Application/provider dependent"),
      langgraph: cap("compose", "Bring your retrievers"),
    },
  },
  {
    label: "Graph traversal",
    detail: "Relationships, hops, and typed connections",
    values: {
      faim: cap("native", "Typed graph + bounded diffusion"),
      pgvector: cap("compose", "Use relational tables or a graph"),
      qdrant: cap("na", "Not a knowledge-graph layer"),
      weaviate: cap("partial", "References; retrieval logic is app-defined"),
      pinecone: cap("na", "Not a graph layer"),
      milvus: cap("na", "Not a knowledge-graph layer"),
      elastic: cap("partial", "Relations require application modeling"),
      chroma: cap("na", "Not a graph layer"),
      graphiti: cap("native", "Entity and fact graph traversal"),
      mem0: cap("partial", "Entity links; typed relations vary by product"),
      letta: cap("na", "Not a graph retrieval layer"),
      langgraph: cap("partial", "Execution graph, not memory graph"),
    },
  },
  {
    label: "Temporal truth",
    detail: "Valid-time history and changing facts",
    values: {
      faim: cap(
        "partial",
        "Validity fields + contradiction handling; full solver path not claimed",
      ),
      pgvector: cap("compose", "Model timestamps and history in SQL"),
      qdrant: cap("compose", "Payload timestamps; app owns semantics"),
      weaviate: cap("compose", "Properties and filters; app owns semantics"),
      pinecone: cap("compose", "Metadata timestamps; app owns semantics"),
      milvus: cap("compose", "Scalar fields; app owns semantics"),
      elastic: cap("partial", "Time fields and historical documents"),
      chroma: cap("compose", "Metadata; app owns semantics"),
      graphiti: cap("native", "Temporal edges and invalidation"),
      mem0: cap(
        "partial",
        "Extracted time context; not a formal valid-time model",
      ),
      letta: cap("partial", "State history, not temporal fact reasoning"),
      langgraph: cap("native", "Checkpoint history and replay"),
    },
  },
  {
    label: "Evidence + provenance",
    detail: "Source anchors, citations, and audit context",
    values: {
      faim: cap("native", "Raw refs, evidence blocks, reason ledger"),
      pgvector: cap("compose", "Store source fields yourself"),
      qdrant: cap("partial", "Payloads; citation policy is app-defined"),
      weaviate: cap(
        "partial",
        "Object properties; citation policy is app-defined",
      ),
      pinecone: cap("partial", "Metadata; citation policy is app-defined"),
      milvus: cap("partial", "Scalar fields; citation policy is app-defined"),
      elastic: cap("partial", "Stored fields and query explanations"),
      chroma: cap("partial", "Documents and metadata"),
      graphiti: cap("native", "Episodes and graph facts"),
      mem0: cap("partial", "Memory records and metadata"),
      letta: cap("partial", "Agent state and archival records"),
      langgraph: cap("native", "Checkpoint metadata and state history"),
    },
  },
  {
    label: "Memory lifecycle",
    detail: "Review, update, merge, prune, and restore",
    values: {
      faim: cap("native", "Guarded proposals, backups, evolution controls"),
      pgvector: cap("compose", "Transactions and application jobs"),
      qdrant: cap("partial", "CRUD, snapshots, and payload updates"),
      weaviate: cap("partial", "CRUD and data management"),
      pinecone: cap("partial", "Upsert/delete; application governs policy"),
      milvus: cap(
        "partial",
        "Insert/delete/partitions; application governs policy",
      ),
      elastic: cap("partial", "Index lifecycle; application governs policy"),
      chroma: cap("partial", "Collection CRUD; application governs policy"),
      graphiti: cap("native", "Incremental graph updates and invalidation"),
      mem0: cap("native", "Memory add/update/delete pipeline"),
      letta: cap("native", "Editable memory blocks + archival memory"),
      langgraph: cap("native", "Checkpoint, resume, fork, replay"),
    },
  },
  {
    label: "Tenant isolation",
    detail: "How isolation is expressed, not a security guarantee by itself",
    values: {
      faim: cap("native", "API-key, tenant scope, encrypted raw storage"),
      pgvector: cap("compose", "SQL policies/roles are application-owned"),
      qdrant: cap("native", "Payload filters, tenant indexing, sharding"),
      weaviate: cap("native", "Collection/tenant primitives"),
      pinecone: cap("native", "Namespaces and metadata filters"),
      milvus: cap("partial", "Databases, collections, partitions, filters"),
      elastic: cap("partial", "Security and filtered indices"),
      chroma: cap("partial", "Collections and deployment controls"),
      graphiti: cap("partial", "Graph/group scoping is application-defined"),
      mem0: cap("native", "User/agent/app/run scopes"),
      letta: cap("native", "Agent-scoped state"),
      langgraph: cap("native", "Thread and namespace scopes"),
    },
  },
  {
    label: "Documents + OCR",
    detail: "File perception before memory write",
    values: {
      faim: cap("native", "PDF/DOCX/XLSX/PPTX + bounded OCR"),
      pgvector: cap("compose", "Bring an ingestion pipeline"),
      qdrant: cap("compose", "Bring an ingestion pipeline"),
      weaviate: cap("compose", "Bring modules or an ingestion pipeline"),
      pinecone: cap("compose", "Bring an ingestion pipeline"),
      milvus: cap("compose", "Bring an ingestion pipeline"),
      elastic: cap("partial", "Ingest pipelines; OCR is an integration"),
      chroma: cap("partial", "Documents supported; OCR is an integration"),
      graphiti: cap("compose", "Episodes are supplied by the application"),
      mem0: cap("compose", "Memory payloads are supplied by the application"),
      letta: cap("compose", "Files and tools are integrations"),
      langgraph: cap("compose", "Nodes/tools define ingestion"),
    },
  },
  {
    label: "LLM dependency",
    detail: "Whether an LLM is required for the core data path",
    values: {
      faim: cap("optional", "Optional at the application/Cortex boundary"),
      pgvector: cap("na", "No LLM in the extension"),
      qdrant: cap("na", "No LLM in the database"),
      weaviate: cap("optional", "Model integrations are optional"),
      pinecone: cap("na", "No LLM in the vector index"),
      milvus: cap("na", "No LLM in the vector engine"),
      elastic: cap("optional", "Semantic workflows can add models"),
      chroma: cap("optional", "Embedding provider is configurable"),
      graphiti: cap("native", "LLM extraction is part of the graph workflow"),
      mem0: cap("native", "LLM-driven memory extraction"),
      letta: cap("native", "Agent runtime is model-led"),
      langgraph: cap("optional", "Model calls are workflow nodes"),
    },
  },
  {
    label: "Replay / determinism",
    detail: "Reproducible behavior under the same inputs and dependencies",
    values: {
      faim: cap(
        "partial",
        "Core math is deterministic; model/OCR outputs are not promised",
      ),
      pgvector: cap(
        "partial",
        "Exact scans can be repeatable; ANN is approximate",
      ),
      qdrant: cap("partial", "HNSW is approximate; query settings matter"),
      weaviate: cap("partial", "ANN search is approximate; settings matter"),
      pinecone: cap("partial", "Managed index behavior is service-dependent"),
      milvus: cap("partial", "Index and consistency settings matter"),
      elastic: cap("partial", "Query replay is possible; ANN is approximate"),
      chroma: cap("partial", "ANN configuration affects results"),
      graphiti: cap("partial", "Incremental extraction depends on model calls"),
      mem0: cap("partial", "Memory extraction and ranking depend on providers"),
      letta: cap(
        "partial",
        "Checkpoint state is replayable; model calls can vary",
      ),
      langgraph: cap(
        "native",
        "Checkpoint replay/fork; downstream calls can vary",
      ),
    },
  },
];

const STATUS_META: Record<
  CapabilityStatus,
  { label: string; className: string; Icon: LucideIcon }
> = {
  native: {
    label: "Native",
    className: "border-cyan-400/30 bg-cyan-400/10 text-cyan-200",
    Icon: Check,
  },
  optional: {
    label: "Optional",
    className: "border-violet-400/30 bg-violet-400/10 text-violet-200",
    Icon: CircleDashed,
  },
  partial: {
    label: "Partial",
    className: "border-amber-400/30 bg-amber-400/10 text-amber-200",
    Icon: CircleDashed,
  },
  compose: {
    label: "Compose",
    className: "border-slate-600 bg-slate-800/60 text-slate-300",
    Icon: ArrowUpRight,
  },
  na: {
    label: "Not primary",
    className: "border-slate-800 bg-slate-900/60 text-slate-600",
    Icon: Minus,
  },
};

const SIGNAL_TONE = {
  cyan: "border-cyan-400/20 bg-cyan-400/10 text-cyan-300",
  violet: "border-violet-400/20 bg-violet-400/10 text-violet-300",
  amber: "border-amber-400/20 bg-amber-400/10 text-amber-300",
} as const;

function StatusBadge({ status }: { status: CapabilityStatus }) {
  const meta = STATUS_META[status];
  const Icon = meta.Icon;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[9px] font-semibold uppercase tracking-[0.12em] ${meta.className}`}
    >
      <Icon className="h-2.5 w-2.5" aria-hidden="true" />
      {meta.label}
    </span>
  );
}

function SourceLink({ system }: { system: System }) {
  return (
    <a
      href={system.href}
      target="_blank"
      rel="noreferrer"
      className="group/link inline-flex items-center gap-1 text-[10px] text-slate-500 transition-colors hover:text-cyan-300"
    >
      {system.source}
      <ExternalLink
        className="h-2.5 w-2.5 opacity-60 transition-transform group-hover/link:-translate-y-0.5 group-hover/link:translate-x-0.5"
        aria-hidden="true"
      />
    </a>
  );
}

export default function RAGComparison() {
  return (
    <section
      id="comparison"
      className="relative overflow-hidden bg-[#050814] px-4 py-20 sm:px-6 lg:py-28"
    >
      <div className="absolute inset-0 faim-grid opacity-20" />
      <div className="relative mx-auto max-w-[1500px]">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mx-auto max-w-4xl text-center"
        >
          <span className="inline-flex items-center gap-2 rounded-full border border-cyan-400/25 bg-cyan-400/5 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-cyan-300">
            <BookOpenCheck className="h-3.5 w-3.5" aria-hidden="true" />
            Evidence-led comparison
          </span>
          <h2 className="mt-6 text-3xl font-bold tracking-tight text-white sm:text-4xl lg:text-5xl">
            FAIM in context: a memory engine, not just a vector index
          </h2>
          <p className="mx-auto mt-5 max-w-3xl text-base leading-7 text-slate-400 sm:text-lg">
            FAIM combines a deterministic, inspectable core with model-assisted
            perception and optional Cortex integrations. The useful comparison
            is architectural: which capabilities are built in, which are
            partial, and which must be composed by your application.
          </p>
        </motion.div>

        <div className="mt-10 grid gap-4 md:grid-cols-3">
          {[
            {
              title: "What FAIM has today",
              text: "Graph-aware retrieval, durable Postgres state, optional Qdrant acceleration, evidence links, tenant-scoped APIs, bounded OCR, and guarded evolution paths.",
              icon: ShieldCheck,
              tone: "cyan",
            },
            {
              title: "What deterministic means here",
              text: "The core math, routing, scoring, and storage contracts are designed for repeatability with the same inputs. External LLM and OCR calls can still vary.",
              icon: CircleDashed,
              tone: "violet",
            },
            {
              title: "What this page does not claim",
              text: "No universal winner, speed ranking, or accuracy percentage. Those require the same corpus, queries, models, hardware, and evaluation harness for every system.",
              icon: BookOpenCheck,
              tone: "amber",
            },
          ].map((item) => {
            const Icon = item.icon;
            return (
              <div
                key={item.title}
                className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5"
              >
                <div
                  className={`mb-3 flex h-9 w-9 items-center justify-center rounded-xl border ${SIGNAL_TONE[item.tone as keyof typeof SIGNAL_TONE]}`}
                >
                  <Icon className="h-4 w-4" aria-hidden="true" />
                </div>
                <h3 className="text-sm font-semibold text-white">
                  {item.title}
                </h3>
                <p className="mt-2 text-xs leading-5 text-slate-400">
                  {item.text}
                </p>
              </div>
            );
          })}
        </div>

        <div className="mt-10 overflow-hidden rounded-2xl border border-slate-800 bg-slate-950/70 shadow-2xl shadow-cyan-950/10">
          <div className="flex flex-col gap-4 border-b border-slate-800 bg-slate-900/60 px-5 py-5 sm:flex-row sm:items-end sm:justify-between sm:px-6">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-cyan-400">
                Representative systems
              </p>
              <h3 className="mt-2 text-xl font-semibold text-white sm:text-2xl">
                Capability matrix — side by side
              </h3>
              <p className="mt-2 max-w-3xl text-xs leading-5 text-slate-400">
                This is intentionally broad, not exhaustive. It includes vector
                databases, search engines, temporal/context graphs, memory
                layers, and agent runtimes because they solve different parts of
                the memory problem.
              </p>
            </div>
            <div className="flex flex-wrap gap-2 text-[10px] text-slate-500">
              {(Object.keys(STATUS_META) as CapabilityStatus[]).map(
                (status) => (
                  <StatusBadge key={status} status={status} />
                ),
              )}
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-[2240px] w-full table-fixed border-collapse text-left">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/80">
                  <th className="sticky left-0 z-20 w-[230px] min-w-[230px] border-r border-slate-800 bg-slate-900/95 px-5 py-4 align-top text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500 backdrop-blur">
                    Capability
                  </th>
                  {SYSTEMS.map((system) => (
                    <th
                      key={system.key}
                      className={`w-[170px] min-w-[170px] px-4 py-4 align-top ${system.key === "faim" ? "bg-cyan-400/[0.06]" : ""}`}
                    >
                      <div
                        className={`text-sm font-semibold ${system.key === "faim" ? "text-cyan-200" : "text-slate-200"}`}
                      >
                        {system.name}
                      </div>
                      <div
                        title={system.summary}
                        className="mt-1 min-h-8 text-[10px] font-normal leading-4 text-slate-500"
                      >
                        {system.kind}
                      </div>
                      <SourceLink system={system} />
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {ROWS.map((row) => (
                  <tr
                    key={row.label}
                    className="border-b border-slate-800/70 last:border-b-0"
                  >
                    <th className="sticky left-0 z-10 border-r border-slate-800 bg-slate-950/95 px-5 py-5 align-top backdrop-blur">
                      <div className="text-xs font-semibold text-slate-200">
                        {row.label}
                      </div>
                      <div className="mt-1 text-[10px] font-normal leading-4 text-slate-600">
                        {row.detail}
                      </div>
                    </th>
                    {SYSTEMS.map((system) => {
                      const value = row.values[system.key];
                      return (
                        <td
                          key={system.key}
                          className={`px-4 py-5 align-top ${system.key === "faim" ? "bg-cyan-400/[0.035]" : ""}`}
                        >
                          <StatusBadge status={value.status} />
                          <p
                            className={`mt-2 text-[11px] leading-5 ${system.key === "faim" ? "text-cyan-100/90" : "text-slate-400"}`}
                          >
                            {value.text}
                          </p>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex flex-col gap-2 border-t border-slate-800 bg-slate-900/40 px-5 py-4 text-[10px] leading-5 text-slate-500 sm:flex-row sm:items-center sm:justify-between sm:px-6">
            <span>
              Rows describe documented capability shape, not a benchmark score.
              “Compose” means application code or another service is required.
            </span>
            <span className="font-mono text-slate-600">
              {SYSTEMS.length} systems · {ROWS.length} dimensions · sources
              linked
            </span>
          </div>
        </div>

        <div className="mt-10 grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-2xl border border-cyan-400/20 bg-cyan-400/[0.04] p-6">
            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-cyan-300">
              How to read the FAIM column
            </p>
            <h3 className="mt-3 text-xl font-semibold text-white">
              A composed system with a clear boundary
            </h3>
            <p className="mt-3 text-sm leading-6 text-slate-400">
              FAIM is not claiming to replace every database, search engine,
              memory layer, or agent framework. Its boundary is the memory
              substrate: durable graph state, retrieval signals, evidence,
              tenant controls, and guarded lifecycle operations. An LLM can sit
              above that boundary, but it is not the source of memory truth.
            </p>
            <div className="mt-5 flex flex-wrap gap-2">
              {[
                "Graph-native state",
                "Evidence-first answers",
                "Tenant-scoped APIs",
                "Optional Qdrant",
                "Guarded evolution",
              ].map((item) => (
                <span
                  key={item}
                  className="rounded-full border border-cyan-400/20 bg-slate-950/40 px-3 py-1.5 text-[10px] font-medium text-cyan-100/80"
                >
                  {item}
                </span>
              ))}
            </div>
          </div>
          <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6">
            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">
              Benchmark responsibly
            </p>
            <h3 className="mt-3 text-xl font-semibold text-white">
              The next honest comparison is empirical
            </h3>
            <p className="mt-3 text-sm leading-6 text-slate-400">
              To publish recall, latency, cost, or answer-quality claims, run
              the same corpus and question set through each system, pin model
              and index settings, record hardware and version, and publish the
              raw harness and failures. Until that exists, this page stays
              descriptive.
            </p>
            <a
              href="/benchmarks"
              className="mt-5 inline-flex items-center gap-2 text-xs font-semibold text-cyan-300 transition-colors hover:text-cyan-200"
            >
              See the FAIM benchmark surface{" "}
              <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
            </a>
          </div>
        </div>

        <p className="mt-8 text-center text-[10px] leading-5 text-slate-600">
          Sources are first-party documentation links captured for this page.
          Product capabilities change; re-run the comparison review before using
          it as a procurement or performance decision.
        </p>
      </div>
    </section>
  );
}
