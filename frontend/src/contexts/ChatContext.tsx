"use client";

/**
 * Chat Context — Multi-Thread Edition
 *
 * Manages threads (conversations) and streaming.
 * Threads are persisted to localStorage under "faim.threads".
 */

import React, { createContext, useContext, useState, useCallback, useEffect } from "react";
import { getSession } from "next-auth/react";
import { getActiveProvider } from "@/lib/providers";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  thinking?: string;           // LLM reasoning/thinking content
  thinkingDurationMs?: number; // time spent thinking (ms)
  timestamp: string;
  queryData?: FaimQueryResponse | null;
}

export interface FaimQueryAnswerCitation {
  node_id: string;
  raw_id?: string;
  block_id?: string;
  anchor?: Record<string, unknown> | null;
  score: number;
}

export interface FaimQueryAnswerSpan {
  node_id: string;
  text: string;
  score: number;
  temporal_status?: string | null;
}

export interface FaimQueryAnswer {
  direct_answer: string;
  supporting_spans: FaimQueryAnswerSpan[];
  citations: FaimQueryAnswerCitation[];
  contradiction_notes: string[];
  confidence: number;
  provenance: Record<string, unknown>;
  quotes: string[];
}

export interface FaimQueryResultItem {
  node_id: string;
  vector_hash: string;
  score: number;
  score_components: Record<string, number>;
  level: number;
  touch_count: number;
  evidence?: {
    raw_id?: string;
    block_id?: string;
    anchor?: Record<string, unknown> | null;
  } | null;
  explain?: Record<string, unknown> | null;
  temporal_status?: string | null;
}

export interface FaimQueryResponse {
  tenant_id: string;
  graph_id: string;
  graph_version: number;
  graph_hash: string;
  query_hash: string;
  k: number;
  profile: string;
  results: FaimQueryResultItem[];
  answer?: FaimQueryAnswer | null;
  metrics?: Record<string, number>;
  duration_ms?: number;
}

type StorageUploadFileResult = {
  filename: string;
  status: string;
  raw_id?: string | null;
  packet_hash?: string | null;
  node_count: number;
  vector_count: number;
  error?: string | null;
};

type StorageUploadBatchResponse = {
  job_id: string;
  graph_id: string;
  status: string;
  requested_files: number;
  processed_files: number;
  success_files: number;
  failed_files: number;
  dedup_hits: number;
  cancelled_files: number;
  files: StorageUploadFileResult[];
};

export interface Thread {
  id: string;
  title: string;
  messages: Message[];
  createdAt: string;
  updatedAt: string;
}

interface ChatContextType {
  // Current thread messages (derived from activeThreadId)
  messages: Message[];
  isStreaming: boolean;
  error: string | null;

  // Thread management
  threads: Thread[];
  activeThreadId: string | null;
  switchThread: (id: string) => void;
  newThread: () => void;
  deleteThread: (id: string) => void;
  renameThread: (id: string, title: string) => void;
  purgeAllThreads: () => void;

  // Chat
  sendMessage: (content: string) => Promise<void>;
  uploadFiles: (files: File[]) => Promise<void>;

  // Thinking/Reasoning
  thinkingEnabled: boolean;
  toggleThinking: () => void;
  isThinking: boolean;
  liveThinkingBuffer: string;
}

// ---------------------------------------------------------------------------
// localStorage helpers
// ---------------------------------------------------------------------------

const LS_KEY = "faim.threads";

function loadThreads(): Thread[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(LS_KEY);
    return raw ? (JSON.parse(raw) as Thread[]) : [];
  } catch {
    return [];
  }
}

function saveThreads(threads: Thread[]): void {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(threads));
  } catch {}
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function now(): string {
  return new Date().toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function isoNow(): string {
  return new Date().toISOString();
}

function makeTitle(firstMessage: string): string {
  const trimmed = firstMessage.trim().replace(/\s+/g, " ");
  return trimmed.length > 40 ? trimmed.slice(0, 40).trimEnd() + "…" : trimmed;
}

function resolveStoredGraphId(): string | null {
  if (typeof window === "undefined") return null;
  const keys = [
    "faim.universe_graph_id",
    "faim_universe_graph_id",
  ];
  for (const key of keys) {
    const value = window.localStorage.getItem(key);
    if (value?.trim()) return value.trim();
  }
  return null;
}

async function buildAuthorizedHeaders(extra?: HeadersInit): Promise<HeadersInit> {
  const session = await getSession();
  const token = (session as { accessToken?: string } | null)?.accessToken;
  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  };
}

