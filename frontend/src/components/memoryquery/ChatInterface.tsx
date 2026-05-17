"use client";

import React, { useEffect, useRef } from "react";
import { User, Bot, MessageSquarePlus, Database } from "lucide-react";
import { motion } from "framer-motion";
import { ANSWER_MODE_LABELS, useChat } from "@/contexts/ChatContext";
import { MarkdownRenderer } from "./MarkdownRenderer";
import { ThinkingPane } from "./ThinkingPane";
import { MemoryTraceFooter } from "./QueryAnswerCard";
import { CortexStatePanel } from "./CortexStatePanel";

export function ChatInterface() {
  const {
    messages,
    isStreaming,
    newThread,
    activeThreadId,
    isThinking,
    liveThinkingBuffer,
  } = useChat();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Empty state: no messages in current thread (or no thread selected)
  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="flex flex-col items-center gap-5 text-center px-8 max-w-sm"
        >
          <div className="w-14 h-14 rounded-2xl bg-primary-500/10 border border-primary-500/20 flex items-center justify-center">
            <Bot size={26} className="text-primary-400" />
          </div>
          <div className="space-y-2">
            <h3 className="text-base font-bold text-white tracking-tight">
              {activeThreadId ? "Session is empty" : "Start a memory session"}
            </h3>
            <p className="text-[12px] text-slate-500 leading-relaxed">
              {
                "Type a message below to ask FAIM Cortex to run a structured brain turn over your memory graph. Switch the answer mode to Direct, Timeline, Contradiction, or Provenance for different reasoning styles. Answers stay grounded in citations, provenance, contradiction notes, and the Cortex state tree."
              }
            </p>
          </div>
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-primary-500/10 border border-primary-500/20">
            <Database size={13} className="text-primary-300 flex-shrink-0" />
            <span className="text-[11px] text-primary-300 font-semibold">
              FAIM Cortex active
            </span>
          </div>
          <button
            onClick={newThread}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary-500/10 border border-primary-500/20 hover:bg-primary-500/20 text-primary-300 text-[12px] font-bold uppercase tracking-widest transition-all"
          >
            <MessageSquarePlus size={14} />
            New Session
          </button>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto custom-scrollbar">
      <div className="max-w-4xl mx-auto py-10 px-6 space-y-10">
        {messages.map((msg, i) => (
          <motion.div
            key={msg.id}
            initial={{ opacity: 0, x: -8, filter: "blur(12px)" }}
            animate={{ opacity: 1, x: 0, filter: "blur(0px)" }}
            transition={{
              duration: 0.6,
              delay: i * 0.15,
              ease: [0.16, 1, 0.3, 1],
            }}
            className="w-full"
          >
            {msg.role === "assistant" ? (
              <article className="w-full rounded-[30px] border border-white/8 bg-[var(--os-surface-1)]/95 px-6 py-6 sm:px-8 sm:py-7 shadow-[0_24px_80px_rgba(0,0,0,0.28)]">
                <div className="flex flex-wrap items-center gap-2 text-[9px] font-black uppercase tracking-[0.28em]">
                  <span className="text-primary-300">FAIM Cortex</span>
                  <span className="rounded-full border border-primary-500/15 bg-primary-500/5 px-2.5 py-1 text-[8px] text-primary-300">
                    {ANSWER_MODE_LABELS[msg.answerMode ?? "direct"]}
                  </span>
                  {msg.cortexData?.task_type && (
                    <span className="rounded-full border border-violet-500/15 bg-violet-500/5 px-2.5 py-1 text-[8px] text-violet-300">
                      {msg.cortexData.task_type}
                    </span>
                  )}
                  <span className="text-slate-600 tracking-tighter">
                    {msg.timestamp}
                  </span>
                </div>

                {msg.cortexData?.brain_state ? (
                  <div className="mt-3 grid gap-2 rounded-2xl border border-white/8 bg-white/[0.02] p-3 text-[10px] text-slate-400 sm:grid-cols-3">
                    <div>
                      <div className="text-[8px] font-black uppercase tracking-[0.24em] text-slate-600">
                        Session Turns
                      </div>
                      <div className="mt-1 text-slate-200">
                        {msg.cortexData.brain_state.session_turn_count}
                      </div>
                    </div>
                    <div className="sm:col-span-2">
                      <div className="text-[8px] font-black uppercase tracking-[0.24em] text-slate-600">
                        Session Summary
                      </div>
                      <div className="mt-1 text-slate-200 leading-6">
                        {msg.cortexData.brain_state.session_summary ||
                          "Single-turn session so far."}
                      </div>
                    </div>
                  </div>
                ) : null}

                {msg.thinking || (isThinking && i === messages.length - 1) ? (
                  <div className="mt-4">
                    <ThinkingPane
                      content={msg.thinking ?? liveThinkingBuffer}
                      durationMs={msg.thinkingDurationMs}
                      isActive={isThinking && i === messages.length - 1}
                    />
                  </div>
                ) : null}

                <div className="mt-4 space-y-4">
                  {msg.content ? (
                    <div className="prose-faim max-w-none">
                      <MarkdownRenderer content={msg.content} />
                    </div>
                  ) : (
                    isStreaming && (
                      <motion.span
                        animate={{ opacity: [0.4, 1, 0.4] }}
                        transition={{ duration: 1.5, repeat: Infinity }}
                        className="inline-block text-primary-400 text-lg"
                      >
                        ▌
                      </motion.span>
                    )
                  )}
                  {msg.cortexData && (
                    <CortexStatePanel cortexData={msg.cortexData} />
                  )}
                  {msg.queryData && (
                    <MemoryTraceFooter
                      queryData={msg.queryData}
                      answerMode={msg.answerMode ?? "direct"}
                    />
                  )}
                </div>
              </article>
            ) : (
              <div className="flex gap-6 w-full group relative">
                {/* High-Precision Identity Column */}
                <div className="flex flex-col items-center shrink-0 w-10">
                  <div className="w-10 h-10 rounded-xl flex items-center justify-center border transition-all duration-500 shadow-2xl overflow-hidden bg-white/5 border-white/10 text-slate-500 group-hover:text-slate-300">
                    <User size={20} />
                  </div>
                  <div className="flex-1 w-[1px] bg-gradient-to-b from-slate-800 to-transparent mt-4 opacity-30" />
                </div>

                <div className="flex-1 space-y-3 min-w-0">
                  <div className="flex items-center gap-3">
                    <span className="text-[10px] font-black uppercase tracking-[0.25em] text-slate-400">
                      Operator_Identity
                    </span>
                    <div className="h-[1px] w-2 bg-slate-800" />
                    <span className="text-[9px] font-mono text-slate-600 tracking-tighter uppercase">
                      {msg.timestamp}
                    </span>
                  </div>

                  <div className="max-w-[90%] transition-colors duration-300">
                    <p className="text-[14px] leading-7 text-slate-300 group-hover:text-slate-100">
                      {msg.content}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </motion.div>
        ))}
      </div>

      {/* Auto-scroll anchor */}
      <div ref={bottomRef} className="h-32" />
    </div>
  );
}
