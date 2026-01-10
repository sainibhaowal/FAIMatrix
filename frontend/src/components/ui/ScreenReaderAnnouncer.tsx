"use client";

/**
 * Screen Reader Announcer
 * 
 * Provides a way to announce messages to screen readers without
 * visual changes. Uses ARIA live regions.
 * 
 * Usage:
 *   import { announce } from "@/components/ui/ScreenReaderAnnouncer";
 *   announce("File uploaded successfully");
 */

import React, { createContext, useContext, useState, useCallback, useEffect } from "react";

interface AnnouncerContextType {
  announce: (message: string, priority?: "polite" | "assertive") => void;
}

const AnnouncerContext = createContext<AnnouncerContextType | null>(null);

export function useAnnouncer() {
  const context = useContext(AnnouncerContext);
  if (!context) {
    // Return no-op if used outside provider
    return { announce: () => {} };
  }
  return context;
}

// Global announce function for use outside React components
let globalAnnounce: ((message: string, priority?: "polite" | "assertive") => void) | null = null;

export function announce(message: string, priority: "polite" | "assertive" = "polite") {
  if (globalAnnounce) {
    globalAnnounce(message, priority);
  }
}

export function ScreenReaderAnnouncer({ children }: { children: React.ReactNode }) {
  const [politeMessage, setPoliteMessage] = useState("");
  const [assertiveMessage, setAssertiveMessage] = useState("");

  const handleAnnounce = useCallback((message: string, priority: "polite" | "assertive" = "polite") => {
    if (priority === "assertive") {
      setAssertiveMessage(message);
      // Clear after announcement
      setTimeout(() => setAssertiveMessage(""), 1000);
    } else {
      setPoliteMessage(message);
      setTimeout(() => setPoliteMessage(""), 1000);
    }
  }, []);

  // Set global announce function
  useEffect(() => {
    globalAnnounce = handleAnnounce;
    return () => {
      globalAnnounce = null;
    };
  }, [handleAnnounce]);

  return (
    <AnnouncerContext.Provider value={{ announce: handleAnnounce }}>
      {children}
      
      {/* Polite announcements (for non-urgent updates) */}
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      >
        {politeMessage}
      </div>

      {/* Assertive announcements (for urgent updates) */}
      <div
        role="alert"
        aria-live="assertive"
        aria-atomic="true"
        className="sr-only"
      >
        {assertiveMessage}
      </div>
    </AnnouncerContext.Provider>
  );
}