// ---------------------------------------------------------------------------
// Conversational intent detector — skip FAIM retrieval for non-memory queries
// ---------------------------------------------------------------------------

const CONVERSATIONAL_PATTERNS = [
  /^(hi|hey|hello|hiya|howdy|sup|yo)[\s!?.]*$/i,
  /^(how are you|how's it going|what's up|whats up|how do you do)[\s!?.]*$/i,
  /^(good morning|good afternoon|good evening|good night|gm|gn)[\s!?.]*$/i,
  /^(thanks|thank you|thx|ty|cheers|awesome|great|ok|okay|sure|cool|nice|perfect)[\s!?.]*$/i,
  /^(bye|goodbye|see you|cya|later|ttyl)[\s!?.]*$/i,
  /^(yes|no|yep|nope|yeah|nah|agreed|correct|exactly|right)[\s!?.]*$/i,
];

function isConversationalMessage(text: string): boolean {
  const trimmed = text.trim();
  // Very short with no content signal
  if (trimmed.length < 4) return true;
  // Matches a known conversational pattern
  return CONVERSATIONAL_PATTERNS.some((re) => re.test(trimmed));
}

function buildConversationalSystemPrompt(): string {
  return [
    "You are FAIM SentineL — a memory assistant. The user sent a conversational message, not a memory query.",
    "Respond briefly and naturally. Remind them they can ask questions about their ingested documents, data, or memory.",
    "Do not make up information. Do not mention retrieving data — none was retrieved for this message.",
  ].join("\n");
}

// ---------------------------------------------------------------------------
// FAIM → LLM context builder
// ---------------------------------------------------------------------------

interface MemoryFileEntry {
  raw_id: string;
  filename: string;
  mime_type: string;
  node_count: number;
  uploaded_at?: string | null;
  ingested_at?: string | null;
}

interface MemoryInventory {
  totalFiles: number;
  byType: Record<string, number>;
  files: MemoryFileEntry[];
}

