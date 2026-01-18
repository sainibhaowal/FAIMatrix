"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Filter, Search, Calendar, Tag, Sparkles, X } from "lucide-react";

interface FilterStats {
  total_nodes: number;
  filtered_nodes: number;
  total_links: number;
  filtered_links: number;
  topics_found: string[];
  date_range: string | null;
}

interface Topic {
  topic: string;
  count: number;
}

interface Props {
  graphId: string;
  onApplyFilters?: (filters: FilterOptions) => void;
}

export interface FilterOptions {
  topic: string | null;
  dateFrom: string | null;
  dateTo: string | null;
  minUsage: number;
  kind: string | null;
}

export default function GraphFiltersPanel({ graphId, onApplyFilters }: Props) {
  const [isLoading, setIsLoading] = useState(false);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [filterStats, setFilterStats] = useState<FilterStats | null>(null);

  // Filter state
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);
  const [topicSearch, setTopicSearch] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [minUsage, setMinUsage] = useState(0);

  // Load topics on mount
  useEffect(() => {
    const loadTopics = async () => {
      try {
        const res = await fetch(`/api/v1/graphs/${graphId}/topics?limit=30`);
        const data = await res.json();
        if (data.topics) {
          setTopics(data.topics);
        }
      } catch (e) {
        console.error("Failed to load topics:", e);
      }
    };
    loadTopics();
  }, [graphId]);

  // Apply filters
  const applyFilters = useCallback(async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams();
      if (selectedTopic || topicSearch) {
        params.set("topic", selectedTopic || topicSearch);
      }
      if (dateFrom) params.set("date_from", dateFrom);
      if (dateTo) params.set("date_to", dateTo);
      if (minUsage > 0) params.set("min_usage", minUsage.toString());

      const res = await fetch(
        `/api/v1/graphs/${graphId}/filtered?${params.toString()}`,
      );
      const data = await res.json();

      if (data.filter_stats) {
        setFilterStats(data.filter_stats);
      }

      // Call the callback to update parent
      if (onApplyFilters) {
        onApplyFilters({
          topic: selectedTopic || topicSearch || null,
          dateFrom: dateFrom || null,
          dateTo: dateTo || null,
          minUsage,
          kind: null,
        });
      }
    } catch (e) {
      console.error("Filter failed:", e);
    } finally {
      setIsLoading(false);
    }
  }, [
    graphId,
    selectedTopic,
    topicSearch,
    dateFrom,
    dateTo,
    minUsage,
    onApplyFilters,
  ]);

  // Clear all filters
  const clearFilters = () => {
    setSelectedTopic(null);
    setTopicSearch("");
    setDateFrom("");
    setDateTo("");
    setMinUsage(0);
    setFilterStats(null);
  };

  const hasActiveFilters =
    selectedTopic || topicSearch || dateFrom || dateTo || minUsage > 0;

  return (
    <div className="space-y-4 p-2">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold text-slate-100 flex items-center gap-2">
          <Filter size={14} className="text-violet-400" />
          Graph Filters
        </h3>
        {hasActiveFilters && (
          <button
            onClick={clearFilters}
            className="text-[10px] text-slate-400 hover:text-red-300 flex items-center gap-1"
          >
            <X size={10} />
            Clear
          </button>
        )}
      </div>

      {/* Topic Search */}
      <div className="space-y-2">
        <label className="text-[10px] text-slate-500 uppercase tracking-wider">
          Topic / Keyword
        </label>
        <div className="relative">
          <Search
            size={14}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"
          />
          <input
            type="text"
            value={topicSearch}
            onChange={(e) => {
              setTopicSearch(e.target.value);
              setSelectedTopic(null);
            }}
            placeholder="Search topics..."
            className="w-full rounded-lg border border-slate-800 bg-slate-900/50 py-2 pl-9 pr-3 text-xs text-slate-200 placeholder-slate-500 focus:border-violet-500/50 focus:outline-none"
          />
        </div>

        {/* Topic Pills */}
        {topics.length > 0 && (
          <div className="flex flex-wrap gap-1 max-h-24 overflow-auto">
            {topics
              .filter((t) =>
                t.topic.toLowerCase().includes(topicSearch.toLowerCase()),
              )
              .slice(0, 15)
              .map((t) => (
                <button
                  key={t.topic}
                  onClick={() => {
                    setSelectedTopic(t.topic);
                    setTopicSearch("");
                  }}
                  className={`px-2 py-1 rounded-full text-[10px] border transition-all ${
                    selectedTopic === t.topic
                      ? "border-violet-400/50 bg-violet-500/20 text-violet-200"
                      : "border-slate-700 bg-slate-800/50 text-slate-400 hover:border-violet-400/30"
                  }`}
                >
                  {t.topic}
                  <span className="ml-1 opacity-50">{t.count}</span>
                </button>
              ))}
          </div>
        )}
      </div>

      {/* Date Range */}
      <div className="space-y-2">
        <label className="text-[10px] text-slate-500 uppercase tracking-wider flex items-center gap-1">
          <Calendar size={10} />
          Date Range
        </label>
        <div className="grid grid-cols-2 gap-2">
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="rounded-lg border border-slate-800 bg-slate-900/50 px-2 py-1.5 text-[10px] text-slate-200 focus:border-violet-500/50 focus:outline-none"
          />
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="rounded-lg border border-slate-800 bg-slate-900/50 px-2 py-1.5 text-[10px] text-slate-200 focus:border-violet-500/50 focus:outline-none"
          />
        </div>
      </div>

      {/* Min Usage */}
      <div className="space-y-2">
        <label className="text-[10px] text-slate-500 uppercase tracking-wider flex items-center justify-between">
          <span className="flex items-center gap-1">
            <Sparkles size={10} />
            Min Usage
          </span>
          <span className="text-slate-400">{minUsage}</span>
        </label>
        <input
          type="range"
          min={0}
          max={20}
          value={minUsage}
          onChange={(e) => setMinUsage(parseInt(e.target.value))}
          className="w-full accent-violet-500"
        />
        <div className="flex justify-between text-[9px] text-slate-600">
          <span>All</span>
          <span>Hot only</span>
        </div>
      </div>

      {/* Apply Button */}
      <button
        onClick={applyFilters}
        disabled={isLoading}
        className={`w-full flex items-center justify-center gap-2 rounded-lg border px-4 py-2 text-xs font-medium transition-all ${
          isLoading
            ? "border-slate-700 bg-slate-800 text-slate-400 cursor-wait"
            : "border-violet-500/30 bg-violet-500/10 text-violet-300 hover:bg-violet-500/20"
        }`}
      >
        <Filter size={14} />
        {isLoading ? "Filtering..." : "Apply Filters"}
      </button>

      {/* Filter Stats */}
      {filterStats && (
        <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-3 space-y-2">
          <div className="flex justify-between text-[10px]">
            <span className="text-slate-400">Nodes</span>
            <span className="font-mono text-slate-300">
              {filterStats.filtered_nodes} / {filterStats.total_nodes}
            </span>
          </div>
          <div className="flex justify-between text-[10px]">
            <span className="text-slate-400">Links</span>
            <span className="font-mono text-slate-300">
              {filterStats.filtered_links} / {filterStats.total_links}
            </span>
          </div>
          {filterStats.date_range && (
            <div className="text-[10px] text-slate-500">
              {filterStats.date_range}
            </div>
          )}
          {filterStats.topics_found.length > 0 && (
            <div className="flex flex-wrap gap-1 pt-1">
              {filterStats.topics_found.slice(0, 5).map((t) => (
                <span
                  key={t}
                  className="px-1.5 py-0.5 rounded text-[9px] bg-violet-500/10 text-violet-300 border border-violet-500/20"
                >
                  {t}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
