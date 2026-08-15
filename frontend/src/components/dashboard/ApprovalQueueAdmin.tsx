"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  XCircle,
  HardDrive,
  RefreshCw,
  Loader2,
  Filter,
  Eye,
  MoreHorizontal,
  Clock,
  Shield,
  FileText,
  Trash2,
  Download,
  Upload,
  RotateCcw,
  Search,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface ApprovalItem {
  id: number;
  tenant_id: string;
  graph_id: string;
  session_id: string | null;
  turn_id: string | null;
  tool_name: string;
  status: "pending" | "approved" | "rejected";
  execution_status: string;
  args: Record<string, unknown>;
  reason: string;
  proposed_by: string;
  decision_by: string | null;
  decision_note: string | null;
  created_at: string;
  decided_at: string | null;
  executed_at: string | null;
  receipt: Record<string, unknown>;
}

interface ApprovalStats {
  total: number;
  pending: number;
  approved: number;
  rejected: number;
}

interface ApprovalFilters {
  status: string;
  tool_name: string;
  tenant_id: string;
  limit: number;
}

export function ApprovalQueueAdmin({
  className = "",
  tenantId = "default",
}: {
  className?: string;
  tenantId?: string;
}) {
  const [approvals, setApprovals] = useState<ApprovalItem[]>([]);
  const [stats, setStats] = useState<ApprovalStats>({ total: 0, pending: 0, approved: 0, rejected: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<ApprovalFilters>({
    status: "",
    tool_name: "",
    tenant_id: tenantId,
    limit: 50,
  });
  const [selectedApproval, setSelectedApproval] = useState<ApprovalItem | null>(null);
  const [showDetails, setShowDetails] = useState(false);

  const API_BASE = "/api/v1";

  const authHeaders = async (): Promise<Record<string, string>> => {
    const { getSession } = await import("next-auth/react");
    const session = await getSession();
    const token = (session as { accessToken?: string } | null)?.accessToken;
    const tenantId = (session as { tenantId?: string } | null)?.tenantId;
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token) headers.Authorization = `Bearer ${token}`;
    if (tenantId) headers["X-Tenant-Id"] = tenantId;
    return headers;
  };

  const fetchApprovals = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const headers = await authHeaders();
      const params = new URLSearchParams();
      if (filters.status) params.set("status", filters.status);
      if (filters.limit) params.set("limit", filters.limit.toString());

      const res = await fetch(`${API_BASE}/cortex/tool-approvals?${params}`, { headers });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setApprovals(data.items || []);
      setStats({
        total: data.total || 0,
        pending: data.items?.filter((a: ApprovalItem) => a.status === "pending").length || 0,
        approved: data.items?.filter((a: ApprovalItem) => a.status === "approved").length || 0,
        rejected: data.items?.filter((a: ApprovalItem) => a.status === "rejected").length || 0,
      });
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchApprovals();
  }, [fetchApprovals]);

  const handleApprove = async (approval: ApprovalItem) => {
    try {
      const headers = await authHeaders();
      const res = await fetch(`${API_BASE}/cortex/tool-approvals/${approval.id}/approve`, {
        method: "POST",
        headers,
        body: JSON.stringify({ note: "Approved via admin UI" }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      fetchApprovals();
    } catch (e: any) {
      alert(`Failed to approve: ${e.message}`);
    }
  };

  const handleReject = async (approval: ApprovalItem) => {
    const note = prompt("Reason for rejection:") || "Rejected via admin UI";
    try {
      const headers = await authHeaders();
      const res = await fetch(`${API_BASE}/cortex/tool-approvals/${approval.id}/reject`, {
        method: "POST",
        headers,
        body: JSON.stringify({ note }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      fetchApprovals();
    } catch (e: any) {
      alert(`Failed to reject: ${e.message}`);
    }
  };

  const handleViewDetails = (approval: ApprovalItem) => {
    setSelectedApproval(approval);
    setShowDetails(true);
  };

  const formatTime = (ts: string | null) => {
    if (!ts) return "—";
    try {
      return new Date(ts).toLocaleString();
    } catch {
      return ts;
    }
  };

  const statusColor = (status: string) => {
    switch (status) {
      case "pending": return "text-amber-300 bg-amber-500/10 border-amber-500/20";
      case "approved": return "text-emerald-300 bg-emerald-500/10 border-emerald-500/20";
      case "rejected": return "text-rose-300 bg-rose-500/10 border-rose-500/20";
      default: return "text-slate-400 bg-slate-500/10 border-slate-500/20";
    }
  };

  const statusIcon = (status: string) => {
    switch (status) {
      case "pending": return <Clock className="w-4 h-4" />;
      case "approved": return <CheckCircle2 className="w-4 h-4" />;
      case "rejected": return <XCircle className="w-4 h-4" />;
      default: return <AlertTriangle className="w-4 h-4" />;
    }
  };

  const filteredApprovals = approvals.filter((a) => {
    if (filters.status && a.status !== filters.status) return false;
    if (filters.tool_name && a.tool_name !== filters.tool_name) return false;
    return true;
  });

  const toolNames = Array.from(new Set(approvals.map((a) => a.tool_name)));

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 p-4 border-b border-white/6 bg-black/30">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-amber-500/30 bg-amber-500/10 text-amber-300">
            <Shield className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold tracking-wide text-white">Approval Queue Admin</h2>
            <p className="text-[10px] text-slate-500">Human-in-the-loop tool approval management</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchApprovals}
            disabled={loading}
            className="px-3 py-1.5 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 text-slate-300 hover:text-slate-100 text-xs font-medium flex items-center gap-1.5"
          >
            <RefreshCw className={loading ? "animate-spin" : ""} size={14} />
            Refresh
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 border-b border-white/6 bg-black/20">
        <div className="p-3 rounded-xl border border-white/5 bg-white/5">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Total</span>
            <span className="text-2xl font-bold text-white">{stats.total}</span>
          </div>
        </div>
        <div className="p-3 rounded-xl border border-amber-500/20 bg-amber-500/5">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold uppercase tracking-wider text-amber-300">Pending</span>
            <span className="text-2xl font-bold text-amber-300">{stats.pending}</span>
          </div>
        </div>
        <div className="p-3 rounded-xl border border-emerald-500/20 bg-emerald-500/5">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-300">Approved</span>
            <span className="text-2xl font-bold text-emerald-300">{stats.approved}</span>
          </div>
        </div>
        <div className="p-3 rounded-xl border border-rose-500/20 bg-rose-500/5">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold uppercase tracking-wider text-rose-300">Rejected</span>
            <span className="text-2xl font-bold text-rose-300">{stats.rejected}</span>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="p-4 border-b border-white/6 bg-black/20 flex flex-wrap gap-3">
        <select
          value={filters.status}
          onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value }))}
          className="px-3 py-2 rounded-lg border border-white/10 bg-black/30 text-slate-100 text-sm focus:border-cyan-500/50 focus:outline-none focus:ring-1 focus:ring-cyan-500/50"
        >
          <option value="">All Status</option>
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
        </select>

        <select
          value={filters.tool_name}
          onChange={(e) => setFilters((f) => ({ ...f, tool_name: e.target.value }))}
          className="px-3 py-2 rounded-lg border border-white/10 bg-black/30 text-slate-100 text-sm focus:border-cyan-500/50 focus:outline-none focus:ring-1 focus:ring-cyan-500/50"
        >
          <option value="">All Tools</option>
          {toolNames.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>

        <input
          type="number"
          value={filters.limit}
          onChange={(e) => setFilters((f) => ({ ...f, limit: parseInt(e.target.value) || 50 }))}
          min="1"
          max="200"
          className="w-24 px-3 py-2 rounded-lg border border-white/10 bg-black/30 text-slate-100 text-sm focus:border-cyan-500/50 focus:outline-none focus:ring-1 focus:ring-cyan-500/50"
        />

        <span className="text-[10px] text-slate-500">Limit</span>
      </div>

      {/* Approvals Table */}
      <div className="flex-1 overflow-hidden">
        {error && (
          <div className="p-4 bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm rounded-lg m-4">
            Error: {error}
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/6 bg-black/30 text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                <th className="px-4 py-3 text-left">ID</th>
                <th className="px-4 py-3 text-left">Tool</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-left">Tenant / Graph</th>
                <th className="px-4 py-3 text-left">Args Preview</th>
                <th className="px-4 py-3 text-left">Created</th>
                <th className="px-4 py-3 text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                    <div className="flex items-center justify-center gap-2">
                      <Loader2 className="w-5 h-5 animate-spin" />
                      <span>Loading approvals...</span>
                    </div>
                  </td>
                </tr>
              ) : filteredApprovals.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                    No approvals found
                  </td>
                </tr>
              ) : (
                filteredApprovals.map((approval) => (
                  <tr key={approval.id} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                    <td className="px-4 py-3 font-mono text-[10px] text-slate-400">#{approval.id}</td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/20 text-cyan-300 text-[10px] font-mono">
                        {approval.tool_name}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium ${statusColor(approval.status)}`}>
                        {statusIcon(approval.status)}
                        {approval.status}
                        {approval.execution_status !== "pending" && (
                          <span className="text-[9px] text-slate-400">({approval.execution_status})</span>
                        )}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-[11px] text-slate-300">
                      <div className="font-mono text-[10px] text-slate-400">{approval.tenant_id}</div>
                      <div className="font-mono text-[10px] text-slate-500">{approval.graph_id}</div>
                    </td>
                    <td className="px-4 py-3 text-[10px] text-slate-500 max-w-xs truncate font-mono">
                      {JSON.stringify(approval.args).slice(0, 60)}...
                    </td>
                    <td className="px-4 py-3 text-[10px] text-slate-500 font-mono">
                      {new Date(approval.created_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => window.open(`#`, "_blank")}
                          className="px-2 py-1 text-[10px] rounded bg-slate-800 border border-white/10 hover:bg-slate-700 text-slate-300"
                          title="View Details"
                        >
                          View
                        </button>
                        {approval.status === "pending" && (
                              <div className="flex gap-1">
                                <button
                                  onClick={() => handleApprove(approval)}
                                  className="px-2 py-1 text-[10px] font-semibold rounded bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/30 transition"
                                  title="Approve"
                                >
                                  Approve
                                </button>
                                <button
                                  onClick={() => handleReject(approval)}
                                  className="px-2 py-1 text-[10px] font-semibold rounded bg-rose-500/20 border border-rose-500/30 text-rose-300 hover:bg-rose-500/30 transition"
                                  title="Reject"
                                >
                                  Reject
                                </button>
                              </div>
                            )}
                            {approval.status !== "pending" && (
                              <span className="text-[10px] text-slate-500">
                                {approval.execution_status === "executed" && <span className="text-emerald-300">✓ Executed</span>}
                                {approval.execution_status === "failed" && <span className="text-rose-300">✗ Failed</span>}
                                {approval.execution_status === "skipped" && <span className="text-amber-300">⊘ Skipped</span>}
                              </span>
                            )}
                      </div>
                    </td>
                  </tr>
                  )
                )
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default ApprovalQueueAdmin;