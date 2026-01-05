"use client";

import React from "react";

/* =============================================================================
   FAIM UI — Progress Component
   
   Progress bars and circular progress indicators.
============================================================================= */

export interface ProgressProps {
  /** Current value (0-100) */
  value: number;
  /** Maximum value */
  max?: number;
  /** Size variant */
  size?: "sm" | "md" | "lg";
  /** Color variant */
  variant?: "primary" | "success" | "warning" | "error" | "gradient";
  /** Show percentage label */
  showLabel?: boolean;
  /** Custom label */
  label?: string;
  /** Animated stripe effect */
  animated?: boolean;
  /** Additional class names */
  className?: string;
}

const sizeConfig = {
  sm: { height: "h-1.5", text: "text-[10px]" },
  md: { height: "h-2", text: "text-xs" },
  lg: { height: "h-3", text: "text-sm" },
};

const colorConfig = {
  primary: "bg-[var(--faim-primary)]",
  success: "bg-[var(--faim-success)]",
  warning: "bg-[var(--faim-warning)]",
  error: "bg-[var(--faim-error)]",
  gradient: "bg-gradient-to-r from-[var(--faim-primary)] via-[var(--faim-secondary)] to-[var(--faim-accent)]",
};

export const Progress: React.FC<ProgressProps> = ({
  value,
  max = 100,
  size = "md",
  variant = "primary",
  showLabel = false,
  label,
  animated = false,
  className = "",
}) => {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));
  const config = sizeConfig[size];
  const colorClass = colorConfig[variant];

  return (
    <div className={["w-full", className].join(" ")}>
      {/* Label row */}
      {(showLabel || label) && (
        <div className="flex justify-between items-center mb-1.5">
          {label && (
            <span className={["text-[var(--text-secondary)]", config.text].join(" ")}>
              {label}
            </span>
          )}
          {showLabel && (
            <span className={["text-[var(--text-primary)] font-medium", config.text].join(" ")}>
              {Math.round(percentage)}%
            </span>
          )}
        </div>
      )}

      {/* Progress bar */}
      <div
        className={[
          "w-full rounded-full overflow-hidden",
          "bg-[var(--surface-2)]",
          config.height,
        ].join(" ")}
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
      >
        <div
          className={[
            "h-full rounded-full",
            "transition-all duration-500 ease-out",
            colorClass,
            animated && "bg-[length:1rem_1rem] animate-[progress-stripe_1s_linear_infinite]",
            animated && "bg-[linear-gradient(45deg,rgba(255,255,255,0.15)_25%,transparent_25%,transparent_50%,rgba(255,255,255,0.15)_50%,rgba(255,255,255,0.15)_75%,transparent_75%,transparent)]",
          ]
            .filter(Boolean)
            .join(" ")}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
};

/* =============================================================================
   Circular Progress
============================================================================= */

export interface CircularProgressProps {
  /** Current value (0-100) */
  value: number;
  /** Size in pixels */
  size?: number;
  /** Stroke width */
  strokeWidth?: number;
  /** Color variant */
  variant?: "primary" | "success" | "warning" | "error";
  /** Show percentage in center */
  showLabel?: boolean;
  /** Custom center content */
  children?: React.ReactNode;
  /** Additional class names */
  className?: string;
}

const circularColorConfig = {
  primary: "var(--faim-primary)",
  success: "var(--faim-success)",
  warning: "var(--faim-warning)",
  error: "var(--faim-error)",
};

export const CircularProgress: React.FC<CircularProgressProps> = ({
  value,
  size = 48,
  strokeWidth = 4,
  variant = "primary",
  showLabel = false,
  children,
  className = "",
}) => {
  const percentage = Math.min(100, Math.max(0, value));
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (percentage / 100) * circumference;
  const color = circularColorConfig[variant];

  return (
    <div
      className={["relative inline-flex items-center justify-center", className].join(" ")}
      style={{ width: size, height: size }}
      role="progressbar"
      aria-valuenow={value}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <svg
        width={size}
        height={size}
        className="transform -rotate-90"
      >
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--surface-2)"
          strokeWidth={strokeWidth}
        />
        {/* Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-500 ease-out"
          style={{
            filter: `drop-shadow(0 0 6px ${color})`,
          }}
        />
      </svg>

      {/* Center content */}
      {(showLabel || children) && (
        <div className="absolute inset-0 flex items-center justify-center">
          {children ?? (
            <span className="text-xs font-semibold text-[var(--text-primary)]">
              {Math.round(percentage)}%
            </span>
          )}
        </div>
      )}
    </div>
  );
};
