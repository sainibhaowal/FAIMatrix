"use client";

import React from "react";
import { cva, type VariantProps } from "class-variance-authority";

/* =============================================================================
   FAIM UI — Button Component
   
   A versatile button component with multiple variants and sizes.
   Uses CSS custom properties from design-tokens for consistent theming.
============================================================================= */

const buttonVariants = cva(
  /* Base styles */
  [
    "inline-flex items-center justify-center gap-2",
    "font-medium transition-all",
    "focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--surface-0)]",
    "disabled:cursor-not-allowed disabled:opacity-50",
    "active:scale-[0.98]",
  ].join(" "),
  {
    variants: {
      variant: {
        primary: [
          "bg-[var(--faim-primary)] text-slate-900",
          "hover:bg-[var(--faim-primary-hover)]",
          "focus-visible:ring-[var(--faim-primary)]",
          "shadow-[var(--glow-cyan)]",
        ].join(" "),
        secondary: [
          "bg-[var(--faim-secondary-muted)] text-[var(--faim-secondary)]",
          "border border-[var(--faim-secondary)]/30",
          "hover:bg-[var(--faim-secondary)]/20 hover:border-[var(--faim-secondary)]/50",
          "focus-visible:ring-[var(--faim-secondary)]",
        ].join(" "),
        ghost: [
          "bg-transparent text-[var(--text-secondary)]",
          "hover:bg-[var(--glass-hover)] hover:text-[var(--text-primary)]",
          "focus-visible:ring-[var(--faim-primary)]",
        ].join(" "),
        outline: [
          "bg-transparent text-[var(--text-primary)]",
          "border border-[var(--border-default)]",
          "hover:bg-[var(--glass-hover)] hover:border-[var(--border-primary)]",
          "focus-visible:ring-[var(--faim-primary)]",
        ].join(" "),
        danger: [
          "bg-[var(--faim-error-muted)] text-[var(--faim-error-text)]",
          "border border-[var(--faim-error)]/30",
          "hover:bg-[var(--faim-error)]/20 hover:border-[var(--faim-error)]/50",
          "focus-visible:ring-[var(--faim-error)]",
        ].join(" "),
        success: [
          "bg-[var(--faim-success-muted)] text-[var(--faim-success-text)]",
          "border border-[var(--faim-success)]/30",
          "hover:bg-[var(--faim-success)]/20 hover:border-[var(--faim-success)]/50",
          "focus-visible:ring-[var(--faim-success)]",
        ].join(" "),
      },
      size: {
        xs: "h-7 px-2 text-[11px] rounded-md gap-1",
        sm: "h-8 px-3 text-xs rounded-lg gap-1.5",
        md: "h-9 px-4 text-sm rounded-lg gap-2",
        lg: "h-11 px-6 text-base rounded-xl gap-2",
        xl: "h-12 px-8 text-lg rounded-xl gap-3",
        icon: "h-9 w-9 rounded-lg p-0",
        "icon-sm": "h-8 w-8 rounded-md p-0",
        "icon-lg": "h-11 w-11 rounded-xl p-0",
      },
      fullWidth: {
        true: "w-full",
        false: "",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
      fullWidth: false,
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  loading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className = "",
      variant,
      size,
      fullWidth,
      loading = false,
      leftIcon,
      rightIcon,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    return (
      <button
        ref={ref}
        className={buttonVariants({ variant, size, fullWidth }) + " " + className}
        disabled={disabled || loading}
        {...props}
      >
        {loading ? (
          <Spinner size={size === "xs" || size === "sm" ? 12 : 16} />
        ) : (
          leftIcon
        )}
        {children}
        {!loading && rightIcon}
      </button>
    );
  }
);
Button.displayName = "Button";

/* Mini spinner for loading state */
function Spinner({ size = 16 }: { size?: number }) {
  return (
    <svg
      className="animate-spin"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}

export { buttonVariants };
