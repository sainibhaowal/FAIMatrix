"use client";

import React, { useEffect, useState } from "react";
import { Play, CheckCircle, Clock, XCircle, Loader2 } from "lucide-react";

interface Job {
  id: string;
  name: string;
  status: string;
  started_at: string | null;
  duration_seconds: number | null;
  exit_code: number | null;
}

const STATUS_STYLES: Record<string, { icon: React.ElementType; color: string; label: string }> = {
  running: { icon: Loader2, color: "text-cyan-400", label: "Running" },
  completed: { icon: CheckCircle, color: "text-emerald-400", label: "Completed" },
  failed: { icon: XCircle, color: "text-rose-400", label: "Failed" },
  pending: { icon: Clock, color: "text-slate-400", label: "Pending" },
};

function formatDuration(seconds: number | null): string {
  if (seconds === null) return "—";
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const min = Math.floor(seconds / 60);
  const sec = Math.round(seconds % 60);
  return `${min}m ${sec}s`;
}

function formatJobName(name: string): string {
  return name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function JobsPanel() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/ops/jobs")
      .then((r) => r.json())
      .then((data) => {
        setJobs(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold text-slate-100 flex items-center gap-2">
          <Play size={14} className="text-violet-400" />
          Background Jobs
        </h3>
        <span className="text-[10px] text-slate-500">{jobs.length} jobs</span>
      </div>

      {loading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-10 bg-slate-800/50 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : jobs.length === 0 ? (
        <div className="text-center py-6 text-[11px] text-slate-500">
          No background jobs
        </div>
      ) : (
        <div className="space-y-2">
          {jobs.map((job) => {
            const s = STATUS_STYLES[job.status] || STATUS_STYLES.pending;
            const Icon = s.icon;
            return (
              <div
                key={job.id}
                className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-2"
              >
                <div className="flex items-center gap-2">
                  <Icon
                    size={14}
                    className={`${s.color} ${job.status === "running" ? "animate-spin" : ""}`}
                  />
                  <span className="text-[11px] text-slate-200">
                    {formatJobName(job.name)}
                  </span>
                </div>
                <div className="flex items-center gap-3 text-[10px]">
                  <span className={s.color}>{s.label}</span>
                  <span className="text-slate-500">
                    {formatDuration(job.duration_seconds)}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
