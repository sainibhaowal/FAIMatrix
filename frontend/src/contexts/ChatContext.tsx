"use client";

/**
 * Chat Context — Multi-Thread Edition
 *
 * Manages threads (conversations) and streaming.
 * Threads are persisted to localStorage under "faim.threads".
 */

import React, { createContext, useContext, useState, useCallback, useEffect } from "react";
import { useProviders } from "./ProviderContext";

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

// ---------------------------------------------------------------------------
// System prompt
// ---------------------------------------------------------------------------

const FAIM_SYSTEM_PROMPT =
  "You are FAIM Sentinel, an AI assistant connected to the user's memory graph. Answer questions about their stored memories, knowledge, and context. Be concise and precise.";

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const [threads, setThreads] = useState<Thread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [thinkingEnabled, setThinkingEnabled] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [liveThinkingBuffer, setLiveThinkingBuffer] = useState("");
  const { activeProvider } = useProviders();

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
      if (!activeProvider) {
        setError("No active provider selected");
        return;
      }

      setError(null);

      // Ensure we have an active thread; create one on first message
      let threadId = activeThreadId;
      let currentMessages: Message[] = messages;

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
        currentMessages = [];
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
      };

      // Append messages to thread; auto-title on first user message
      setThreads((prev) =>
        prev.map((t) => {
          if (t.id !== threadId) return t;
          const isFirst = t.messages.length === 0;
          return {
            ...t,
            title: isFirst ? makeTitle(content) : t.title,
            messages: [...t.messages, userMsg, assistantMsg],
            updatedAt: isoNow(),
          };
        })
      );

      setIsStreaming(true);
      setIsThinking(false);
      setLiveThinkingBuffer("");

      // Refs for thinking accumulation (not state, to avoid re-renders on every token)
      const thinkingAccRef = { current: "" };
      const thinkingStartRef = { current: null as number | null };
      const inThinkBlockRef = { current: false };
      const contentAccRef = { current: "" };
      const lastThinkBufferUpdateRef = { current: 0 };

      try {
        const historyPayload = currentMessages
          .filter((m) => m.role !== "assistant" || m.content)
          .map((m) => ({ role: m.role, content: m.content }));

        const res = await fetch("/api/provider/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            providerUrl: activeProvider.baseUrl,
            apiKey: activeProvider.apiKey,
            model: activeProvider.activeModel,
            messages: [...historyPayload, { role: "user", content: userMsg.content }],
            systemPrompt: FAIM_SYSTEM_PROMPT,
          }),
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.message || `HTTP ${res.status}`);
        }

        const reader = res.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const data = line.slice(6).trim();
            if (data === "[DONE]" || !data) continue;

            try {
              const json = JSON.parse(data);
              const token = json.choices?.[0]?.delta?.content ?? "";
              const reasoningToken = json.choices?.[0]?.delta?.reasoning_content ?? "";

              // Handle thinking tokens (LM Studio / LLaMA.cpp style with <think> tags)
              if (token) {
                contentAccRef.current += token;

                // Check for <think> opening tag
                if (!inThinkBlockRef.current && contentAccRef.current.includes("<think>")) {
                  inThinkBlockRef.current = true;
                  thinkingStartRef.current = Date.now();
                  setIsThinking(true);
                }

                // Extract thinking content between <think> and </think>
                if (inThinkBlockRef.current) {
                  thinkingAccRef.current += token;

                  // Check for closing </think> tag
                  if (thinkingAccRef.current.includes("</think>")) {
                    inThinkBlockRef.current = false;
                    const duration = thinkingStartRef.current ? Date.now() - thinkingStartRef.current : 0;

                    // Extract content before and after thinking block
                    const beforeThink = contentAccRef.current.split("<think>")[0];
                    const thinkContent = thinkingAccRef.current.split("<think>")[1]?.split("</think>")[0] ?? "";
                    const afterThink = contentAccRef.current.split("</think>")[1] ?? "";
                    contentAccRef.current = beforeThink + afterThink;
                    thinkingAccRef.current = thinkContent;

                    // Flush to message
                    setThreads((prev) =>
                      prev.map((t) => {
                        if (t.id !== threadId) return t;
                        return {
                          ...t,
                          messages: t.messages.map((m) =>
                            m.id === assistantId
                              ? {
                                  ...m,
                                  thinking: thinkingAccRef.current,
                                  thinkingDurationMs: duration,
                                  content: contentAccRef.current,
                                }
                              : m
                          ),
                        };
                      })
                    );
                    setLiveThinkingBuffer("");
                    setIsThinking(false);
                  } else {
                    // Still thinking - throttle buffer updates to 100ms
                    const now = Date.now();
                    if (now - lastThinkBufferUpdateRef.current > 100) {
                      setLiveThinkingBuffer(thinkingAccRef.current);
                      lastThinkBufferUpdateRef.current = now;
                    }
                  }
                } else {
                  // Normal content (outside thinking block)
                  setThreads((prev) =>
                    prev.map((t) => {
                      if (t.id !== threadId) return t;
                      return {
                        ...t,
                        messages: t.messages.map((m) =>
                          m.id === assistantId ? { ...m, content: contentAccRef.current } : m
                        ),
                      };
                    })
                  );
                }
              }

              // Handle OpenAI o1/o3 style reasoning_content
              if (reasoningToken) {
                if (!thinkingStartRef.current) {
                  thinkingStartRef.current = Date.now();
                  setIsThinking(true);
                }
                thinkingAccRef.current += reasoningToken;

                // Throttle buffer updates
                const now = Date.now();
                if (now - lastThinkBufferUpdateRef.current > 100) {
                  setLiveThinkingBuffer(thinkingAccRef.current);
                  lastThinkBufferUpdateRef.current = now;
                }
              }
            } catch {}
          }
        }

        // Flush any remaining thinking content
        if (thinkingAccRef.current && thinkingStartRef.current) {
          const duration = Date.now() - thinkingStartRef.current;
          setThreads((prev) =>
            prev.map((t) => {
              if (t.id !== threadId) return t;
              return {
                ...t,
                messages: t.messages.map((m) =>
                  m.id === assistantId
                    ? {
                        ...m,
                        thinking: thinkingAccRef.current,
                        thinkingDurationMs: duration,
                        content: contentAccRef.current,
                      }
                    : m
                ),
              };
            })
          );
        }

        setIsThinking(false);
        setLiveThinkingBuffer("");
      } catch (e: any) {
        const errorMsg = e.message || "Failed to get response from provider";
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
    [activeThreadId, messages, isStreaming, activeProvider]
  );

  return (
    <ChatContext.Provider
      value={{
        messages,
        isStreaming,
        error,
        threads,
        activeThreadId,
        switchThread,
        newThread,
        deleteThread,
        renameThread,
        purgeAllThreads,
        sendMessage,
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
