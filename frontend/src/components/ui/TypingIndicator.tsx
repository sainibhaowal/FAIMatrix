import React from "react";

export function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 px-1">
      <div
        className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-bounce"
        style={{ animationDelay: "0ms" }}
      />
      <div
        className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-bounce"
        style={{ animationDelay: "150ms" }}
      />
      <div
        className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-bounce"
        style={{ animationDelay: "300ms" }}
      />
    </div>
  );
}
