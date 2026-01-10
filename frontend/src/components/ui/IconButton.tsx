"use client";

import React from "react";

export function IconButton({
  title,
  active,
  onClick,
  children,
  className = "",
  disabled,
}: {
  title: string;
  active?: boolean;
  onClick?: () => void;
  children: React.ReactNode;
  className?: string;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      title={title}
      aria-label={title}
      aria-pressed={active}
      disabled={disabled}
      onClick={onClick}
      className={[
        "inline-flex h-9 w-9 items-center justify-center rounded-lg border",
        active
          ? "border-cyan-400/35 bg-cyan-500/10"
          : "border-slate-800/70 bg-slate-950/50",
        "text-slate-200 hover:border-cyan-400/25 hover:bg-cyan-500/5",
        "transition-all duration-150 active:scale-[0.98]",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        className,
      ].join(" ")}
    >
      {children}
    </button>
  );
}
