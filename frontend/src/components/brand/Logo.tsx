"use client";

import React from "react";

export type LogoProps = {
  size?: "sm" | "md" | "lg" | "small" | "medium" | "large";
  className?: string;
  title?: string;
  px?: number;
};

/**
 * FAIMATRIX — FRACTAL SNOWFLAKE LOGO (Pure SVG)
 * ----------------------------------------------------------------
 * A clean, vector-based fractal design for the FAIMATRIX brand.
 */
export default function Logo({
  size = "small",
  className,
  title = "FAIMATRIX",
  px,
}: LogoProps) {
  const s = size === "lg" || size === "large" ? "large" : size === "md" || size === "medium" ? "medium" : "small";
  const basePx = s === "large" ? 180 : s === "medium" ? 120 : 64;
  const finalPx = typeof px === "number" ? px : basePx;

  return (
    <div
      className={["relative flex items-center justify-center shrink-0 group select-none", className].join(" ")}
      style={{ width: finalPx, height: finalPx }}
      aria-label={title}
      role="img"
    >
      <svg
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-full"
      >
        <defs>
          <linearGradient id="faim-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#22D3EE" />
            <stop offset="50%" stopColor="#38BDF8" />
            <stop offset="100%" stopColor="#8B5CF6" />
          </linearGradient>
        </defs>
        
        {/* Main Fractal Shape */}
        <g fill="url(#faim-gradient)">
          {/* Center Hub */}
          <circle cx="50" cy="50" r="8" />
          
          {/* Primary Arms (6-fold symmetry) */}
          {[0, 60, 120, 180, 240, 300].map((angle, i) => (
            <g key={i} transform={`rotate(${angle} 50 50)`}>
              {/* Main arm */}
              <ellipse cx="50" cy="30" rx="4" ry="12" />
              {/* Branch nodes */}
              <circle cx="50" cy="18" r="3" />
              <circle cx="42" cy="24" r="2" />
              <circle cx="58" cy="24" r="2" />
              {/* Sub-branches */}
              <ellipse cx="38" cy="28" rx="2" ry="6" transform="rotate(-30 38 28)" />
              <ellipse cx="62" cy="28" rx="2" ry="6" transform="rotate(30 62 28)" />
              {/* Outer nodes */}
              <circle cx="50" cy="12" r="2" />
              <circle cx="35" cy="22" r="1.5" />
              <circle cx="65" cy="22" r="1.5" />
            </g>
          ))}
          
          {/* Inner Ring Detail */}
          <circle cx="50" cy="50" r="14" stroke="url(#faim-gradient)" strokeWidth="1" fill="none" opacity="0.6" />
        </g>
      </svg>
    </div>
  );
}
