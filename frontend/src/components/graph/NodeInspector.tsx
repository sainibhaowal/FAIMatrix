"use client";

import * as React from "react";
import { useEffect, useRef, useState } from "react";
import clsx from "clsx";
import { DEFAULT_GRAPH_ID, getUniverseGraphId } from "@/lib/api-client";
import { fetchNodeDetail } from "@/lib/api";
import { InheritanceChart } from "./InheritanceChart";

type InspectorMode = "A" | "B" | "C";
type ParentItem = { id: string; fraction?: number };
type ChildItem = { id: string; weight?: number };

interface NodeInspectorProps {
  nodeId: string | null;
  // NEW: support multiple selection
  nodeIds?: string[];
  graphId?: string;
}

// ----------------------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------------------

function clamp(n: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, n));
}

/**
 * Sticky glow vars for panel-level hover:
 * - Updates --mx/--my on mouse move
 * - Keeps last position (no reset on leave)
 * - Uses a controlled intensity (not too strong)
 */
function useStickyGlowVars(intensity = 0.28) {
  const ref = useRef<HTMLElement | null>(null);

  const onPointerMoveCapture = (e: React.PointerEvent<HTMLElement>) => {
    const el = ref.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const x = clamp((e.clientX - r.left) / Math.max(1, r.width), 0, 1) * 100;
    const y = clamp((e.clientY - r.top) / Math.max(1, r.height), 0, 1) * 100;
    el.style.setProperty("--mx", `${x.toFixed(2)}%`);
    el.style.setProperty("--my", `${y.toFixed(2)}%`);
    el.style.setProperty("--gvis", String(intensity));
  };

  const onPointerLeave = () => {
    // sticky: do nothing
  };

  return { ref, onPointerMoveCapture, onPointerLeave };
}

function buildNodeTooltip(node: any): string {
  const id = node.id ?? "(no id)";
  const label = node.label ?? node.name ?? "";
  const rawPayload: unknown =
    node.preview ??
    node.snippet ??
    node.payload ??
    node.text ??
    node.body ??
    "";

  let preview = "";
  if (rawPayload && typeof rawPayload === "string") {
    preview = rawPayload.split("\n").slice(0, 3).join(" ").trim();
    if (preview.length > 220) preview = preview.slice(0, 220) + "…";
  }

  const header = label ? `${label}\n${id}` : id;
  return preview ? `${header}\n\n${preview}` : header;
}

