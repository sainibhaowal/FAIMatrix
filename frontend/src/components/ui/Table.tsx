"use client";

/**
 * Table Component
 * 
 * Data table with sorting and glass theme.
 * shadcn/ui style.
 */

import { ReactNode, useState, useMemo } from "react";
import { ChevronUp, ChevronDown, ChevronsUpDown } from "lucide-react";

// Types
export interface Column<T> {
  key: keyof T | string;
  header: string;
  sortable?: boolean;
  render?: (value: unknown, row: T) => ReactNode;
  className?: string;
}

export interface TableProps<T extends Record<string, unknown>> {
  data: T[];
  columns: Column<T>[];
  className?: string;
  emptyMessage?: string;
  onRowClick?: (row: T) => void;
}

type SortDirection = "asc" | "desc" | null;

// Component
export function Table<T extends Record<string, unknown>>({
  data,
  columns,
  className = "",
  emptyMessage = "No data available",
  onRowClick,
}: TableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<SortDirection>(null);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : sortDir === "desc" ? null : "asc");
      if (sortDir === "desc") setSortKey(null);
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  const sortedData = useMemo(() => {
    if (!sortKey || !sortDir) return data;
    
    return [...data].sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      
      if (aVal === bVal) return 0;
      if (aVal == null) return 1;
      if (bVal == null) return -1;
      
      const cmp = aVal < bVal ? -1 : 1;
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [data, sortKey, sortDir]);

  return (
    <div className={`overflow-x-auto rounded-xl border border-slate-700/50 ${className}`}>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-700/50 bg-slate-800/30">
            {columns.map((col) => (
              <th
                key={String(col.key)}
                className={`
                  px-4 py-3 text-left font-medium text-slate-300
                  ${col.sortable ? "cursor-pointer select-none hover:bg-slate-700/30" : ""}
                  ${col.className || ""}
                `}
                onClick={() => col.sortable && handleSort(String(col.key))}
              >
                <span className="flex items-center gap-1.5">
                  {col.header}
                  {col.sortable && (
                    <span className="text-slate-500">
                      {sortKey === col.key && sortDir === "asc" && <ChevronUp className="w-3.5 h-3.5" />}
                      {sortKey === col.key && sortDir === "desc" && <ChevronDown className="w-3.5 h-3.5" />}
                      {(sortKey !== col.key || !sortDir) && <ChevronsUpDown className="w-3.5 h-3.5" />}
                    </span>
                  )}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sortedData.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                className="px-4 py-8 text-center text-slate-500"
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            sortedData.map((row, i) => (
              <tr
                key={i}
                onClick={() => onRowClick?.(row)}
                className={`
                  border-b border-slate-800/50 last:border-b-0
                  ${onRowClick ? "cursor-pointer hover:bg-slate-800/40" : ""}
                  transition-colors
                `}
              >
                {columns.map((col) => {
                  const value = row[col.key as keyof T];
                  return (
                    <td
                      key={String(col.key)}
                      className={`px-4 py-3 text-slate-200 ${col.className || ""}`}
                    >
                      {col.render ? col.render(value, row) : String(value ?? "")}
                    </td>
                  );
                })}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