function buildFaimSystemPrompt(queryData: FaimQueryResponse, thinkingEnabled: boolean, inventory?: MemoryInventory): string {
  const spans   = queryData.answer?.supporting_spans    ?? [];
  const quotes  = queryData.answer?.quotes              ?? [];
  const direct  = queryData.answer?.direct_answer       ?? "";
  const contra  = queryData.answer?.contradiction_notes ?? [];
  const conf    = queryData.answer?.confidence          ?? 0;
  const results = queryData.results                     ?? [];

  // Build rawId → filename map from inventory
  const rawIdToFilename: Record<string, string> = {};
  if (inventory) {
    for (const f of inventory.files) rawIdToFilename[f.raw_id] = f.filename;
  }

  // Build node_id → full result item map
  const resultMap: Record<string, FaimQueryResultItem> = {};
  for (const r of results) resultMap[r.node_id] = r;

  function fmtNodeMeta(nodeId: string): string {
    const r = resultMap[nodeId];
    if (!r?.evidence) return "";
    const anchor = r.evidence.anchor ?? {};
    const rawId = r.evidence.raw_id ?? "";
    const filename = rawIdToFilename[rawId] ?? rawId;
    const page = anchor.page ?? anchor.page_number;
    const section = anchor.section as string | undefined;
    const blockType = (anchor.block_type ?? anchor.content_type ?? "text") as string;
    const column = anchor.column as string | undefined;
    const parts: string[] = [filename];
    if (page != null) parts.push(`p.${page}`);
    if (section) parts.push(`§${section}`);
    if (column) parts.push(`col ${column}`);
    return `[${blockType.toUpperCase()}] [${parts.join(" · ")}]`;
  }

  function fmtScore(score: number): string {
    if (score >= 0.80) return `${Math.round(score * 100)}% ▲ high`;
    if (score >= 0.55) return `${Math.round(score * 100)}% ◆ moderate`;
    return `${Math.round(score * 100)}% ▼ weak`;
  }

  const lines: string[] = [];

  // ── Identity ──────────────────────────────────────────────────────────────
  lines.push("You are FAIM SentineL — a retrieval-grounded memory assistant.");
  lines.push("Every answer you give must be derived exclusively from the FAIM memory nodes below.");
  lines.push("You have no internet access, no training knowledge, no outside facts.");
  lines.push("If the answer is not in the nodes below, say so precisely: 'That data is not in your FAIM memory.'");
  lines.push("");

  // ── Memory inventory (document metadata) ─────────────────────────────────
  if (inventory && inventory.totalFiles > 0) {
    lines.push(`MEMORY INVENTORY — your complete knowledge base has ${inventory.totalFiles} document(s):`);
    const typeList = Object.entries(inventory.byType).map(([t, n]) => `${t.toUpperCase()} (${n})`).join(", ");
    if (typeList) lines.push(`  File types: ${typeList}`);
    inventory.files.forEach((f) => {
      const when = f.ingested_at ? new Date(f.ingested_at).toLocaleDateString() : (f.uploaded_at ? new Date(f.uploaded_at).toLocaleDateString() : "unknown date");
      lines.push(`  • ${f.filename} | ${f.node_count} nodes | ingested ${when} | id:${f.raw_id}`);
    });
    lines.push("  → Use this inventory to answer: 'how many docs?', 'what files?', 'when ingested?', 'how many nodes?'");
    lines.push("");
  } else if (inventory && inventory.totalFiles === 0) {
    lines.push("MEMORY INVENTORY: No documents have been ingested yet. Tell the user to upload files in Storage.");
    lines.push("");
  }

  // ── Signal legend ─────────────────────────────────────────────────────────
  lines.push("SIGNAL LEGEND (FAIM computed these — use them to shape your answer):");
  lines.push("  CURRENT    → most recent, authoritative version of this fact");
  lines.push("  SUPERSEDED → an older version exists; a newer node overrides it");
  lines.push("  CONFLICTED → value contradicts another node; flag both to the user");
  lines.push("  score ≥80% → treat as strong evidence; cite source and page");
  lines.push("  score 55–79% → supporting evidence; note if other nodes agree");
  lines.push("  score <55%  → weak match; qualify with 'weakly supported'");
  lines.push(`  graph confidence: ${Math.round(conf * 100)}% — your answer certainty ceiling`);
  lines.push("");

  // ── Retrieved nodes ───────────────────────────────────────────────────────
  if (spans.length > 0) {
    lines.push("RETRIEVED MEMORY NODES:");
    spans.forEach((s, i) => {
      const status = s.temporal_status ? ` [${s.temporal_status}]` : " [CURRENT]";
      const meta = fmtNodeMeta(s.node_id);
      lines.push(`--- Node ${i + 1} | ${fmtScore(s.score)} | ${status} | ${meta}`);
      lines.push(s.text);
    });
    lines.push("");
  } else if (results.length === 0) {
    lines.push("RETRIEVED MEMORY NODES: none");
    lines.push("→ No nodes matched this query. Respond: 'No memory found for this query — ingest that data first.'");
    lines.push("");
  }

  // ── FAIM's own direct answer (extractive, pre-LLM) ───────────────────────
  if (direct) {
    lines.push(`FAIM EXTRACTIVE SUMMARY (score: ${Math.round(conf * 100)}% confidence):`);
    lines.push(direct);
    lines.push("→ Use this as your factual anchor. Expand on it using the nodes above. Do not contradict it.");
    lines.push("");
  }

  // ── Verbatim quotes extracted by FAIM ────────────────────────────────────
  if (quotes.length > 0) {
    lines.push("VERBATIM QUOTES FROM DOCUMENTS:");
    quotes.forEach((q) => lines.push(`  "${q}"`));
    lines.push("→ These are exact document text. Use them directly in your answer when relevant.");
    lines.push("");
  }

  // ── Contradictions FAIM already detected ─────────────────────────────────
  if (contra.length > 0) {
    lines.push("CONTRADICTIONS DETECTED BY FAIM:");
    contra.forEach((c) => lines.push(`  ⚠ ${c}`));
    lines.push("→ Surface these contradictions explicitly to the user. Do not resolve them by guessing.");
    lines.push("");
  }

  // ── Behavioural contract (minimal, data-tied) ─────────────────────────────
  lines.push("RESPONSE CONTRACT:");
  lines.push("  1. Cite source + page for every factual claim (format: [filename · p.N])");
  lines.push("  2. SUPERSEDED nodes: state 'older data — superseded by Node X'");
  lines.push("  3. CONFLICTED nodes: state both values and the conflict — never pick one silently");
  lines.push(`  4. If graph confidence is below 40% (current: ${Math.round(conf * 100)}%), open with a confidence caveat`);
  lines.push("  5. No answer exists in nodes → say exactly what is missing, nothing more");
  if (thinkingEnabled) lines.push("  6. Reason through node scores and temporal status before composing your answer");

  return lines.join("\n");
}

