"use client";

import React, { useRef } from "react";
import { useOutsideClick } from "../../ui/index";

function cx(...parts: Array<string | false | null | undefined>) {
  return parts.filter(Boolean).join(" ");
}

export function Dropdown({
  open,
  anchorRef,
  onClose,
  children,
  className,
}: {
  open: boolean;
  anchorRef: React.RefObject<HTMLElement | null>;
  onClose: () => void;
  children: React.ReactNode;
  className?: string;
}) {
  const panelRef = useRef<HTMLDivElement>(null);
  useOutsideClick([anchorRef as any, panelRef as any], onClose, open);
  if (!open) return null;
  return (
    <div
      ref={panelRef}
      className={cx(
        "absolute right-0 mt-2 w-[320px] rounded-2xl border border-white/10 bg-slate-950/95 backdrop-blur-xl shadow-[0_20px_60px_-28px_rgba(0,0,0,0.9)]",
        className,
      )}
    >
      {children}
    </div>
  );
}
