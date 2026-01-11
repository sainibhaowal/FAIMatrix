"use client";

import React from "react";
import { UploadCloud } from "lucide-react";
import { Spinner } from "@/components/ui";

interface FileUploaderProps {
  onUpload: (files: FileList | File[]) => void;
  activeUploads: Record<string, number>;
  isDragOver: boolean;
  setIsDragOver: (value: boolean) => void;
  isAuthenticated: boolean;
}

export function FileUploader({
  onUpload,
  activeUploads,
  isDragOver,
  setIsDragOver,
  isAuthenticated,
}: FileUploaderProps) {
  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };
  const onDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };
  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files) {
      onUpload(e.dataTransfer.files);
    }
  };

  const handleInputUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) onUpload(e.target.files);
    e.target.value = "";
  };

  return (
    <div
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      className={[
        "relative border-dashed border-2 rounded-xl transition-all duration-200 group",
        isDragOver
          ? "border-cyan-500 bg-cyan-500/10 scale-[1.01]"
          : "border-[var(--border-default)] bg-[var(--surface-1)] hover:bg-[var(--surface-2)]",
      ].join(" ")}
    >
      <div className="p-10 text-center">
        <input
          type="file"
          multiple
          onChange={handleInputUpload}
          disabled={!isAuthenticated}
          className="absolute inset-0 opacity-0 cursor-pointer disabled:cursor-not-allowed z-10"
        />
        <div
          className={[
            "w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4 transition-transform duration-300",
            isDragOver
              ? "bg-cyan-500 text-white scale-110"
              : "bg-[var(--faim-secondary-muted)] text-[var(--faim-secondary)] group-hover:scale-110",
          ].join(" ")}
        >
          <UploadCloud size={28} />
        </div>
        <div className="font-semibold text-base text-[var(--text-primary)] mb-1">
          {isDragOver ? "Drop files now" : "Click or drag files to upload"}
        </div>
        <div className="text-xs text-[var(--text-muted)]">
          Supports PDF, DOCX, TXT, MD, Code • Max 50MB per file
        </div>
      </div>

      {Object.keys(activeUploads).length > 0 && (
        <div className="border-t border-[var(--border-subtle)] p-4 space-y-3 bg-[var(--surface-2)] rounded-b-xl">
          <div className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
            Uploading {Object.keys(activeUploads).length} files...
          </div>
          {Object.entries(activeUploads).map(([name, progress]) => (
            <div key={name} className="flex items-center gap-3 text-xs">
              <Spinner size="xs" />
              <div className="flex-1 min-w-0">
                <div className="flex justify-between mb-1">
                  <span className="truncate text-[var(--text-primary)]">{name}</span>
                  <span className="text-[var(--text-muted)]">{progress}%</span>
                </div>
                <div className="h-1 bg-[var(--surface-3)] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-cyan-500 transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
