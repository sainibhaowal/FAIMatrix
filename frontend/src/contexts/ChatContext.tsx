"use client";

/**
 * Chat Context — Multi-Thread Edition
 *
 * Manages threads (conversations) and streaming.
 * Threads are persisted to localStorage under "faim.threads".
 */

import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
} from "react";
import { getSession } from "next-auth/react";
import { getActiveProvider } from "@/lib/providers";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type AnswerMode = "auto" | "direct" | "timeline" | "contradiction" | "provenance";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  answerMode?: AnswerMode;
  thinking?: string; // LLM reasoning/thinking content
  thinkingDurationMs?: number; // time spent thinking (ms)
  timestamp: string;
  queryData?: FaimQueryResponse | null;
  cortexData?: FaimCortexTurnResponse | null;
}

export const ANSWER_MODE_LABELS: Record<AnswerMode, string> = {
  auto: "Cortex Auto",
  direct: "Direct",
  timeline: "Timeline",
  contradiction: "Contradiction",
  provenance: "Provenance",
};

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
  supersedes?: string[] | null;
  superseded_by?: string | null;
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

export interface FaimCortexReasoningNode {
  node_id: string;
  branch: string;
  title: string;
  summary: string;
  evidence_node_ids: string[];
  confidence: number;
  depends_on: string[];
  output: Record<string, unknown>;
  created_at: string;
}

type FaimTraversalPath = {
  node_ids?: string[];
  edge_ids?: string[];
  path_length?: number;
  confidence?: number;
};

export interface FaimCortexTurnSummary {
  turn_id: string;
  query_text: string;
  answer_mode: string;
  task_type: string;
  confidence: number;
  narrative: string;
  open_question_count: number;
  contradiction_count: number;
  created_at: string;
}

export interface FaimCortexSessionSummary {
  session_id: string;
  tenant_id: string;
  graph_id: string;
  title: string;
  turn_count: number;
  last_turn_id?: string | null;
  last_task_type?: string | null;
  last_confidence?: number | null;
  last_turn_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface FaimCortexBrainState {
  turn_id: string;
  tenant_id: string;
  graph_id: string;
  session_id?: string | null;
  query_text: string;
  answer_mode: string;
  task_type: string;
  query_hash: string;
  graph_version: number;
  graph_hash: string;
  goal: string;
  session_turn_count: number;
  session_summary: string;
  active_facts: string[];
  evidence_nodes: FaimQueryResultItem[];
  contradictions: string[];
  open_questions: string[];
  hypotheses: string[];
  predictions: string[];
  next_actions: string[];
  confidence: number;
  retrieval_summary?: Record<string, unknown>;
  recent_turns: FaimCortexTurnSummary[];
  reasoning_tree: FaimCortexReasoningNode[];
  writeback_candidates: Array<Record<string, unknown>>;
  answer_packet: FaimQueryAnswer;
  narrative: string;
}

export interface FaimCortexTurnResponse {
  tenant_id: string;
  graph_id: string;
  session_id?: string | null;
  turn_id: string;
  query_hash: string;
  task_type: string;
  answer_mode: string;
  answer?: FaimQueryAnswer | null;
  brain_state: FaimCortexBrainState;
  narrative: string;
  duration_ms: number;
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

function adaptCortexTurnToQueryResponse(
  turn: FaimCortexTurnResponse,
): FaimQueryResponse {
  const brain = turn.brain_state;
  const answer = turn.answer ?? brain.answer_packet;
  return {
    tenant_id: turn.tenant_id,
    graph_id: turn.graph_id,
    graph_version: brain.graph_version ?? 0,
    graph_hash: brain.graph_hash ?? "",
    query_hash: turn.query_hash,
    k: brain.evidence_nodes?.length ?? 0,
    profile: String(brain.answer_mode || turn.answer_mode || "RELAXED"),
    results: brain.evidence_nodes ?? [],
    answer,
    metrics: {
      confidence: brain.confidence ?? 0,
      reasoning_nodes: brain.reasoning_tree?.length ?? 0,
    },
    duration_ms: turn.duration_ms ?? 0,
  };
}

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
  answerMode: AnswerMode;
  setAnswerMode: (mode: AnswerMode) => void;
  isThinking: boolean;
  liveThinkingBuffer: string;
  activeReasoningPath: FigExplainPath | null;
  setReasoningPath: (path: FigExplainPath | null) => void;
}

export type FigExplainPath = {
  nodeIdSet: Set<string>;
  edgeIdSet: Set<string>;
};

// ---------------------------------------------------------------------------
// localStorage helpers
// ---------------------------------------------------------------------------

const LS_KEY = "faim.threads";
const LS_MODE_KEY = "faim.memory.answer_mode";

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
  const keys = ["faim.universe_graph_id", "faim_universe_graph_id"];
  for (const key of keys) {
    const value = window.localStorage.getItem(key);
    if (value?.trim()) return value.trim();
  }
  return null;
}

