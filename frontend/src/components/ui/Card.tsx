"use client";

import React from "react";

/* =============================================================================
   FAIM UI — Card Component
   
   A premium card component with the signature FAIM glow effect.
   Supports cursor-follow spotlight and multiple elevation levels.
============================================================================= */

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Enable cursor-follow glow effect */
  glow?: boolean;
  /** Intensity of the glow (0-1) */
  glowIntensity?: number;
  /** Card elevation level */
  elevation?: 0 | 1 | 2 | 3;
  /** Remove padding */
  noPadding?: boolean;
  /** Make card interactive (adds hover effects) */
  interactive?: boolean;
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  (
    {
      className = "",
      glow = true,
      glowIntensity = 0.12,
      elevation = 1,
      noPadding = false,
      interactive = false,
      children,
      ...props
    },
    ref,
  ) => {
    const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
      if (!glow) return;
      const el = e.currentTarget;
      const rect = el.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 100;
      const y = ((e.clientY - rect.top) / rect.height) * 100;
      el.style.setProperty("--gx", `${x.toFixed(2)}%`);
      el.style.setProperty("--gy", `${y.toFixed(2)}%`);
    };

    const surfaceClass = {
      0: "bg-transparent border-transparent shadow-none",
      1: "os-card", // Default card style
      2: "os-surface", // Deeper surface
      3: "bg-[var(--os-surface-3)] border-[rgba(255,255,255,0.1)]",
    }[elevation];

    return (
      <div
        ref={ref}
        onMouseMove={handleMouseMove}
        className={[
          /* Base styles */
          "relative overflow-hidden transition-all duration-300",
          !surfaceClass.includes("os-") && "rounded-2xl border border-white/10", // Fallback for custom elevations
          surfaceClass,

          /* Glow effect (when enabled) */
          glow &&
            [
              "before:absolute before:inset-0 before:pointer-events-none before:rounded-[inherit]",
              "before:bg-gradient-to-b before:from-cyan-500/5 before:to-transparent",
              "after:absolute after:inset-0 after:pointer-events-none after:rounded-[inherit]",
              `after:bg-[radial-gradient(400px_circle_at_var(--gx,50%)_var(--gy,50%),rgba(34,211,238,${glowIntensity}),transparent_60%)]`,
              "after:opacity-0 hover:after:opacity-100 after:transition-opacity after:duration-300",
            ].join(" "),

          /* Interactive styles */
          interactive &&
            [
              "cursor-pointer",
              "hover:border-cyan-500/30",
              "hover:-translate-y-1",
              "hover:shadow-[0_0_30px_rgba(34,211,238,0.1)]",
              "active:scale-[0.99]",
            ].join(" "),

          /* Padding */
          !noPadding && "p-5",

          className,
        ]
          .filter(Boolean)
          .join(" ")}
        style={
          {
            "--gx": "50%",
            "--gy": "50%",
            ...props.style,
          } as React.CSSProperties
        }
        {...props}
      >
        {/* Inner glow border */}
        <div className="pointer-events-none absolute inset-0 rounded-[inherit] border border-white/5" />

        {/* Content */}
        <div className="relative">{children}</div>
      </div>
    );
  },
);
Card.displayName = "Card";

/* =============================================================================
   Card Header
============================================================================= */

export interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  description?: string;
  action?: React.ReactNode;
}

export const CardHeader: React.FC<CardHeaderProps> = ({
  title,
  description,
  action,
  className = "",
  children,
  ...props
}) => {
  return (
    <div
      className={[
        "flex items-start justify-between gap-4",
        "pb-4 border-b border-[var(--border-subtle)]",
        className,
      ].join(" ")}
      {...props}
    >
      <div className="flex-1 min-w-0">
        {title && (
          <h3 className="text-sm font-bold text-white uppercase tracking-tight">
            {title}
          </h3>
        )}
        {description && (
          <p className="mt-1 text-xs text-[var(--text-secondary)]">
            {description}
          </p>
        )}
        {children}
      </div>
      {action && <div className="flex-shrink-0">{action}</div>}
    </div>
  );
};

/* =============================================================================
   Card Content
============================================================================= */

export const CardContent: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  className = "",
  children,
  ...props
}) => {
  return (
    <div className={["py-4", className].join(" ")} {...props}>
      {children}
    </div>
  );
};

/* =============================================================================
   Card Footer
============================================================================= */

export const CardFooter: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  className = "",
  children,
  ...props
}) => {
  return (
    <div
      className={[
        "flex items-center justify-end gap-2",
        "pt-4 border-t border-[var(--border-subtle)]",
        className,
      ].join(" ")}
      {...props}
    >
      {children}
    </div>
  );
};
