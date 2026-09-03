"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  AlertTriangle,
  HardDrive,
  FileText,
  Clock,
  CheckCircle,
  XCircle,
  Shield,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import {
  buildAuthorizedHeaders,
  resolveActiveGraphId,
} from "@/contexts/ChatContext";
import { useChat } from "@/contexts/ChatContext";

interface ApprovalRecord {
  id: number;
  approval_id: string;
  tool_name: string;
  args: Record<string, unknown>;
  reason: string;
  status: "pending" | "approved" | "rejected";
  notes?: string;
  created_at: string;
  approved_at?: string;
  approved_by?: string;
  approved_by_name?: string;
}

interface ApprovalHistoryPanelProps {
  threadId?: string;
}

export function ApprovalHistoryPanel({ threadId }: ApprovalHistoryPanelProps) {
  const {
    threads,
    activeThreadId,
    switchThread,
    newThread,
    deleteThread,
  } = useChat();

  const [approvals, setApprovals] = useState<ApprovalRecord[]>([]);
  const [loadingApprovals, setLoadingApprovals] = useState(false);
  const [showPendingOnly, setShowPendingOnly] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let cancelled = false;
    async function loadApprovals() {
      setLoadingApprovals(true);
      try {
        const graphId = await resolveActiveGraphId();
        if (!graphId) {
          setApprovals([]);
          return;
        }
        const headers = await buildAuthorizedHeaders();
        const url = threadId
          ? `/api/v1/cortex/tool-approvals?graph_id=${encodeURIComponent(
              graphId,
            )}&thread_id=${encodeURIComponent(threadId)}&limit=20`
          : `/api/v1/cortex/tool-approvals?graph_id=${encodeURIComponent(
              graphId,
            )}&limit=20`;
        const res = await fetch(url, { headers });
        if (!res.ok) {
          console.error("Failed to load approvals:", res.status);
          setApprovals([]);
          return;
        }
        const data = (await res.json()) as {
          approvals?: ApprovalRecord[];
        };
        if (!cancelled) setApprovals(data.approvals ?? []);
      } catch (err) {
        console.error("Error loading approvals:", err);
        if (!cancelled) setApprovals([]);
      } finally {
        if (!cancelled) setLoadingApprovals(false);
      }
    }
    loadApprovals();
    return () => {
      cancelled = true;
    };
  }, [threadId]);

  const formatDate = (iso: string): string => {
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    return `${days}d ago`;
  };

  const statusClass = (status: string) => {
    switch (status) {
      case "approved":
        return "bg-green-500/30 text-green-300";
      case "rejected":
        return "bg-rose-500/30 text-rose-300";
      case "pending":
        return "bg-amber-500/30 text-amber-300";
      default:
        return "bg-slate-500/30 text-slate-300";
    }
  };

  const statusText = (status: string) => {
    switch (status) {
      case "approved":
        return "Approved";
      case "rejected":
        return "Rejected";
      case "pending":
        return "Pending";
      default:
        return "Unknown";
    }
  };

  const rowClass = (
    status: string,
    isActive: boolean,
  ) => [
    "rounded-lg border px-3 py-2 transition-all cursor-pointer group flex items-start justify-between gap-2",
    isActive
      ? `border-amber-500/25 bg-amber-500/10`
      : "hover:bg-white/[0.04] border-transparent hover:border-white/5",
  ].join(" ");

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
          <AlertTriangle size={13} className="text-amber-400" />
          <h2 className="text-[10px] font-black uppercase tracking-[0.25em] text-white">
            Approval History
          </h2>
        </div>
        <Button
          variant="outline"
          fullWidth
          size="sm"
          onClick={() => setShowPendingOnly(!showPendingOnly)}
          className="h-6 w-6 flex items-center justify-center rounded-lg hover:bg-amber-500/20 text-amber-300 hover:text-amber-100 transition-all"
          title={showPendingOnly ? "Show all" : "Show pending only"}
        >
          <ChevronDown size={11} />
        </Button>
      </div>

      {/* List Content */}
      <div
        className={`flex-1 overflow-y-auto custom-scrollbar p-2 space-y-0.5 ${showPendingOnly
          ? "filter: grayscale(25%)"
          : ""}`}
      >
        <div className="mb-2 rounded-xl border border-amber-500/15 bg-amber-500/[0.04] p-3">
          <div className="flex items-center gap-2 text-[9px] font-black uppercase tracking-[0.24em] text-amber-300">
            <HardDrive size={12} />
            Approvals
          </div>

          {loadingApprovals && (
            <p className="text-[10px] text-amber-500">
              Loading approvals...
            </p>
          )}

          {approvals.length === 0 && (
            <div className="h-24 flex items-center justify-center text-[11px] text-amber-500">
              {showPendingOnly
                ? "No pending approvals found"
                : "No approvals found. Use the dashboard to view full history."}
            </div>
          )}

          {!loadingApprovals &&
          approvals.length > 0 && (
            <div className="mt-3 space-y-1">
              {approvals
                .filter((a) => showPendingOnly ? a.status === "pending" : true)
                .map((approval) => {
                  const isActive =
                    approval.status === "pending" &&
                    activeThreadId === `pending_approval_${approval.id}`;
                  const formattedDate = formatDate(approval.created_at);
                  return (
                    <div
                      key={approval.id}
                      onClick={() => {}}
                      className={rowClass(approval.status, isActive)}
                    >
                      <div className="flex items-center gap-2">
                        <div
                          className={[
                            "w-2 h-2 rounded-full",
                            approval.status === "approved"
                              ? "bg-green-400"
                              : approval.status === "rejected"
                              ? "bg-rose-400"
                              : "bg-amber-400",
                          ].join(" ")}
                        />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-[11px] font-semibold text-slate-100 line-clamp-1">
                              {approval.tool_name}
                            </span>
                            <span className="text-[8px] font-black uppercase tracking-[0.2em] text-amber-500">
                              {approval.approval_id || `#${approval.id}`}
                            </span>
                          </div>
                          <p className="mt-1 text-[10px] text-amber-400 line-clamp-1">
                            {approval.reason || "No reason provided"}
                          </p>
                        </div>
                        <div className="flex items-center gap-1">
                          <span className="text-[9px] font-mono text-amber-400">
                            {formattedDate}
                          </span>
                          {approval.notes && (
                            <span
                              className="text-[8px] font-black uppercase tracking-[0.15em] text-amber-500"
                            >
                              {"  •  " + approval.notes}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center justify-between mt-1">
                        <div className="flex items-center gap-1 text-[8px] text-amber-400 uppercase">
                          {statusText(approval.status)}
                        </div>
                        {approval.status !== "pending" && (
                          <span
                            className={[
                              "px-2 py-0.5 rounded text-[8px] font-black",
                              approval.status === "approved"
                                ? "bg-green-500/20 text-green-300"
                                : "bg-rose-500/20 text-rose-300",
                            ].join(" ")}
                          >
                            {approval.approved_at
                              ? formatDate(approval.approved_at)
                              : "—"}
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div
        className="p-3 border-t bg-black/20"
        style={{ borderColor: "var(--os-stroke)" }}
      >
        <Button
          variant="outline"
          fullWidth
          size="sm"
          onClick={() => setShowPendingOnly(!showPendingOnly)}
          className="h-7 text-[9px] font-black uppercase tracking-[0.3em] border-white/5 bg-white/5 hover:bg-amber-500/10 hover:border-amber-500/20 hover:text-amber-300 transition-all"
        >
          {showPendingOnly ? "Show all approvals" : "Show pending only"}
        </Button>
      </div>
    </div>
  );
}