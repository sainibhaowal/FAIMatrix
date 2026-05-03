"use client";

import Link from "next/link";
import { ServerCog } from "lucide-react";

import { GlassHeader } from "@/components/layout/GlassHeader";
import { ControlPlanePanel } from "@/components/storage/ControlPlanePanel";

export default function ControlPlanePage() {
  return (
    <div className="relative space-y-4 pb-8 text-slate-100 px-1">
      <div className="faim-grid" />

      <GlassHeader
        title="Control Plane"
        titleTestId="control-plane-page-title"
        subtitle="Power-user graph maintenance, repair, and enrichment"
        icon={ServerCog}
        actions={
          <Link
            href="/dashboard/storage"
            className="inline-flex h-10 items-center justify-center gap-2 rounded-xl border border-white/5 bg-white/5 px-5 text-[11px] font-bold uppercase tracking-widest transition-all hover:bg-white/10 backdrop-blur-md shadow-sm"
            style={{ color: "var(--text-primary)" }}
          >
            Back to Storage
          </Link>
        }
      />

      <ControlPlanePanel />
    </div>
  );
}
