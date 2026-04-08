"use client";

/**
 * FIG View — Search Bar
 *
 * Keyboard-navigable search overlay for graph nodes.
 * Opens on "/" keypress (handled by parent), closes on Escape or blur.
 *
 * Behaviour:
 *   - Fuzzy match by title, kind, or node_id prefix (via filterNodesBySearch)
 *   - Arrow keys navigate results list
 *   - Enter selects highlighted result → calls onSelectNode + onClose
 *   - Click also selects
 *   - createPortal not needed — parent mounts only when search is open
 *   - No API calls — pure client-side search index
 */

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { Badge } from "@/components/ui";
import {
  buildSearchIndex,
  filterNodesBySearch,
  type SearchIndexEntry,
} from "@/lib/figViewGraphTransform";
import { nodeColorByState } from "@/lib/figViewLayout";
import { nodeStateClass, safeNodeTitle } from "@/lib/figViewSafety";
import type { FigNode, FigNodeDisplayState } from "@/types/figView";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type FigSearchProps = {
  nodes: FigNode[];
  nodeIndex: Map<string, FigNode>;
  onSelectNode: (nodeId: string) => void;
  onClose: () => void;
};

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function FigSearch({
  nodes,
  nodeIndex,
  onSelectNode,
  onClose,
}: FigSearchProps) {
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Build index once on mount / when nodes change
  const searchIndex = useMemo(() => buildSearchIndex(nodes), [nodes]);

  // Filtered results — max 12 shown
  const results: SearchIndexEntry[] = useMemo(() => {
    if (!query.trim()) return searchIndex.slice(0, 12);
    return filterNodesBySearch(searchIndex, query).slice(0, 12);
  }, [searchIndex, query]);

  // Reset active index when results change
  useEffect(() => {
    setActiveIndex(0);
  }, [results.length]);

  // Auto-focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Scroll active item into view
  useEffect(() => {
    const item = listRef.current?.querySelector<HTMLElement>(
      `[data-idx="${activeIndex}"]`
    );
    item?.scrollIntoView({ block: "nearest" });
  }, [activeIndex]);

  const handleSelect = useCallback(
    (nodeId: string) => {
      onSelectNode(nodeId);
      onClose();
    },
    [onSelectNode, onClose]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIndex((i) => Math.min(i + 1, results.length - 1));
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIndex((i) => Math.max(i - 1, 0));
        return;
      }
      if (e.key === "Enter") {
        const entry = results[activeIndex];
        if (entry) handleSelect(entry.node_id);
        return;
      }
    },
    [results, activeIndex, handleSelect, onClose]
  );

  return (
    /* Backdrop */
    <div
      className="absolute inset-0 z-50 flex items-start justify-center pt-16"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-[480px] mx-4 rounded-2xl border border-slate-700/70 bg-slate-950/98 shadow-[0_16px_48px_rgba(0,0,0,0.7)] backdrop-blur-md overflow-hidden">

        {/* Search input */}
        <div className="flex items-center gap-2 border-b border-slate-800/70 px-4 py-3">
          <svg
            className="h-4 w-4 text-slate-500 shrink-0"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <circle cx={11} cy={11} r={8} />
            <path d="m21 21-4.35-4.35" />
          </svg>
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search nodes by title, kind, or ID…"
            className="flex-1 bg-transparent text-sm text-slate-100 placeholder-slate-500 outline-none"
            spellCheck={false}
          />
          <button
            onClick={onClose}
            className="shrink-0 rounded-md border border-slate-700/60 px-2 py-0.5 text-[9px] text-slate-500 hover:text-slate-300 transition-colors"
          >
            ESC
          </button>
        </div>

        {/* Results */}
        <div ref={listRef} className="max-h-72 overflow-auto">
          {results.length === 0 ? (
            <div className="px-4 py-6 text-center">
              <p className="text-sm text-slate-500">No nodes match "{query}"</p>
              <p className="text-xs text-slate-700 mt-1">
                Try title keywords, node kind, or ID prefix
              </p>
            </div>
          ) : (
            results.map((entry, idx) => {
              const node = nodeIndex.get(entry.node_id);
              const color = node
                ? nodeColorByState(
                    nodeStateClass(node) as FigNodeDisplayState,
                    false
                  )
                : "#475569";
              const isActive = idx === activeIndex;

              return (
                <button
                  key={entry.node_id}
                  data-idx={idx}
                  onClick={() => handleSelect(entry.node_id)}
                  onMouseEnter={() => setActiveIndex(idx)}
                  className={`flex w-full items-center gap-3 px-4 py-2.5 text-left transition-colors ${
                    isActive
                      ? "bg-slate-800/70"
                      : "hover:bg-slate-800/40"
                  }`}
                >
                  {/* State color dot */}
                  <span
                    className="h-2 w-2 rounded-full shrink-0"
                    style={{ backgroundColor: color }}
                  />

                  {/* Title + kind */}
                  <div className="flex flex-1 items-center gap-2 min-w-0">
                    <span
                      className={`truncate text-sm font-medium ${
                        isActive ? "text-slate-100" : "text-slate-300"
                      }`}
                    >
                      {entry.title}
                    </span>
                    <Badge size="sm" variant="outline">
                      {entry.kind}
                    </Badge>
                  </div>

                  {/* Node ID hint */}
                  <span className="shrink-0 font-mono text-[9px] text-slate-600">
                    {entry.node_id.slice(0, 8)}
                  </span>

                  {/* Enter hint on active */}
                  {isActive && (
                    <span className="shrink-0 rounded border border-slate-700/60 bg-slate-900/60 px-1.5 py-0.5 text-[9px] text-slate-500">
                      ↵
                    </span>
                  )}
                </button>
              );
            })
          )}
        </div>

        {/* Footer hints */}
        <div className="flex items-center gap-4 border-t border-slate-800/60 px-4 py-2">
          <span className="text-[9px] text-slate-600">↑↓ navigate</span>
          <span className="text-[9px] text-slate-600">↵ select</span>
          <span className="text-[9px] text-slate-600">ESC close</span>
          {results.length > 0 && (
            <span className="ml-auto text-[9px] text-slate-600">
              {results.length} result{results.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>

      </div>
    </div>
  );
}
