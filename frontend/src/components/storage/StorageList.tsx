"use client";

import React from "react";
import { File as FileIcon, MoreVertical, Trash2 } from "lucide-react";
import { Card, Skeleton, EmptyState, useOutsideClick } from "@/components/ui";

type Doc = {
  id: string;
  filename: string;
  status: string;
  created_at: string;
  file_size_bytes: number;
};

interface StorageListProps {
  docs: Doc[];
  loading: boolean;
  selectedIds: Set<string>;
  onToggleSelection: (id: string, multi: boolean) => void;
  onSelectAll: () => void;
  onPreview: (doc: Doc) => void;
  onDelete: (doc: Doc) => void;
  formatBytes: (bytes: number) => string;
}

export function StorageList({
  docs,
  loading,
  selectedIds,
  onToggleSelection,
  onSelectAll,
  onPreview,
  onDelete,
  formatBytes,
}: StorageListProps) {
  return (
    <Card noPadding className="overflow-hidden">
      <div className="px-4 py-3 border-b border-[var(--border-subtle)] bg-[var(--surface-1)] flex items-center gap-3">
        <input
          type="checkbox"
          className="rounded border-[var(--border-default)] bg-[var(--surface-2)] text-cyan-500 focus:ring-cyan-500/30"
          checked={docs.length > 0 && selectedIds.size === docs.length}
          onChange={onSelectAll}
        />
        <span className="text-xs font-semibold text-[var(--text-secondary)]">Name</span>
        <div className="ml-auto text-xs font-semibold text-[var(--text-secondary)] pr-20">Status</div>
      </div>

      {loading ? (
        <div className="p-5 space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="flex items-center gap-4">
              <Skeleton height={40} width={40} className="rounded-lg" />
              <div className="space-y-2 flex-1">
                <Skeleton height={14} width="40%" />
                <Skeleton height={10} width="20%" />
              </div>
            </div>
          ))}
        </div>
      ) : docs.length === 0 ? (
        <EmptyState
          icon="documents"
          title="No files found"
          description="Upload documents to get started."
          size="sm"
        />
      ) : (
        <div className="divide-y divide-[var(--border-subtle)]">
          {docs.map((doc) => {
            const isSelected = selectedIds.has(doc.id);
            return (
              <div
                key={doc.id}
                className={`group px-4 py-3 flex items-center gap-3 hover:bg-[var(--surface-2)] transition-colors ${
                  isSelected ? "bg-cyan-500/5 text-cyan-100" : ""
                }`}
              >
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={() => onToggleSelection(doc.id, true)}
                  className="rounded border-[var(--border-default)] bg-[var(--surface-2)] text-cyan-500 focus:ring-cyan-500/30 opacity-40 group-hover:opacity-100 transition-opacity"
                />

                <div className="w-9 h-9 shrink-0 rounded-lg bg-[var(--surface-3)] flex items-center justify-center text-[var(--text-secondary)]">
                  <FileIcon size={16} />
                </div>

                <button
                  onClick={() => onPreview(doc)}
                  className="flex-1 min-w-0 text-left"
                >
                  <div className="flex items-center gap-2">
                    <span
                      className={`font-medium text-sm truncate hover:underline ${
                        isSelected ? "text-cyan-200" : "text-[var(--text-primary)]"
                      }`}
                    >
                      {doc.filename}
                    </span>
                  </div>
                  <div className="text-[11px] text-[var(--text-muted)] flex items-center gap-2 mt-0.5">
                    <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                    <span>•</span>
                    <span>{formatBytes(doc.file_size_bytes)}</span>
                  </div>
                </button>

                <StatusBadge status={doc.status} />

                <DropdownMenu doc={doc} onDelete={() => onDelete(doc)} />
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}

function DropdownMenu({ doc, onDelete }: { doc: Doc; onDelete: () => void }) {
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef(null);
  useOutsideClick(ref as any, () => setOpen(false));

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-3)] transition-all"
      >
        <MoreVertical size={14} />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 w-32 bg-[var(--surface-2)] border border-[var(--border-subtle)] rounded-lg shadow-xl z-10 overflow-hidden py-1">
          <button
            onClick={() => {
              setOpen(false);
              onDelete();
            }}
            className="w-full text-left px-3 py-2 text-xs text-rose-400 hover:bg-rose-500/10 flex items-center gap-2"
          >
            <Trash2 size={12} /> Delete
          </button>
        </div>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const variantMap: Record<string, string> = {
    completed: "bg-emerald-500/20 text-emerald-400",
    processed: "bg-emerald-500/20 text-emerald-400",
    processing: "bg-amber-500/20 text-amber-400",
    failed: "bg-rose-500/20 text-rose-400",
    default: "bg-slate-500/20 text-slate-400",
  };
  const classes = variantMap[status] || variantMap.default;
  return (
    <div className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold tracking-wider ${classes}`}>
      {status}
    </div>
  );
}
