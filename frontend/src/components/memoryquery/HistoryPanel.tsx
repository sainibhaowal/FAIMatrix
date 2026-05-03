"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  MessageSquare,
  Trash2,
  Edit3,
  Clock,
  Check,
  X,
  Plus,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { useChat } from "@/contexts/ChatContext";

export function HistoryPanel() {
  const {
    threads,
    activeThreadId,
    switchThread,
    newThread,
    deleteThread,
    renameThread,
    purgeAllThreads,
  } = useChat();

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const [confirmPurge, setConfirmPurge] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editingId && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editingId]);

  const startEdit = (id: string, title: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(id);
    setEditValue(title);
  };

  const commitEdit = () => {
    if (!editingId) return;
    renameThread(editingId, editValue);
    setEditingId(null);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditValue("");
  };

  const handleDelete = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    deleteThread(id);
  };

  function formatDate(iso: string): string {
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    return `${days}d ago`;
  }

  return (
    <div className="flex flex-col h-full overflow-hidden bg-transparent">
      {/* Header */}
      <div
        className="px-4 py-3 border-b flex items-center justify-between gap-2"
        style={{
          borderColor: "var(--os-stroke)",
          background: "rgba(255,255,255,0.02)",
        }}
      >
        <div className="flex items-center gap-2">
          <Clock size={13} className="text-primary-400" />
          <h2 className="text-[10px] font-black uppercase tracking-[0.25em] text-white">
            Cortex Sessions
          </h2>
          <span className="text-[9px] font-bold text-slate-600 tabular-nums">
            {threads.length}
          </span>
        </div>
        <button
          onClick={newThread}
          className="h-6 w-6 flex items-center justify-center rounded-lg hover:bg-primary-500/20 text-slate-500 hover:text-primary-300 transition-all"
          title="New thread"
        >
          <Plus size={13} />
        </button>
      </div>

      {/* Thread List */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-2 space-y-0.5">
        {threads.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-3 py-12">
            <MessageSquare size={22} className="text-slate-700" />
            <p className="text-[10px] text-slate-600 uppercase tracking-widest text-center">
              No sessions yet
            </p>
            <button
              onClick={newThread}
              className="text-[9px] font-bold text-primary-500 hover:text-primary-300 uppercase tracking-widest transition-colors"
            >
              Start a memory session
            </button>
          </div>
        ) : (
          threads.map((thread) => {
            const isActive = thread.id === activeThreadId;
            const isEditing = editingId === thread.id;

            return (
              <div
                key={thread.id}
                onClick={() => !isEditing && switchThread(thread.id)}
                className={[
                  "group relative flex flex-col gap-0.5 px-3 py-2.5 rounded-xl transition-all duration-200 cursor-pointer border",
                  isActive
                    ? "bg-primary-500/10 border-primary-500/20 shadow-[0_0_10px_rgba(34,211,238,0.05)]"
                    : "hover:bg-white/[0.04] border-transparent hover:border-white/5",
                ].join(" ")}
              >
                {/* Active indicator */}
                {isActive && (
                  <span className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-[2px] rounded-r-full bg-gradient-to-b from-primary-400 to-secondary-400" />
                )}

                <div className="flex items-start justify-between gap-2">
                  {isEditing ? (
                    <div
                      className="flex-1 flex items-center gap-1.5"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <input
                        ref={inputRef}
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") commitEdit();
                          if (e.key === "Escape") cancelEdit();
                        }}
                        className="flex-1 text-[12px] font-semibold bg-white/10 border border-primary-500/40 rounded px-2 py-0.5 text-white outline-none focus:border-primary-500/70"
                      />
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          commitEdit();
                        }}
                        className="h-5 w-5 flex items-center justify-center rounded-md bg-primary-500/20 hover:bg-primary-500/30 text-primary-400 transition-all"
                      >
                        <Check size={10} />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          cancelEdit();
                        }}
                        className="h-5 w-5 flex items-center justify-center rounded-md hover:bg-white/10 text-slate-500 transition-all"
                      >
                        <X size={10} />
                      </button>
                    </div>
                  ) : (
                    <>
                      <span
                        className={[
                          "text-[12px] font-semibold line-clamp-1 leading-none tracking-tight flex-1 transition-colors",
                          isActive
                            ? "text-primary-200"
                            : "text-slate-300 group-hover:text-white",
                        ].join(" ")}
                      >
                        {thread.title}
                      </span>
                      <div className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1 shrink-0">
                        <button
                          onClick={(e) => startEdit(thread.id, thread.title, e)}
                          className="h-5 w-5 flex items-center justify-center rounded-md hover:bg-white/10 text-slate-500 hover:text-white transition-all"
                          title="Rename"
                        >
                          <Edit3 size={10} />
                        </button>
                        <button
                          onClick={(e) => handleDelete(thread.id, e)}
                          className="h-5 w-5 flex items-center justify-center rounded-md hover:bg-rose-500/15 text-slate-500 hover:text-rose-400 transition-all"
                          title="Delete"
                        >
                          <Trash2 size={10} />
                        </button>
                      </div>
                    </>
                  )}
                </div>

                {!isEditing && (
                  <div className="flex items-center gap-2">
                    <span className="text-[8px] font-black font-mono text-slate-600 uppercase tracking-widest">
                      {formatDate(thread.updatedAt)}
                    </span>
                    <div className="h-0.5 w-0.5 rounded-full bg-slate-800" />
                    <span className="text-[8px] font-black text-slate-700 uppercase tracking-[0.2em]">
                      {thread.messages.length} msgs
                    </span>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Footer */}
      <div
        className="p-3 border-t bg-black/20"
        style={{ borderColor: "var(--os-stroke)" }}
      >
        {confirmPurge ? (
          <div className="space-y-2">
              <p className="text-[9px] text-rose-400 font-bold uppercase tracking-widest text-center">
              Delete all {threads.length} sessions?
              </p>
            <div className="flex gap-2">
              <button
                onClick={() => {
                  purgeAllThreads();
                  setConfirmPurge(false);
                }}
                className="flex-1 h-7 rounded-lg bg-rose-500/20 border border-rose-500/40 text-rose-400 text-[9px] font-black uppercase tracking-widest hover:bg-rose-500/30 transition-all"
              >
                Delete All
              </button>
              <button
                onClick={() => setConfirmPurge(false)}
                className="flex-1 h-7 rounded-lg bg-white/5 border border-white/10 text-slate-400 text-[9px] font-black uppercase tracking-widest hover:bg-white/10 transition-all"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <Button
            variant="outline"
            fullWidth
            size="sm"
            onClick={() => setConfirmPurge(true)}
            disabled={threads.length === 0}
            className="h-8 text-[9px] font-black uppercase tracking-[0.3em] border-white/5 bg-white/5 hover:bg-rose-500/10 hover:border-rose-500/20 hover:text-rose-400 transition-all disabled:opacity-30"
          >
            Purge Buffer
          </Button>
        )}
      </div>
    </div>
  );
}
