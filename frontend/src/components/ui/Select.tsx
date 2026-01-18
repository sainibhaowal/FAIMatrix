"use client";

import React, { useState, useRef, useEffect } from "react";
import { createPortal } from "react-dom";
import { ChevronDown, Check } from "lucide-react";

/* =============================================================================
   FAIM UI — Select Component (NeonDropdown)
   
   A styled dropdown/select component with the signature FAIM neon glow effect.
============================================================================= */

export interface SelectOption {
  value: string;
  label: string;
  icon?: React.ReactNode;
  disabled?: boolean;
}

export interface SelectProps {
  /** Array of options */
  options: SelectOption[];
  /** Currently selected value */
  value?: string;
  /** Callback when selection changes */
  onChange?: (value: string) => void;
  /** Placeholder text */
  placeholder?: string;
  /** Size variant */
  size?: "sm" | "md" | "lg";
  /** Full width */
  fullWidth?: boolean;
  /** Disabled state */
  disabled?: boolean;
  /** Error state */
  error?: boolean;
  /** Label */
  label?: string;
  /** Helper text */
  helperText?: string;
  /** Error message */
  errorMessage?: string;
  /** Additional class names */
  className?: string;
}

const sizeConfig = {
  sm: {
    trigger: "h-8 px-3 text-xs gap-1.5",
    option: "px-3 py-1.5 text-xs",
    icon: 14,
  },
  md: {
    trigger: "h-9 px-3 text-sm gap-2",
    option: "px-3 py-2 text-sm",
    icon: 16,
  },
  lg: {
    trigger: "h-11 px-4 text-sm gap-2",
    option: "px-4 py-2.5 text-sm",
    icon: 18,
  },
};

export const Select: React.FC<SelectProps> = ({
  options,
  value,
  onChange,
  placeholder = "Select an option",
  size = "md",
  fullWidth = false,
  disabled = false,
  error = false,
  label,
  helperText,
  errorMessage,
  className = "",
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [dropdownStyle, setDropdownStyle] = useState<React.CSSProperties>({});

  const config = sizeConfig[size];
  const selectedOption = options.find((opt) => opt.value === value);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Calculate dropdown position
  useEffect(() => {
    if (isOpen && triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      const spaceBelow = window.innerHeight - rect.bottom;
      const dropdownHeight = Math.min(options.length * 40, 240);

      setDropdownStyle({
        position: "fixed",
        left: rect.left,
        width: rect.width,
        ...(spaceBelow >= dropdownHeight + 8
          ? { top: rect.bottom + 4 }
          : { bottom: window.innerHeight - rect.top + 4 }),
      });
    }
  }, [isOpen, options.length]);

  // Close on outside click
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (
        triggerRef.current &&
        !triggerRef.current.contains(e.target as Node) &&
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setIsOpen(false);
        triggerRef.current?.focus();
      }
    };

    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [isOpen]);

  const handleSelect = (optValue: string) => {
    onChange?.(optValue);
    setIsOpen(false);
    triggerRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      setIsOpen(!isOpen);
    } else if (e.key === "ArrowDown" && !isOpen) {
      e.preventDefault();
      setIsOpen(true);
    }
  };

  return (
    <div className={[fullWidth ? "w-full" : "w-fit", className].join(" ")}>
      {/* Label */}
      {label && (
        <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1.5">
          {label}
        </label>
      )}

      {/* Trigger button */}
      <button
        ref={triggerRef}
        type="button"
        disabled={disabled}
        onClick={() => setIsOpen(!isOpen)}
        onKeyDown={handleKeyDown}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        className={[
          "relative flex items-center justify-between",
          "w-full rounded-lg",
          "bg-[var(--surface-1)]",
          "border transition-all duration-200",
          "focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-1 focus-visible:ring-offset-[var(--surface-0)]",
          config.trigger,
          disabled && "opacity-50 cursor-not-allowed",
          error
            ? "border-[var(--faim-error)]/50 focus-visible:ring-[var(--faim-error)]/20"
            : isOpen
              ? "border-[var(--faim-primary)] ring-2 ring-[var(--faim-primary)]/20 shadow-[var(--glow-cyan)]"
              : "border-[var(--border-default)] hover:border-[var(--border-primary)]",
        ]
          .filter(Boolean)
          .join(" ")}
      >
        <span
          className={[
            "truncate",
            selectedOption
              ? "text-[var(--text-primary)]"
              : "text-[var(--text-muted)]",
          ].join(" ")}
        >
          {selectedOption ? (
            <span className="flex items-center gap-2">
              {selectedOption.icon}
              {selectedOption.label}
            </span>
          ) : (
            placeholder
          )}
        </span>
        <ChevronDown
          size={config.icon}
          className={[
            "flex-shrink-0 text-[var(--text-tertiary)]",
            "transition-transform duration-200",
            isOpen && "rotate-180",
          ].join(" ")}
        />

        {/* Glow effect when open */}
        {isOpen && (
          <div className="absolute inset-0 rounded-lg bg-gradient-radial from-[var(--faim-primary)]/10 to-transparent pointer-events-none" />
        )}
      </button>

      {/* Dropdown */}
      {mounted &&
        isOpen &&
        createPortal(
          <div
            ref={dropdownRef}
            role="listbox"
            style={dropdownStyle}
            className={[
              "z-[var(--z-dropdown)]",
              "py-1 rounded-xl",
              "bg-[var(--surface-2)]",
              "border border-[var(--border-default)]",
              "shadow-[var(--shadow-xl)]",
              "overflow-hidden",
              "animate-[fadeIn_0.15s_var(--ease-faim)]",
            ].join(" ")}
          >
            {/* Inner glow */}
            <div className="absolute inset-0 rounded-xl bg-gradient-to-b from-[var(--faim-primary)]/5 to-transparent pointer-events-none" />

            {/* Options */}
            <div className="relative max-h-60 overflow-y-auto">
              {options.map((option) => {
                const isSelected = option.value === value;
                return (
                  <button
                    key={option.value}
                    type="button"
                    role="option"
                    aria-selected={isSelected}
                    disabled={option.disabled}
                    onClick={() => handleSelect(option.value)}
                    className={[
                      "w-full flex items-center justify-between",
                      config.option,
                      "transition-colors duration-100",
                      option.disabled && "opacity-40 cursor-not-allowed",
                      isSelected
                        ? "bg-[var(--faim-primary-muted)] text-[var(--faim-primary)]"
                        : "text-[var(--text-primary)] hover:bg-[var(--glass-hover)]",
                    ]
                      .filter(Boolean)
                      .join(" ")}
                  >
                    <span className="flex items-center gap-2 truncate">
                      {option.icon}
                      {option.label}
                    </span>
                    {isSelected && (
                      <Check
                        size={config.icon}
                        className="flex-shrink-0 text-[var(--faim-primary)]"
                      />
                    )}
                  </button>
                );
              })}
            </div>
          </div>,
          document.body
        )}

      {/* Helper text / Error */}
      {(errorMessage || helperText) && (
        <p
          className={[
            "mt-1.5 text-xs",
            errorMessage
              ? "text-[var(--faim-error)]"
              : "text-[var(--text-tertiary)]",
          ].join(" ")}
        >
          {errorMessage || helperText}
        </p>
      )}
    </div>
  );
};

