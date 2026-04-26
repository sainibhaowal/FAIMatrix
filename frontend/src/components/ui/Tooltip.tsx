"use client";

import React, {
  useState,
  useRef,
  useEffect,
  cloneElement,
  isValidElement,
} from "react";
import { createPortal } from "react-dom";

/* =============================================================================
   FAIM UI — Tooltip Component
   
   Hover tooltip with FAIM styling and smart positioning.
============================================================================= */

export interface TooltipProps {
  /** Tooltip content */
  content: React.ReactNode;
  /** Trigger element */
  children: React.ReactElement<{
    onMouseEnter?: React.MouseEventHandler;
    onMouseLeave?: React.MouseEventHandler;
    onFocus?: React.FocusEventHandler;
    onBlur?: React.FocusEventHandler;
  }>;
  /** Position relative to trigger */
  position?: "top" | "bottom" | "left" | "right";
  /** Delay before showing (ms) */
  delay?: number;
  /** Additional class names for tooltip */
  className?: string;
  /** Disable tooltip */
  disabled?: boolean;
}

export const Tooltip: React.FC<TooltipProps> = ({
  content,
  children,
  position = "top",
  delay = 300,
  className = "",
  disabled = false,
}) => {
  const [visible, setVisible] = useState(false);
  const [coords, setCoords] = useState({ x: 0, y: 0 });
  const [mounted, setMounted] = useState(false);
  const triggerRef = useRef<HTMLElement>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setMounted(true);
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  const show = () => {
    if (disabled) return;
    timeoutRef.current = setTimeout(() => {
      if (triggerRef.current) {
        const rect = triggerRef.current.getBoundingClientRect();
        const scrollX = window.scrollX;
        const scrollY = window.scrollY;

        let x = 0;
        let y = 0;

        switch (position) {
          case "top":
            x = rect.left + rect.width / 2 + scrollX;
            y = rect.top + scrollY;
            break;
          case "bottom":
            x = rect.left + rect.width / 2 + scrollX;
            y = rect.bottom + scrollY;
            break;
          case "left":
            x = rect.left + scrollX;
            y = rect.top + rect.height / 2 + scrollY;
            break;
          case "right":
            x = rect.right + scrollX;
            y = rect.top + rect.height / 2 + scrollY;
            break;
        }

        setCoords({ x, y });
        setVisible(true);
      }
    }, delay);
  };

  const hide = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setVisible(false);
  };

  // Clone child with event handlers
  const trigger = isValidElement(children)
    ? cloneElement(children, {
        ref: triggerRef,
        onMouseEnter: (e: React.MouseEvent) => {
          show();
          (
            children.props as { onMouseEnter?: React.MouseEventHandler }
          ).onMouseEnter?.(e);
        },
        onMouseLeave: (e: React.MouseEvent) => {
          hide();
          (
            children.props as { onMouseLeave?: React.MouseEventHandler }
          ).onMouseLeave?.(e);
        },
        onFocus: (e: React.FocusEvent) => {
          show();
          (children.props as { onFocus?: React.FocusEventHandler }).onFocus?.(
            e,
          );
        },
        onBlur: (e: React.FocusEvent) => {
          hide();
          (children.props as { onBlur?: React.FocusEventHandler }).onBlur?.(e);
        },
      } as Partial<typeof children.props>)
    : children;

  const positionStyles: Record<string, React.CSSProperties> = {
    top: {
      left: coords.x,
      top: coords.y,
      transform: "translate(-50%, calc(-100% - 8px))",
    },
    bottom: {
      left: coords.x,
      top: coords.y,
      transform: "translate(-50%, 8px)",
    },
    left: {
      left: coords.x,
      top: coords.y,
      transform: "translate(calc(-100% - 8px), -50%)",
    },
    right: {
      left: coords.x,
      top: coords.y,
      transform: "translate(8px, -50%)",
    },
  };

  return (
    <>
      {trigger}
      {mounted &&
        visible &&
        createPortal(
          <div
            role="tooltip"
            className={[
              "fixed z-[var(--z-tooltip)]",
              "px-3 py-2 rounded-lg",
              "bg-[var(--surface-3)]",
              "border border-[var(--border-default)]",
              "text-xs text-[var(--text-primary)]",
              "shadow-[var(--shadow-lg)]",
              "animate-[fadeIn_0.15s_var(--ease-faim)]",
              "max-w-xs",
              className,
            ].join(" ")}
            style={positionStyles[position]}
          >
            {content}
          </div>,
          document.body,
        )}
    </>
  );
};

/* =============================================================================
   FAIM UI — Tabs Component
   
   Tab navigation with FAIM styling.
============================================================================= */

export interface Tab {
  id: string;
  label: string;
  icon?: React.ReactNode;
  disabled?: boolean;
}

export interface TabsProps {
  /** Array of tab definitions */
  tabs: Tab[];
  /** Currently active tab ID */
  activeTab: string;
  /** Callback when tab changes */
  onChange: (tabId: string) => void;
  /** Size variant */
  size?: "sm" | "md" | "lg";
  /** Full width tabs */
  fullWidth?: boolean;
  /** Additional class names */
  className?: string;
}

const tabSizeConfig = {
  sm: "h-8 px-3 text-xs gap-1.5",
  md: "h-9 px-4 text-sm gap-2",
  lg: "h-10 px-5 text-sm gap-2",
};

export const Tabs: React.FC<TabsProps> = ({
  tabs,
  activeTab,
  onChange,
  size = "md",
  fullWidth = false,
  className = "",
}) => {
  return (
    <div
      role="tablist"
      className={[
        "flex items-center",
        "p-1 rounded-xl",
        "bg-[var(--surface-1)]",
        "border border-[var(--border-subtle)]",
        fullWidth && "w-full",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {tabs.map((tab) => {
        const isActive = tab.id === activeTab;
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            disabled={tab.disabled}
            onClick={() => onChange(tab.id)}
            className={[
              "flex items-center justify-center",
              tabSizeConfig[size],
              "rounded-lg",
              "font-medium",
              "transition-all duration-200",
              fullWidth && "flex-1",
              tab.disabled && "opacity-50 cursor-not-allowed",
              isActive
                ? "bg-[var(--faim-primary-muted)] text-[var(--faim-primary)] shadow-[var(--glow-cyan)]"
                : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--glass-hover)]",
            ]
              .filter(Boolean)
              .join(" ")}
          >
            {tab.icon}
            {tab.label}
          </button>
        );
      })}
    </div>
  );
};
