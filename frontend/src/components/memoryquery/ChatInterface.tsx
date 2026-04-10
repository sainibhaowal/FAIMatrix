"use client";

import React from "react";
import { User, Zap, Bot } from "lucide-react";
import { motion } from "framer-motion";
import { useChat } from "@/contexts/ChatContext";
import { useProviders } from "@/contexts/ProviderContext";

const WELCOME_MESSAGE = {
  id: "welcome",
  role: "assistant" as const,
  content:
    "Neural core online. Connect to an LLM provider to start querying your memory graph. Select a provider from the dashboard.",
  timestamp: new Date().toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }),
};

export function ChatInterface() {
  const { messages, isStreaming } = useChat();
  const { activeProvider } = useProviders();

  // Show welcome message if no provider is selected and no messages
  const displayMessages =
    messages.length === 0 && !activeProvider ? [WELCOME_MESSAGE] : messages;

  return (
    <div className="flex-1 overflow-y-auto custom-scrollbar">
      <div className="max-w-4xl mx-auto py-10 px-6 space-y-10">
        {displayMessages.map((msg, i) => (
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
              
              {/* Professional Linear Content */}
              <div
                className={`text-[14px] leading-relaxed tracking-tight text-slate-300 max-w-[90%] transition-colors duration-300 group-hover:text-slate-100 ${
                  msg.role === 'assistant' ? 'font-medium' : ''
                }`}
              >
                {msg.content}
                {msg.role === 'assistant' && isStreaming && !msg.content && (
                  <motion.span
                    animate={{ opacity: [0.4, 1, 0.4] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                    className="ml-1 inline-block text-primary-400"
                  >
                    ▌
                  </motion.span>
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
      
      {/* Precision Bottom Anchor - Compensates for Floating Capsule */}
      <div className="h-32" />
    </div>
  );
}
