"use client";

import React, { useState, useEffect } from "react";
import {
  BrainCircuit,
  Zap,
  BookOpen,
  Wifi,
  X,
} from "lucide-react";
import { ChatInterface } from "@/components/memoryquery/ChatInterface";
import { ChatComposer } from "@/components/memoryquery/ChatComposer";
import { HistoryPanel } from "@/components/memoryquery/HistoryPanel";
import { ApprovalHistoryPanel } from "@/components/memoryquery/ApprovalHistoryPanel";
import { CortexChat } from "@/components/memoryquery/CortexChat";
import { CortexManual } from "@/components/manuals/CortexManual";
import { useUser } from "@/contexts/UserContext";

type ChatMode = "http" | "websocket";

export default function MemoryQueryPage() {
  const { graphId } = useUser();
  const [isManualModalOpen, setIsManualModalOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [chatMode, setChatMode] = useState<ChatMode>("http");
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <div className="flex h-full text-slate-100 overflow-hidden bg-transparent relative">
      {/* Main Workspace Column */}
      <div className="flex-1 flex flex-col min-w-0 h-full relative">
        {/* ── Top Header Toolbar with Small Cortex Manual Button ────────────────── */}
        <div className="h-12 border-b border-white/6 px-4 flex items-center justify-between bg-black/20 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg border border-cyan-500/30 bg-cyan-500/10 text-cyan-300">
              <BrainCircuit size={16} />
            </div>
            <span className="text-xs font-bold tracking-wide text-white">
              FAIM Cortex
            </span>
            <span className="inline-flex items-center gap-1 rounded-full border border-cyan-400/25 bg-cyan-500/10 px-2 py-0.5 text-[9px] font-semibold text-cyan-300">
              <Zap size={9} /> Active Engine
            </span>
            <div className="ml-2 flex items-center gap-1 rounded-lg border border-white/10 bg-black/30 p-0.5">
              <button
                onClick={() => setChatMode("http")}
                className={`rounded-md px-2 py-0.5 text-[10px] font-semibold transition ${
                  chatMode === "http" ? "bg-cyan-500/20 text-cyan-300" : "text-slate-500 hover:text-slate-300"
                }`}
                title="HTTP Query Mode"
              >
                HTTP
              </button>
              <button
                onClick={() => setChatMode("websocket")}
                className={`rounded-md px-2 py-0.5 text-[10px] font-semibold transition ${
                  chatMode === "websocket" ? "bg-cyan-500/20 text-cyan-300" : "text-slate-500 hover:text-slate-300"
                }`}
                title="Real-time WebSocket Chat Mode"
              >
                <Wifi size={10} className="inline mr-1" />
                WebSocket
              </button>
            </div>
            <button
              onClick={() => setIsManualModalOpen(true)}
              className="ml-2 flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 text-slate-300 hover:text-slate-100 text-xs font-semibold"
              title="Open User Manual"
            >
              <BookOpen size={12} className="text-cyan-400" />
              User Manual
            </button>
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="ml-2 flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 text-slate-300 hover:text-slate-100 text-xs font-semibold"
              title={sidebarOpen ? "Hide sidebar" : "Show sidebar"}
            >
              {sidebarOpen ? <X size={14} /> : <BookOpen size={14} className="text-cyan-400" />}
              {sidebarOpen ? "Hide" : "Sidebar"}
            </button>
          </div>
        </div>

        {/* Workspace: Dynamic Message Stream + Composer */}
        <div className="flex-1 flex flex-col min-h-0 relative">
          {chatMode === "http" ? (
            <>
              <ChatInterface />
              <div className="absolute bottom-0 left-0 right-0 z-30 invisible pointer-events-none">
                <div className="visible pointer-events-auto w-full">
                  <ChatComposer />
                </div>
              </div>
            </>
          ) : (
            <CortexChat
              graphId={graphId || "default-graph"}
              tenantId="default"
            />
          )}
        </div>
      </div>

      {/* Intelligence Sidebar - Floating Right Anchor */}
      <div className={`shrink-0 h-full w-[360px] pt-2.5 pl-2.5 pr-2.5 pb-0 ${sidebarOpen ? "block" : "hidden xl:block"}`}>
        <div
          className="h-full rounded-t-[28px] overflow-hidden border-t border-l border-r shadow-2xl"
          style={{
            borderColor: "rgba(255,255,255,0.08)",
            background: "linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))",
          }}
        >
          <HistoryPanel />
          <ApprovalHistoryPanel />
        </div>
      </div>

      {/* ── UNIFIED MANUAL MODAL ────────────────────────────────────────────── */}
      {mounted && (
        <CortexManual
          open={isManualModalOpen}
          onClose={() => setIsManualModalOpen(false)}
        />
      )}
    </div>
  );
}