export async function buildAuthorizedHeaders(
  extra?: HeadersInit,
): Promise<HeadersInit> {
  const session = await getSession();
  const token = (session as { accessToken?: string } | null)?.accessToken;
  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  };
}

// ---------------------------------------------------------------------------
// Answer Mode Prompt Guidance
// ---------------------------------------------------------------------------

function buildAnswerModeGuidance(answerMode: AnswerMode): string[] {
  switch (answerMode) {
    case "timeline":
      return [
        "ANSWER MODE: Timeline",
        "Reconstruct events chronologically in one connected narrative.",
        "Lead with what changed, then what came before, then what is current.",
        "Use explicit dates, temporal status, and sequence markers whenever they appear in the memory nodes.",
        "Do not collapse historical and current facts into one sentence.",
      ];
    case "contradiction":
      return [
        "ANSWER MODE: Contradiction-aware",
        "Open with the disagreement or ambiguity if one exists.",
        "Present both sides in fluent prose, with their sources and why they conflict.",
        "Never hide a conflict by picking one side silently.",
        "If the evidence favors one side, say that cautiously and explain the basis.",
      ];
    case "provenance":
      return [
        "ANSWER MODE: Provenance-first",
        "Lead with the source trail: which files, pages, sections, and anchors support the answer.",
        "Explain why these memories were selected before giving the conclusion.",
        "Keep the answer readable prose, but privilege traceability and evidence lineage.",
        "Mention confidence and source coverage when it helps the user trust the answer.",
      ];
    case "direct":
    default:
      return [
        "ANSWER MODE: Direct",
        "Lead with the answer first, then expand with the most relevant evidence in the same narrative flow.",
        "Use fluent prose instead of a retrieval dump.",
        "Keep the response compact unless the question needs a fuller explanation.",
        "Do not use tables unless the user explicitly asks for one.",
      ];
  }
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

function buildFaimSystemPrompt(
  queryData: FaimQueryResponse,
  answerMode: AnswerMode,
  inventory?: MemoryInventory,
): string {
  const spans = queryData.answer?.supporting_spans ?? [];
  const contra = queryData.answer?.contradiction_notes ?? [];
  const conf = queryData.answer?.confidence ?? 0;
  const results = queryData.results ?? [];

  const rawIdToFilename: Record<string, string> = {};
  if (inventory) {
    for (const f of inventory.files) rawIdToFilename[f.raw_id] = f.filename;
  }

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
    const blockType = (anchor.block_type ??
      anchor.content_type ??
      "text") as string;
    const column = anchor.column as string | undefined;
    const parts: string[] = [filename];
    if (page != null) parts.push(`p.${page}`);
    if (section) parts.push(`§${section}`);
    if (column) parts.push(`col ${column}`);
    return `[${blockType.toUpperCase()}] [${parts.join(" · ")}]`;
  }

  function fmtScore(score: number): string {
    if (score >= 0.8) return `${Math.round(score * 100)}% high`;
    if (score >= 0.55) return `${Math.round(score * 100)}% moderate`;
    return `${Math.round(score * 100)}% weak`;
  }

  const lines: string[] = [];

  lines.push("You are FAIM Cortex — the cognitive memory synthesis engine powering the FAIM Matrix platform.");

  if (spans.length > 0) {
    lines.push(
      "Synthesize a clear, accurate, markdown response grounded in the retrieved FAIM evidence.",
    );
    lines.push(
      "Use inline citations like [filename · p.N] when tying claims to source documents.",
    );
    lines.push(
      "Do not invent outside facts. Keep the answer readable and direct.",
    );
    buildAnswerModeGuidance(answerMode).forEach((line) => lines.push(line));
    lines.push("");

    if (inventory && inventory.totalFiles > 0) {
      lines.push(
        `MEMORY INVENTORY — ${inventory.totalFiles} document(s) available in active graph memory.`,
      );
    }

    lines.push("RETRIEVED EVIDENCE:");
    spans.forEach((s, i) => {
      const status = s.temporal_status ? ` [${s.temporal_status}]` : "";
      const meta = fmtNodeMeta(s.node_id);
      lines.push(
        `- Evidence ${i + 1} | ${fmtScore(s.score)} |${status} ${meta}`.trim(),
      );
      lines.push(`  ${s.text}`);
    });

    if (contra.length > 0) {
      lines.push("");
      lines.push("CONFLICT WARNING:");
      contra.forEach((c) => lines.push(`  - ${c}`));
    }
  } else {
    lines.push(
      "The user sent a message or question where no specific document evidence spans were returned from graph memory.",
    );
    lines.push(
      "If the user is asking a conversational question, greeting, or identity query (such as 'who are you', 'what can you do', 'hi', 'help'), respond naturally, articulately, and comprehensively as FAIM Cortex.",
    );
    lines.push(
      "Explain clearly that you are FAIM Cortex — the cognitive memory synthesis engine powering FAIM Matrix, capable of grounded document search, 1–24+ hop graph reasoning, temporal contradiction resolution, and evidence provenance tracking.",
    );
    lines.push(
      "If the user is asking for specific facts from a document that is not present in graph memory, politely state that no matching document memory was found.",
    );
    lines.push("Always maintain a professional, intelligent, conversational tone with complete sentences.");
  }

  return lines.join("\n");
}

