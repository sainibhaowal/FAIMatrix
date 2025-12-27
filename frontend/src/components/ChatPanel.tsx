'use client';

/* ============================================================================
 * FAIM LAB — ChatPanel (Production)
 * File: src/components/ChatPanel.tsx
 *
 * Goals
 * - Always chat against the correct Universe graph (U:...) when available
 * - Never touch window/localStorage at module scope (avoids SSR/hydration issues)
 * - Fail-soft: if Universe not known yet, fall back to provided prop graphId
 *
 * Notes
 * - Preferred source order:
 *   1) localStorage faim.universe_graph_id if it starts with "U:"
 *   2) props.graphId if it starts with "U:"
 *   3) props.graphId (even if not U:) as last resort (keeps UI usable)
 * ========================================================================== */

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { postChat, type ChatTurn, type UsedNodeSummary } from '../lib/api';

type ChatPanelProps = {
  graphId?: string;
  onContextUpdate?(nodes: UsedNodeSummary[]): void;
};

const LS_UNIVERSE_KEY = 'faim.universe_graph_id';

function clamp(n: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, n));
}

/**
 * Glow for card:
 * - Updates --mx/--my on hover
 * - Shows glow while inside, hides on leave
 */
function useGlow() {
  const ref = useRef<HTMLDivElement | null>(null);

  const onMouseMove = (e: React.MouseEvent) => {
    const el = ref.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const x = clamp((e.clientX - r.left) / Math.max(1, r.width), 0, 1) * 100;
    const y = clamp((e.clientY - r.top) / Math.max(1, r.height), 0, 1) * 100;
    el.style.setProperty('--mx', `${x.toFixed(2)}%`);
    el.style.setProperty('--my', `${y.toFixed(2)}%`);
    el.style.setProperty('--gvis', `1`);
  };

  const onMouseLeave = () => {
    const el = ref.current;
    if (!el) return;
    el.style.setProperty('--gvis', `0`);
  };

  return { ref, onMouseMove, onMouseLeave };
}

