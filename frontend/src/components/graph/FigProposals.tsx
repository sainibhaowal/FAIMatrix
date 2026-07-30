"use client";

import { Check, X, BrainCircuit, Info } from "lucide-react";
import { Badge } from "@/components/ui";
import { motion, AnimatePresence } from "framer-motion";

export type WritebackProposal = {
  id: string;
  node_id: string;
  original_content: string;
  proposed_content: string;
  reasoning: string;
  confidence: number;
  type: "update" | "create" | "link";
};

type FigProposalsProps = {
  proposals: WritebackProposal[];
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
};

export default function FigProposals({
  proposals,
  onApprove,
  onReject,
}: FigProposalsProps) {
  if (proposals.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-center border border-dashed border-slate-800 rounded-2xl bg-slate-900/20">
        <BrainCircuit className="h-8 w-8 text-slate-700 mb-3" />
        <p className="text-sm font-medium text-slate-500">No active proposals</p>
        <p className="text-[10px] text-slate-600 mt-1 uppercase tracking-widest">
          Cortex is currently in observation mode
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between px-1">
        <span className="text-[10px] font-black uppercase tracking-[0.2em] text-cyan-400/70">
          {proposals.length} Memory Proposals
        </span>
      </div>

      <div className="max-h-[300px] overflow-y-auto pr-2 space-y-2 faim-scrollbar">
        <AnimatePresence mode="popLayout">
          {proposals.map((p) => (
            <motion.div
              key={p.id}
              layout
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="group relative p-4 rounded-xl border border-slate-800 bg-slate-950/40 hover:border-cyan-500/30 transition-all"
            >
              <div className="flex items-start justify-between mb-2">
                <Badge variant="outline" size="sm" className="text-[9px] uppercase tracking-tighter">
                  {p.type}
                </Badge>
                <span className="text-[10px] font-mono text-cyan-500/60">
                  conf: {(p.confidence * 100).toFixed(0)}%
                </span>
              </div>

              <div className="space-y-2 mb-3">
                <div className="text-[11px] leading-relaxed text-slate-400">
                  <span className="text-slate-600 block text-[9px] uppercase font-bold mb-1">Reasoning</span>
                  {p.reasoning}
                </div>
                
                <div className="grid grid-cols-2 gap-2 mt-2 pt-2 border-t border-slate-800/50">
                   <div className="text-[9px] text-slate-500">
                      <span className="block font-bold text-slate-600 mb-1 uppercase">Original</span>
                      <div className="truncate opacity-50">{p.original_content}</div>
                   </div>
                   <div className="text-[9px] text-emerald-400/80">
                      <span className="block font-bold text-emerald-500/60 mb-1 uppercase">Proposed</span>
                      <div className="truncate">{p.proposed_content}</div>
                   </div>
                </div>
              </div>

              <div className="flex items-center gap-2 mt-4">
                <button
                  onClick={() => onApprove(p.id)}
                  className="flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] font-bold hover:bg-emerald-500 hover:text-slate-950 transition-all"
                >
                  <Check size={12} />
                  Approve
                </button>
                <button
                  onClick={() => onReject(p.id)}
                  className="flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-slate-800/40 border border-slate-700/50 text-slate-400 text-[10px] font-bold hover:bg-rose-500 hover:border-rose-400 hover:text-white transition-all"
                >
                  <X size={12} />
                  Reject
                </button>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
