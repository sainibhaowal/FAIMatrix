"use client";

/**
 * Chat Context
 *
 * Manages chat message state and streaming logic.
 * Calls /api/provider/chat and streams tokens in real-time.
 */

import React, { createContext, useContext, useState, useCallback } from "react";
import { useProviders } from "./ProviderContext";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

interface ChatContextType {
  messages: Message[];
  isStreaming: boolean;
  error: string | null;
  sendMessage: (content: string) => Promise<void>;
  clearMessages: () => void;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

const FAIM_SYSTEM_PROMPT = `You are FAIM Sentinel, an AI assistant connected to the user's memory graph. Answer questions about their stored memories, knowledge, and context. Be concise and precise.`;

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { activeProvider } = useProviders();

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isStreaming) return;
      if (!activeProvider) {
        setError("No active provider selected");
        return;
      }

      // Clear previous errors
      setError(null);

      // Create user message
      const userMsg: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content: content.trim(),
        timestamp: new Date().toLocaleTimeString("en-US", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: false,
        }),
      };

      // Create empty assistant message (will be filled with tokens)
      const assistantId = crypto.randomUUID();
      const assistantMsg: Message = {
        id: assistantId,
        role: "assistant",
        content: "",
        timestamp: new Date().toLocaleTimeString("en-US", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: false,
        }),
      };

      // Add messages to state
      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsStreaming(true);

      try {
        // Prepare messages payload (exclude system prompt from history)
        const historyMessages = messages
          .filter((m) => m.role !== "assistant" || m.content) // Skip empty assistant messages
          .map((m) => ({
            role: m.role,
            content: m.content,
          }));

        const res = await fetch("/api/provider/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            providerUrl: activeProvider.baseUrl,
            apiKey: activeProvider.apiKey,
            model: activeProvider.activeModel,
            messages: [...historyMessages, { role: "user", content: userMsg.content }],
            systemPrompt: FAIM_SYSTEM_PROMPT,
          }),
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.message || `HTTP ${res.status}`);
        }

        // Stream the response
        const reader = res.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();

          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");

          // Keep the last incomplete line in the buffer
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;

            const data = line.slice(6).trim();

            // Skip the [DONE] marker
            if (data === "[DONE]") continue;

            // Skip empty lines
            if (!data) continue;

            try {
              const json = JSON.parse(data);

              // Extract token from OpenAI-compatible format
              const token = json.choices?.[0]?.delta?.content ?? "";

              if (token) {
                // Append token to the assistant message
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId ? { ...m, content: m.content + token } : m
                  )
                );
              }
            } catch (e) {
              // Skip lines that aren't valid JSON (e.g., heartbeats)
            }
          }
        }
      } catch (e: any) {
        const errorMsg = e.message || "Failed to get response from provider";
        setError(errorMsg);

        // Mark assistant message with error indicator
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: `[Error: ${errorMsg}]` }
              : m
          )
        );
      } finally {
        setIsStreaming(false);
      }
    },
    [messages, isStreaming, activeProvider]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return (
    <ChatContext.Provider
      value={{
        messages,
        isStreaming,
        error,
        sendMessage,
        clearMessages,
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
