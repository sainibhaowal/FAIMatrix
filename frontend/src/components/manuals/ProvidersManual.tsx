"use client";

import React from "react";
import {
  ManualShell,
  SectionHeading,
  SubHeading,
  Callout,
  DTable,
  type TocItem,
} from "@/components/manuals/ManualShell";

const TOC: TocItem[] = [
  { id: "overview", label: "1. Introduction" },
  { id: "tabs", label: "2. Provider Tabs", children: [{ id: "nav-tab", label: "Navigator" }, { id: "llm-tab", label: "LLM" }, { id: "embedding-tab", label: "Embedding" }, { id: "reranker-tab", label: "Reranker" }, { id: "ocr-tab", label: "OCR" }] },
  { id: "add", label: "3. Adding a Provider", children: [{ id: "add-llm", label: "LLM Provider" }, { id: "add-emb", label: "Embedding Provider" }, { id: "add-rerank", label: "Reranker" }, { id: "add-ocr", label: "OCR Config" }] },
  { id: "config", label: "4. Provider Configuration" },
  { id: "selection", label: "5. Downstream Selection" },
  { id: "security", label: "6. Security & Tenant Isolation" },
  { id: "troubleshoot", label: "7. Troubleshooting" },
];

export function ProvidersManual({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <ManualShell
      open={open}
      onClose={onClose}
      title="FAIM Providers — User Manual"
      subtitle="Foundation Models & Runtime Connectivity"
      toc={TOC}
    >
      <SectionHeading id="overview" kicker="Chapter 01" title="Introduction">
        <p>
          The Providers page is the central control plane for every external
          AI/ML service FAIM talks to — LLM chat models, embedding encoders,
          rerankers, and OCR engines. Each provider is added once, then
          selected in downstream workflows (Cortex chat, ingest pipelines,
          search) with tenant-scoped credentials.
        </p>
      </SectionHeading>

      <SectionHeading id="tabs" kicker="Chapter 02" title="Provider Tabs">
        <p>
          The page is organized into six tabs. Switch tabs via the header
          selector; the URL carries <span className="font-mono text-cyan-300">?tab=</span>.
        </p>
        <SubHeading id="nav-tab">Navigator</SubHeading>
        <p>Overview dashboard showing all active provider families at a glance.</p>
        <SubHeading id="llm-tab">LLM</SubHeading>
        <p>
          Chat/completion models. Built-in families: OpenAI, Anthropic,
          Google, OpenRouter, Groq, OpenAI-Compatible, LM Studio, Ollama,
          OpenCode Zen. Each family lists known models; you add a provider by
          picking a family and pasting your API key / endpoint.
        </p>
        <SubHeading id="embedding-tab">Embedding</SubHeading>
        <p>
          Vector encoders. Built-in: FAIM Native (BAAI/bge-small-en-v1.5,
          BAAI/bge-m3) and OpenAI Embeddings (text-embedding-3-small/large,
          ada-002). Selection here drives all graph node embedding and
          semantic search.
        </p>
        <SubHeading id="reranker-tab">Reranker</SubHeading>
        <p>
          Reorders search results for relevance. Built-in: FAIM Deterministic
          ReRanker V2 (internal, no external call).
        </p>
        <SubHeading id="ocr-tab">OCR</SubHeading>
        <p>
          Configuration for document text extraction:
          <span className="font-mono">FAIM_OCR_ENABLED</span>,{" "}
          <span className="font-mono">FAIM_OCR_ENGINE</span> (paddleocr_v6,
          tesseract), <span className="font-mono">FAIM_OCR_FAIL_CLOSED</span>,
          <span className="font-mono">FAIM_OCR_LANGS</span>.
        </p>
      </SectionHeading>

      <SectionHeading id="add" kicker="Chapter 03" title="Adding a Provider">
        <SubHeading id="add-llm">LLM Provider</SubHeading>
        <ol className="list-decimal space-y-1 pl-5">
          <li>Click <span className="font-mono text-cyan-300">Add New Provider</span> on the LLM tab.</li>
          <li>Choose a family (OpenAI, Anthropic, Google, etc.).</li>
          <li>Enter your API key and endpoint URL.</li>
          <li>Confirm — the provider appears in the active list immediately.</li>
        </ol>
        <SubHeading id="add-emb">Embedding Provider</SubHeading>
        <p>Same flow: pick family, key, endpoint. Selects the vector model for the graph.</p>
        <SubHeading id="add-rerank">Reranker</SubHeading>
        <p>Usually only the internal FAIM Reranker V2 is used; add if you deploy a custom reranker service.</p>
        <SubHeading id="add-ocr">OCR Config</SubHeading>
        <p>Toggle the four settings; changes apply to the next storage ingest.</p>
      </SectionHeading>

      <SectionHeading id="config" kicker="Chapter 04" title="Provider Configuration">
{/* eslint-disable-next-line react/jsx-key */}
        <DTable
          head={["Property", "Description"]}
          rows={[
            { cells: [<span key="id" className="font-mono">id</span>, "Unique system identifier"] },
            { cells: [<span key="name" className="font-mono">name</span>, "Human-readable label"] },
            { cells: [<span key="code" className="font-mono">code</span>, "Machine-readable slug (e.g. openai)"] },
            { cells: [<span key="type" className="font-mono">type</span>, "openai / anthropic / google / custom / local"] },
            { cells: [<span key="default-url" className="font-mono">defaultUrl</span>, "API base URL"] },
            { cells: [<span key="models" className="font-mono">models</span>, "Comma-separated model names"] },
            { cells: [<span key="status" className="font-mono">status</span>, "active / inactive / deprecated"] },
          ]}
        />
        <p>
          Edit any property inline; deactivate instead of delete to keep audit
          history.
        </p>
      </SectionHeading>

      <SectionHeading id="selection" kicker="Chapter 05" title="Downstream Selection">
{/* eslint-disable-next-line react/jsx-key */}
        <DTable
          head={["Workflow", "Uses Provider Type"]}
          rows={[
            { cells: ["Cortex Chat", "LLM provider"] },
            { cells: ["Graph Node Embedding", "Embedding provider"] },
            { cells: ["Semantic Search / Similarity", "Embedding + Reranker"] },
            { cells: ["Storage Ingest (OCR)", "OCR engine config"] },
            { cells: ["Cluster Analysis", "Embedding provider"] },
          ]}
        />
        <p>
          Selection is sticky per session — once you pick a provider it stays
          active until you change it.
        </p>
      </SectionHeading>

      <SectionHeading id="security" kicker="Chapter 06" title="Security & Tenant Isolation">
        <ul className="list-disc space-y-1 pl-5">
          <li>API keys stored securely server-side; never exposed to frontend code.</li>
          <li>Keys are bound to a single tenant — cross-tenant use is rejected.</li>
          <li>Rate limits are per-provider and configurable; 429 responses include <span className="font-mono">X-Rate-Limit-Remaining</span>.</li>
          <li>Rotation supported: generate a new key, update the provider, revoke the old.</li>
        </ul>
      </SectionHeading>

      <SectionHeading id="troubleshoot" kicker="Chapter 07" title="Troubleshooting">
{/* eslint-disable-next-line react/jsx-key */}
        <DTable
          head={["Problem", "Cause", "Fix"]}
          rows={[
            { cells: ["Provider not in dropdown", "Not saved or status inactive", "Save provider, set status active"] },
            { cells: ["Auth rejected", "Invalid/expired key", "Regenerate key, update provider"] },
            { cells: ["Model not found", "Typo in model name", "Match exact spelling from family list"] },
            { cells: ["Connection timeout", "Wrong URL or service down", "Verify endpoint, check service status"] },
            { cells: ["Rate limit hit", "Too many requests", "Wait or raise provider limit"] },
          ]}
        />
      </SectionHeading>
    </ManualShell>
  );
}
