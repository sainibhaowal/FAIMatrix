"use client";

import React from "react";
import { Info } from "lucide-react";

import { Tooltip } from "@/components/ui";

export function DomainInfoTip({
  label,
  content,
}: {
  label: string;
  content: React.ReactNode;
}) {
  return (
    <Tooltip
      position="bottom"
      className="max-w-[14rem] rounded-[14px] px-3 py-2"
      content={
        <div className="max-w-[14rem]">
          <p className="text-[9px] font-black uppercase tracking-[0.22em] text-cyan-200">
            {label}
          </p>
          <div className="mt-1 text-[11px] leading-4.5 text-slate-200">
            {content}
          </div>
        </div>
      }
    >
      <button
        type="button"
        aria-label={`${label} info`}
        className="inline-flex h-5 w-5 items-center justify-center rounded-[10px] border border-cyan-400/18 bg-cyan-400/8 text-cyan-200 transition-colors hover:bg-cyan-400/14"
      >
        <Info size={10} />
      </button>
    </Tooltip>
  );
}
