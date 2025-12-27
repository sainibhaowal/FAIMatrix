'use client';

import * as React from 'react';
import { useState } from 'react';
import { API_BASE_URL as API_BASE, buildFaimHeaders } from "@/lib/api";

type AddMemoryPanelProps = {
  graphId: string;
  onAddComplete?: () => void;
};

type AddResponse = {
  created_nodes?: number;
  node_ids?: string[];
  [key: string]: unknown;
};

function clamp(n: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, n));
}

/**
 * Sticky glow (panel-level):
 * - updates --mx/--my on pointer move capture
 * - does NOT reset on leave (sticky)
 * - controlled intensity
 */
function onStickyGlowMove(intensity = 0.22) {
  return (e: React.PointerEvent<HTMLElement>) => {
    const el = e.currentTarget as HTMLElement;
    const r = el.getBoundingClientRect();
    const x = clamp((e.clientX - r.left) / Math.max(1, r.width), 0, 1) * 100;
    const y = clamp((e.clientY - r.top) / Math.max(1, r.height), 0, 1) * 100;
    el.style.setProperty('--mx', `${x.toFixed(2)}%`);
    el.style.setProperty('--my', `${y.toFixed(2)}%`);
    el.style.setProperty('--gvis', String(intensity));
  };
}

const AddMemoryPanel: React.FC<AddMemoryPanelProps> = ({
  graphId,
  onAddComplete,
}) => {
  const [text, setText] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [status, setStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState<string | null>(null);

  const graphReady = (graphId || '').startsWith('U:');
  const canSubmit = text.trim().length > 0 && !isSending && graphReady;

  const handleSubmit: React.FormEventHandler<HTMLFormElement> = async (e) => {
    e.preventDefault();
    if (!canSubmit) return;

    const payloadText = text.trim();
    if (!payloadText) return;

    setIsSending(true);
    setStatus('idle');
    setMessage(null);

    try {
      if (!graphReady) {
        throw new Error('Universe graph_id is not ready.');
      }

      const res = await fetch(
        `${API_BASE}/graphs/${encodeURIComponent(graphId)}/add`,
        {
          method: 'POST',
          headers: buildFaimHeaders({ "Content-Type": "application/json" }),
          body: JSON.stringify({ text: payloadText }),
        },
      );

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      let info: string | null = null;
      try {
        const body = (await res.json()) as AddResponse;
        if (typeof body.created_nodes === 'number') {
          info = `Added ${body.created_nodes} node${
            body.created_nodes === 1 ? '' : 's'
          } to FAIM.`;
        } else if (Array.isArray(body.node_ids)) {
          const n = body.node_ids.length;
          info = `Added ${n} node${n === 1 ? '' : 's'} to FAIM.`;
        }
      } catch {
        // ignore JSON parsing errors – we still treat it as success
      }

      setStatus('success');
      setMessage(info ?? 'Fragment added to FAIM memory.');
      setText('');

      if (onAddComplete) {
        onAddComplete();
      }
    } catch (err) {
      console.error('Error adding fragment to FAIM:', err);
      setStatus('error');
      setMessage(
        'Failed to add fragment. Check backend /graphs/{graph_id}/add endpoint.',
      );
    } finally {
      setIsSending(false);
    }
  };

  const charCount = text.length;

  return (
    <section
      onPointerMoveCapture={onStickyGlowMove(0.22)}
      onPointerLeave={() => {
        // sticky: do nothing
      }}
      style={
        {
          '--mx': '52%',
          '--my': '28%',
          '--gvis': '0',
        } as React.CSSProperties
      }
      className={[
        // base
        'group relative mb-3 overflow-hidden rounded-2xl border border-slate-800/70 bg-slate-950/55 p-3 text-xs',
        // neon cyan frame line
        'ring-1 ring-inset ring-cyan-500/10',
        // hover border pop
        'transition duration-200 hover:border-cyan-500/35',
        // depth
        'shadow-[0_0_0_1px_rgba(15,23,42,0.55),0_18px_70px_-40px_rgba(0,0,0,0.85)]',

        // pseudo glow layers must have content
        "before:content-[''] before:pointer-events-none before:absolute before:inset-0",
        "after:content-[''] after:pointer-events-none after:absolute after:inset-0",

        // sticky glow layers (controlled intensity)
        'before:[background:radial-gradient(620px_circle_at_var(--mx)_var(--my),rgba(34,211,238,0.11),transparent_66%)]',
        'before:opacity-[var(--gvis)]',
        'after:[background:radial-gradient(460px_circle_at_var(--mx)_var(--my),rgba(168,85,247,0.09),transparent_70%)]',
        'after:opacity-[var(--gvis)]',
      ].join(' ')}
    >
      {/* neon edge line */}
      <div className="pointer-events-none absolute inset-0 rounded-2xl border border-cyan-400/10" />

      <div className="relative z-[1]">
        <header className="mb-2 flex items-center justify-between gap-2">
          <div>
            <h2 className="text-xs font-semibold text-slate-100">
              Add text fragment
            </h2>
            <p className="text-[11px] text-slate-400">
              Type a small fragment and push it directly into FAIM as memory.
            </p>
          </div>
        </header>

        <form onSubmit={handleSubmit} className="space-y-2">
          <textarea
            className={[
              'h-20 w-full resize-none rounded-md border border-slate-800 bg-slate-900/80 px-2 py-1 text-xs text-slate-100',
              'placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-cyan-500/70',
              'transition duration-200 group-hover:border-cyan-500/25',
            ].join(' ')}
            placeholder="Example: This is a new FAIM memory about my project..."
            value={text}
            onChange={(e) => setText(e.target.value)}
          />

          <div className="flex items-center justify-between gap-2">
            <button
              type="submit"
              disabled={!canSubmit}
              className={[
                'rounded-md px-3 py-1 text-[11px] font-medium',
                'transition duration-200',
                canSubmit
                  ? 'bg-cyan-500 text-slate-950 hover:bg-cyan-400'
                  : 'bg-slate-700 text-slate-300 disabled:cursor-not-allowed',
              ].join(' ')}
            >
              {isSending ? 'Adding…' : 'Add to FAIM'}
            </button>

            <span className="text-[10px] text-slate-500">
              {charCount} character{charCount === 1 ? '' : 's'}
            </span>
          </div>
        </form>

        {message && (
          <p
            className={`mt-2 rounded-md px-2 py-1 text-[11px] ${
              status === 'success'
                ? 'border border-emerald-900/60 bg-emerald-950/60 text-emerald-200'
                : status === 'error'
                  ? 'border border-red-900/60 bg-red-950/60 text-red-100'
                  : 'text-slate-300'
            }`}
          >
            {message}
          </p>
        )}

        {!graphReady && (
          <p className="mt-2 text-[10px] text-amber-200/80">
            Waiting for your Universe ID (U:...) before adding memory.
          </p>
        )}

        <p className="mt-1 text-[10px] text-slate-500">
          Backend: POST{' '}
          <code className="font-mono text-[10px]">
            /graphs/{'{graph_id}'}/add
          </code>{' '}
          → <span className="font-mono text-[10px]">engine.add_memory</span>
        </p>
      </div>
    </section>
  );
};

export default AddMemoryPanel;
