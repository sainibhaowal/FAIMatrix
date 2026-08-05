"use client";

import React, { useRef, useState } from "react";
import {
  Plus,
  Send,
  Zap,
  Paperclip,
  AlertCircle,
  MessageSquarePlus,
  Brain,
  Database,
  Sparkles,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/Button";
import {
  ANSWER_MODE_LABELS,
  type AnswerMode,
  useChat,
} from "@/contexts/ChatContext";
import { useProviders } from "@/contexts/ProviderContext";
import { providerReasoningCapability } from "@/lib/providers";

const ANSWER_MODES: AnswerMode[] = [
  "auto",
  "direct",
  "timeline",
  "contradiction",
  "provenance",
];

export function ChatComposer() {
  const [value, setValue] = useState("");
  const [showTools, setShowTools] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const {
    sendMessage,
    uploadFiles,
    isStreaming,
    error,
    newThread,
    answerMode,
    setAnswerMode,
  } = useChat();

  const handleSend = async () => {
    if (!value.trim() || isStreaming) return;
    await sendMessage(value);
    setValue("");
  };

  const handleAttachClick = () => {
    if (isStreaming) return;
    fileInputRef.current?.click();
  };

  const handleFileChange = async (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;
    await uploadFiles(files);
    event.target.value = "";
    setShowTools(false);
  };

  return (
    <div className="w-full relative px-4 sm:px-6 pb-3 pt-2 bg-transparent pointer-events-none">
      <input
        ref={fileInputRef}
        type="file"
        multiple
        className="hidden"
        onChange={handleFileChange}
      />

      {/* Answer Mode Toggle Options Bar */}
      <div className="max-w-4xl mx-auto mb-2 flex items-center justify-between gap-2 px-1 pointer-events-auto">
        <div className="flex items-center gap-2">
          <span className="text-[9px] font-black uppercase tracking-[0.3em] text-slate-500">
            Answer mode
          </span>
          {ANSWER_MODES.map((mode) => {
            const active = mode === answerMode;
            return (
              <button
                key={mode}
                onClick={() => setAnswerMode(mode)}
                className={`px-3 py-1.5 rounded-xl border text-[10px] font-black uppercase tracking-[0.22em] transition-all duration-300 relative overflow-hidden group/mode ${
                  active
                    ? mode === "auto"
                      ? "bg-gradient-to-br from-primary-500/20 to-violet-500/20 border-primary-400/50 text-white shadow-[0_0_20px_rgba(34,211,238,0.3)] font-bold"
                      : "bg-primary-500/15 border-primary-500/35 text-primary-200 shadow-[0_0_16px_rgba(34,211,238,0.15)] font-bold"
                    : "bg-white/[0.03] border-white/5 text-slate-500 hover:text-slate-200 hover:border-white/10 hover:bg-white/5"
                }`}
                title={`Generate a ${ANSWER_MODE_LABELS[mode].toLowerCase()} answer`}
              >
                {mode === "auto" && active && (
                  <motion.div
                    layoutId="mode-glow"
                    className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full animate-[shimmer_2s_infinite]"
                  />
                )}
                {ANSWER_MODE_LABELS[mode]}
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Composer Box */}
      <div
        className="max-w-4xl mx-auto flex items-center gap-3 p-2.5 rounded-[32px] border-[1px] shadow-[0_30px_70px_rgba(0,0,0,0.7)] backdrop-blur-3xl pointer-events-auto transition-all duration-500 relative"
        style={{
          background: "rgba(11, 18, 28, 0.9)",
          borderColor: isStreaming
            ? "var(--primary-400)"
            : "rgba(255,255,255,0.03)",
        }}
      >
        {/* Dynamic Glowing Foundation */}
        <AnimatePresence>
          {isStreaming && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 bg-primary-500/5 z-0 pointer-events-none"
            />
          )}
        </AnimatePresence>

        <div className="relative shrink-0 z-10">
          <button
            onClick={() => setShowTools(!showTools)}
            className={`flex h-11 w-11 items-center justify-center rounded-[20px] transition-all duration-300 border ${
              showTools
                ? "bg-primary-500/10 border-primary-500/30 text-primary-300 shadow-[0_0_15px_rgba(34,211,238,0.2)]"
                : "bg-white/5 border-white/5 text-slate-500 hover:text-slate-300 hover:bg-white/10"
            }`}
          >
            <Plus
              size={20}
              className={`transition-transform duration-500 ${showTools ? "rotate-[135deg]" : ""}`}
            />
          </button>

          <AnimatePresence>
            {showTools && (
              <motion.div
                initial={{ opacity: 0, y: 12, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 12, scale: 0.95 }}
                className="absolute bottom-16 left-0 z-50 p-1.5 rounded-2xl border bg-slate-900 shadow-2xl flex flex-col gap-0.5 min-w-[180px]"
                style={{ borderColor: "var(--os-stroke)" }}
              >
                <button
                  onClick={() => {
                    newThread();
                    setShowTools(false);
                  }}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs text-slate-300 hover:text-white hover:bg-white/5 transition-colors text-left"
                >
                  <MessageSquarePlus size={14} className="text-primary-400" />
                  <span>New Chat Thread</span>
                </button>
                <button
                  onClick={handleAttachClick}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs text-slate-300 hover:text-white hover:bg-white/5 transition-colors text-left"
                >
                  <Paperclip size={14} className="text-violet-400" />
                  <span>Attach Knowledge File</span>
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Text Input Area */}
        <div className="flex-1 relative z-10 flex items-center">
          <input
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Ask FAIM Cortex to run a structured brain turn over memory..."
            disabled={isStreaming}
            className="w-full bg-transparent text-sm text-slate-100 placeholder-slate-500 focus:outline-none py-2 px-1 disabled:opacity-50 font-normal tracking-wide"
          />
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2 shrink-0 z-10">
          <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-primary-500/20 bg-primary-500/5 text-primary-300 text-[10px] font-black uppercase tracking-wider">
            <Database size={11} className="text-primary-400" />
            <span>FAIM Cortex</span>
          </div>

          <button
            onClick={handleSend}
            disabled={!value.trim() || isStreaming}
            className={`flex h-11 w-11 items-center justify-center rounded-[20px] transition-all duration-300 border ${
              value.trim() && !isStreaming
                ? "bg-primary-500 text-slate-950 border-primary-400 shadow-[0_0_20px_rgba(34,211,238,0.4)] hover:scale-105 active:scale-95"
                : "bg-white/5 border-white/5 text-slate-600 cursor-not-allowed"
            }`}
          >
            <Send size={18} className={value.trim() && !isStreaming ? "translate-x-0.5" : ""} />
          </button>
        </div>
      </div>

      {/* Error Message Toast */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="max-w-4xl mx-auto mt-2 p-2.5 rounded-2xl border border-rose-500/30 bg-rose-500/10 text-rose-300 text-xs flex items-center gap-2 pointer-events-auto shadow-lg"
          >
            <AlertCircle size={14} className="shrink-0" />
            <span>{error}</span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
