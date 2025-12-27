'use client';

import * as React from 'react';
import clsx from 'clsx';

function clamp(n: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, n));
}
function useGlowVars() {
  return React.useCallback((e: React.MouseEvent<HTMLElement>) => {
    const el = e.currentTarget as HTMLElement;
    const r = el.getBoundingClientRect();
    const x = clamp((e.clientX - r.left) / Math.max(r.width, 1), 0, 1);
    const y = clamp((e.clientY - r.top) / Math.max(r.height, 1), 0, 1);
    el.style.setProperty('--mx', `${(x * 100).toFixed(2)}%`);
    el.style.setProperty('--my', `${(y * 100).toFixed(2)}%`);
  }, []);
}

export type MemoryEventKind =
  | 'ingest'
  | 'evolve'
  | 'retain'
  | 'query'
  | 'merge'
  | 'metrics'
  | 'delta'
  | 'prune'
  | 'note';

export type SpeedTier = 'HOT' | 'WARM' | 'COLD' | 'MIXED';

export interface MemoryEvent {
  id: string;
  timestamp: string; // ISO string
  kind: MemoryEventKind;
  label: string;
  details?: string;
  cr?: number;
  redundancy?: number;
  drift?: number;
  speedTier?: SpeedTier;
}

interface MemoryTimelineProps {
  events: MemoryEvent[];
  className?: string;
}

function formatTime(iso: string) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

function kindBadge(kind: MemoryEventKind) {
  const base =
    'inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium';
  switch (kind) {
    case 'ingest':
      return `${base} border-cyan-500/30 bg-cyan-500/10 text-cyan-200`;
    case 'evolve':
      return `${base} border-purple-500/30 bg-purple-500/10 text-purple-200`;
    case 'retain':
      return `${base} border-emerald-500/30 bg-emerald-500/10 text-emerald-200`;
    case 'query':
      return `${base} border-slate-500/30 bg-slate-500/10 text-slate-200`;
    case 'merge':
      return `${base} border-amber-500/30 bg-amber-500/10 text-amber-200`;
    case 'metrics':
      return `${base} border-sky-500/30 bg-sky-500/10 text-sky-200`;
    default:
      return `${base} border-slate-500/30 bg-slate-500/10 text-slate-200`;
  }
}

function tierPill(tier?: SpeedTier) {
  if (!tier) return null;
  const base =
    'inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium';
  if (tier === 'HOT') return `${base} border-cyan-500/30 bg-cyan-500/10 text-cyan-200`;
  if (tier === 'WARM') return `${base} border-amber-500/30 bg-amber-500/10 text-amber-200`;
  if (tier === 'COLD') return `${base} border-slate-500/30 bg-slate-500/10 text-slate-200`;
  return `${base} border-purple-500/30 bg-purple-500/10 text-purple-200`;
}

export function MemoryTimeline({ events, className }: MemoryTimelineProps) {
  const onMove = useGlowVars();

  const sorted = [...events].sort((a, b) => {
    const ta = Date.parse(a.timestamp);
    const tb = Date.parse(b.timestamp);
    if (Number.isNaN(ta) || Number.isNaN(tb)) return 0;
    return tb - ta;
  });

  return (
    <section
      onMouseMove={onMove}
      className={clsx(
        'group h-full rounded-xl border border-slate-800 bg-slate-950/80 p-4 shadow-inner shadow-slate-900/60 transition duration-200 hover:border-cyan-500/35 hover:bg-slate-950/75',
        'flex flex-col gap-3',
        className
      )}
      style={{
        backgroundImage:
          'radial-gradient(520px 240px at var(--mx, 50%) var(--my, 50%), rgba(34,211,238,0.12), transparent 62%)',
      }}
    >
      <header className="flex items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-slate-100">
            Memory Timeline
          </h2>
          <p className="text-xs text-slate-400">
            Time-ordered view of FAIM activity (ingest, evolution, retention,
            queries).
          </p>
        </div>
        <span className="rounded-full bg-slate-800 px-2 py-1 text-[10px] text-slate-200">
          {sorted.length} event{sorted.length === 1 ? '' : 's'}
        </span>
      </header>

      {sorted.length === 0 ? (
        <p className="mt-2 text-xs text-slate-500">
          No activity recorded yet. As you ingest data, run evolution or ask
          questions, events will appear here with CR, redundancy, drift and speed
          tier.
        </p>
      ) : (
        <div className="flex-1 overflow-y-auto pr-1">
          <ol className="space-y-3">
            {sorted.map((ev) => (
              <li
                key={ev.id}
                className="rounded-xl border border-slate-800 bg-slate-950/70 p-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={kindBadge(ev.kind)}>{ev.kind}</span>
                      {ev.speedTier ? (
                        <span className={tierPill(ev.speedTier)!}>
                          {ev.speedTier}
                        </span>
                      ) : null}
                      <span className="text-[10px] text-slate-500">
                        {formatTime(ev.timestamp)}
                      </span>
                    </div>
                    <div className="mt-1 text-[12px] font-semibold text-slate-100">
                      {ev.label}
                    </div>
                    {ev.details ? (
                      <div className="mt-1 text-[11px] text-slate-400">
                        {ev.details}
                      </div>
                    ) : null}
                  </div>

                  <div className="shrink-0 text-right text-[10px] text-slate-400">
                    {typeof ev.cr === 'number' ? (
                      <div>CR {ev.cr.toFixed(2)}×</div>
                    ) : null}
                    {typeof ev.redundancy === 'number' ? (
                      <div>R {(ev.redundancy * 100).toFixed(2)}%</div>
                    ) : null}
                    {typeof ev.drift === 'number' ? (
                      <div>D {(ev.drift * 100).toFixed(2)}%</div>
                    ) : null}
                  </div>
                </div>

                <div className="relative mt-3 border-l border-slate-800 pl-3 text-[10px] text-slate-500">
                  <span className="absolute left-0 top-2.5 h-2 w-2 -translate-x-1/2 rounded-full bg-cyan-400" />
                  Event recorded
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}
    </section>
  );
}