export function NodeInspector({ nodeId, nodeIds, graphId }: NodeInspectorProps) {
  const [detail, setDetail] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<InspectorMode>("B"); // default = Option B

  const effectiveGraphId = graphId ?? DEFAULT_GRAPH_ID;
  const glow = useStickyGlowVars(0.2);

  // Derive effective selection
  const selection = nodeIds && nodeIds.length > 0 ? nodeIds : (nodeId ? [nodeId] : []);
  const isMulti = selection.length > 1;
  const primaryId = selection.length > 0 ? selection[selection.length - 1] : null;

  useEffect(() => {
    if (!primaryId || isMulti) {
      setDetail(null);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);

    fetchNodeDetail(effectiveGraphId, primaryId)
      .then((d) => {
        setDetail(d);
        setError(null);
      })
      .catch((err) => {
        console.warn("fetchNodeDetail failed", err);
        setDetail(null);
        setError("Unable to load node detail.");
      })
      .finally(() => setLoading(false));
  }, [primaryId, isMulti, effectiveGraphId]);

  if (selection.length === 0) {
    return (
      <aside
        ref={glow.ref as React.RefObject<HTMLElement>}
        onPointerMoveCapture={glow.onPointerMoveCapture}
        onPointerLeave={glow.onPointerLeave}
        style={
          {
            "--mx": "55%",
            "--my": "22%",
            "--gvis": "0",
          } as React.CSSProperties
        }
        className={clsx(
          "h-full rounded-2xl border border-slate-800/70 bg-slate-950/55 p-4 text-xs text-slate-400",
          "ring-1 ring-inset ring-cyan-500/0",
          "shadow-[0_0_0_1px_rgba(15,23,42,0.55),0_18px_70px_-40px_rgba(0,0,0,0.85)]",
          "relative overflow-hidden before:content-[''] before:pointer-events-none before:absolute before:inset-0",
          "after:content-[''] after:pointer-events-none after:absolute after:inset-0",
          "before:[background:radial-gradient(620px_circle_at_var(--mx)_var(--my),rgba(34,211,238,0.11),transparent_66%)]",
          "before:opacity-[var(--gvis)]",
          "after:[background:radial-gradient(460px_circle_at_var(--mx)_var(--my),rgba(168,85,247,0.09),transparent_70%)]",
          "after:opacity-[var(--gvis)]",
        )}
      >
        <div className="pointer-events-none absolute inset-0 rounded-2xl border border-cyan-400/10" />
        <div className="relative z-[1]">
          <header className="mb-2 flex items-center justify-between gap-2">
            <div>
              <h2 className="text-xs font-semibold text-slate-100">
                Node inspector
              </h2>
              <p className="text-[11px] text-slate-400">
                Click a node in the FIG to inspect it here.
              </p>
            </div>
          </header>
          <p className="mt-4 text-[11px] text-slate-500">
             No node selected yet. Shift+Click to select multiple.
          </p>
        </div>
      </aside>
    );
  }

  // Multi-select View
  if (isMulti) {
    return (
      <aside
        className={clsx(
          "h-full rounded-2xl border border-slate-800/70 bg-slate-950/55 p-4 text-xs",
          "ring-1 ring-inset ring-cyan-500/10",
           "relative overflow-hidden"
        )}
      >
        <div className="pointer-events-none absolute inset-0 rounded-2xl border border-cyan-400/10" />
        <div className="relative z-[1] h-full flex flex-col">
          <header className="mb-3">
             <h2 className="text-xs font-semibold text-slate-100">
                Selection ({selection.length})
              </h2>
              <p className="text-[11px] text-slate-400">
                Multiple nodes selected.
              </p>
          </header>
          
          <div className="flex-1 overflow-y-auto space-y-1 pr-1">
             {selection.map(id => (
               <div key={id} className="flex items-center justify-between rounded border border-slate-800 bg-slate-900/40 px-2 py-1.5 text-[11px] text-slate-200">
                  <span className="truncate">{id}</span>
               </div>
             ))}
          </div>
          
          <div className="mt-3 pt-3 border-t border-slate-800">
             <p className="text-[10px] text-slate-500 text-center">Batch actions coming soon</p>
          </div>
        </div>
      </aside>
    );
  }

  return (
    <aside
      ref={glow.ref as React.RefObject<HTMLElement>}
      onPointerMoveCapture={glow.onPointerMoveCapture}
      onPointerLeave={glow.onPointerLeave}
      style={
        {
          "--mx": "55%",
          "--my": "30%",
          "--gvis": "0.35",
        } as React.CSSProperties
      }
      className={clsx(
        "h-full rounded-2xl border border-slate-800/70 bg-slate-950/55 p-4 text-xs",
        "ring-1 ring-inset ring-cyan-500/10",
        "shadow-[0_0_0_1px_rgba(15,23,42,0.55),0_18px_70px_-40px_rgba(0,0,0,0.85)]",
        "relative overflow-hidden before:content-[''] before:pointer-events-none before:absolute before:inset-0",
        "after:content-[''] after:pointer-events-none after:absolute after:inset-0",
        "before:[background:radial-gradient(620px_circle_at_var(--mx)_var(--my),rgba(34,211,238,0.11),transparent_66%)]",
        "before:opacity-[var(--gvis)]",
        "after:[background:radial-gradient(460px_circle_at_var(--mx)_var(--my),rgba(168,85,247,0.09),transparent_70%)]",
        "after:opacity-[var(--gvis)]",
      )}
    >
      <div className="pointer-events-none absolute inset-0 rounded-2xl border border-cyan-400/10" />

      <div className="relative z-[1]">
        <header className="mb-3 flex items-center justify-between gap-2">
          <div>
            <h2 className="text-xs font-semibold text-slate-100">
              Node inspector
            </h2>
            <p className="text-[11px] text-slate-400">
              Modes: A (minimal), B (default), C (advanced).
            </p>
          </div>
          <ModeToggle mode={mode} onChange={setMode} />
        </header>

        {loading && <p className="text-[11px] text-slate-400">Loading node…</p>}
        {error && <p className="text-[11px] text-rose-400">{error}</p>}
        {!loading && !error && !detail && (
          <p className="text-[11px] text-slate-400">
            No detail available for this node.
          </p>
        )}
        {!loading && !error && detail && (
          <NodeDetailBody detail={detail} mode={mode} />
        )}
      </div>
    </aside>
  );
}

