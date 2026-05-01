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
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/Button";
import { useChat } from "@/contexts/ChatContext";
import { useProviders } from "@/contexts/ProviderContext";

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
    thinkingEnabled,
    toggleThinking,
  } = useChat();
  const { activeProvider } = useProviders();

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
      {/* Floating thinking toggle button */}
      <div className="absolute top-[-44px] left-4 sm:left-6 pointer-events-auto z-20">
        <button
          onClick={toggleThinking}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl border text-[9px] font-black uppercase tracking-widest transition-all duration-300 ${
            thinkingEnabled
              ? "bg-primary-500/10 border-primary-500/40 text-primary-300 shadow-[0_0_12px_rgba(34,211,238,0.3)]"
              : "bg-black/40 border-white/5 text-slate-600 hover:text-slate-400 hover:border-white/10"
          }`}
          title={
            thinkingEnabled
              ? "Thinking ON — click to disable"
              : "Thinking OFF — click to enable"
          }
        >
          <Brain
            size={11}
            className={thinkingEnabled ? "text-primary-400" : "text-slate-600"}
          />
          <span>Think</span>
          {thinkingEnabled && (
            <span className="w-1.5 h-1.5 rounded-full bg-primary-400 animate-pulse" />
          )}
        </button>
      </div>

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
                  className="flex items-center gap-3 px-3 py-2.5 text-[10px] font-black uppercase tracking-[0.2em] text-slate-500 hover:text-white hover:bg-white/5 rounded-xl transition-all"
                >
                  <MessageSquarePlus size={15} className="text-primary-400" />
                  New Thread
                </button>
                <button
                  onClick={handleAttachClick}
                  className="flex items-center gap-3 px-3 py-2.5 text-[10px] font-black uppercase tracking-[0.2em] text-slate-500 hover:text-white hover:bg-white/5 rounded-xl transition-all"
                >
                  <Paperclip size={15} className="text-slate-500" />
                  Upload To Storage
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <div className="flex-1 relative z-10 self-center">
          <textarea
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Query FAIM contextual graph..."
            className="w-full bg-transparent border-none outline-none focus:outline-none focus:ring-0 text-slate-100 px-2 py-3 text-[14px] placeholder:text-slate-600 resize-none max-h-[200px] custom-scrollbar selection:bg-primary-500/30 transition-all font-medium"
            rows={1}
            style={{ minHeight: "26px" }}
          />
        </div>

        <div className="relative z-10 flex items-center gap-2">
          <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-primary-500/8 border border-primary-500/15">
            <Database size={12} className="text-primary-300" />
            <span className="text-[10px] font-semibold uppercase tracking-widest text-primary-300">
              FAIM Query
            </span>
          </div>
          {error && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-rose-500/10 border border-rose-500/20"
              title={error}
            >
              <AlertCircle size={14} className="text-rose-500 flex-shrink-0" />
              <span className="text-[10px] text-rose-500 font-semibold uppercase tracking-widest truncate">
                {error}
              </span>
            </motion.div>
          )}
          <Button
            onClick={handleSend}
            disabled={!value.trim() || isStreaming}
            className={`h-11 w-11 !p-0 rounded-[20px] transition-all duration-500 relative overflow-hidden group ${
              isStreaming
                ? "bg-primary-500 text-white shadow-[0_0_25px_rgba(34,211,238,0.5)]"
                : "bg-white/5 border-white/5 text-slate-600 hover:text-primary-300 hover:bg-primary-500/10 hover:border-primary-500/30"
            }`}
            variant="outline"
            title={
              activeProvider
                ? "Send query to FAIM and active provider context"
                : "Send query to FAIM"
            }
          >
            {isStreaming ? (
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
              >
                <Zap size={20} fill="currentColor" />
              </motion.div>
            ) : (
              <Send
                size={20}
                className={value.trim() ? "text-primary-300" : "text-slate-700"}
              />
            )}

            <AnimatePresence>
              {isStreaming && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="absolute inset-0 bg-white/20 blur-xl scale-150"
                  transition={{
                    duration: 1,
                    repeat: Infinity,
                    repeatType: "reverse",
                  }}
                />
              )}
            </AnimatePresence>
          </Button>
        </div>
      </div>
    </div>
  );
}
