"use client";

import React from "react";

/* =============================================================================
   FAIM UI — Spinner Component
   
   A loading spinner with FAIM styling and multiple sizes.
============================================================================= */

export interface SpinnerProps {
  /** Size of the spinner */
  size?: "xs" | "sm" | "md" | "lg" | "xl" | number;
  /** Custom color (defaults to --faim-primary) */
  color?: string;
  /** Label for accessibility */
  label?: string;
  /** Additional class names */
  className?: string;
}

const sizeMap = {
  xs: 12,
  sm: 16,
  md: 20,
  lg: 24,
  xl: 32,
};

export const Spinner: React.FC<SpinnerProps> = ({
  size = "md",
  color,
  label = "Loading",
  className = "",
}) => {
  const pixelSize = typeof size === "number" ? size : sizeMap[size];

  return (
    <div
      role="status"
      aria-label={label}
      className={["inline-flex items-center justify-center", className].join(" ")}
    >
      <svg
        className="animate-spin"
        width={pixelSize}
        height={pixelSize}
        viewBox="0 0 24 24"
        fill="none"
        style={{ color: color || "var(--faim-primary)" }}
      >
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="3"
        />
        <path
          className="opacity-100"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        />
      </svg>
      <span className="sr-only">{label}</span>
    </div>
  );
};

/* =============================================================================
   FAIM UI — Skeleton Component
   
   A loading placeholder with animated shimmer effect.
============================================================================= */

export interface SkeletonProps {
  /** Width of the skeleton */
  width?: string | number;
  /** Height of the skeleton */
  height?: string | number;
  /** Make it a circle */
  circle?: boolean;
  /** Border radius */
  rounded?: "sm" | "md" | "lg" | "xl" | "full";
  /** Additional class names */
  className?: string;
}

const radiusMap = {
  sm: "var(--radius-sm)",
  md: "var(--radius-md)",
  lg: "var(--radius-lg)",
  xl: "var(--radius-xl)",
  full: "var(--radius-full)",
};

export const Skeleton: React.FC<SkeletonProps> = ({
  width = "100%",
  height = "1rem",
  circle = false,
  rounded = "md",
  className = "",
}) => {
  const style: React.CSSProperties = {
    width: typeof width === "number" ? `${width}px` : width,
    height: typeof height === "number" ? `${height}px` : height,
    borderRadius: circle ? "50%" : radiusMap[rounded],
  };

  if (circle) {
    style.width = style.height;
  }

  return (
    <div
      className={[
        "relative overflow-hidden",
        "bg-[var(--surface-2)]",
        "before:absolute before:inset-0",
        "before:bg-gradient-to-r before:from-transparent before:via-white/5 before:to-transparent",
        "before:animate-[shimmer_2s_infinite]",
        className,
      ].join(" ")}
      style={style}
      aria-hidden="true"
    />
  );
};

/* =============================================================================
   Skeleton Text (multiple lines)
============================================================================= */

export interface SkeletonTextProps {
  /** Number of lines */
  lines?: number;
  /** Last line width */
  lastLineWidth?: string;
  /** Gap between lines */
  gap?: string;
  /** Additional class names */
  className?: string;
}

export const SkeletonText: React.FC<SkeletonTextProps> = ({
  lines = 3,
  lastLineWidth = "75%",
  gap = "0.5rem",
  className = "",
}) => {
  return (
    <div className={["space-y-2", className].join(" ")} style={{ gap }}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          height="0.875rem"
          width={i === lines - 1 ? lastLineWidth : "100%"}
        />
      ))}
    </div>
  );
};

/* =============================================================================
   Skeleton Card
============================================================================= */

export const SkeletonCard: React.FC<{ className?: string }> = ({
  className = "",
}) => {
  return (
    <div
      className={[
        "rounded-2xl border border-[var(--border-default)] bg-[var(--surface-1)] p-4",
        className,
      ].join(" ")}
    >
      <div className="flex items-center gap-3 mb-4">
        <Skeleton circle height={40} />
        <div className="flex-1">
          <Skeleton height="0.875rem" width="60%" />
          <Skeleton height="0.75rem" width="40%" className="mt-2" />
        </div>
      </div>
      <SkeletonText lines={3} />
    </div>
  );
};
