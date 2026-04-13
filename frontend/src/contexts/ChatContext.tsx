"use client";

/**
 * Chat Context — Multi-Thread Edition
 *
 * Manages threads (conversations) and streaming.
 * Threads are persisted to localStorage under "faim.threads".
 */

import React, { createContext, useContext, useState, useCallback, useEffect } from "react";
import { getSession } from "next-auth/react";

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
  const messages = activeThread?.messages ?? [];

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

      try {
        const graphId = await resolveActiveGraphId();
        if (!graphId) {
          throw new Error("No active graph found for memory query");
        }

        const headers = await buildAuthorizedHeaders();
        const res = await fetch("/api/v1/query", {
          method: "POST",
          headers: { "Content-Type": "application/json", ...headers },
          body: JSON.stringify({
            graph_id: graphId,
            query_text: userMsg.content,
            k: 8,
            profile: "STRICT",
            return_explain: true,
          }),
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || errData.message || `HTTP ${res.status}`);
        }

        const queryData = (await res.json()) as FaimQueryResponse;
        const fallbackContent =
          queryData.answer || queryData.results?.length
            ? "FAIM retrieved evidence and prepared a structured answer."
            :
          (queryData.results?.length
            ? `Retrieved ${queryData.results.length} matching memory result${queryData.results.length === 1 ? "" : "s"}.`
            : "No matching memory found.");

        setThreads((prev) =>
          prev.map((t) => {
            if (t.id !== threadId) return t;
            return {
              ...t,
              messages: t.messages.map((m) =>
                m.id === assistantId
                  ? {
                      ...m,
                      content: fallbackContent,
                      queryData,
                    }
                  : m
              ),
            };
          })
        );
      } catch (e: any) {
        const errorMsg = e.message || "Failed to query FAIM";
        setError(errorMsg);
        setThreads((prev) =>
          prev.map((t) => {
            if (t.id !== threadId) return t;
            return {
              ...t,
              messages: t.messages.map((m) =>
                m.id === assistantId ? { ...m, content: `[Error: ${errorMsg}]` } : m
              ),
            };
          })
        );
      } finally {
        setIsStreaming(false);
        setIsThinking(false);
      }
    },
    [activeThreadId, messages, isStreaming]
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
