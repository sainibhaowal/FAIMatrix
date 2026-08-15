"use client";

import React, { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle,
  ChevronDown,
  GitCommit,
  GitCompare,
  Loader2,
  RotateCcw,
  Scale,
  ShieldCheck,
} from "lucide-react";
import { Badge, Button } from "@/components/ui";

export interface VersionChangeItem {
  winner_id: string;
  loser_id: string;
  winner_label: string;
  loser_label: string;
  score: number;
  selector: string;
}

export interface GraphVersionRow {
  version: number;
  completed_at?: string | null;
  merges: number;
  prunes: number;
  inventions: number;
  diagnostics: Record<string, number>;
  changes: VersionChangeItem[];
  backup_count: number;
}

export interface InventionVersionsData {
  graph_id: string;
  current_version: number;
  versions: GraphVersionRow[];
}

interface EvolutionVersionHistoryProps {
  data?: InventionVersionsData | null;
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  onRestore?: (
    version: number,
  ) => Promise<{ restored: number; skipped: number } | void> | void;
  restoringVersion?: number | null;
}

const DIAGNOSTIC_LABELS: Record<string, string> = {
  D_hat: "D",
  H_hat: "H",
  lambda_hat: "λ",
  redundancy_R: "R",
  novelty_N: "N",
  energy_E: "E",
};