// ---------------------------------------------------------------------------

export async function resolveActiveGraphId(): Promise<string | null> {
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
  const thinkingEnabled = true;
  const [answerMode, setAnswerModeState] = useState<AnswerMode>(() => {
    if (typeof window === "undefined") return "auto";
    const raw = window.localStorage.getItem(LS_MODE_KEY) as AnswerMode;
    const valid = ["auto", "direct", "timeline", "contradiction", "provenance"];
    return valid.includes(raw) ? raw : "auto";
  });

  const setAnswerMode = useCallback((mode: AnswerMode) => {
    setAnswerModeState(mode);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(LS_MODE_KEY, mode);
    }
  }, []);
  const [isThinking, setIsThinking] = useState(false);
  const [liveThinkingBuffer, setLiveThinkingBuffer] = useState("");
  const [activeReasoningPath, setActiveReasoningPath] = useState<FigExplainPath | null>(null);

  const setReasoningPath = useCallback((path: FigExplainPath | null) => {
    setActiveReasoningPath(path);
  }, []);

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

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      window.localStorage.setItem(LS_MODE_KEY, answerMode);
    } catch {
      // ignore
    }
  }, [answerMode]);

  // Derived: messages of the active thread
  const activeThread = threads.find((t) => t.id === activeThreadId) ?? null;
  const messages = React.useMemo(
    () => activeThread?.messages ?? [],
    [activeThread],
  );

  // ── Thread actions ──────────────────────────────────────────────────────

  const switchThread = useCallback((id: string) => {
    setActiveThreadId(id);
    setError(null);
  }, []);

  const toggleThinking = useCallback(() => {
    // Cortex thinking is always-on by backend policy. Keep this no-op for
    // backward-compatible context consumers while the UI shows status only.
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

      // Best-effort delete session from Cortex backend
      resolveActiveGraphId().then((graphId) => {
        if (!graphId) return;
        buildAuthorizedHeaders().then((headers) => {
          fetch(
            `/api/v1/cortex/sessions/${encodeURIComponent(id)}?graph_id=${encodeURIComponent(graphId)}`,
            {
              method: "DELETE",
              headers,
            },
          ).catch(() => {});
        });
      });
    },
    [activeThreadId],
  );

  const renameThread = useCallback((id: string, title: string) => {
    setThreads((prev) =>
      prev.map((t) =>
        t.id === id ? { ...t, title: title.trim() || t.title } : t,
      ),
    );
  }, []);

  const purgeAllThreads = useCallback(() => {
    const currentThreads = [...threads];
    setThreads([]);
    setActiveThreadId(null);
    setError(null);
    saveThreads([]);

    resolveActiveGraphId().then((graphId) => {
      if (!graphId) return;
      buildAuthorizedHeaders().then((headers) => {
        for (const t of currentThreads) {
          fetch(
            `/api/v1/cortex/sessions/${encodeURIComponent(t.id)}?graph_id=${encodeURIComponent(graphId)}`,
            {
              method: "DELETE",
              headers,
            },
          ).catch(() => {});
        }
      });
    });
  }, [threads]);

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
        answerMode,
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
            ],
      );

      setIsStreaming(true);
      setIsThinking(false);
      setLiveThinkingBuffer("");
      setActiveReasoningPath(null); // Clear previous path on new message

      // Capture history BEFORE we append the new messages (messages is still stale here)
      const historySnapshot = messages
        .slice(-8)
        .map((m) => ({
          role: m.role as "user" | "assistant",
          content: m.content || "",
        }))
        .filter((m) => m.content.trim());

      try {
        const graphId = await resolveActiveGraphId();
        if (!graphId) throw new Error("No active graph found for memory query");

        // ── Step 1: FAIM Cortex retrieval turn ──────────────────────────────
        const headers = await buildAuthorizedHeaders();
        let queryData: FaimQueryResponse | null = null;

        const cortexRes = await fetch("/api/v1/cortex/turn", {
          method: "POST",
          headers: { "Content-Type": "application/json", ...headers },
          body: JSON.stringify({
            graph_id: graphId,
            query_text: userMsg.content,
            k: 15,
            profile: "RELAXED",
            return_explain: true,
            answer_mode: answerMode,
            think_enabled: true,
            session_id: threadId,
          }),
        });

        if (!cortexRes.ok) {
          const errData = await cortexRes.json().catch(() => ({}));
          throw new Error(
            errData.detail || errData.message || `HTTP ${cortexRes.status}`,
          );
        }

        const cortexTurn = (await cortexRes.json()) as FaimCortexTurnResponse;
        queryData = adaptCortexTurnToQueryResponse(cortexTurn);

        setThreads((prev) =>
          prev.map((t) =>
            t.id !== threadId
              ? t
              : {
                  ...t,
                  messages: t.messages.map((m) =>
                    m.id === assistantId
                      ? {
                          ...m,
                          content: "",
                          queryData,
                          cortexData: cortexTurn,
                          answerMode,
                        }
                      : m,
                  ),
                },
          ),
        );

        // Prefer the exact traversal branch path when available.
        const traversalBranch = cortexTurn.brain_state.reasoning_tree.find(
          (node) => node.branch === "traversal",
        );
        const traversalPaths = Array.isArray(traversalBranch?.output?.paths)
          ? (traversalBranch?.output?.paths as FaimTraversalPath[])
          : [];
        const firstTraversalPath = traversalPaths[0];

        if (firstTraversalPath?.node_ids?.length) {
          setActiveReasoningPath({
            nodeIdSet: new Set(firstTraversalPath.node_ids),
            edgeIdSet: new Set(firstTraversalPath.edge_ids ?? []),
          });
        } else {
          const nodeIds = cortexTurn.brain_state.evidence_nodes.map((n) => n.node_id);
          const edgeIds = cortexTurn.brain_state.reasoning_tree.flatMap(
            (n) => n.evidence_node_ids,
          );

          setActiveReasoningPath({
            nodeIdSet: new Set([
              ...nodeIds,
              ...cortexTurn.brain_state.reasoning_tree.map((n) => n.node_id),
            ]),
            edgeIdSet: new Set(edgeIds),
          });
        }

        // Fetch memory inventory for the final LLM synthesis prompt.
        let inventory: MemoryInventory | undefined;
        try {
          const [summaryRes, filesRes] = await Promise.all([
            fetch(
              `/api/v1/storage/summary?graph_id=${encodeURIComponent(graphId)}`,
              { headers },
            ),
            fetch(
              `/api/v1/storage/files?graph_id=${encodeURIComponent(graphId)}&limit=50&status=ready`,
              { headers },
            ),
          ]);
          if (summaryRes.ok && filesRes.ok) {
            const summary = (await summaryRes.json()) as {
              total_files: number;
              by_type: Record<string, number>;
            };
            const filesData = (await filesRes.json()) as {
              items?: Array<MemoryFileEntry>;
            };
            inventory = {
              totalFiles: summary.total_files ?? 0,
              byType: summary.by_type ?? {},
              files: (filesData.items ?? []).slice(0, 50),
            };
          }
        } catch {
          // inventory stays undefined — the answer prompt works without it
        }

        const systemPrompt = buildFaimSystemPrompt(queryData, answerMode, inventory);

        const provider = getActiveProvider();

        if (!provider) {
          const textLower = userMsg.content.trim().toLowerCase();
          const isGreeting = /^(hi|hey|hello|hiya|howdy|sup|yo)[\s!?.]*$/i.test(textLower);
          const isIdentity = /^(who|what)\s+(are|is|can)\s+(you|u|faim|cortex).*/i.test(textLower) || textLower.includes("who are you") || textLower.includes("what can you do");

          let fallback: string;
          if (isIdentity) {
            fallback =
              "I am **FAIM Cortex** — the cognitive memory synthesis engine powering the FAIM Matrix platform.\n\n" +
              "I perform grounded document retrieval with zero hallucinations, multi-hop relational graph reasoning across 1 to 24+ hops, temporal contradiction resolution (separating active `CURRENT` facts from outdated `HISTORICAL` statements), and cryptographic evidence provenance tracking with inline source citations.\n\n" +
              "How can I assist you with your knowledge graph memory today?";
          } else if (isGreeting) {
            fallback =
              "Hello! I am **FAIM Cortex**, ready to assist you with your knowledge graph memory.\n\n" +
              "You can ask me questions about your ingested files, explore multi-hop relationships across documents, or upload new files to expand our active memory graph.\n\n" +
              "What would you like to explore today?";
          } else {
            const firstSpan = queryData?.answer?.supporting_spans?.[0]?.text;
            fallback =
              queryData?.answer?.direct_answer ||
              firstSpan ||
              (queryData?.results && queryData.results.length > 0
                ? `FAIM Cortex retrieved verified memory nodes (Node ID: \`${queryData.results[0].node_id}\`) from your knowledge graph.`
                : `I searched our knowledge graph memory for **"${userMsg.content}"**, but no matching document nodes or relational assertions were found in the active universe graph.\n\n**Tips**:\n- Make sure the target file has been uploaded and ingested.\n- Try rephrasing your search terms or switching to **Cortex Auto** answer mode.`);
          }

          setThreads((prev) =>
            prev.map((t) =>
              t.id !== threadId
                ? t
                : {
                    ...t,
                    messages: t.messages.map((m) =>
                      m.id === assistantId
                        ? { ...m, content: fallback, queryData }
                        : m,
                    ),
                  },
            ),
          );
          setIsStreaming(false);
          return;
        }

        // ── Step 3: Call LLM provider and stream response ──────────────────
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
          throw new Error(
            errData.error || `Provider error (${chatRes.status})`,
          );
        }

        // Stream token by token
        const reader = chatRes.body?.getReader();
        const decoder = new TextDecoder();
        let accumulated = "";

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

                if (delta.content) {
                  accumulated += delta.content;
                  setThreads((prev) =>
                    prev.map((t) =>
                      t.id !== threadId
                        ? t
                        : {
                            ...t,
                            messages: t.messages.map((m) =>
                              m.id !== assistantId
                                ? m
                                : {
                                    ...m,
                                    content: accumulated,
                                    queryData,
                                    answerMode,
                                  },
                            ),
                          },
                    ),
                  );
                }
              } catch {
                /* skip malformed SSE lines */
              }
            }
          }
        }

        // Finalise — ensure we always have something
        const finalContent =
          accumulated ||
          "I couldn't generate an answer from the retrieved memory. Please try again.";

        setThreads((prev) =>
          prev.map((t) =>
            t.id !== threadId
              ? t
              : {
                  ...t,
                  messages: t.messages.map((m) =>
                    m.id !== assistantId
                      ? m
                      : {
                          ...m,
                          content: finalContent,
                          queryData,
                          answerMode,
                        },
                  ),
                  updatedAt: isoNow(),
                },
          ),
        );
      } catch (e: unknown) {
        const errorMsg =
          e instanceof Error ? e.message : "Failed to query FAIM";
        setError(errorMsg);
        setThreads((prev) =>
          prev.map((t) =>
            t.id !== threadId
              ? t
              : {
                  ...t,
                  messages: t.messages.map((m) =>
                    m.id === assistantId
                      ? { ...m, content: `[Error: ${errorMsg}]` }
                      : m,
                  ),
                },
          ),
        );
      } finally {
        setIsStreaming(false);
        setIsThinking(false);
        setLiveThinkingBuffer("");
      }
    },
    [activeThreadId, messages, isStreaming, answerMode],
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
        answerMode: "direct",
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
                : t,
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
            ],
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
          throw new Error(
            errData.detail || errData.message || `HTTP ${res.status}`,
          );
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
                    m.id === assistantId
                      ? { ...m, content: lines.join("\n") }
                      : m,
                  ),
                  updatedAt: isoNow(),
                }
              : t,
          ),
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
                    m.id === assistantId
                      ? { ...m, content: `[Upload error: ${errorMsg}]` }
                      : m,
                  ),
                }
              : t,
          ),
        );
      } finally {
        setIsUploading(false);
      }
    },
    [activeThreadId, isStreaming, isUploading],
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
        answerMode,
        setAnswerMode,
        isThinking,
        liveThinkingBuffer,
        activeReasoningPath,
        setReasoningPath,
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
