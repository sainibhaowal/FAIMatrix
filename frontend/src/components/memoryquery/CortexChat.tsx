"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import {
  Bot,
  User,
  Send,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Loader2,
  Sparkles,
  HardDrive,
  RefreshCw,
  AlertTriangle,
  MessageSquare,
  Terminal,
  Zap,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useCortexWS, CortexWSMessage, CortexWSMessageType } from "@/hooks/useCortexWS";

interface ToolApproval {
  id: number;
  tool_name: string;
  args: Record<string, unknown>;
  reason: string;
  status: "pending" | "approved" | "rejected";
}

interface CortexChatProps {
  graphId: string;
  tenantId: string;
  sessionId?: string;
  apiKey?: string;
  className?: string;
}

export function CortexChat({
  graphId,
  tenantId,
  sessionId,
  apiKey,
  className = "",
}: CortexChatProps) {
  const [messages, setMessages] = useState<Array<{
    id: string;
    role: "user" | "assistant" | "system";
    content: string;
    type?: CortexWSMessageType;
    payload?: Record<string, unknown>;
    timestamp: string;
  }>>([]);
  const [pendingApprovals, setPendingApprovals] = useState<ToolApproval[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isConnecting, setIsConnecting] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const formatTime = (ts: string) => {
    try {
      return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    } catch {
      return new Date().toLocaleTimeString();
    }
  };

  const handleWSMessage = useCallback((msg: CortexWSMessage) => {
    const timestamp = new Date().toISOString();
    const baseMsg = {
      id: `${msg.type}-${Date.now()}-${Math.random().toString(36).slice(2)}`,
      timestamp,
      payload: msg.payload,
    };

    switch (msg.type) {
      case "session_created":
        setMessages((prev) => [...prev, { ...baseMsg, role: "system", content: `Session created: ${msg.payload?.session_id}`, type: msg.type }]);
        break;
      case "user_message_echo":
        setMessages((prev) => [...prev, { ...baseMsg, role: "user", content: msg.content || "", type: msg.type }]);
        break;
      case "thinking":
        setMessages((prev) => [...prev, { ...baseMsg, role: "assistant", content: (msg.payload?.message as string) || "Cortex is thinking...", type: msg.type }]);
        break;
      case "agent_response":
        setMessages((prev) => [...prev, { ...baseMsg, role: "assistant", content: msg.content || "", type: msg.type, payload: msg.payload }]);
        break;
      case "tool_call":
        setMessages((prev) => [...prev, { ...baseMsg, role: "assistant", content: `🔧 Tool call: ${msg.payload?.tool_name}`, type: msg.type, payload: msg.payload }]);
        break;
      case "tool_result":
        setMessages((prev) => [...prev, { ...baseMsg, role: "system", content: `✅ Tool result: ${JSON.stringify(msg.payload?.result || {})}`, type: msg.type, payload: msg.payload }]);
        break;
      case "tool_approved":
        setMessages((prev) => [...prev, { ...baseMsg, role: "system", content: `✅ Tool approved and executed`, type: msg.type, payload: msg.payload }]);
        setPendingApprovals((prev) => prev.filter((a) => a.id !== (msg.payload?.approval as { approval_id?: number } | undefined)?.approval_id));
        break;
      case "tool_rejected":
        setMessages((prev) => [...prev, { ...baseMsg, role: "system", content: `❌ Tool rejected`, type: msg.type, payload: msg.payload }]);
        setPendingApprovals((prev) => prev.filter((a) => a.id !== msg.payload?.approval_id));
        break;
      case "error":
        setMessages((prev) => [...prev, { ...baseMsg, role: "system", content: `❌ Error: ${msg.payload?.message || "Unknown error"}`, type: msg.type, payload: msg.payload }]);
        break;
      default:
        setMessages((prev) => [...prev, { ...baseMsg, role: "system", content: `[${msg.type}] ${JSON.stringify(msg.payload || {})}`, type: msg.type, payload: msg.payload }]);
    }
  }, []);

  const handleToolCall = useCallback((approvalId: number, toolName: string, args: Record<string, unknown>) => {
    const newApproval: ToolApproval = {
      id: approvalId,
      tool_name: toolName,
      args,
      reason: args.reason as string || "",
      status: "pending",
    };
    setPendingApprovals((prev) => [...prev, newApproval]);
  }, []);

  const {
    connected,
    connecting,
    error: wsError,
    sessionId: wsSessionId,
    sendUserMessage,
    approveTool,
    rejectTool,
    connect,
    disconnect,
  } = useCortexWS({
    graphId,
    tenantId,
    sessionId,
    apiKey,
    onMessage: handleWSMessage,
    onToolCall: handleToolCall,
    onError: (err) => setConnectionError(err),
  });

  const handleSendMessage = async () => {
    const content = inputValue.trim();
    if (!content || !connected) return;

    setInputValue("");
    const sent = sendUserMessage(content);
    if (!sent) {
      alert("Not connected. Please wait for connection.");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleApprove = async (approvalId: number) => {
    const approval = pendingApprovals.find((a) => a.id === approvalId);
    if (!approval) return;

    setPendingApprovals((prev) => prev.map((a) => (a.id === approvalId ? { ...a, status: "approved" } : a)));
    await approveTool(approvalId);
  };

  const handleReject = async (approvalId: number) => {
    const note = prompt("Reason for rejection (optional):") || "";
    setPendingApprovals((prev) => prev.map((a) => (a.id === approvalId ? { ...a, status: "rejected" } : a)));
    await rejectTool(approvalId, note);
  };

  const handleConnect = () => {
    connect();
    setIsConnecting(true);
    setTimeout(() => setIsConnecting(false), 2000);
  };

  const handleDisconnect = () => {
    disconnect();
  };

  const clearMessages = () => {
    setMessages([]);
    setPendingApprovals([]);
  };

  return (
    <div className={`flex flex-col h-full bg-black/20 border border-white/6 rounded-[18px] ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between h-12 px-4 border-b border-white/6 bg-black/30 shrink-0 rounded-t-[18px]">
        <div className="flex items-center gap-3">
          <div className={`flex h-8 w-8 items-center justify-center rounded-lg border ${
            connected ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300" :
            connecting ? "border-amber-500/30 bg-amber-500/10 text-amber-300 animate-pulse" :
            "border-rose-500/30 bg-rose-500/10 text-rose-300"
          }`}>
            <Zap size={16} />
          </div>
          <div>
            <p className="text-xs font-bold tracking-wide text-white">FAIM Cortex WebSocket</p>
            <p className="text-[10px] font-mono text-slate-400">
              {connected ? "Connected" : connecting ? "Connecting..." : wsError ? "Error" : "Disconnected"}
              {wsSessionId && <span className="ml-2 text-[9px] font-mono text-slate-500">Session: {wsSessionId.slice(0, 20)}...</span>}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {connected && (
            <button
              onClick={clearMessages}
              className="px-2 py-1 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 text-slate-400 hover:text-slate-200 text-[10px] font-mono"
              title="Clear chat"
            >
              <Terminal size={12} className="mr-1" /> Clear
            </button>
          )}
          {!connected && !connecting && (
            <button
              onClick={handleConnect}
              className="px-3 py-1.5 rounded-lg border border-cyan-500/30 bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 text-xs font-semibold tracking-wide"
            >
              <RefreshCw size={12} className="mr-1" /> Connect
            </button>
          )}
          {connected && (
            <button
              onClick={handleDisconnect}
              className="px-2 py-1 rounded-lg border border-rose-500/30 bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 text-[10px] font-mono"
              title="Disconnect"
            >
              <XCircle size={12} className="mr-1" /> Disconnect
            </button>
          )}
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-4">
        <AnimatePresence mode="popLayout">
          {messages.map((msg, i) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.3, delay: i * 0.05 }}
              className="w-full"
            >
              {msg.role === "assistant" ? (
                <div className="flex gap-3">
                  <div className="flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center border border-cyan-500/30 bg-cyan-500/10 text-cyan-300">
                    <Bot size={18} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.25em] mb-1">
                      <span className="text-cyan-300">FAIM Cortex</span>
                      <span className="text-slate-600">{new Date(msg.timestamp).toLocaleTimeString()}</span>
                      {msg.type === "tool_call" && <span className="text-amber-400 text-[9px]">TOOL CALL</span>}
                      {msg.type === "tool_result" && <span className="text-emerald-400 text-[9px]">TOOL RESULT</span>}
                      {msg.type === "thinking" && <span className="text-amber-400 text-[9px] animate-pulse">THINKING</span>}
                    </div>
                    <div className="prose prose-sm max-w-none text-slate-300">
                      {msg.payload && msg.type === "agent_response" && msg.payload?.brain_state ? (
                        <>
                          <div className="mb-2 text-[11px] text-slate-500">
                            <span className="font-mono">Turn:</span> {String(msg.payload.turn_id ?? "").slice(0, 16)}... ·{' '}
                            <span className="font-mono">Session:</span> {String(msg.payload.session_id ?? "").slice(0, 16)}...
                          </div>
                          <div className="text-sm whitespace-pre-wrap">{msg.content}</div>
                        </>
                      ) : (
                        <div className="text-sm whitespace-pre-wrap">{msg.content}</div>
                      )}
                    {msg.payload && msg.type === "tool_call" && (
                      <details className="mt-2 text-[11px] text-slate-500">
                        <summary className="cursor-pointer text-amber-400">Tool Call Details</summary>
                        <pre className="mt-1 p-2 bg-black/30 rounded text-[10px] overflow-auto">
                          {JSON.stringify(msg.payload, null, 2)}
                        </pre>
                      </details>
                    )}
                    {msg.payload && msg.type === "tool_result" && (
                      <details className="mt-2 text-[11px] text-slate-500">
                        <summary className="cursor-pointer text-emerald-400">Tool Result Details</summary>
                        <pre className="mt-1 p-2 bg-black/30 rounded text-[10px] overflow-auto">
                          {JSON.stringify(msg.payload, null, 2)}
                        </pre>
                      </details>
                    )}
                    {(() => {
                      const brain = msg.payload?.brain_state as Record<string, unknown> | undefined;
                      if (!brain) return null;
                      return (
                        <details className="mt-2 text-[11px] text-slate-500">
                          <summary className="cursor-pointer text-cyan-400">Brain State</summary>
                          <pre className="mt-1 p-2 bg-black/30 rounded text-[10px] overflow-auto max-h-64">
                            {JSON.stringify({
                              task_type: brain.task_type,
                              confidence: brain.confidence,
                              evidence_count: (brain.evidence_nodes as unknown[])?.length,
                              reasoning_nodes: (brain.reasoning_tree as unknown[])?.length,
                            }, null, 2)}
                          </pre>
                        </details>
                      );
                    })()}
                  </div>
                </div>
              </div>
            ) : msg.role === "user" ? (
              <div className="flex gap-3 justify-end">
                <div className="flex-1 min-w-0" />
                <div className="flex flex-col items-end max-w-[80%]">
                  <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.25em] mb-1 justify-end">
                    <span className="text-slate-400">{new Date(msg.timestamp).toLocaleTimeString()}</span>
                    <span className="text-slate-400">Operator</span>
                  </div>
                  <div
                    className="rounded-2xl bg-cyan-500/20 border border-cyan-500/30 px-4 py-2 text-slate-100 text-sm"
                  >
                    {msg.content}
                  </div>
                </div>
                <div className="flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center border border-slate-600 bg-slate-700/50 text-slate-400">
                  <User size={18} />
                </div>
              </div>
            ) : (
              <div className="flex justify-center">
                <div className="max-w-[80%] px-3 py-1.5 rounded-lg bg-slate-800/50 border border-white/5 text-[11px] text-slate-500 text-center">
                  {msg.type === "error" && <AlertTriangle size={12} className="inline mr-1 text-rose-400" />}
                  {msg.type === "tool_approved" && <CheckCircle2 size={12} className="inline mr-1 text-emerald-400" />}
                  {msg.type === "tool_rejected" && <XCircle size={12} className="inline mr-1 text-rose-400" />}
                  {msg.content}
                  {msg.payload && (
                    <details className="mt-1 text-left">
                      <summary className="cursor-pointer text-[10px] text-slate-400">Details</summary>
                      <pre className="mt-1 p-2 bg-black/30 rounded text-[9px] overflow-auto">
                        {JSON.stringify(msg.payload, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              </div>
            )}
          </motion.div>
          ))}
        </AnimatePresence>
        <div ref={messagesEndRef} />
      </div>

      {/* Pending Approvals Banner */}
      {pendingApprovals.length > 0 && (
        <div className="border-t border-amber-500/30 p-3 bg-amber-500/5">
          <div className="flex items-center gap-2 text-amber-300 mb-2">
            <AlertTriangle size={14} />
            <span className="font-semibold text-xs">Awaiting Human Approval ({pendingApprovals.length})</span>
          </div>
          <div className="space-y-1">
            {pendingApprovals.map((approval) => (
              <div key={approval.id} className="flex items-center gap-2 p-2 bg-black/30 rounded-lg border border-amber-500/20">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1 text-[10px] font-semibold text-amber-300">
                    <HardDrive size={10} />
                    <span>{approval.tool_name}</span>
                    <span className="text-[9px] text-amber-500/80">#{approval.id}</span>
                  </div>
                  <div className="text-[9px] text-slate-400 truncate">
                    {JSON.stringify(approval.args).slice(0, 80)}...
                  </div>
                </div>
                <button
                  onClick={() => handleApprove(approval.id)}
                  className="px-2 py-1 text-[10px] font-semibold rounded bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/30 transition"
                >
                  Approve
                </button>
                <button
                  onClick={() => handleReject(approval.id)}
                  className="px-2 py-1 text-[10px] font-semibold rounded bg-rose-500/20 border border-rose-500/30 text-rose-300 hover:bg-rose-500/30 transition"
                >
                  Reject
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Input Area */}
      <div className="border-t border-white/6 p-3 bg-black/30 shrink-0 rounded-b-[18px]">
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={connected ? "Ask Cortex anything..." : "Connect to start chatting..."}
            disabled={!connected}
            rows={1}
            className="flex-1 resize-none bg-black/50 border border-white/10 rounded-xl px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-cyan-500/50 focus:outline-none focus:ring-1 focus:ring-cyan-500/50 disabled:opacity-50"
            style={{ minHeight: "44px", maxHeight: "120px" }}
          />
          <button
            onClick={handleSendMessage}
            disabled={!connected || !inputValue.trim()}
            className="flex-shrink-0 h-10 w-10 rounded-xl flex items-center justify-center border border-cyan-500/30 bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 disabled:opacity-50 disabled:cursor-not-allowed transition"
            aria-label="Send message"
          >
            <Send size={18} />
          </button>
        </div>
        <div className="flex items-center justify-between mt-2 text-[10px] text-slate-500">
          <span>WebSocket: {connected ? "🟢 Live" : connecting ? "🟡 Connecting..." : "🔴 Offline"}</span>
          <span>Session: {sessionId || wsSessionId || "auto"}</span>
        </div>
      </div>
    </div>
  );
}

export default CortexChat;