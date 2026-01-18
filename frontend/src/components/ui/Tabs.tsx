"use client";

/**
 * Tabs Component
 * 
 * Animated tabs with underline indicator.
 * shadcn/ui style with FAIM glass theme.
 */

import { createContext, useContext, useState, ReactNode } from "react";
import { motion } from "framer-motion";

// Context
interface TabsContextValue {
  value: string;
  onValueChange: (value: string) => void;
}

const TabsContext = createContext<TabsContextValue | null>(null);

function useTabsContext() {
  const ctx = useContext(TabsContext);
  if (!ctx) throw new Error("Tabs components must be used within <Tabs />");
  return ctx;
}

// Root
export interface TabsProps {
  value?: string;
  defaultValue?: string;
  onValueChange?: (value: string) => void;
  children: ReactNode;
  className?: string;
}

export function Tabs({ value, defaultValue, onValueChange, children, className = "" }: TabsProps) {
  const [internalValue, setInternalValue] = useState(defaultValue || "");
  const currentValue = value ?? internalValue;
  
  const handleChange = (newValue: string) => {
    setInternalValue(newValue);
    onValueChange?.(newValue);
  };

  return (
    <TabsContext.Provider value={{ value: currentValue, onValueChange: handleChange }}>
      <div className={className}>{children}</div>
    </TabsContext.Provider>
  );
}

// List
export function TabsList({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={`
        inline-flex items-center gap-1 p-1 rounded-lg
        bg-slate-800/50 border border-slate-700/50
        ${className}
      `}
    >
      {children}
    </div>
  );
}

// Trigger
export interface TabsTriggerProps {
  value: string;
  children: ReactNode;
  className?: string;
  disabled?: boolean;
}

export function TabsTrigger({ value, children, className = "", disabled }: TabsTriggerProps) {
  const { value: currentValue, onValueChange } = useTabsContext();
  const isActive = currentValue === value;

  return (
    <button
      type="button"
      role="tab"
      aria-selected={isActive}
      disabled={disabled}
      onClick={() => onValueChange(value)}
      className={`
        relative px-3 py-1.5 text-sm font-medium rounded-md
        transition-colors duration-200
        ${isActive
          ? "text-slate-100"
          : "text-slate-400 hover:text-slate-200 hover:bg-slate-700/30"
        }
        ${disabled ? "opacity-50 cursor-not-allowed" : ""}
        ${className}
      `}
    >
      {isActive && (
        <motion.div
          layoutId="tab-indicator"
          className="absolute inset-0 bg-slate-700/60 rounded-md"
          transition={{ type: "spring", duration: 0.3 }}
        />
      )}
      <span className="relative z-10">{children}</span>
    </button>
  );
}

// Content
export interface TabsContentProps {
  value: string;
  children: ReactNode;
  className?: string;
}

export function TabsContent({ value, children, className = "" }: TabsContentProps) {
  const { value: currentValue } = useTabsContext();
  
  if (currentValue !== value) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