function formatTime(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatScore(value: number): string {
  return value.toFixed(4);
}

export const EvolutionVersionHistory: React.FC<EvolutionVersionHistoryProps> = ({
  data,
  loading = false,
  error = null,
  onRetry,
  onRestore,
  restoringVersion = null,
}) => {
  const [expanded, setExpanded] = useState<number | null>(null);

  const versions = data?.versions ?? [];
  const currentVersion = data?.current_version ?? 0;
  const isEmpty = !loading && !error && data != null && versions.length === 0;

  return (
    <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)]">
      <div className="flex items-center justify-between border-b border-white/6 px-5 py-3">
        <div>
          <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">
            Graph Version History
          </p>
          <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
            Per-cycle diffs derived from the event journal
          </p>
        </div>
        {!loading && !error && data != null && (
          <Badge variant="secondary" size="xs">
            v{currentVersion} · {versions.length} cycles
          </Badge>
        )}
      </div>

      <div className="px-5 pb-5 pt-4">
        {loading && (
          <div className="flex items-center justify-center gap-2 py-8">
            <Loader2 size={16} className="animate-spin text-purple-400" />
            <span className="font-mono text-xs uppercase tracking-widest text-slate-400">
              Loading version journal…
            </span>
          </div>
        )}

        {!loading && error && (
          <div className="flex flex-col items-center justify-center gap-2 py-8 text-center">
            <AlertTriangle size={18} className="text-rose-400" />
            <p className="max-w-sm text-xs text-slate-400">{error}</p>
            {onRetry && (
              <Button size="sm" variant="secondary" onClick={onRetry}>
                <RotateCcw size={12} className="mr-1" />
                Retry
              </Button>
            )}
          </div>
        )}

        {!loading && !error && isEmpty && (
          <p className="py-6 text-center text-xs text-slate-500">
            No completed evolution cycles yet. Run an evolution cycle — each
            completion is recorded here as a version with its full diff.
          </p>
        )}

        {!loading && !error && versions.length > 0 && (
          <div className="max-h-72 space-y-2 overflow-y-auto pr-1 custom-scrollbar">
            {[...versions].reverse().map((row) => {
              const isExpanded = expanded === row.version;
              return (
                <div
                  key={row.version}
                  className={`overflow-hidden rounded-xl border transition-colors ${
                    isExpanded
                      ? "border-purple-500/40 bg-purple-500/[0.04]"
                      : "border-white/8 bg-white/[0.02] hover:border-white/16"
                  }`}
                >
                  <button
                    type="button"
                    onClick={() =>
                      setExpanded(isExpanded ? null : row.version)
                    }
                    className="flex w-full items-center gap-2 px-3 py-2.5 text-left"
                  >
                    <GitCommit
                      size={14}
                      className={
                        row.version === currentVersion
                          ? "text-amber-300"
                          : "text-slate-500"
                      }
                    />
                    <span
                      className={`font-mono text-xs font-bold ${
                        row.version === currentVersion
                          ? "text-amber-300"
                          : "text-slate-200"
                      }`}
                    >
                      v{row.version}
                      {row.version === currentVersion && (
                        <span className="ml-1.5 text-[9px] font-normal uppercase tracking-wider text-amber-400/80">
                          current
                        </span>
                      )}
                    </span>
                    <span className="hidden sm:block font-mono text-[10px] text-slate-500">
                      {formatTime(row.completed_at)}
                    </span>
                    <span className="ml-auto flex items-center gap-1.5 text-[10px] font-mono">
                      {row.merges > 0 && (
                        <span className="text-sky-300">
                          +{row.merges}m
                        </span>
                      )}
                      {row.prunes > 0 && (
                        <span className="text-rose-300">
                          −{row.prunes}p
                        </span>
                      )}
                      {row.inventions > 0 && (
                        <span className="text-purple-300">
                          +{row.inventions}i
                        </span>
                      )}
                      {row.merges === 0 &&
                        row.prunes === 0 &&
                        row.inventions === 0 && (
                          <span className="text-slate-600">no actions</span>
                        )}
                      {row.version < currentVersion && (
                        <ChevronDown
                          size={12}
                          className={`transition-transform text-slate-500 ${
                            isExpanded ? "rotate-180" : ""
                          }`}
                        />
                      )}
                    </span>
                  </button>

                  <AnimatePresence initial={false}>
                    {isExpanded && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.18 }}
                        className="overflow-hidden"
                      >
                        <div className="space-y-3 border-t border-white/8 px-3 py-3">
                          {Object.keys(row.diagnostics).length > 0 && (
                            <div>
                              <p className="mb-1.5 font-mono text-[9px] font-bold uppercase tracking-widest text-slate-500">
                                Cycle diagnostics
                              </p>
                              <div className="flex flex-wrap gap-1.5">
                                {Object.entries(row.diagnostics).map(
                                  ([key, value]) => (
                                    <span
                                      key={key}
                                      className="rounded-md border border-white/8 bg-white/[0.03] px-1.5 py-0.5 font-mono text-[10px] text-slate-300"
                                    >
                                      {DIAGNOSTIC_LABELS[key] ?? key}{" "}
                                      <span className="text-cyan-300">
                                        {value.toFixed(4)}
                                      </span>
                                    </span>
                                  ),
                                )}
                              </div>
                            </div>
                          )}

                          {row.changes.length > 0 ? (
                            <div>
                              <p className="mb-1.5 font-mono text-[9px] font-bold uppercase tracking-widest text-slate-500">
                                Merges in this cycle · {row.changes.length}
                              </p>
                              <div className="space-y-1.5">
                                {row.changes.map((change, idx) => (
                                  <div
                                    key={`${change.winner_id}-${change.loser_id}-${idx}`}
                                    className="rounded-lg border border-white/8 bg-[#050810]/60 p-2"
                                  >
                                    <div className="flex items-center gap-1.5">
                                      <ShieldCheck
                                        size={11}
                                        className="shrink-0 text-emerald-400"
                                      />
                                      <span className="min-w-0 flex-1 truncate text-[11px] text-emerald-200">
                                        {change.winner_label}
                                      </span>
                                      <Badge variant="info" size="xs">
                                        {formatScore(change.score)}
                                      </Badge>
                                    </div>
                                    <div className="mt-1 flex items-center gap-1.5">
                                      <Scale
                                        size={11}
                                        className="shrink-0 text-rose-400"
                                      />
                                      <span className="min-w-0 flex-1 truncate text-[11px] text-rose-200/90">
                                        {change.loser_label}
                                      </span>
                                      <Badge variant="outline" size="xs">
                                        {change.selector}
                                      </Badge>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          ) : (
                            <p className="text-[11px] text-slate-500 italic">
                              {row.merges > 0
                                ? "Merges recorded but no journal entries with ids."
                                : "No merges — cycle only invented or pruned."}
                            </p>
                          )}
                        </div>

                        {row.backup_count > 0 && onRestore && (
                          <div className="border-t border-white/8 px-3 py-2.5 flex items-center justify-between gap-2">
                            <span className="font-mono text-[10px] text-slate-500">
                              {row.backup_count} backed-up node
                              {row.backup_count === 1 ? "" : "s"} · safe to undo
                            </span>
                            <button
                              type="button"
                              disabled={restoringVersion === row.version}
                              onClick={() => void onRestore(row.version)}
                              className="flex items-center gap-1.5 rounded-lg border border-amber-500/40 bg-amber-500/15 px-2.5 py-1 text-[11px] font-mono text-amber-300 transition-all hover:bg-amber-500/25 disabled:cursor-not-allowed disabled:opacity-50"
                            >
                              {restoringVersion === row.version ? (
                                <Loader2 size={11} className="animate-spin" />
                              ) : (
                                <RotateCcw size={11} />
                              )}
                              Restore this cycle
                            </button>
                          </div>
                        )}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              );
            })}
          </div>
        )}

        {!loading && !error && versions.length > 0 && (
          <p className="mt-3 flex items-center gap-1.5 border-t border-white/6 pt-3 font-mono text-[10px] text-slate-500">
            <GitCompare size={11} className="text-slate-600" />
            Latest cycle diff is also highlighted on the 2.5D canvas via the
            Cycle diff toggle.
          </p>
        )}
      </div>
    </div>
  );
};