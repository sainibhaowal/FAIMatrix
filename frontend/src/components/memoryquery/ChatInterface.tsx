"use client";

import React, { useEffect, useRef } from "react";
import { User, Bot, MessageSquarePlus, Database } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useChat } from "@/contexts/ChatContext";
import { MarkdownRenderer } from "./MarkdownRenderer";
import { ThinkingPane } from "./ThinkingPane";
import { QueryAnswerCard } from "./QueryAnswerCard";

export function ChatInterface() {
  const { messages, isStreaming, newThread, activeThreadId, isThinking, liveThinkingBuffer } = useChat();
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
              {activeThreadId ? "Thread is empty" : "Start a conversation"}
            </h3>
            <p className="text-[12px] text-slate-500 leading-relaxed">
              {"Type a message below to query your memory graph. FAIM answer synthesis, citations, provenance, and explain data render directly from backend query results."}
            </p>
          </div>
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-primary-500/10 border border-primary-500/20">
            <Database size={13} className="text-primary-300 flex-shrink-0" />
            <span className="text-[11px] text-primary-300 font-semibold">FAIM query path active</span>
          </div>
          <button
            onClick={newThread}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary-500/10 border border-primary-500/20 hover:bg-primary-500/20 text-primary-300 text-[12px] font-bold uppercase tracking-widest transition-all"
          >
            <MessageSquarePlus size={14} />
            New Thread
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
            transition={{ duration: 0.6, delay: i * 0.15, ease: [0.16, 1, 0.3, 1] }}
            className="flex gap-6 w-full group relative"
          >
            {/* High-Precision Identity Column */}
            <div className="flex flex-col items-center shrink-0 w-10">
              <div 
                className={`w-10 h-10 rounded-xl flex items-center justify-center border transition-all duration-500 shadow-2xl overflow-hidden ${
                  msg.role === 'assistant' 
                    ? 'bg-primary-500/10 border-primary-500/30 text-primary-300 shadow-primary-500/10' 
                    : 'bg-white/5 border-white/10 text-slate-500 group-hover:text-slate-300'
                }`}
              >
                {msg.role === 'assistant' ? <Bot size={20} /> : <User size={20} />}
              </div>
              <div className="flex-1 w-[1px] bg-gradient-to-b from-slate-800 to-transparent mt-4 opacity-30" />
            </div>
            
            <div className="flex-1 space-y-3 min-w-0">
              {/* Minimalist Message Header */}
              <div className="flex items-center gap-3">
                <span className={`text-[10px] font-black uppercase tracking-[0.25em] ${msg.role === 'assistant' ? 'text-primary-300' : 'text-slate-400'}`}>
                  {msg.role === 'assistant' ? 'FAIM SentineL' : 'Operator_Identity'}
                </span>
                <div className="h-[1px] w-2 bg-slate-800" />
                <span className="text-[9px] font-mono text-slate-600 tracking-tighter uppercase">{msg.timestamp}</span>
              </div>

              {/* Thinking Pane (for assistant messages) */}
              {msg.role === 'assistant' && (msg.thinking || (isThinking && i === messages.length - 1)) && (
                <ThinkingPane
                  content={msg.thinking ?? liveThinkingBuffer}
                  durationMs={msg.thinkingDurationMs}
                  isActive={isThinking && i === messages.length - 1}
                />
              )}

              {/* Rendered Content */}
              <div className="max-w-[90%] transition-colors duration-300">
                {msg.role === "user" ? (
                  <p className="text-[14px] leading-7 text-slate-300 group-hover:text-slate-100">
                    {msg.content}
                  </p>
                ) : (
                  <div className="space-y-4">
                    {msg.content ? (
                      <div className="prose-faim">
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
                    {msg.queryData && <QueryAnswerCard queryData={msg.queryData} />}
                  </div>
                )}
              </div>

              {/* Action Ribbon (Internal/Contextual) */}
              {msg.role === 'assistant' && (
                <div className="flex items-center gap-4 pt-2 opacity-0 group-hover:opacity-100 transition-all duration-500 translate-y-1 group-hover:translate-y-0">
                  <div className="flex items-center gap-1.5 cursor-pointer hover:text-primary-300 transition-colors">
                    <div className="w-1 h-1 rounded-full bg-primary-500/50" />
                    <span className="text-[9px] font-black uppercase tracking-widest text-slate-600">Trace Vector</span>
                  </div>
                  <div className="flex items-center gap-1.5 cursor-pointer hover:text-emerald-400 transition-colors">
                    <div className="w-1 h-1 rounded-full bg-emerald-500/50" />
                    <span className="text-[9px] font-black uppercase tracking-widest text-slate-600">Memory Commit</span>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        ))}
      </div>

      {/* Auto-scroll anchor */}
      <div ref={bottomRef} className="h-32" />
    </div>
  );
}
