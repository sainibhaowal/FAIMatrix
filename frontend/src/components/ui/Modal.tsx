"use client";

import React, { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { Button } from "./Button";

/* =============================================================================
   FAIM UI — Modal Component
   
   Accessible modal dialog with focus trap, backdrop, and animations.
============================================================================= */

export interface ModalProps {
  /** Whether the modal is open */
  open: boolean;
  /** Callback when modal should close */
  onClose: () => void;
  /** Modal title */
  title?: React.ReactNode;
  /** Modal description */
  description?: string;
  /** Modal content */
  children: React.ReactNode;
  /** Footer content (typically buttons) */
  footer?: React.ReactNode;
  /** Size variant */
  size?: "sm" | "md" | "lg" | "xl" | "full";
  /** Close on backdrop click */
  closeOnBackdrop?: boolean;
  /** Close on Escape key */
  closeOnEscape?: boolean;
  /** Show close button */
  showCloseButton?: boolean;
  /** Additional class names */
  className?: string;
}

const sizeConfig = {
  sm: "max-w-sm",
  md: "max-w-md",
  lg: "max-w-lg",
  xl: "max-w-xl",
  full: "max-w-[calc(100vw-2rem)] max-h-[calc(100vh-2rem)]",
};

export const Modal: React.FC<ModalProps> = ({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  size = "md",
  closeOnBackdrop = true,
  closeOnEscape = true,
  showCloseButton = true,
  className = "",
}) => {
  const [mounted, setMounted] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);
  const previousActiveElement = useRef<HTMLElement | null>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Handle escape key
  useEffect(() => {
    if (!open || !closeOnEscape) return;

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [open, closeOnEscape, onClose]);

  // Focus management
  useEffect(() => {
    if (open) {
      previousActiveElement.current = document.activeElement as HTMLElement;
      dialogRef.current?.focus();
    } else {
      previousActiveElement.current?.focus();
    }
  }, [open]);

  // Lock body scroll
  useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  if (!mounted) return null;

  return createPortal(
    <div
      className={[
        "fixed inset-0 z-[var(--z-modal)]",
        "flex items-center justify-center p-4",
        open ? "pointer-events-auto" : "pointer-events-none",
      ].join(" ")}
      aria-hidden={!open}
    >
      {/* Backdrop */}
      <div
        className={[
          "absolute inset-0",
          "bg-black/60 backdrop-blur-sm",
          "transition-opacity duration-300",
          open ? "opacity-100" : "opacity-0",
        ].join(" ")}
        onClick={closeOnBackdrop ? onClose : undefined}
        aria-hidden="true"
      />

      {/* Dialog */}
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? "modal-title" : undefined}
        aria-describedby={description ? "modal-description" : undefined}
        tabIndex={-1}
        className={[
          "relative w-full",
          sizeConfig[size],
          "rounded-2xl",
          "bg-[var(--surface-1)]",
          "border border-[var(--border-default)]",
          "shadow-[var(--shadow-xl)]",
          "transition-all duration-300",
          open
            ? "opacity-100 scale-100 translate-y-0"
            : "opacity-0 scale-95 translate-y-4",
          className,
        ].join(" ")}
      >
        {/* Glow effect */}
        <div className="absolute inset-0 rounded-2xl bg-gradient-to-b from-[var(--faim-primary)]/5 to-transparent pointer-events-none" />

        {/* Header */}
        {(title || showCloseButton) && (
          <div className="relative flex items-start justify-between gap-4 p-4 border-b border-[var(--border-subtle)]">
            <div>
              {title && (
                <h2
                  id="modal-title"
                  className="text-base font-semibold text-[var(--text-primary)]"
                >
                  {title}
                </h2>
              )}
              {description && (
                <p
                  id="modal-description"
                  className="mt-1 text-sm text-[var(--text-secondary)]"
                >
                  {description}
                </p>
              )}
            </div>
            {showCloseButton && (
              <button
                type="button"
                onClick={onClose}
                className={[
                  "flex-shrink-0 p-2 rounded-lg",
                  "text-[var(--text-tertiary)]",
                  "hover:text-[var(--text-primary)] hover:bg-[var(--glass-hover)]",
                  "transition-colors",
                ].join(" ")}
                aria-label="Close"
              >
                <X size={18} />
              </button>
            )}
          </div>
        )}

        {/* Content */}
        <div className="relative p-4 max-h-[60vh] overflow-y-auto">{children}</div>

        {/* Footer */}
        {footer && (
          <div className="relative flex items-center justify-end gap-2 p-4 border-t border-[var(--border-subtle)]">
            {footer}
          </div>
        )}
      </div>
    </div>,
    document.body
  );
};

/* =============================================================================
   Confirm Dialog (convenience wrapper)
============================================================================= */

export interface ConfirmDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "primary" | "danger";
  loading?: boolean;
}

export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  open,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  variant = "primary",
  loading = false,
}) => {
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={title}
      size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={loading}>
            {cancelLabel}
          </Button>
          <Button
            variant={variant === "danger" ? "danger" : "primary"}
            onClick={onConfirm}
            loading={loading}
          >
            {confirmLabel}
          </Button>
        </>
      }
    >
      <p className="text-sm text-[var(--text-secondary)]">{message}</p>
    </Modal>
  );
};
