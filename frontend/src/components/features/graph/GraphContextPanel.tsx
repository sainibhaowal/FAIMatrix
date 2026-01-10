// Graph Context Search Panel - Find related nodes by semantic similarity
"use client";

import { useState } from "react";

interface ContextNode {
  id: string;
  label: string;
  payload: string;
  score: number;
  kind: string;
}

interface Props {
  graphId: string;
  onNodeSelect?: (nodeId: string) => void;
}

export default function GraphContextPanel({ graphId, onNodeSelect }: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<ContextNode[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSearch() {
    if (!query.trim()) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const res = await fetch(
        `/api/v1/graphs/${graphId}/context?query=${encodeURIComponent(query)}&k=10`
      );
      
      if (!res.ok) {
        throw new Error(`Failed to search: ${res.status}`);
      }
      
      const data = await res.json();
      setResults(data.nodes || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-4 space-y-4">
      <div>
        <h3 className="text-sm font-semibold text-slate-100 mb-1">Context Search</h3>
        <p className="text-xs text-slate-400">
          Find semantically related memory nodes
        </p>
      </div>

      {/* Search input */}
      <div className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder="Search memories..."
          className="flex-1 h-9 rounded-lg border border-slate-700 bg-slate-900/50 px-3 text-sm text-slate-100 placeholder:text-slate-500 focus:border-cyan-400/40 focus:outline-none focus:ring-1 focus:ring-cyan-400/20"
        />
        <button
          onClick={handleSearch}
          disabled={loading || !query.trim()}
          className="h-9 px-4 rounded-lg bg-cyan-500/15 border border-cyan-400/30 text-xs font-medium text-cyan-200 hover:bg-cyan-500/25 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? "..." : "Search"}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg p-2">
          {error}
        </div>
      )}

      {/* Results */}
      <div className="space-y-2 max-h-[400px] overflow-y-auto">
        {results.length === 0 && !loading && query && (
          <div className="text-xs text-slate-500 text-center py-4">
            No results found
          </div>
        )}

        {results.map((node, i) => (
          <div
            key={node.id}
            onClick={() => onNodeSelect?.(node.id)}
            className="p-3 rounded-xl border border-slate-800/70 bg-slate-900/50 hover:border-cyan-400/30 hover:bg-slate-900/80 cursor-pointer transition-colors"
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-cyan-300">
                #{i + 1} • {node.kind || "memory"}
              </span>
              <span className="text-[10px] text-slate-500">
                Score: {(node.score * 100).toFixed(1)}%
              </span>
            </div>
            <div className="text-sm text-slate-200 line-clamp-2">
              {node.label || node.payload?.slice(0, 100)}
            </div>
            <div className="text-[10px] text-slate-500 mt-1 truncate">
              {node.id}
            </div>
          </div>
        ))}
      </div>

      {/* Stats */}
      {results.length > 0 && (
        <div className="text-[10px] text-slate-500 text-center">
          Found {results.length} related nodes
        </div>
      )}
    </div>
  );
}
