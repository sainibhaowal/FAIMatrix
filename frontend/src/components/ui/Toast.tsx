"use client";

import React, { createContext, useContext, useState, useCallback } from "react";
import { createPortal } from "react-dom";
import { X, CheckCircle, AlertCircle, Info, AlertTriangle } from "lucide-react";

/* =============================================================================
   FAIM UI — Toast Notification System
   
   A global toast notification system with FAIM styling.
   Usage:
     const { toast } = useToast();
     toast.success("Document uploaded!");
     toast.error("Connection failed");
============================================================================= */

type ToastType = "success" | "error" | "warning" | "info";

interface Toast {
  id: string;
  type: ToastType;
  title: string;
  description?: string;
  duration?: number;
}

interface ToastContextValue {
  toasts: Toast[];
  toast: {
    success: (title: string, description?: string, duration?: number) => void;
    error: (title: string, description?: string, duration?: number) => void;
    warning: (title: string, description?: string, duration?: number) => void;
    info: (title: string, description?: string, duration?: number) => void;
  };
  dismiss: (id: string) => void;
  dismissAll: () => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

/* =============================================================================
   Toast Provider
============================================================================= */

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback(
    (type: ToastType, title: string, description?: string, duration = 5000) => {
      const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;

      setToasts((prev) => [
        ...prev,
        { id, type, title, description, duration },
      ]);

      if (duration > 0) {
        setTimeout(() => {
          setToasts((prev) => prev.filter((t) => t.id !== id));
        }, duration);
      }
    },
    [],
  );

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const dismissAll = useCallback(() => {
    setToasts([]);
  }, []);

  const value: ToastContextValue = {
    toasts,
    toast: {
      success: (title, description, duration) =>
        addToast("success", title, description, duration),
      error: (title, description, duration) =>
        addToast("error", title, description, duration ?? 8000),
      warning: (title, description, duration) =>
        addToast("warning", title, description, duration),
      info: (title, description, duration) =>
        addToast("info", title, description, duration),
    },
    dismiss,
    dismissAll,
  };

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastContainer toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  );
}

/* =============================================================================
   useToast Hook
============================================================================= */

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}

/* =============================================================================
   Toast Container (Portal)
============================================================================= */

function ToastContainer({
  toasts,
  onDismiss,
}: {
  toasts: Toast[];
  onDismiss: (id: string) => void;
}) {
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  return createPortal(
    <div
      className="fixed bottom-4 right-4 z-[var(--z-toast)] flex flex-col gap-2 pointer-events-none"
      aria-live="polite"
      aria-label="Notifications"
    >
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onDismiss={onDismiss} />
      ))}
    </div>,
    document.body,
  );
}

/* =============================================================================
   Toast Item
============================================================================= */

const iconMap = {
  success: CheckCircle,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
};

const styleMap = {
  success: {
    bg: "bg-[var(--faim-success-muted)]",
    border: "border-[var(--faim-success)]/30",
    icon: "text-[var(--faim-success)]",
    glow: "shadow-[0_0_20px_rgba(52,211,153,0.15)]",
  },
  error: {
    bg: "bg-[var(--faim-error-muted)]",
    border: "border-[var(--faim-error)]/30",
    icon: "text-[var(--faim-error)]",
    glow: "shadow-[0_0_20px_rgba(248,113,113,0.15)]",
  },
  warning: {
    bg: "bg-[var(--faim-warning-muted)]",
    border: "border-[var(--faim-warning)]/30",
    icon: "text-[var(--faim-warning)]",
    glow: "shadow-[0_0_20px_rgba(251,191,36,0.15)]",
  },
  info: {
    bg: "bg-[var(--faim-info-muted)]",
    border: "border-[var(--faim-info)]/30",
    icon: "text-[var(--faim-info)]",
    glow: "shadow-[0_0_20px_rgba(96,165,250,0.15)]",
  },
};

function ToastItem({
  toast,
  onDismiss,
}: {
  toast: Toast;
  onDismiss: (id: string) => void;
}) {
  const Icon = iconMap[toast.type];
  const styles = styleMap[toast.type];

  return (
    <div
      className={[
        "pointer-events-auto",
        "w-80 max-w-[calc(100vw-2rem)]",
        "p-4 rounded-xl border",
        styles.bg,
        styles.border,
        styles.glow,
        "backdrop-blur-md",
        "animate-[slideIn_0.3s_var(--ease-faim)]",
      ].join(" ")}
      role="alert"
    >
      <div className="flex gap-3">
        <Icon
          className={["flex-shrink-0 mt-0.5", styles.icon].join(" ")}
          size={18}
        />

        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-[var(--text-primary)]">
            {toast.title}
          </p>
          {toast.description && (
            <p className="mt-1 text-xs text-[var(--text-secondary)]">
              {toast.description}
            </p>
          )}
        </div>

        <button
          type="button"
          onClick={() => onDismiss(toast.id)}
          className={[
            "flex-shrink-0 p-1 rounded-md",
            "text-[var(--text-tertiary)]",
            "hover:text-[var(--text-primary)] hover:bg-[var(--glass-hover)]",
            "transition-colors",
          ].join(" ")}
          aria-label="Dismiss"
        >
          <X size={14} />
        </button>
      </div>
    </div>
  );
}

/* =============================================================================
   Animation Keyframes (add to globals.css if not using Tailwind)
============================================================================= */
// @keyframes slideIn {
//   from {
//     opacity: 0;
//     transform: translateX(100%);
//   }
//   to {
//     opacity: 1;
//     transform: translateX(0);
//   }
// }