// ---------------------------------------------------------------------------

async function resolveActiveGraphId(): Promise<string | null> {
  const session = await getSession();
  const fromSession =
    ((session as { graphId?: string } | null)?.graphId || "").trim() || null;
  if (fromSession) return fromSession;

  const fromStorage = resolveStoredGraphId();
  if (fromStorage) return fromStorage;

  const headers = await buildAuthorizedHeaders();
  const res = await fetch("/api/v1/auth/me", { headers });
  if (!res.ok) return null;
  const data = await res.json().catch(() => null);
  const graphId =
    String(data?.user?.graph_id || data?.graph_id || "").trim() || null;
  if (graphId && typeof window !== "undefined") {
    window.localStorage.setItem("faim.universe_graph_id", graphId);
    window.localStorage.setItem("faim_universe_graph_id", graphId);
  }
  return graphId;
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const [threads, setThreads] = useState<Thread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [thinkingEnabled, setThinkingEnabled] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [liveThinkingBuffer, setLiveThinkingBuffer] = useState("");

  // Load from localStorage on mount
  useEffect(() => {
    const loaded = loadThreads();
    setThreads(loaded);
    if (loaded.length > 0) {
      setActiveThreadId(loaded[0].id);
    }
  }, []);

  // Persist whenever threads change
  useEffect(() => {
    if (threads.length > 0 || typeof window !== "undefined") {
      saveThreads(threads);
    }
  }, [threads]);

  // Derived: messages of the active thread
  const activeThread = threads.find((t) => t.id === activeThreadId) ?? null;
  const messages = React.useMemo(
    () => activeThread?.messages ?? [],
    [activeThread]
  );

  // ── Thread actions ──────────────────────────────────────────────────────

  const switchThread = useCallback((id: string) => {
    setActiveThreadId(id);
    setError(null);
  }, []);

  const toggleThinking = useCallback(() => {
    setThinkingEnabled((p) => !p);
  }, []);

  const newThread = useCallback(() => {
    // Smart guard: don't create a new thread if active thread already has 0 messages
    const active = threads.find((t) => t.id === activeThreadId);
    if (active && active.messages.length === 0) {
      return; // already on an empty thread
    }

    const thread: Thread = {
      id: crypto.randomUUID(),
      title: "New Thread",
      messages: [],
      createdAt: isoNow(),
      updatedAt: isoNow(),
    };
    setThreads((prev) => [thread, ...prev]);
    setActiveThreadId(thread.id);
    setError(null);
  }, [threads, activeThreadId]);

  const deleteThread = useCallback(
    (id: string) => {
      setThreads((prev) => {
        const next = prev.filter((t) => t.id !== id);
        saveThreads(next);
        // Switch to nearest thread
        if (activeThreadId === id) {
          setActiveThreadId(next.length > 0 ? next[0].id : null);
        }
        return next;
      });
    },
    [activeThreadId]
  );

  const renameThread = useCallback((id: string, title: string) => {
    setThreads((prev) =>
      prev.map((t) => (t.id === id ? { ...t, title: title.trim() || t.title } : t))
    );
  }, []);

  const purgeAllThreads = useCallback(() => {
    setThreads([]);
    setActiveThreadId(null);
    setError(null);
    saveThreads([]);
  }, []);

  // ── sendMessage ─────────────────────────────────────────────────────────

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isStreaming) return;

      setError(null);

      // Ensure we have an active thread; create one on first message
      let threadId = activeThreadId;

      if (!threadId) {
        const thread: Thread = {
          id: crypto.randomUUID(),
          title: makeTitle(content),
          messages: [],
          createdAt: isoNow(),
          updatedAt: isoNow(),
        };
        setThreads((prev) => [thread, ...prev]);
        setActiveThreadId(thread.id);
        threadId = thread.id;
      }

      const userMsg: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content: content.trim(),
        timestamp: now(),
      };

      const assistantId = crypto.randomUUID();
      const assistantMsg: Message = {
        id: assistantId,
        role: "assistant",
        content: "",
        timestamp: now(),
        queryData: null,
      };

      // Append messages to thread; auto-title on first user message
      setThreads((prev) =>
        prev.some((t) => t.id === threadId)
          ? prev.map((t) => {
              if (t.id !== threadId) return t;
              const isFirst = t.messages.length === 0;
              return {
                ...t,
                title: isFirst ? makeTitle(content) : t.title,
                messages: [...t.messages, userMsg, assistantMsg],
                updatedAt: isoNow(),
              };
            })
          : [
              {
                id: threadId!,
                title: makeTitle(content),
                messages: [userMsg, assistantMsg],
                createdAt: isoNow(),
                updatedAt: isoNow(),
              },
              ...prev,
            ]
      );

      setIsStreaming(true);
      setIsThinking(false);
      setLiveThinkingBuffer("");

      // Capture history BEFORE we append the new messages (messages is still stale here)
      const historySnapshot = messages
        .slice(-8)
        .map((m) => ({ role: m.role as "user" | "assistant", content: m.content || "" }))
        .filter((m) => m.content.trim());

      try {
        const graphId = await resolveActiveGraphId();
        if (!graphId) throw new Error("No active graph found for memory query");

        // ── Step 1: FAIM retrieval (skip for conversational messages) ─────────
        const headers = await buildAuthorizedHeaders();
        const skipRetrieval = isConversationalMessage(userMsg.content);
        let queryData: FaimQueryResponse | null = null;

        if (!skipRetrieval) {
          const queryRes = await fetch("/api/v1/query", {
            method: "POST",
            headers: { "Content-Type": "application/json", ...headers },
            body: JSON.stringify({
              graph_id: graphId,
              query_text: userMsg.content,
              k: 15,
              profile: "RELAXED",
              return_explain: true,
            }),
          });

          if (!queryRes.ok) {
            const errData = await queryRes.json().catch(() => ({}));
            throw new Error(errData.detail || errData.message || `HTTP ${queryRes.status}`);
          }

          queryData = (await queryRes.json()) as FaimQueryResponse;

          // Attach queryData so the sources card appears while LLM streams
          setThreads((prev) =>
            prev.map((t) =>
              t.id !== threadId ? t : {
                ...t,
                messages: t.messages.map((m) =>
                  m.id === assistantId ? { ...m, queryData } : m
                ),
              }
            )
          );
        }

        // ── Step 2: Check active provider ──────────────────────────────────
        const provider = getActiveProvider();

        if (!provider) {
          // No LLM — fall back to FAIM extractive answer or plain message
          const fallback = queryData
            ? queryData.answer?.direct_answer ||
              (queryData.results?.length
                ? `Retrieved ${queryData.results.length} memory result${queryData.results.length === 1 ? "" : "s"}.`
                : "No matching memory found for this query.")
            : "Hi! Ask me anything about your ingested documents and data.";
          setThreads((prev) =>
            prev.map((t) =>
              t.id !== threadId ? t : {
                ...t,
                messages: t.messages.map((m) =>
                  m.id === assistantId ? { ...m, content: fallback, queryData } : m
                ),
              }
            )
          );
          return;
        }

        // ── Step 3: Fetch memory inventory for system prompt ──────────────
        let inventory: MemoryInventory | undefined;
        try {
          const [summaryRes, filesRes] = await Promise.all([
            fetch(`/api/v1/storage/summary?graph_id=${encodeURIComponent(graphId)}`, { headers }),
            fetch(`/api/v1/storage/files?graph_id=${encodeURIComponent(graphId)}&limit=50&status=ready`, { headers }),
          ]);
          if (summaryRes.ok && filesRes.ok) {
            const summary = await summaryRes.json() as { total_files: number; by_type: Record<string, number> };
            const filesData = await filesRes.json() as { items?: Array<MemoryFileEntry> };
            inventory = {
              totalFiles: summary.total_files ?? 0,
              byType: summary.by_type ?? {},
              files: (filesData.items ?? []).slice(0, 50),
            };
          }
        } catch {
          // inventory stays undefined — system prompt works without it
        }

        // ── Step 4: Build system prompt ────────────────────────────────────
        const systemPrompt = queryData
          ? buildFaimSystemPrompt(queryData, thinkingEnabled, inventory)
          : buildConversationalSystemPrompt();

        // ── Step 4: Call LLM provider and stream response ──────────────────
        const llmMessages = [
          ...historySnapshot,
          { role: "user" as const, content: userMsg.content },
        ];

        const chatRes = await fetch("/api/provider/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            providerUrl: provider.baseUrl,
            apiKey: provider.apiKey || undefined,
            model: provider.activeModel,
            messages: llmMessages,
            systemPrompt,
          }),
        });

        if (!chatRes.ok) {
          const errData = await chatRes.json().catch(() => ({}));
          throw new Error(errData.error || `Provider error (${chatRes.status})`);
        }

        // Stream token by token
        const reader = chatRes.body?.getReader();
        const decoder = new TextDecoder();
        let accumulated = "";
        let thinkingAccum = "";

        if (reader) {
          outer: while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            for (const line of chunk.split("\n")) {
              if (!line.startsWith("data: ")) continue;
              const raw = line.slice(6).trim();
              if (raw === "[DONE]") break outer;

              try {
                const parsed = JSON.parse(raw);
                const delta = parsed.choices?.[0]?.delta;
                if (!delta) continue;

                if (delta.thinking) {
                  thinkingAccum += delta.thinking;
                  setIsThinking(true);
                  setLiveThinkingBuffer(thinkingAccum);
                  continue;
                }

                if (delta.content) {
                  accumulated += delta.content;
                  setThreads((prev) =>
                    prev.map((t) =>
                      t.id !== threadId ? t : {
                        ...t,
                        messages: t.messages.map((m) =>
                          m.id !== assistantId ? m : {
                            ...m,
                            content: accumulated,
                            queryData,
                            ...(thinkingAccum ? { thinking: thinkingAccum } : {}),
                          }
                        ),
                      }
                    )
                  );
                }
              } catch { /* skip malformed SSE lines */ }
            }
          }
        }

        // Finalise — ensure we always have something
        const finalContent = accumulated ||
          queryData?.answer?.direct_answer ||
          "I couldn't generate an answer. Please check the source results below.";

        setThreads((prev) =>
          prev.map((t) =>
            t.id !== threadId ? t : {
              ...t,
              messages: t.messages.map((m) =>
                m.id !== assistantId ? m : {
                  ...m,
                  content: finalContent,
                  queryData,
                  ...(thinkingAccum ? { thinking: thinkingAccum } : {}),
                }
              ),
              updatedAt: isoNow(),
            }
          )
        );

      } catch (e: unknown) {
        const errorMsg = e instanceof Error ? e.message : "Failed to query FAIM";
        setError(errorMsg);
        setThreads((prev) =>
          prev.map((t) =>
            t.id !== threadId ? t : {
              ...t,
              messages: t.messages.map((m) =>
                m.id === assistantId ? { ...m, content: `[Error: ${errorMsg}]` } : m
              ),
            }
          )
        );
      } finally {
        setIsStreaming(false);
        setIsThinking(false);
        setLiveThinkingBuffer("");
      }
    },
    [activeThreadId, messages, isStreaming, thinkingEnabled]
  );

  const uploadFiles = useCallback(
    async (files: File[]) => {
      if (!files.length || isStreaming || isUploading) return;

      setError(null);

      let threadId = activeThreadId;
      if (!threadId) {
        const thread: Thread = {
          id: crypto.randomUUID(),
          title: "Memory Upload",
          messages: [],
          createdAt: isoNow(),
          updatedAt: isoNow(),
        };
        setThreads((prev) => [thread, ...prev]);
        setActiveThreadId(thread.id);
        threadId = thread.id;
      }

      const assistantId = crypto.randomUUID();
      const assistantMsg: Message = {
        id: assistantId,
        role: "assistant",
        content: `Uploading ${files.length} file${files.length === 1 ? "" : "s"} into FAIM storage...`,
        timestamp: now(),
      };

      setThreads((prev) =>
        prev.some((t) => t.id === threadId)
          ? prev.map((t) =>
              t.id === threadId
                ? {
                    ...t,
                    messages: [...t.messages, assistantMsg],
                    updatedAt: isoNow(),
                  }
                : t
            )
          : [
              {
                id: threadId!,
                title: "Memory Upload",
                messages: [assistantMsg],
                createdAt: isoNow(),
                updatedAt: isoNow(),
              },
              ...prev,
            ]
      );

      setIsUploading(true);

      try {
        const graphId = await resolveActiveGraphId();
        if (!graphId) throw new Error("No active graph found for upload");

        const headers = await buildAuthorizedHeaders();
        const formData = new FormData();
        formData.set("graph_id", graphId);
        formData.set("profile", "strict");
        formData.set("persist_mode", "relaxed");
        for (const file of files) formData.append("files", file);

        const res = await fetch("/api/v1/storage/uploads", {
          method: "POST",
          headers,
          body: formData,
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || errData.message || `HTTP ${res.status}`);
        }

        const batch = (await res.json()) as StorageUploadBatchResponse;
        const lines = [
          `FAIM storage ingest completed for ${batch.success_files}/${batch.requested_files} file${batch.requested_files === 1 ? "" : "s"}.`,
          batch.dedup_hits ? `Dedup hits: ${batch.dedup_hits}.` : "",
          batch.failed_files ? `Failures: ${batch.failed_files}.` : "",
          "",
          ...batch.files.map((item) => {
            const details = [
              item.status,
              item.raw_id ? `raw ${item.raw_id}` : "",
              item.node_count ? `${item.node_count} nodes` : "",
              item.vector_count ? `${item.vector_count} vectors` : "",
              item.error || "",
            ].filter(Boolean);
            return `- ${item.filename}: ${details.join(" · ")}`;
          }),
        ].filter(Boolean);

        setThreads((prev) =>
          prev.map((t) =>
            t.id === threadId
              ? {
                  ...t,
                  messages: t.messages.map((m) =>
                    m.id === assistantId ? { ...m, content: lines.join("\n") } : m
                  ),
                  updatedAt: isoNow(),
                }
              : t
          )
        );
      } catch (e: any) {
        const errorMsg = e.message || "Failed to upload files to FAIM storage";
        setError(errorMsg);
        setThreads((prev) =>
          prev.map((t) =>
            t.id === threadId
              ? {
                  ...t,
                  messages: t.messages.map((m) =>
                    m.id === assistantId ? { ...m, content: `[Upload error: ${errorMsg}]` } : m
                  ),
                }
              : t
          )
        );
      } finally {
        setIsUploading(false);
      }
    },
    [activeThreadId, isStreaming, isUploading]
  );

  return (
    <ChatContext.Provider
      value={{
        messages,
        isStreaming: isStreaming || isUploading,
        error,
        threads,
        activeThreadId,
        switchThread,
        newThread,
        deleteThread,
        renameThread,
        purgeAllThreads,
        sendMessage,
        uploadFiles,
        thinkingEnabled,
        toggleThinking,
        isThinking,
        liveThinkingBuffer,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

export function useChat(): ChatContextType {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error("useChat must be used within a ChatProvider");
  }
  return context;
}