/* =============================================================================
   Multi-Select Variant
============================================================================= */

export interface MultiSelectProps extends Omit<SelectProps, "value" | "onChange"> {
  /** Currently selected values */
  value?: string[];
  /** Callback when selection changes */
  onChange?: (values: string[]) => void;
  /** Maximum selections allowed */
  maxSelections?: number;
}

export const MultiSelect: React.FC<MultiSelectProps> = ({
  options,
  value = [],
  onChange,
  placeholder = "Select options",
  size = "md",
  fullWidth = false,
  disabled = false,
  maxSelections,
  className = "",
  ...props
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [dropdownStyle, setDropdownStyle] = useState<React.CSSProperties>({});

  const config = sizeConfig[size];
  const selectedOptions = options.filter((opt) => value.includes(opt.value));

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (isOpen && triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      setDropdownStyle({
        position: "fixed",
        left: rect.left,
        top: rect.bottom + 4,
        width: rect.width,
      });
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (
        triggerRef.current &&
        !triggerRef.current.contains(e.target as Node) &&
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  const handleToggle = (optValue: string) => {
    const newValues = value.includes(optValue)
      ? value.filter((v) => v !== optValue)
      : maxSelections && value.length >= maxSelections
        ? value
        : [...value, optValue];
    onChange?.(newValues);
  };

  return (
    <div className={[fullWidth ? "w-full" : "w-fit", className].join(" ")}>
      {props.label && (
        <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1.5">
          {props.label}
        </label>
      )}

      <button
        ref={triggerRef}
        type="button"
        disabled={disabled}
        onClick={() => setIsOpen(!isOpen)}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        className={[
          "relative flex items-center justify-between",
          "w-full rounded-lg",
          "bg-[var(--surface-1)]",
          "border transition-all duration-200",
          config.trigger,
          disabled && "opacity-50 cursor-not-allowed",
          isOpen
            ? "border-[var(--faim-primary)] ring-2 ring-[var(--faim-primary)]/20 shadow-[var(--glow-cyan)]"
            : "border-[var(--border-default)] hover:border-[var(--border-primary)]",
        ]
          .filter(Boolean)
          .join(" ")}
      >
        <span className="truncate text-left">
          {selectedOptions.length > 0 ? (
            <span className="text-[var(--text-primary)]">
              {selectedOptions.length} selected
            </span>
          ) : (
            <span className="text-[var(--text-muted)]">{placeholder}</span>
          )}
        </span>
        <ChevronDown
          size={config.icon}
          className={[
            "flex-shrink-0 text-[var(--text-tertiary)]",
            "transition-transform duration-200",
            isOpen && "rotate-180",
          ].join(" ")}
        />
      </button>

      {mounted &&
        isOpen &&
        createPortal(
          <div
            ref={dropdownRef}
            role="listbox"
            aria-multiselectable="true"
            style={dropdownStyle}
            className={[
              "z-[var(--z-dropdown)]",
              "py-1 rounded-xl",
              "bg-[var(--surface-2)]",
              "border border-[var(--border-default)]",
              "shadow-[var(--shadow-xl)]",
              "overflow-hidden max-h-60 overflow-y-auto",
              "animate-[fadeIn_0.15s_var(--ease-faim)]",
            ].join(" ")}
          >
            {options.map((option) => {
              const isSelected = value.includes(option.value);
              return (
                <button
                  key={option.value}
                  type="button"
                  role="option"
                  aria-selected={isSelected}
                  disabled={option.disabled}
                  onClick={() => handleToggle(option.value)}
                  className={[
                    "w-full flex items-center justify-between",
                    config.option,
                    "transition-colors duration-100",
                    option.disabled && "opacity-40 cursor-not-allowed",
                    isSelected
                      ? "bg-[var(--faim-primary-muted)] text-[var(--faim-primary)]"
                      : "text-[var(--text-primary)] hover:bg-[var(--glass-hover)]",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                >
                  <span className="flex items-center gap-2 truncate">
                    {option.icon}
                    {option.label}
                  </span>
                  {isSelected && <Check size={config.icon} />}
                </button>
              );
            })}
          </div>,
          document.body
        )}
    </div>
  );
};
