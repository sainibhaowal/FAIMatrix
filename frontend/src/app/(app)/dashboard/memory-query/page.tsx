"use client";

import React from "react";
import { Search } from "lucide-react";
import { GlassHeader } from "@/components/layout/GlassHeader";
import { ChatInterface } from "@/components/memoryquery/ChatInterface";
import { ChatComposer } from "@/components/memoryquery/ChatComposer";
import { HistoryPanel } from "@/components/memoryquery/HistoryPanel";
import { ChatProvider } from "@/contexts/ChatContext";

export default function MemoryQueryPage() {
  return (
    <ChatProvider>
      <div className="flex h-full text-slate-100 overflow-hidden bg-[var(--os-bg)]">
        {/*
            Main Command Space
            - Navigation is the global sidebar
            - Center: Dynamic Message Stream
            - Right: Intelligence History Pane
        */}
        <div className="flex-1 flex flex-col min-w-0 h-full relative">
          {/* Workspace: Message Stream + Composer */}
          <div className="flex-1 flex flex-col min-h-0 relative">
            <ChatInterface />

            <div className="absolute bottom-0 left-0 right-0 z-30 invisible pointer-events-none">
              <div className="visible pointer-events-auto w-full">
                <ChatComposer />
              </div>
            </div>
          </div>
        </div>

        {/* Intelligence Sidebar - Floating Right Anchor */}
        <div className="hidden xl:block shrink-0 h-full w-[360px] pt-2.5 pl-2.5 pr-2.5 pb-0">
          <div
            className="h-full rounded-t-[28px] overflow-hidden border-t border-l border-r shadow-2xl"
            style={{
              borderColor: "var(--os-stroke)",
              background: "var(--os-surface-1)",
            }}
          >
            <HistoryPanel />
          </div>
        </div>
      </div>
    </ChatProvider>
  );
}
