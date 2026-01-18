"use client";

import React, { useState, useEffect } from "react";
import { 
  Gavel, 
  CheckCircle, 
  XCircle, 
  Info, 
  RefreshCcw, 
  Search,
  ChevronRight,
  ShieldCheck,
  Zap
} from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui";

interface Proposal {
  id: string;
  kind: string;
  details: {
    node_id?: string;
    keep_id?: string;
    drop_id?: string;
    reason: string;
    summary: string;
  };
  status: string;
  analysis_score: number;
  created_at: string;
}

export function GovernanceDashboard() {
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [loading, setLoading] = useState(true);
  const [judging, setJudging] = useState<string | null>(null);

  const fetchProposals = async () => {
    try {
      const { getSession } = await import("next-auth/react");
      const session = await getSession();
      const headers: Record<string, string> = {};
      if (session && (session as any).accessToken) {
        headers["Authorization"] = `Bearer ${(session as any).accessToken}`;
      }

      const res = await fetch("/api/ops/evolution/proposals?status=pending", { headers });
      if (res.ok) {
        const data = await res.json();
        setProposals(data);
      }
    } catch (err) {
      console.error("Failed to fetch proposals:", err);
    } finally {
      setLoading(false);
    }
  };

  const judgeProposal = async (id: string, approved: boolean) => {
    setJudging(id);
    try {
      const { getSession } = await import("next-auth/react");
      const session = await getSession();
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (session && (session as any).accessToken) {
        headers["Authorization"] = `Bearer ${(session as any).accessToken}`;
      }

      const res = await fetch(`/api/ops/evolution/proposals/${id}/judge`, {
        method: "POST",
        headers,
        body: JSON.stringify({ approved })
      });

      if (res.ok) {
        setProposals(proposals.filter(p => p.id !== id));
      }
    } catch (err) {
      console.error("Failed to judge proposal:", err);
    } finally {
      setJudging(null);
    }
  };

  useEffect(() => {
    fetchProposals();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col h-full bg-[var(--surface-1)] border border-[var(--border-default)] rounded-xl animate-pulse p-8 items-center justify-center space-y-4">
        <RefreshCcw className="h-8 w-8 text-[var(--text-muted)] animate-spin" />
        <span className="text-sm font-medium text-[var(--text-muted)]">Scanning Staging Area...</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-[var(--surface-1)] border border-[var(--border-default)] rounded-xl overflow-hidden shadow-2xl">
      {/* Header */}
      <div className="p-4 border-b border-[var(--border-default)] bg-[var(--surface-2)] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-500/10 rounded-lg text-indigo-400 border border-indigo-500/20">
            <Gavel size={20} />
          </div>
          <div>
            <h3 className="text-sm font-bold text-[var(--text-primary)]">Interactive Governance</h3>
            <p className="text-[10px] text-[var(--text-muted)] uppercase tracking-widest font-semibold flex items-center gap-1">
              <ShieldCheck size={10} className="text-emerald-500" /> Human-in-the-Loop Validation
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <div className="text-[14px] font-bold text-[var(--text-primary)] tabular-nums">{proposals.length}</div>
            <div className="text-[8px] text-[var(--text-muted)] uppercase font-bold">Staged Changes</div>
          </div>
          <button 
            onClick={fetchProposals}
            className="p-2 hover:bg-[var(--surface-3)] rounded-lg transition-colors text-[var(--text-muted)] hover:text-indigo-400"
          >
            <RefreshCcw size={16} />
          </button>
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {proposals.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-8 space-y-3 opacity-50">
            <Zap className="h-10 w-10 text-emerald-500/30" />
            <p className="text-xs font-medium text-[var(--text-muted)]">Neural Core is stable. No proposals pending.</p>
          </div>
        ) : (
          proposals.map((proposal) => (
            <div 
              key={proposal.id}
              className="bg-[var(--surface-2)] border border-[var(--border-subtle)] rounded-xl p-3 hover:border-indigo-500/30 transition-all group"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 space-y-2">
                  <div className="flex items-center gap-2">
                    <Badge 
                      variant="outline" 
                      className={`text-[9px] uppercase font-bold px-1.5 py-0 ${
                        proposal.kind === 'merge' ? 'border-amber-500/30 text-amber-500 bg-amber-500/5' :
                        proposal.kind === 'prune' ? 'border-rose-500/30 text-rose-500 bg-rose-500/5' :
                        'border-emerald-500/30 text-emerald-500 bg-emerald-500/5'
                      }`}
                    >
                      {proposal.kind}
                    </Badge>
                    <span className="text-[10px] text-[var(--text-muted)] font-mono">ID: {proposal.id.slice(0, 8)}</span>
                  </div>
                  
                  <div className="text-xs font-semibold text-[var(--text-primary)] group-hover:text-indigo-400 transition-colors">
                    {proposal.details.summary}
                  </div>
                  
                  <div className="text-[10px] text-[var(--text-muted)] flex items-start gap-1">
                    <Info size={10} className="mt-0.5 shrink-0" />
                    {proposal.details.reason}
                  </div>
                </div>

                <div className="flex flex-col items-end gap-3">
                  <div className="text-right">
                    <div className={`text-xs font-bold tabular-nums ${
                      proposal.analysis_score > 80 ? 'text-emerald-400' :
                      proposal.analysis_score > 60 ? 'text-amber-400' : 'text-rose-400'
                    }`}>
                      {proposal.analysis_score}%
                    </div>
                    <div className="text-[8px] text-[var(--text-muted)] uppercase font-bold">AI Confidence</div>
                  </div>

                  <div className="flex items-center gap-1">
                    <button 
                      disabled={judging === proposal.id}
                      onClick={() => judgeProposal(proposal.id, false)}
                      className="p-1.5 hover:bg-rose-500/10 text-[var(--text-muted)] hover:text-rose-500 rounded-lg transition-all"
                    >
                      <XCircle size={18} />
                    </button>
                    <button 
                      disabled={judging === proposal.id}
                      onClick={() => judgeProposal(proposal.id, true)}
                      className="p-1.5 hover:bg-emerald-500/10 text-[var(--text-muted)] hover:text-emerald-500 rounded-lg transition-all"
                    >
                      <CheckCircle size={18} />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Footer */}
      <div className="p-3 bg-[var(--surface-2)] border-t border-[var(--border-default)] flex items-center justify-between text-[10px] text-[var(--text-muted)]">
        <div className="flex items-center gap-2">
          <Search size={12} />
          <span>Scanning Graph Regions...</span>
        </div>
        <div className="flex items-center gap-1 group cursor-pointer hover:text-indigo-400 transition-colors">
          <span>Staging Manifest</span>
          <ChevronRight size={12} className="group-hover:translate-x-0.5 transition-transform" />
        </div>
      </div>
    </div>
  );
}
