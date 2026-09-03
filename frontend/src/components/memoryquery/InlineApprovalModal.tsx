"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import { createPortal } from "react-dom";
import {
  AlertTriangle,
  HardDrive,
  X,
  CheckCircle2,
  XCircle,
  Loader2,
  Shield,
  FileText,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/Button";

interface ToolApproval {
  id: number;
  tool_name: string;
  args: Record<string, unknown>;
  reason: string;
  status: "pending" | "approved" | "rejected";
}

interface InlineApprovalModalProps {
  approval: ToolApproval | null;
  onApprove: (approvalId: number, note?: string) => Promise<void>;
  onReject: (approvalId: number, note: string) => Promise<void>;
  onClose: () => void;
  isLoading?: boolean;
}

export function InlineApprovalModal({
  approval,
  onApprove,
  onReject,
  onClose,
  isLoading = false,
}: InlineApprovalModalProps) {
  const [note, setNote] = useState("");
  const [showDetails, setShowDetails] = useState(false);
  const modalRef = useRef<HTMLDivElement>(null);
  const focusRef = useRef<HTMLTextAreaElement>(null);

  const handleApprove = useCallback(async () => {
    if (!approval) return;
    await onApprove(approval.id, note || "Approved via inline modal");
    onClose();
  }, [approval, note, onApprove, onClose]);

  const handleReject = useCallback(async () => {
    if (!approval) return;
    const reason = note || prompt("Reason for rejection (required):") || "Rejected via inline modal";
    if (!reason) return;
    await onReject(approval.id, reason);
    onClose();
  }, [approval, note, onReject, onClose]);

  useEffect(() => {
    if (approval) {
      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === "Escape") onClose();
        if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
          handleApprove();
        }
      };
      document.addEventListener("keydown", handleKeyDown);
      focusRef.current?.focus();
      return () => document.removeEventListener("keydown", handleKeyDown);
    }
  }, [approval, onClose, handleApprove, handleReject]);

  if (!approval) return null;

  const toolIcon = () => {
    switch (approval.tool_name) {
      case "faim_storage_delete":
      case "storage_delete":
        return <HardDrive className="text-rose-400" />;
      case "faim_storage_ingest":
      case "storage_ingest":
        return <FileText className="text-cyan-400" />;
      default:
        return <HardDrive className="text-amber-400" />;
    }
  };

  return createPortal(
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: -20 }}
        transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
        className="relative w-full max-w-2xl max-h-[85vh] flex flex-col rounded-[20px] border border-white/10 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.96))] shadow-[0_24px_80px_rgba(0,0,0,0.7)] overflow-hidden"
        role="dialog"
        aria-modal="true"
        aria-labelledby="approval-title"
      >
        {/* Top accent bar */}
        <div className="absolute top-0 left-8 right-8 h-[2px] bg-gradient-to-r from-amber-500/80 via-amber-500/50 to-transparent rounded-full" />

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/6 shrink-0 bg-white/[0.01]">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-300 shrink-0">
              <AlertTriangle size={20} />
            </div>
            <div>
              <h2 id="approval-title" className="text-sm font-bold text-white tracking-wide flex items-center gap-2">
                Approval Required
              </h2>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Cortex needs your permission to execute this action
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition-colors shrink-0"
            aria-label="Close approval"
          >
            <X size={16} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 min-h-0 overflow-y-auto p-6 space-y-4">
          {/* Tool Info Card */}
          <div className="relative overflow-hidden rounded-[14px] border border-amber-500/20 bg-amber-500/[0.04] p-4 space-y-3">
            <div className="absolute top-0 left-0 bottom-0 w-[3px] bg-amber-400" />
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-300 shrink-0">
                {toolIcon()}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 text-xs font-bold text-amber-300">
                  <span>{approval.tool_name}</span>
                  <span className="text-[9px] font-mono text-amber-500/80">#{approval.id}</span>
                </div>
                <p className="text-[11px] text-slate-400 truncate">{approval.reason || "No reason provided"}</p>
              </div>
              <span className="inline-flex items-center gap-1 px-2 py-1 rounded bg-amber-500/20 border border-amber-500/30 text-amber-300 text-[10px] font-semibold">
                PENDING
              </span>
            </div>
          </div>

          {/* Arguments Details */}
          <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4 space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                <FileText size={13} /> Arguments
              </h3>
              <button
                onClick={() => setShowDetails(!showDetails)}
                className="flex items-center gap-1 px-2 py-1 text-[10px] font-mono text-slate-400 hover:text-slate-200 transition-colors"
              >
                {showDetails ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                {showDetails ? "Collapse" : "Expand"}
              </button>
            </div>

            <AnimatePresence>
              {showDetails && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <div className="mt-2 p-3 bg-black/30 rounded-lg border border-white/5 overflow-x-auto">
                    <pre className="text-[10px] font-mono text-slate-300 whitespace-pre-wrap">
                      {JSON.stringify(approval.args, null, 2)}
                    </pre>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Custom Note */}
          <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4 space-y-2">
            <h3 className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
              <FileText size={13} /> Your Note (Optional)
            </h3>
            <textarea
              ref={focusRef}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={3}
              className="w-full resize-none bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-cyan-500/50 focus:outline-none focus:ring-1 focus:ring-cyan-500/50"
              placeholder="Add a note for the approval decision (e.g., reason for approval, context)..."
            />
            <p className="text-[9px] text-slate-500">
              This note will be recorded in the approval ledger for audit purposes.
            </p>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-end gap-3 border-t border-white/6 px-6 py-4 shrink-0 bg-white/[0.01]">
          <Button
            variant="ghost"
            size="md"
            onClick={onClose}
            disabled={isLoading}
            className="h-10 px-5 text-[11px] font-semibold"
          >
            Cancel
          </Button>
          <Button
            variant="outline"
            size="md"
            onClick={handleReject}
            disabled={isLoading}
            className="h-10 px-5 text-[11px] font-semibold border-rose-500/30 text-rose-300 hover:bg-rose-500/10"
            leftIcon={<XCircle size={14} />}
          >
            Reject
          </Button>
          <Button
            variant="primary"
            size="md"
            onClick={handleApprove}
            disabled={isLoading}
            loading={isLoading}
            className="h-10 px-6 text-[11px] font-semibold shadow-sm"
            leftIcon={<CheckCircle2 size={14} />}
          >
            Approve
          </Button>
        </div>
      </motion.div>

      {/* Backdrop click to close */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="absolute inset-0"
        onClick={onClose}
      />
    </div>,
    document.body
  );
}