"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export type CortexWSMessageType =
  | "user_message"
  | "agent_response"
  | "thinking"
  | "tool_call"
  | "tool_result"
  | "tool_approved"
  | "tool_rejected"
  | "session_created"
  | "error"
  | "ping"
  | "pong"
  | "user_message_echo"
  | "approve_tool"
  | "reject_tool";

export interface CortexWSMessage {
  type: CortexWSMessageType;
  session_id?: string;
  graph_id: string;
  content?: string;
  payload?: Record<string, unknown>;
}

export interface CortexWSState {
  connected: boolean;
  connecting: boolean;
  error: string | null;
  sessionId: string | null;
  messages: CortexWSMessage[];
}

export interface UseCortexWSOptions {
  graphId: string;
  tenantId: string;
  sessionId?: string;
  apiKey?: string;
  onMessage?: (message: CortexWSMessage) => void;
  onToolCall?: (approvalId: number, toolName: string, args: Record<string, unknown>) => void;
  onError?: (error: string) => void;
}

export function useCortexWS({
  graphId,
  tenantId,
  sessionId,
  apiKey,
  onMessage,
  onToolCall,
  onError,
}: UseCortexWSOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;
  const baseReconnectDelay = 1000;

  const [state, setState] = useState<CortexWSState>({
    connected: false,
    connecting: false,
    error: null,
    sessionId: null,
    messages: [],
  });

  const addMessage = useCallback((msg: CortexWSMessage) => {
    setState((prev) => ({
      ...prev,
      messages: [...prev.messages, msg],
    }));
    onMessage?.(msg);
  }, [onMessage]);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    if (state.connecting) return;

    setState((prev) => ({ ...prev, connecting: true, error: null }));

    const wsUrl = new URL(`${process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000"}/api/v1/cortex/ws/chat`);
    wsUrl.searchParams.set("graph_id", graphId);
    if (sessionId) wsUrl.searchParams.set("session_id", sessionId);

    const ws = new WebSocket(wsUrl.toString());
    wsRef.current = ws;

    ws.onopen = () => {
      setState((prev) => ({ ...prev, connected: true, connecting: false, error: null, sessionId: sessionId || `ws_${graphId}` }));
      reconnectAttemptsRef.current = 0;
      console.log("[CortexWS] Connected");
    };

    ws.onmessage = (event) => {
      try {
        const msg: CortexWSMessage = JSON.parse(event.data);
        addMessage(msg);

        // Handle tool calls that need approval
        if (msg.type === "tool_call" && msg.payload) {
          const approvalId = msg.payload.approval_id as number;
          const toolName = msg.payload.tool_name as string;
          const args = msg.payload.args as Record<string, unknown>;
          onToolCall?.(approvalId, toolName, args);
        }
      } catch (e) {
        console.error("[CortexWS] Failed to parse message:", e);
      }
    };

    ws.onclose = (event) => {
      setState((prev) => ({ ...prev, connected: false, connecting: false }));
      console.log("[CortexWS] Disconnected:", event.code, event.reason);

      // Attempt reconnect
      if (reconnectAttemptsRef.current < maxReconnectAttempts) {
        const delay = baseReconnectDelay * Math.pow(2, reconnectAttemptsRef.current);
        reconnectTimeoutRef.current = setTimeout(() => {
          reconnectAttemptsRef.current += 1;
          connect();
        }, delay);
      } else {
        setState((prev) => ({ ...prev, error: "Max reconnection attempts reached" }));
        onError?.("Max reconnection attempts reached");
      }
    };

    ws.onerror = (event) => {
      console.error("[CortexWS] Error:", event);
      setState((prev) => ({ ...prev, error: "WebSocket error" }));
      onError?.("WebSocket connection error");
    };
  }, [graphId, sessionId, addMessage, onToolCall, onError]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close(1000, "Client disconnect");
      wsRef.current = null;
    }
    setState((prev) => ({ ...prev, connected: false, connecting: false }));
  }, []);

  const sendMessage = useCallback((message: Omit<CortexWSMessage, "session_id" | "graph_id">) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const msg: CortexWSMessage = {
        ...message,
        session_id: state.sessionId ?? undefined,
        graph_id: graphId,
      };
      wsRef.current.send(JSON.stringify(msg));
      return true;
    }
    return false;
  }, [graphId]);

  const sendUserMessage = useCallback((content: string) => {
    return sendMessage({
      type: "user_message",
      content,
    });
  }, [sendMessage]);

  const approveTool = useCallback((approvalId: number, note?: string) => {
    return sendMessage({
      type: "approve_tool",
      payload: { approval_id: approvalId, note },
    });
  }, [sendMessage]);

  const rejectTool = useCallback((approvalId: number, note?: string) => {
    return sendMessage({
      type: "reject_tool",
      payload: { approval_id: approvalId, note },
    });
  }, [sendMessage]);

  const ping = useCallback(() => {
    return sendMessage({ type: "ping" });
  }, [sendMessage]);

  // Auto-connect on mount
  useEffect(() => {
    connect();
    return () => {
      disconnect();
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connect, disconnect]);

  // Periodic ping to keep connection alive
  useEffect(() => {
    if (!state.connected) return;
    const interval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        ping();
      }
    }, 30000);
    return () => clearInterval(interval);
  }, [state.connected, ping]);

  return {
    ...state,
    connect,
    disconnect,
    sendMessage,
    sendUserMessage,
    approveTool,
    rejectTool,
    ping,
  };
}

export type CortexWSMessageInput = Omit<CortexWSMessage, "session_id" | "graph_id">;