"use client";

import React from "react";
import { Copy, Plus, Trash2, ShieldAlert } from "lucide-react";

type APIKey = {
  id: string;
  name: string;
  key_prefix: string;
  created_at: string;
  status: string;
  scopes: string[];
};

interface ApiKeyManagerProps {
  keys: APIKey[];
  loading: boolean;
  error: string;
  newKey: string | null;
  createName: string;
  setCreateName: (name: string) => void;
  isCreating: boolean;
  onCreate: () => Promise<void>;
  onRevoke: (id: string) => Promise<void>;

}

export function ApiKeyManager({
  keys,
  loading,
  error,
  newKey,
  createName,
  setCreateName,
  isCreating,
  onCreate,
  onRevoke,

}: ApiKeyManagerProps) {
  return (
    <div className="space-y-4">
      {error && (
        <div className="text-red-400 bg-red-400/10 p-3 rounded-xl text-xs mb-4">
          {error}
        </div>
      )}

      {/* CREATE SECTION */}
      <section className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 mb-4">
        <h2 className="text-xs font-semibold text-slate-100 mb-3">
          Generate New Key
        </h2>
        <div className="flex gap-3">
          <input
            type="text"
            value={createName}
            onChange={(e) => setCreateName(e.target.value)}
            placeholder="Key Name (e.g. Mobile App)"
            className="flex-1 bg-slate-800/50 border border-slate-700 rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-cyan-500/50 transition-colors placeholder:text-slate-600"
          />
          <button
            onClick={onCreate}
            disabled={!createName || isCreating}
            className="bg-cyan-500 hover:bg-cyan-400 text-black font-semibold px-4 py-2 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 text-xs"
          >
            {isCreating ? (
              "Generating..."
            ) : (
              <>
                <Plus size={14} /> Generate
              </>
            )}
          </button>
        </div>

        {/* SUCCESS MODAL / INLINE */}
        {newKey && (
          <div className="mt-4 bg-cyan-900/20 border border-cyan-500/30 rounded-xl p-3">
            <div className="flex items-start gap-3">
              <ShieldAlert
                className="text-cyan-400 shrink-0 mt-0.5"
                size={16}
              />
              <div className="flex-1 overflow-hidden">
                <div className="font-semibold text-cyan-100 text-xs mb-1">
                  Key Generated Successfully
                </div>
                <div className="text-[10px] text-cyan-200/60 mb-2">
                  Copy this key now. You won&apos;t be able to see it again!
                </div>
                <div className="flex items-center gap-2 bg-black/60 rounded-lg px-2 py-1.5 font-mono text-[10px] text-cyan-300 break-all">
                  <span>{newKey}</span>
                  <button
                    onClick={() => navigator.clipboard.writeText(newKey)}
                    className="ml-auto hover:text-white transition-colors"
                  >
                    <Copy size={12} />
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </section>

      {/* LIST SECTION */}
      <section className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
        <h2 className="text-xs font-semibold text-slate-100 mb-3">
          Active Keys
        </h2>
        {keys.length === 0 && !loading && (
          <div className="text-slate-500 italic text-xs">
            No API keys found.
          </div>
        )}
        <div className="space-y-2">
          {keys.map((key) => (
            <div
              key={key.id}
              className="flex items-center justify-between p-3 rounded-xl border border-slate-700/50 bg-slate-800/30 hover:bg-slate-800/50 transition-colors group"
            >
              <div>
                <div className="font-medium text-slate-200 text-xs">
                  {key.name}
                </div>
                <div className="text-[10px] font-mono text-slate-500 mt-0.5">
                  {key.key_prefix}... • Created{" "}
                  {new Date(key.created_at).toLocaleDateString()}
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="px-2 py-0.5 rounded bg-slate-700/50 text-[9px] text-slate-400 uppercase tracking-wider">
                  {key.status}
                </div>
                <button
                  onClick={() => onRevoke(key.id)}
                  className="p-1.5 rounded-lg text-slate-600 hover:text-red-400 hover:bg-red-400/10 transition-all opacity-0 group-hover:opacity-100"
                  title="Revoke Key"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
