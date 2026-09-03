"use client";

import React, { useState } from "react";
import { BookOpen } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { ApprovalQueueAdmin } from "@/components/dashboard/ApprovalQueueAdmin";
import { ApprovalQueueManual } from "@/components/manuals/ApprovalQueueManual";

export default function ApprovalQueuePage() {
  const [manualOpen, setManualOpen] = useState(false);

  return (
    <>
      <div className="flex h-full text-slate-100 overflow-hidden bg-transparent relative">
        <div className="flex-1 flex flex-col min-w-0 h-full relative">
          <div className="h-12 border-b border-white/6 px-4 flex items-center justify-between bg-black/20 shrink-0">
            <div className="flex items-center gap-2.5">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg border border-amber-500/30 bg-amber-500/10 text-amber-300">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <span className="text-xs font-bold tracking-wide text-white">
                Approval Queue
              </span>
              <span className="inline-flex items-center gap-1 rounded-full border border-amber-400/25 bg-amber-500/10 px-2 py-0.5 text-[9px] font-semibold text-amber-300">
                Admin
              </span>
            </div>
            <Button
              variant="outline"
              leftIcon={<BookOpen size={13} />}
              onClick={() => setManualOpen(true)}
              className="rounded-xl border-white/5 bg-white/5 hover:bg-white/10 backdrop-blur-md h-10 px-5 text-[11px] font-bold uppercase tracking-[0.2em]"
            >
              User Manual
            </Button>
          </div>

          <div className="flex-1 flex flex-col min-h-0 relative p-4">
            <ApprovalQueueAdmin tenantId="default" />
          </div>
        </div>
      </div>
      <ApprovalQueueManual open={manualOpen} onClose={() => setManualOpen(false)} />
    </>
  );
}