"use client";

import React, { useState, useEffect, useRef } from "react";
import { ChevronDown, Brain } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface ThinkingPaneProps {
  content: string; // accumulated thinking text
  durationMs?: number; // set when thinking is complete
  isActive: boolean; // true = still streaming thinking tokens
}

export function ThinkingPane({
  content,
  durationMs,
  isActive,
}: ThinkingPaneProps) {
  const [isExpanded, setIsExpanded] = useState(isActive);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);
  const startTimeRef = useRef<number>(Date.now());

  // Live timer while thinking
  useEffect(() => {
    if (!isActive) return;

    const interval = setInterval(() => {
      const elapsed = (Date.now() - startTimeRef.current) / 1000;
      setElapsedSeconds(Math.round(elapsed * 10) / 10); // one decimal place
    }, 100);

    return () => clearInterval(interval);
  }, [isActive]);

  // Auto-expand when thinking starts
  useEffect(() => {
    if (isActive) {
      setIsExpanded(true);
    }
  }, [isActive]);

  // Auto-scroll to bottom while streaming
  useEffect(() => {
    if (isActive && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [content, isActive]);

  if (!content && !isActive) return null;

  const displayDuration = isActive
    ? `${elapsedSeconds}s`
    : durationMs
      ? `${(durationMs / 1000).toFixed(1)}s`
      : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      transition={{ duration: 0.3 }}
      className="my-4 rounded-xl border border-primary-500/15 overflow-hidden bg-primary-500/5 shadow-lg"
    >
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between gap-3 hover:bg-primary-500/10 transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <Brain size={13} className="text-primary-400 flex-shrink-0" />
          <span className="text-[10px] font-black uppercase tracking-widest text-primary-300">
            Thinking
          </span>
          {isActive && (
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-primary-400 animate-pulse ml-1" />
          )}
          {displayDuration && (
            <span className="text-[9px] font-mono text-primary-400 ml-2">
              {displayDuration}
            </span>
          )}
        </div>
        <ChevronDown
          size={13}
          className={`text-primary-400 transition-transform duration-300 ${
            isExpanded ? "rotate-180" : ""
          }`}
        />
      </button>

      {/* Content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden border-t border-primary-500/10"
          >
            <div
              ref={scrollRef}
              className="max-h-48 overflow-y-auto custom-scrollbar px-4 py-3 bg-primary-500/[0.02]"
            >
              <p className="font-mono text-[11px] text-slate-400 leading-relaxed whitespace-pre-wrap break-words">
                {content || (isActive ? "Thinking..." : "")}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
