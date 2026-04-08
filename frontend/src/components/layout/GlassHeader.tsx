"use client";

import React from "react";
import { LucideIcon } from "lucide-react";
import { motion } from "framer-motion";

interface GlassHeaderProps {
  title: string;
  subtitle: string;
  icon: LucideIcon;
  accentColor?: string;
  actions?: React.ReactNode;
}

export function GlassHeader({
  title,
  subtitle,
  icon: Icon,
  accentColor = "var(--faim-primary)",
  actions,
}: GlassHeaderProps) {
  // Split title into first character and the rest for custom sizing (16px / 14px)
  const firstChar = title.charAt(0).toUpperCase();
  const restChars = title.slice(1).toUpperCase();

  return (
    <header className="relative flex flex-wrap items-center justify-between gap-6 px-2 py-1.5">
      <div className="flex items-center gap-5">
        {/* Animated Vertical Accent Bar */}
        <div className="relative h-8 w-[3px] bg-white/5 rounded-full overflow-hidden">
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: "100%" }}
            transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1], delay: 0.2 }}
            className="w-full shadow-[0_0_15px_rgba(34,211,238,0.3)]"
            style={{ backgroundColor: accentColor }}
          />
        </div>

        <div className="flex flex-col gap-0.5">
          <div className="flex items-center gap-3">
            <Icon className="shrink-0 opacity-80" size={20} strokeWidth={2} style={{ color: accentColor }} />
            <h1 className="font-bold flex items-baseline gap-[1px] text-white leading-none tracking-tight">
              <span className="text-[22px] font-extrabold">{firstChar}</span>
              <span className="text-[18px] font-semibold opacity-90">{restChars}</span>
            </h1>
          </div>
          <p className="text-[9px] font-bold uppercase tracking-[0.2em] text-slate-500/60 leading-tight">
            {subtitle}
          </p>
        </div>
      </div>

      {actions && (
        <div className="flex items-center gap-3">
          {actions}
        </div>
      )}
    </header>
  );
}