function ModeToggle({
  mode,
  onChange,
}: {
  mode: InspectorMode;
  onChange: (m: InspectorMode) => void;
}) {
  const options: { label: string; value: InspectorMode; desc: string }[] = [
    { label: "A", value: "A", desc: "Minimal" },
    { label: "B", value: "B", desc: "Inspector" },
    { label: "C", value: "C", desc: "Advanced" },
  ];

  return (
    <div className="inline-flex items-center rounded-full border border-slate-700 bg-slate-900/80 p-0.5 text-[10px]">
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChange(opt.value)}
          className={clsx(
            "px-2 py-0.5 rounded-full transition",
            mode === opt.value
              ? "bg-cyan-500 text-slate-950"
              : "text-slate-300 hover:bg-slate-800",
          )}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

function NodeDetailBody({
  detail,
  mode,
}: {
  detail: any;
  mode: InspectorMode;
}) {
  const anyDetail = detail as any;

  const payload: string | undefined =
    (detail as any).payload ?? anyDetail.text ?? anyDetail.body ?? undefined;

  const shortPreview =
    payload && payload.length > 0
      ? payload.split("\n").slice(0, 3).join("\n")
      : undefined;

  // Parents / children / neighbors
  const parents: ParentItem[] =
    (anyDetail.parents as ParentItem[]) ??
    (anyDetail.lineage?.parents as ParentItem[]) ??
    (Array.isArray(anyDetail.inheritance)
      ? (
          anyDetail.inheritance as Array<{
            parent_id?: string;
            id?: string;
            weight?: unknown;
          }>
        )
          .map(
            (p): ParentItem => ({
              id: String(p.parent_id ?? p.id ?? ""),
              fraction: typeof p.weight === "number" ? p.weight : undefined,
            }),
          )
          .filter((x) => x.id)
      : []) ??
    (anyDetail.incoming as ParentItem[]) ??
    [];

  const children: ChildItem[] =
    (anyDetail.children as ChildItem[]) ??
    (anyDetail.neighbors?.outgoing as ChildItem[]) ??
    (anyDetail.outgoing as ChildItem[]) ??
    (Array.isArray(anyDetail.descendants)
      ? (
          anyDetail.descendants as Array<{
            node_id?: string;
            id?: string;
            weight?: unknown;
          }>
        )
          .map(
            (c): ChildItem => ({
              id: String(c.node_id ?? c.id ?? ""),
              weight: typeof c.weight === "number" ? c.weight : undefined,
            }),
          )
          .filter((x) => x.id)
      : []) ??
    [];

  const degree = (parents?.length ?? 0) + (children?.length ?? 0);

  // Advanced stats – all optional, we probe safely
  const vectorStats = anyDetail.vector_stats ?? anyDetail.vectorStats ?? null;
  const redundancyScore =
    anyDetail.redundancy_score ?? anyDetail.redundancyScore ?? null;
  const evolutionFlags: string[] =
    anyDetail.evolution_flags ??
    anyDetail.evolutionFlags ??
    anyDetail.flags ??
    [];
  const parentDistances =
    anyDetail.parent_distances ?? anyDetail.parentDistances ?? null;

  return (
    <div className="space-y-3 text-[11px] text-slate-100">
      <section>
        <h3 className="mb-1 text-[11px] font-semibold text-slate-200">Core</h3>
        <dl className="space-y-1">
          <div>
            <dt className="text-[10px] uppercase tracking-wide text-slate-500">
              ID
            </dt>
            <dd className="break-all text-[11px] text-slate-100">
              {anyDetail.node_id ?? anyDetail.id ?? "—"}
            </dd>
          </div>
          {anyDetail.merged_count !== undefined && anyDetail.merged_count > 0 && (
            <div className="flex items-center gap-2">
              <dt className="text-[10px] uppercase tracking-wide text-slate-500">
                Compressed
              </dt>
              <dd className="text-[11px] text-cyan-400 font-bold">
                {anyDetail.merged_count} memories
              </dd>
            </div>
          )}
          {detail.label && (
            <div>
              <dt className="text-[10px] uppercase tracking-wide text-slate-500">
                Label
              </dt>
              <dd className="text-[11px] text-slate-100">{detail.label}</dd>
            </div>
          )}
          {typeof (detail as any).score === "number" && (
            <div>
              <dt className="text-[10px] uppercase tracking-wide text-slate-500">
                Score
              </dt>
              <dd className="text-[11px] text-slate-100">
                {(detail as any).score.toFixed(3)}
              </dd>
            </div>
          )}
          {shortPreview && (
            <div>
              <dt className="text-[10px] uppercase tracking-wide text-slate-500">
                Preview
              </dt>
              <dd className="whitespace-pre-line text-[11px] text-slate-200">
                {shortPreview}
              </dd>
            </div>
          )}
        </dl>
      </section>

      {mode !== "A" && (
        <section className="border-t border-slate-800 pt-2">
          <h3 className="mb-1 text-[11px] font-semibold text-slate-200">
            Payload & parents
          </h3>
          {payload && (
            <div className="mb-2 rounded-md border border-slate-800 bg-slate-900/70 p-2 text-[11px] text-slate-100 max-h-40 overflow-y-auto">
              <div className="mb-1 text-[10px] uppercase tracking-wide text-slate-500">
                Full payload
              </div>
              <pre className="whitespace-pre-wrap text-[11px]">{payload}</pre>
            </div>
          )}

          {parents && parents.length > 0 && (
            <div className="mt-2">
              <div className="mb-1 text-[10px] uppercase tracking-wide text-purple-400 flex items-center gap-1">
                <span>🧬</span>
                <span>Fractal Inheritance</span>
              </div>
              
              <InheritanceChart parents={parents} />

              <ul className="mt-3 space-y-1">
                {parents.map((p: ParentItem) => {
                  // Color fraction badge based on weight
                  const frac = p.fraction ?? 0;
                  const fracColor = frac > 0.7 ? "bg-purple-500/30 text-purple-200" 
                    : frac > 0.3 ? "bg-cyan-500/20 text-cyan-300" 
                    : "bg-slate-700 text-slate-400";
                  return (
                    <li
                      key={p.id}
                      className="flex items-center justify-between gap-2"
                    >
                      <span className="truncate text-[11px] text-slate-100">
                        {p.id.slice(0, 20)}...
                      </span>
                      {typeof p.fraction === "number" && (
                        <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium ${fracColor}`}>
                          {(p.fraction * 100).toFixed(0)}%
                        </span>
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </section>
      )}

      {mode === "C" && (
        <section className="border-t border-slate-800 pt-2 space-y-2">
          <h3 className="text-[11px] font-semibold text-slate-200">Advanced</h3>

          <div className="grid grid-cols-2 gap-2">
            <div className="rounded-md border border-slate-800 bg-slate-900/70 p-2">
              <div className="text-[10px] uppercase tracking-wide text-slate-500">
                Degree
              </div>
              <div className="mt-1 text-[11px] text-slate-100">{degree}</div>
            </div>
            {redundancyScore !== null && (
              <div className="rounded-md border border-amber-500/20 bg-amber-500/5 p-2">
                <div className="text-[10px] uppercase tracking-wide text-amber-400 flex items-center gap-1">
                  <span>⚡</span>
                  <span>Opposition Score</span>
                </div>
                <div className="mt-1 text-[11px] text-amber-200">
                  {(Number(redundancyScore) * 100).toFixed(1)}%
                </div>
              </div>
            )}
            {/* Novelty Indicator - FAIM Self-Inventing Memory */}
            {anyDetail.novelty !== undefined && anyDetail.novelty !== null && (
              <div className="rounded-md border border-emerald-500/20 bg-emerald-500/5 p-2">
                <div className="text-[10px] uppercase tracking-wide text-emerald-400 flex items-center gap-1">
                  <span>✨</span>
                  <span>Δ Novelty</span>
                </div>
                <div className="mt-1 text-[11px] text-emerald-200">
                  {(Number(anyDetail.novelty) * 100).toFixed(0)}%
                </div>
              </div>
            )}
            {/* Inherited indicator */}
            {anyDetail.inherited !== undefined && anyDetail.inherited !== null && (
              <div className="rounded-md border border-purple-500/20 bg-purple-500/5 p-2">
                <div className="text-[10px] uppercase tracking-wide text-purple-400 flex items-center gap-1">
                  <span>🧬</span>
                  <span>Inherited</span>
                </div>
                <div className="mt-1 text-[11px] text-purple-200">
                  {(Number(anyDetail.inherited) * 100).toFixed(0)}%
                </div>
              </div>
            )}
          </div>

          {/* Evolution Flags - FAIM Self-Evolution Status */}
          {evolutionFlags && evolutionFlags.length > 0 && (
            <div className="rounded-md border border-cyan-500/20 bg-cyan-500/5 p-2">
              <div className="mb-1 text-[10px] uppercase tracking-wide text-cyan-400 flex items-center gap-1">
                <span>🔄</span>
                <span>Evolution Flags</span>
              </div>
              <div className="flex flex-wrap gap-1">
                {evolutionFlags.map((flag: string, idx: number) => (
                  <span 
                    key={idx}
                    className="rounded-full bg-cyan-500/20 px-2 py-0.5 text-[9px] text-cyan-200"
                  >
                    {flag}
                  </span>
                ))}
              </div>
            </div>
          )}

          {children && children.length > 0 && (
            <div>
              <div className="mb-1 text-[10px] uppercase tracking-wide text-slate-500">
                Children
              </div>
              <ul className="max-h-24 space-y-1 overflow-y-auto">
                {children.map((c: ChildItem) => (
                  <li
                    key={c.id}
                    className="flex items-center justify-between gap-2"
                  >
                    <span className="truncate text-[11px] text-slate-100">
                      {c.id}
                    </span>
                    {typeof c.weight === "number" && (
                      <span className="shrink-0 rounded-full bg-slate-800 px-2 py-0.5 text-[10px] text-slate-300">
                        {c.weight.toFixed(3)}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {vectorStats && (
            <div className="rounded-md border border-slate-800 bg-slate-900/70 p-2">
              <div className="mb-1 text-[10px] uppercase tracking-wide text-slate-500">
                Vector stats
              </div>
              <dl className="grid grid-cols-3 gap-2 text-[10px] text-slate-200">
                {"norm" in vectorStats && (
                  <div>
                    <dt className="text-slate-500">norm</dt>
                    <dd>{Number(vectorStats.norm).toFixed(3)}</dd>
                  </div>
                )}
                {"mean" in vectorStats && (
                  <div>
                    <dt className="text-slate-500">mean</dt>
                    <dd>{Number(vectorStats.mean).toFixed(3)}</dd>
                  </div>
                )}
                {"std" in vectorStats && (
                  <div>
                    <dt className="text-slate-500">std</dt>
                    <dd>{Number(vectorStats.std).toFixed(3)}</dd>
                  </div>
                )}
                {"min" in vectorStats && (
                  <div>
                    <dt className="text-slate-500">min</dt>
                    <dd>{Number(vectorStats.min).toFixed(3)}</dd>
                  </div>
                )}
                {"max" in vectorStats && (
                  <div>
                    <dt className="text-slate-500">max</dt>
                    <dd>{Number(vectorStats.max).toFixed(3)}</dd>
                  </div>
                )}
              </dl>
            </div>
          )}

          {Array.isArray(evolutionFlags) && evolutionFlags.length > 0 && (
            <div>
              <div className="mb-1 text-[10px] uppercase tracking-wide text-slate-500">
                Evolution flags
              </div>
              <div className="flex flex-wrap gap-1">
                {evolutionFlags.map((flag: string) => (
                  <span
                    key={flag}
                    className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] text-slate-200"
                  >
                    {flag}
                  </span>
                ))}
              </div>
            </div>
          )}

          {parentDistances && (
            <div>
              <div className="mb-1 text-[10px] uppercase tracking-wide text-slate-500">
                Parent distances
              </div>
              <pre className="max-h-20 overflow-y-auto whitespace-pre-wrap rounded-md bg-slate-900/80 p-2 text-[10px] text-slate-200">
                {JSON.stringify(parentDistances, null, 2)}
              </pre>
            </div>
          )}
        </section>
      )}
    </div>
  );
}

export default NodeInspector;
