"use client";

import React from "react";
import { Activity, Cpu, HardDrive, Server, Zap } from "lucide-react";

interface WorkerPoolStatusProps {
  evolution?: {
    is_running: boolean;
    worker_count?: number;
  } | null;
  pipeline?: {
    queue_depth: number;
    throughput: number;
    gpu_active: boolean;
    system_health: { redis: boolean; qdrant: boolean; encryption: boolean };
  } | null;
}

const SERVICES = [
  {
    key: "evolution",
    label: "Evolution Workers",
    icon: Activity,
    color: "text-emerald-400",
    bg: "bg-emerald-400/10",
  },
  {
    key: "ingest",
    label: "Ingest Pipeline",
    icon: HardDrive,
    color: "text-cyan-400",
    bg: "bg-cyan-400/10",
  },
  {
    key: "vector",
    label: "Vector Index",
    icon: Server,
    color: "text-violet-400",
    bg: "bg-violet-400/10",
  },
  {
    key: "gpu",
    label: "GPU Accelerator",
    icon: Zap,
    color: "text-amber-400",
    bg: "bg-amber-400/10",
  },
] as const;

export const WorkerPoolStatus: React.FC<WorkerPoolStatusProps> = ({
  evolution,
  pipeline,
}) => {
  return (
    <div className="flex flex-col h-full w-full gap-3">
      <div className="flex items-center justify-between text-[10px] font-mono uppercase tracking-widest text-slate-500">
        <span>Worker Pool</span>
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-400" />
          <span className="text-emerald-300">Healthy</span>
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2 flex-1">
        {SERVICES.map((s) => {
          let status: "running" | "idle" | "offline" = "idle";
          let detail = "";

          if (s.key === "evolution") {
            if (!evolution) status = "offline";
            else if (evolution.is_running) {
              status = "running";
              detail = `${evolution.worker_count ?? 1} active`;
            } else {
              status = "idle";
              detail = "Waiting for trigger";
            }
          } else if (s.key === "ingest") {
            if (!pipeline) status = "offline";
            else if (pipeline.queue_depth > 0) {
              status = "running";
              detail = `${pipeline.queue_depth} queued · ${pipeline.throughput.toFixed(1)}/s`;
            } else {
              status = "idle";
              detail = "No pending jobs";
            }
          } else if (s.key === "vector") {
            const healthy = pipeline?.system_health?.qdrant ?? false;
            status = healthy ? "idle" : "offline";
            detail = healthy ? "Connected" : "Disconnected";
          } else if (s.key === "gpu") {
            status = pipeline?.gpu_active ? "running" : "idle";
            detail = pipeline?.gpu_active ? "CUDA active" : "CPU fallback";
          }

          const colors = {
            running: { border: "border-emerald-400/40", bg: "bg-emerald-400/10", dot: "bg-emerald-400", text: "text-emerald-300" },
            idle: { border: "border-slate-600/40", bg: "bg-slate-600/10", dot: "bg-slate-500", text: "text-slate-400" },
            offline: { border: "border-rose-400/40", bg: "bg-rose-400/10", dot: "bg-rose-400", text: "text-rose-400" },
          }[status];

          return (
            <div
              key={s.key}
              className={`relative rounded-[12px] border p-2.5 flex flex-col items-start justify-between min-h-[72px] transition-colors ${colors.border} ${colors.bg}`}
            >
              <div className="flex items-center gap-2 w-full min-w-0">
                <span className={`w-6 h-6 shrink-0 rounded-lg flex items-center justify-center ${s.bg}`}>
                  <s.icon size={12} className={s.color} />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-[10px] font-semibold text-white truncate leading-tight">{s.label}</p>
                  <p className={`text-[8px] font-mono uppercase tracking-wider ${colors.text} leading-tight`}>{status.toUpperCase()}</p>
                </div>
              </div>
              <div className="flex items-center justify-between w-full mt-1.5 min-w-0 pr-2">
                <p className="text-[9px] text-slate-500 truncate leading-none">{detail}</p>
                <span className={`w-1.5 h-1.5 shrink-0 rounded-full ${colors.dot}`} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};