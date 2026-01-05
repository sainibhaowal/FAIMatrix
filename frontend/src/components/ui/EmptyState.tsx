"use client";

import React from "react";
import { FileText, Inbox, Search, Upload, AlertCircle } from "lucide-react";
import { Button } from "./Button";

/* =============================================================================
   FAIM UI — EmptyState Component
   
   A consistent empty state component for when there's no data to display.
   Provides helpful guidance and optional action buttons.
============================================================================= */

export interface EmptyStateProps {
  /** Icon to display (or preset name) */
  icon?: React.ReactNode | "documents" | "search" | "upload" | "inbox" | "error";
  /** Title text */
  title: string;
  /** Description text */
  description?: string;
  /** Primary action */
  action?: {
    label: string;
    onClick: () => void;
    variant?: "primary" | "secondary" | "outline";
  };
  /** Secondary action */
  secondaryAction?: {
    label: string;
    onClick: () => void;
  };
  /** Size variant */
  size?: "sm" | "md" | "lg";
  /** Additional class names */
  className?: string;
}

const presetIcons = {
  documents: FileText,
  search: Search,
  upload: Upload,
  inbox: Inbox,
  error: AlertCircle,
};

const sizeConfig = {
  sm: {
    icon: 32,
    iconPadding: "p-3",
    title: "text-sm",
    description: "text-xs",
    gap: "gap-3",
  },
  md: {
    icon: 40,
    iconPadding: "p-4",
    title: "text-base",
    description: "text-sm",
    gap: "gap-4",
  },
  lg: {
    icon: 48,
    iconPadding: "p-5",
    title: "text-lg",
    description: "text-sm",
    gap: "gap-5",
  },
};

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon = "inbox",
  title,
  description,
  action,
  secondaryAction,
  size = "md",
  className = "",
}) => {
  const config = sizeConfig[size];
  
  // Resolve icon
  let IconNode: React.ReactNode;
  if (typeof icon === "string" && icon in presetIcons) {
    const IconComponent = presetIcons[icon as keyof typeof presetIcons];
    IconNode = <IconComponent size={config.icon} />;
  } else {
    IconNode = icon;
  }

  return (
    <div
      className={[
        "flex flex-col items-center justify-center text-center",
        "py-12 px-6",
        config.gap,
        className,
      ].join(" ")}
    >
      {/* Icon container with glow */}
      <div
        className={[
          "rounded-2xl",
          config.iconPadding,
          "bg-[var(--faim-primary-muted)]",
          "text-[var(--faim-primary)]",
          "shadow-[var(--glow-cyan)]",
        ].join(" ")}
      >
        {IconNode}
      </div>

      {/* Text content */}
      <div className="max-w-sm">
        <h3
          className={[
            "font-semibold text-[var(--text-primary)]",
            config.title,
          ].join(" ")}
        >
          {title}
        </h3>
        {description && (
          <p
            className={[
              "mt-2 text-[var(--text-secondary)]",
              config.description,
            ].join(" ")}
          >
            {description}
          </p>
        )}
      </div>

      {/* Actions */}
      {(action || secondaryAction) && (
        <div className="flex items-center gap-3 mt-2">
          {action && (
            <Button
              variant={action.variant || "primary"}
              size={size === "lg" ? "md" : "sm"}
              onClick={action.onClick}
            >
              {action.label}
            </Button>
          )}
          {secondaryAction && (
            <Button
              variant="ghost"
              size={size === "lg" ? "md" : "sm"}
              onClick={secondaryAction.onClick}
            >
              {secondaryAction.label}
            </Button>
          )}
        </div>
      )}
    </div>
  );
};

/* =============================================================================
   FAIM UI — ErrorState Component
   
   A variant of EmptyState specifically for error scenarios.
============================================================================= */

export interface ErrorStateProps {
  /** Error title */
  title?: string;
  /** Error message/description */
  message?: string;
  /** Retry action */
  onRetry?: () => void;
  /** Go back action */
  onGoBack?: () => void;
  /** Size variant */
  size?: "sm" | "md" | "lg";
  /** Additional class names */
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = "Something went wrong",
  message = "An unexpected error occurred. Please try again.",
  onRetry,
  onGoBack,
  size = "md",
  className = "",
}) => {
  const config = sizeConfig[size];

  return (
    <div
      className={[
        "flex flex-col items-center justify-center text-center",
        "py-12 px-6",
        config.gap,
        className,
      ].join(" ")}
    >
      {/* Error icon */}
      <div
        className={[
          "rounded-2xl",
          config.iconPadding,
          "bg-[var(--faim-error-muted)]",
          "text-[var(--faim-error)]",
          "shadow-[var(--glow-error)]",
        ].join(" ")}
      >
        <AlertCircle size={config.icon} />
      </div>

      {/* Text content */}
      <div className="max-w-sm">
        <h3
          className={[
            "font-semibold text-[var(--text-primary)]",
            config.title,
          ].join(" ")}
        >
          {title}
        </h3>
        <p
          className={[
            "mt-2 text-[var(--text-secondary)]",
            config.description,
          ].join(" ")}
        >
          {message}
        </p>
      </div>

      {/* Actions */}
      {(onRetry || onGoBack) && (
        <div className="flex items-center gap-3 mt-2">
          {onRetry && (
            <Button
              variant="primary"
              size={size === "lg" ? "md" : "sm"}
              onClick={onRetry}
            >
              Try Again
            </Button>
          )}
          {onGoBack && (
            <Button
              variant="ghost"
              size={size === "lg" ? "md" : "sm"}
              onClick={onGoBack}
            >
              Go Back
            </Button>
          )}
        </div>
      )}
    </div>
  );
};