function GlowCard({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  const g = useGlow();

  return (
    <div
      ref={g.ref}
      onMouseMove={g.onMouseMove}
      onMouseLeave={g.onMouseLeave}
      style={
        {
          '--mx': '50%',
          '--my': '30%',
          '--gvis': '0',
        } as React.CSSProperties
      }
      className={[
        'group relative overflow-hidden rounded-2xl border border-slate-800/70 bg-slate-950/55',
        'shadow-[0_0_0_1px_rgba(15,23,42,0.6),0_18px_60px_-30px_rgba(0,0,0,0.8)]',
        'transition-transform duration-200 hover:-translate-y-[1px]',
        'before:pointer-events-none before:absolute before:inset-0 before:opacity-0 before:transition-opacity before:duration-200',
        'before:[background:radial-gradient(650px_circle_at_var(--mx)_var(--my),rgba(34,211,238,0.18),transparent_55%)]',
        'hover:before:opacity-[var(--gvis)]',
        'after:pointer-events-none after:absolute after:inset-0 after:opacity-0 after:transition-opacity after:duration-200',
        'after:[background:radial-gradient(420px_circle_at_var(--mx)_var(--my),rgba(168,85,247,0.16),transparent_60%)]',
        'hover:after:opacity-[var(--gvis)]',
        'ring-1 ring-transparent hover:ring-cyan-400/20',
        className ?? '',
      ].join(' ')}
    >
      <div className="relative z-[1]">{children}</div>
    </div>
  );
}

export function ChatPanel({ graphId, onContextUpdate }: ChatPanelProps) {
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Universe from localStorage (read only after mount)
  const [universeId, setUniverseId] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const readUniverse = () => {
      const u = window.localStorage.getItem(LS_UNIVERSE_KEY) || '';
      setUniverseId(u.startsWith('U:') ? u : null);
    };

    readUniverse();

    // If other components update Universe, this catches it (same-tab changes won’t fire storage,
    // but cross-tab does; still useful and harmless)
    const onStorage = (e: StorageEvent) => {
      if (e.key === LS_UNIVERSE_KEY) readUniverse();
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, []);

  // Decide what graph_id to use for chat
  const effectiveGraphId = useMemo(() => {
    if (universeId && universeId.startsWith('U:')) return universeId;
    if (graphId && graphId.startsWith('U:')) return graphId;
    return graphId; // last resort (keeps chat usable even if universe not ready)
  }, [universeId, graphId]);

  const canSend = useMemo(() => input.trim().length > 0 && !busy, [input, busy]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || busy) return;

    setError(null);
    setBusy(true);

    // optimistic user turn
    setTurns((t) => [...t, { role: 'user', content: text }]);
    setInput('');

    try {
      // ✅ Only ONE call
      const res = await postChat(text, effectiveGraphId);

      if (res?.used_nodes && onContextUpdate) onContextUpdate(res.used_nodes);

      setTurns((t) => [
        ...t,
        { role: 'assistant', content: res?.reply ?? '(no reply)' },
      ]);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : 'Chat request failed.';
      setError(msg);
    } finally {
      setBusy(false);
    }
  }

  return (
    <GlowCard className="p-4 md:p-5">
      <header className="mb-3 flex items-center justify-between gap-3">
        <div>
          <div className="text-xs font-semibold text-slate-100">Chat + Memory</div>
          <div className="text-[11px] text-slate-400">
            Talk to the system. FAIM feeds context; you see it on the right.
          </div>
        </div>

        <div className="rounded-full border border-slate-800 bg-slate-950/60 px-3 py-1 text-[10px] uppercase tracking-widest text-cyan-300/80">
          Live
        </div>
      </header>

      <div className="mb-4 h-[420px] overflow-y-auto rounded-xl border border-slate-900/60 bg-slate-950/35 p-3">
        {turns.length === 0 ? (
          <div className="text-xs text-slate-500">
            Ask FAIM anything… your used memory nodes will appear in the Context panel.
          </div>
        ) : (
          <div className="space-y-3">
            {turns.map((t, i) => (
              <div
                key={i}
                className={[
                  'max-w-[92%] rounded-xl border px-3 py-2 text-sm leading-relaxed',
                  t.role === 'user'
                    ? 'ml-auto border-cyan-500/20 bg-cyan-500/10 text-slate-50'
                    : 'mr-auto border-slate-800/70 bg-slate-950/50 text-slate-100',
                ].join(' ')}
              >
                <div className="mb-1 text-[10px] uppercase tracking-widest text-slate-400">
                  {t.role}
                </div>
                <div className="whitespace-pre-wrap">{t.content}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {error ? (
        <div className="mb-3 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-200">
          {error}
        </div>
      ) : null}

      <form onSubmit={onSubmit} className="flex items-end gap-2">
        <textarea
          rows={2}
          placeholder="Ask FAIM anything…"
          className="min-h-[44px] flex-1 resize-none rounded-xl border border-slate-800/70 bg-slate-950/40 px-3 py-2 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-cyan-500/60"
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <button
          type="submit"
          disabled={!canSend}
          className={[
            'h-[44px] rounded-xl px-4 text-sm font-medium',
            'bg-cyan-500 text-slate-950',
            'disabled:cursor-not-allowed disabled:opacity-50',
            'shadow-[0_0_0_1px_rgba(34,211,238,0.25),0_14px_40px_-20px_rgba(34,211,238,0.65)]',
          ].join(' ')}
        >
          {busy ? 'Thinking…' : 'Ask'}
        </button>
      </form>

      {/* Optional tiny debug line (safe). Remove later if you want. */}
      <div className="mt-3 text-[10px] text-slate-600">
        graph_id: {effectiveGraphId ?? '—'}
      </div>
    </GlowCard>
  );
}
