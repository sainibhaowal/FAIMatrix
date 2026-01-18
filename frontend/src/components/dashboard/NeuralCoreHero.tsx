"use client";

import React from "react";
import Link from "next/link";
import { Brain, Dna } from "lucide-react";
import Logo from "@/components/brand/Logo";

interface NeuralCoreHeroProps {
  isHealthy: boolean;
  nodesCount?: number;
}

export function NeuralCoreHero({ isHealthy, nodesCount }: NeuralCoreHeroProps) {
  return (
    <section className="relative overflow-hidden rounded-3xl border border-cyan-500/10 bg-slate-950/40 backdrop-blur-2xl">
      <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/5 via-transparent to-violet-500/5 pointer-events-none" />
      <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-[0.02] pointer-events-none" />
      
      <div className="relative flex items-center gap-6 p-6">
        {/* Animated Logo */}
        <div className="flex-shrink-0">
          <Logo px={180} className="rounded-2xl" />
        </div>
        
        {/* System Info */}
        <div className="flex-1 min-w-0">
          <div className="text-[11px] uppercase tracking-[0.15em] text-cyan-300 font-medium">FAIMATRIX SYNAPSE</div>
          <h2 className="text-xl font-bold text-slate-50 mt-1">Neural Core {isHealthy ? "Online" : "Offline"}</h2>
          <p className="text-sm text-slate-400 mt-1 line-clamp-2">
            Neural Knowledge Synthesis • Your personal intelligence engine
          </p>
          
          {/* Status Indicators */}
          <div className="flex items-center gap-4 mt-3">
            <div className="flex items-center gap-1.5 text-xs">
              <span className={`w-2 h-2 rounded-full ${isHealthy ? "bg-emerald-400 animate-pulse" : "bg-red-400"}`} />
              <span className="text-slate-300">{isHealthy ? "Systems Operational" : "Connection Lost"}</span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-slate-400">
              <Brain size={12} />
              <span>{nodesCount?.toLocaleString() ?? "—"} nodes</span>
            </div>
            {/* Evolution Pulse - FAIM Self-Evolution Indicator */}
            <Link 
              href="/dashboard/evolution"
              className="flex items-center gap-1.5 text-xs text-purple-400 hover:text-purple-300 transition-colors"
            >
              <Dna size={12} className="animate-pulse" />
              <span>Evolution Active</span>
            </Link>
          </div>
        </div>
        
        {/* Quick Action */}

      </div>
    </section>
  );
}
