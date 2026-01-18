"use client";

import React from "react";
import { Settings, Shield, Image as ImageIcon, Braces, Type } from "lucide-react";
import { Badge } from "@/components/ui/Badge";

export interface IngestSettings {
  strip_images: boolean;
  strip_base64: boolean;
  max_chars_per_chunk: number;
  chunk_size_words: number;
  chunk_overlap_words: number;
}

export const DEFAULT_SETTINGS: IngestSettings = {
  strip_images: false,
  strip_base64: true,
  max_chars_per_chunk: 4000,
  chunk_size_words: 1000,
  chunk_overlap_words: 100,
};

interface IngestionSettingsPanelProps {
  settings: IngestSettings;
  onChange: (settings: IngestSettings) => void;
}

export function IngestionSettingsPanel({ settings, onChange }: IngestionSettingsPanelProps) {
  const handleChange = (key: keyof IngestSettings, value: any) => {
    onChange({ ...settings, [key]: value });
  };

  return (
    <div className="bg-[var(--surface-2)] border border-[var(--border-subtle)] rounded-xl p-4 space-y-4 shadow-inner">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-2">
          <Settings size={16} className="text-cyan-400" />
          Cleanroom Ingestion Lab
        </h3>
        <Badge variant="outline" className="text-[9px] border-cyan-500/30 text-cyan-400">
          INDUSTRIAL GRADE
        </Badge>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Toggle Controls */}
        <div className="space-y-3">
          <div className="flex items-center justify-between p-2 rounded-lg hover:bg-[var(--surface-3)] transition-colors">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-rose-500/10 rounded-lg text-rose-400">
                <ImageIcon size={14} />
              </div>
              <div>
                <div className="text-xs font-medium text-[var(--text-primary)]">Strip Visual Assets</div>
                <div className="text-[10px] text-[var(--text-muted)]">Omit images & diagrams from graph</div>
              </div>
            </div>
            <input
              type="checkbox"
              checked={settings.strip_images}
              onChange={(e) => handleChange("strip_images", e.target.checked)}
              className="rounded border-[var(--border-default)] bg-[var(--surface-3)] text-cyan-500 focus:ring-cyan-500/30"
            />
          </div>

          <div className="flex items-center justify-between p-2 rounded-lg hover:bg-[var(--surface-3)] transition-colors">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-emerald-500/10 rounded-lg text-emerald-400">
                <Braces size={14} />
              </div>
              <div>
                <div className="text-xs font-medium text-[var(--text-primary)]">Base64 De-bloat</div>
                <div className="text-[10px] text-[var(--text-muted)]">Strip embedded binary data strings</div>
              </div>
            </div>
            <input
              type="checkbox"
              checked={settings.strip_base64}
              onChange={(e) => handleChange("strip_base64", e.target.checked)}
              className="rounded border-[var(--border-default)] bg-[var(--surface-3)] text-cyan-500 focus:ring-cyan-500/30"
            />
          </div>
        </div>

        {/* Input Controls */}
        <div className="space-y-3">
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-semibold text-[var(--text-secondary)] flex items-center gap-2">
                <Shield size={12} className="text-cyan-400" />
                Hard Character Limit
              </label>
              <span className="text-[10px] text-cyan-500 font-mono">{settings.max_chars_per_chunk}</span>
            </div>
            <input
              type="range"
              min="500"
              max="8000"
              step="500"
              value={settings.max_chars_per_chunk}
              onChange={(e) => handleChange("max_chars_per_chunk", parseInt(e.target.value))}
              className="w-full h-1.5 bg-[var(--surface-3)] rounded-lg appearance-none cursor-pointer accent-cyan-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-[10px] font-semibold text-[var(--text-muted)] uppercase tracking-wider">
                Chunk Size (Words)
              </label>
              <input
                type="number"
                value={settings.chunk_size_words}
                onChange={(e) => handleChange("chunk_size_words", parseInt(e.target.value))}
                className="w-full bg-[var(--surface-1)] border border-[var(--border-default)] rounded-lg px-2 py-1 text-xs text-[var(--text-primary)] focus:border-cyan-500/50 outline-none"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] font-semibold text-[var(--text-muted)] uppercase tracking-wider">
                Overlap (Words)
              </label>
              <input
                type="number"
                value={settings.chunk_overlap_words}
                onChange={(e) => handleChange("chunk_overlap_words", parseInt(e.target.value))}
                className="w-full bg-[var(--surface-1)] border border-[var(--border-default)] rounded-lg px-2 py-1 text-xs text-[var(--text-primary)] focus:border-cyan-500/50 outline-none"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
