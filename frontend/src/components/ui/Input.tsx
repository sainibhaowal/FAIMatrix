"use client";

import React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { Search, X } from "lucide-react";

/* =============================================================================
   FAIM UI — Input Component
   
   Text input with FAIM styling, validation states, and icons.
============================================================================= */

const inputVariants = cva(
  [
    "w-full",
    "bg-[var(--surface-1)]",
    "border rounded-lg",
    "text-[var(--text-primary)]",
    "placeholder:text-[var(--text-muted)]",
    "transition-all duration-200",
    "focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-offset-[var(--surface-0)]",
    "disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-[var(--surface-0)]",
  ].join(" "),
  {
    variants: {
      size: {
        sm: "h-8 px-3 text-xs",
        md: "h-9 px-3 text-sm",
        lg: "h-11 px-4 text-base",
      },
      state: {
        default: [
          "border-[var(--border-default)]",
          "hover:border-[var(--border-primary)]",
          "focus:border-[var(--faim-primary)] focus:ring-[var(--faim-primary)]/20",
        ].join(" "),
        error: [
          "border-[var(--faim-error)]/50",
          "focus:border-[var(--faim-error)] focus:ring-[var(--faim-error)]/20",
        ].join(" "),
        success: [
          "border-[var(--faim-success)]/50",
          "focus:border-[var(--faim-success)] focus:ring-[var(--faim-success)]/20",
        ].join(" "),
      },
    },
    defaultVariants: {
      size: "md",
      state: "default",
    },
  },
);

export interface InputProps
  extends
    Omit<React.InputHTMLAttributes<HTMLInputElement>, "size">,
    VariantProps<typeof inputVariants> {
  /** Left icon */
  leftIcon?: React.ReactNode;
  /** Right icon */
  rightIcon?: React.ReactNode;
  /** Error message */
  error?: string;
  /** Helper text */
  helperText?: string;
  /** Show clear button */
  clearable?: boolean;
  /** Clear callback */
  onClear?: () => void;
  /** Label */
  label?: string;
  /** Required indicator */
  required?: boolean;
  /** Container class */
  containerClassName?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    {
      className = "",
      containerClassName = "",
      size,
      state,
      leftIcon,
      rightIcon,
      error,
      helperText,
      clearable = false,
      onClear,
      label,
      required = false,
      value,
      ...props
    },
    ref,
  ) => {
    const hasValue = value !== undefined && value !== "";
    const showClear = clearable && hasValue && onClear;
    const effectiveState = error ? "error" : state;

    return (
      <div className={["w-full", containerClassName].join(" ")}>
        {/* Label */}
        {label && (
          <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1.5">
            {label}
            {required && (
              <span className="text-[var(--faim-error)] ml-0.5">*</span>
            )}
          </label>
        )}

        {/* Input wrapper */}
        <div className="relative">
          {/* Left icon */}
          {leftIcon && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-tertiary)]">
              {leftIcon}
            </div>
          )}

          {/* Input */}
          <input
            ref={ref}
            value={value}
            className={[
              inputVariants({ size, state: effectiveState }),
              leftIcon && "pl-10",
              (rightIcon || showClear) && "pr-10",
              className,
            ].join(" ")}
            {...props}
          />

          {/* Right icon or clear button */}
          {(rightIcon || showClear) && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2">
              {showClear ? (
                <button
                  type="button"
                  onClick={onClear}
                  className="p-1 text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition-colors"
                >
                  <X size={14} />
                </button>
              ) : (
                <span className="text-[var(--text-tertiary)]">{rightIcon}</span>
              )}
            </div>
          )}
        </div>

        {/* Helper text / Error */}
        {(error || helperText) && (
          <p
            className={[
              "mt-1.5 text-xs",
              error
                ? "text-[var(--faim-error)]"
                : "text-[var(--text-tertiary)]",
            ].join(" ")}
          >
            {error || helperText}
          </p>
        )}
      </div>
    );
  },
);
Input.displayName = "Input";

/* =============================================================================
   Search Input (convenience wrapper)
============================================================================= */

export interface SearchInputProps extends Omit<
  InputProps,
  "leftIcon" | "type"
> {
  onSearch?: (value: string) => void;
}

export const SearchInput = React.forwardRef<HTMLInputElement, SearchInputProps>(
  ({ onSearch, onKeyDown, ...props }, ref) => {
    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter" && onSearch) {
        onSearch((e.target as HTMLInputElement).value);
      }
      onKeyDown?.(e);
    };

    return (
      <Input
        ref={ref}
        type="search"
        leftIcon={<Search size={16} />}
        placeholder="Search..."
        onKeyDown={handleKeyDown}
        {...props}
      />
    );
  },
);
SearchInput.displayName = "SearchInput";

/* =============================================================================
   Textarea
============================================================================= */

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  /** Error message */
  error?: string;
  /** Helper text */
  helperText?: string;
  /** Label */
  label?: string;
  /** Required indicator */
  required?: boolean;
  /** Container class */
  containerClassName?: string;
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  (
    {
      className = "",
      containerClassName = "",
      error,
      helperText,
      label,
      required = false,
      ...props
    },
    ref,
  ) => {
    return (
      <div className={["w-full", containerClassName].join(" ")}>
        {/* Label */}
        {label && (
          <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1.5">
            {label}
            {required && (
              <span className="text-[var(--faim-error)] ml-0.5">*</span>
            )}
          </label>
        )}

        {/* Textarea */}
        <textarea
          ref={ref}
          className={[
            "w-full min-h-[100px] p-3",
            "bg-[var(--surface-1)]",
            "border rounded-lg",
            "text-sm text-[var(--text-primary)]",
            "placeholder:text-[var(--text-muted)]",
            "transition-all duration-200",
            "focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-offset-[var(--surface-0)]",
            "disabled:cursor-not-allowed disabled:opacity-50",
            "resize-y",
            error
              ? "border-[var(--faim-error)]/50 focus:border-[var(--faim-error)] focus:ring-[var(--faim-error)]/20"
              : "border-[var(--border-default)] hover:border-[var(--border-primary)] focus:border-[var(--faim-primary)] focus:ring-[var(--faim-primary)]/20",
            className,
          ].join(" ")}
          {...props}
        />

        {/* Helper text / Error */}
        {(error || helperText) && (
          <p
            className={[
              "mt-1.5 text-xs",
              error
                ? "text-[var(--faim-error)]"
                : "text-[var(--text-tertiary)]",
            ].join(" ")}
          >
            {error || helperText}
          </p>
        )}
      </div>
    );
  },
);
Textarea.displayName = "Textarea";
