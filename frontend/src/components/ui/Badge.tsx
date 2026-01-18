"use client";

import React from "react";
import { cva, type VariantProps } from "class-variance-authority";

/* =============================================================================
   FAIM UI — Badge Component
   
   Status indicators and labels with FAIM styling.
============================================================================= */

const badgeVariants = cva(
  [
    "inline-flex items-center gap-1",
    "font-medium",
    "border",
    "transition-colors",
  ].join(" "),
  {
    variants: {
      variant: {
        default: [
          "bg-[var(--glass-bg)] text-[var(--text-primary)]",
          "border-[var(--border-default)]",
        ].join(" "),
        primary: [
          "bg-[var(--faim-primary-muted)] text-[var(--faim-primary)]",
          "border-[var(--faim-primary)]/30",
        ].join(" "),
        secondary: [
          "bg-[var(--faim-secondary-muted)] text-[var(--faim-secondary)]",
          "border-[var(--faim-secondary)]/30",
        ].join(" "),
        success: [
          "bg-[var(--faim-success-muted)] text-[var(--faim-success-text)]",
          "border-[var(--faim-success)]/30",
        ].join(" "),
        warning: [
          "bg-[var(--faim-warning-muted)] text-[var(--faim-warning-text)]",
          "border-[var(--faim-warning)]/30",
        ].join(" "),
        error: [
          "bg-[var(--faim-error-muted)] text-[var(--faim-error-text)]",
          "border-[var(--faim-error)]/30",
        ].join(" "),
        info: [
          "bg-[var(--faim-info-muted)] text-[var(--faim-info-text)]",
          "border-[var(--faim-info)]/30",
        ].join(" "),
        outline: [
          "bg-transparent text-[var(--text-secondary)]",
          "border-[var(--border-default)]",
        ].join(" "),
      },
      size: {
        xs: "h-5 px-1.5 text-[10px] rounded-md",
        sm: "h-6 px-2 text-[11px] rounded-md",
        md: "h-7 px-2.5 text-xs rounded-lg",
        lg: "h-8 px-3 text-sm rounded-lg",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "sm",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {
  /** Show a dot indicator */
  dot?: boolean;
  /** Dot color (inherits from variant by default) */
  dotColor?: string;
  /** Left icon */
  icon?: React.ReactNode;
}

export const Badge: React.FC<BadgeProps> = ({
  className = "",
  variant,
  size,
  dot = false,
  dotColor,
  icon,
  children,
  ...props
}) => {
  return (
    <span
      className={badgeVariants({ variant, size }) + " " + className}
      {...props}
    >
      {dot && (
        <span
          className="w-1.5 h-1.5 rounded-full"
          style={{ backgroundColor: dotColor || "currentColor" }}
        />
      )}
      {icon}
      {children}
    </span>
  );
};

/* =============================================================================
   FAIM UI — Status Badge (semantic presets)
============================================================================= */

type StatusType = "online" | "offline" | "busy" | "away" | "pending" | "active" | "inactive";

const statusConfig: Record<StatusType, { label: string; variant: "success" | "error" | "warning" | "default"; dot: boolean }> = {
  online: { label: "Online", variant: "success", dot: true },
  offline: { label: "Offline", variant: "error", dot: true },
  busy: { label: "Busy", variant: "error", dot: true },
  away: { label: "Away", variant: "warning", dot: true },
  pending: { label: "Pending", variant: "warning", dot: true },
  active: { label: "Active", variant: "success", dot: true },
  inactive: { label: "Inactive", variant: "default", dot: true },
};

export interface StatusBadgeProps {
  status: StatusType;
  size?: "xs" | "sm" | "md" | "lg";
  showLabel?: boolean;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  size = "sm",
  showLabel = true,
  className = "",
}) => {
  const config = statusConfig[status];

  return (
    <Badge
      variant={config.variant}
      size={size}
      dot={config.dot}
      className={className}
    >
      {showLabel && config.label}
    </Badge>
  );
};
