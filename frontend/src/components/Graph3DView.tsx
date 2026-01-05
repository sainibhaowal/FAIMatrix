"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import type { CSSProperties, MouseEvent } from "react";

import { useFaimStream, type FigDelta } from "@/lib/realtime";
import {
  DEFAULT_GRAPH_ID,
  fetchNodeScan,
  fetchNodeSubgraph,
  fetchSubgraph,
  getUniverseGraphId,
} from "@/lib/api";

/**
 * NOTE:
 * - next/dynamic() LoadableComponent does NOT forward refs reliably.
 * - Do NOT pass ref to ForceGraph3D.
 * - Size it via width/height props from ResizeObserver.
 */
const ForceGraph3D = dynamic(() => import("react-force-graph-3d"), {
  ssr: false,
});

type Graph3DViewProps = {
  onNodeSelect(nodeId: string | null): void;
  graphId?: string | null;
  enableNodeDrag?: boolean;
  /** External data to display (e.g., from filters). Overrides internal fetch. */
  externalData?: { nodes: any[]; links: any[] } | null;
  /** Callback when graph data is refreshed */
  onDataRefresh?: () => void;
};

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
  const ref = useRef<HTMLDivElement | null>(null);

  const onMouseMove = (e: MouseEvent<HTMLDivElement>) => {
    const el = ref.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const x = clamp((e.clientX - r.left) / Math.max(1, r.width), 0, 1) * 100;
    const y = clamp((e.clientY - r.top) / Math.max(1, r.height), 0, 1) * 100;
    el.style.setProperty("--mx", `${x.toFixed(2)}%`);
    el.style.setProperty("--my", `${y.toFixed(2)}%`);
    el.style.setProperty("--gvis", String(intensity));
  };

  const onMouseLeave = () => {
    // sticky: do nothing
  };

  return { ref, onMouseMove, onMouseLeave };
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

type GraphData = { nodes: any[]; links: any[] };

export function Graph3DView({
  onNodeSelect,
  graphId: propGraphId,
  enableNodeDrag,
  externalData,
  onDataRefresh,
}: Graph3DViewProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  const dataRef = useRef<GraphData>({ nodes: [], links: [] });

  // Force a rerender after applying deltas (throttled by RAF)
  const [, bump] = useState(0);
  const rafRef = useRef<number | null>(null);

  const glow = useStickyGlowVars(0.26);

  // Size state (drives ForceGraph props) — avoids ref + avoids fg.width() crash
  const [size, setSize] = useState<{ w: number; h: number }>({
    w: 300,
    h: 300,
  });

  // Universe-first graphId (avoid localStorage during initial render)
  const [graphId, setGraphId] = useState<string>(() => {
    const p = (propGraphId ?? "").trim();
    return p.startsWith("U:") ? p : DEFAULT_GRAPH_ID;
  });

  const normalizeGraphData = (g: GraphData) => {
    if (!g?.nodes || !g?.links) return;

    const nodes = g.nodes;
    const links = g.links;
    const nodeById = new Map<string, any>();

    for (let i = 0; i < nodes.length; i += 1) {
      const n = nodes[i];
      if (n && typeof n === "object") {
        const rawId = (n as any).id ?? (n as any).node_id ?? "";
        const id = String(rawId);
        if (!id) continue;
        if ((n as any).id !== id) (n as any).id = id;
        nodeById.set(id, n);
      } else if (typeof n === "string" || typeof n === "number") {
        const id = String(n);
        if (!id) continue;
        const nn = { id };
        nodes[i] = nn;
        nodeById.set(id, nn);
      }
    }

    for (const l of links) {
      const srcObj = (l as any).source;
      const tgtObj = (l as any).target;

      const srcId =
        srcObj && typeof srcObj === "object"
          ? String((srcObj as any).id ?? (srcObj as any).node_id ?? "")
          : String(srcObj ?? "");
      const tgtId =
        tgtObj && typeof tgtObj === "object"
          ? String((tgtObj as any).id ?? (tgtObj as any).node_id ?? "")
          : String(tgtObj ?? "");

      if (srcId && !nodeById.has(srcId)) {
        const nn =
          srcObj && typeof srcObj === "object" ? srcObj : { id: srcId };
        nodes.push(nn);
        nodeById.set(srcId, nn);
      }
      if (tgtId && !nodeById.has(tgtId)) {
        const nn =
          tgtObj && typeof tgtObj === "object" ? tgtObj : { id: tgtId };
        nodes.push(nn);
        nodeById.set(tgtId, nn);
      }

      if (!(srcObj && typeof srcObj === "object") && srcId)
        (l as any).source = srcId;
      if (!(tgtObj && typeof tgtObj === "object") && tgtId)
        (l as any).target = tgtId;
    }
  };

  const ensureTetherLinks = (g: GraphData) => {
    if (!g.nodes?.length) return;

    const degree = new Map<string, number>();
    const linkKey = new Set<string>();

    for (const n of g.nodes) {
      const id = String(n?.id ?? "");
      if (id) degree.set(id, 0);
    }

    for (const l of g.links || []) {
      const s = String((l as any).source?.id ?? (l as any).source ?? "");
      const t = String((l as any).target?.id ?? (l as any).target ?? "");
      if (!s || !t) continue;
      linkKey.add(`${s}->${t}`);
      linkKey.add(`${t}->${s}`);
      if (degree.has(s)) degree.set(s, (degree.get(s) ?? 0) + 1);
      if (degree.has(t)) degree.set(t, (degree.get(t) ?? 0) + 1);
    }

    const ids = g.nodes.map((n) => String(n?.id ?? "")).filter(Boolean);
    if (ids.length <= 1) return;

    for (let i = 0; i < ids.length; i += 1) {
      const id = ids[i];
      if ((degree.get(id) ?? 0) > 0) continue;

      const target = i > 0 ? ids[i - 1] : ids[i + 1];
      if (!target || target === id) continue;
      if (linkKey.has(`${id}->${target}`)) continue;

      g.links.push({ source: id, target, rel: "tether", weight: 0.05 });
      linkKey.add(`${id}->${target}`);
      linkKey.add(`${target}->${id}`);
      degree.set(id, (degree.get(id) ?? 0) + 1);
      degree.set(target, (degree.get(target) ?? 0) + 1);
    }
  };

  // Sync from prop changes
  useEffect(() => {
    const p = (propGraphId ?? "").trim();
    if (!p.startsWith("U:")) return;
    setGraphId((prev) => (p !== prev ? p : prev));
  }, [propGraphId]);

  // Keep in sync if another component writes the Universe key
  useEffect(() => {
    if (typeof window === "undefined") return;

    const syncUniverse = () => {
      const u = getUniverseGraphId();
      if (u && u.startsWith("U:")) {
        setGraphId((prev) => (u !== prev ? u : prev));
      }
    };

    syncUniverse();

    const onStorage = (e: StorageEvent) => {
      if (!e.key) return;
      if (
        e.key === "faim.universe_graph_id" ||
        e.key === "faim_universe_graph_id" ||
        e.key === "faim_graph_id" ||
        e.key === "faim_entry_graph_id"
      ) {
        syncUniverse();
      }
    };

    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  // Cleanup RAF
  useEffect(() => {
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  // Apply external data (from filters) when provided
  useEffect(() => {
    if (externalData && externalData.nodes && externalData.nodes.length > 0) {
      dataRef.current = {
        nodes: [...externalData.nodes],
        links: [...(externalData.links || [])],
      };
      normalizeGraphData(dataRef.current);
      ensureTetherLinks(dataRef.current);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      rafRef.current = requestAnimationFrame(() => bump((x) => x + 1));
    }
  }, [externalData]);

  // Auto-size to container via ResizeObserver -> width/height props
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    let raf: number | null = null;

    const apply = () => {
      const w = Math.max(1, el.clientWidth);
      const h = Math.max(1, el.clientHeight);
      setSize((prev) => (prev.w === w && prev.h === h ? prev : { w, h }));
    };

    apply();

    const ro = new ResizeObserver(() => {
      if (raf) cancelAnimationFrame(raf);
      raf = requestAnimationFrame(apply);
    });

    ro.observe(el);

    return () => {
      if (raf) cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, []);

  // Realtime deltas
  useFaimStream(graphId, {
    onFigDelta: (d: FigDelta) => {
      if (d.graph_id && d.graph_id !== graphId) return;

      const g = dataRef.current;
      const dd = d.delta;

      const nodeById = new Map<string, any>(
        g.nodes.map((n) => [String(n.id), n]),
      );
      const linkByKey = new Map<string, any>();

      for (const l of g.links) {
        const s = String((l.source as any)?.id ?? l.source);
        const t = String((l.target as any)?.id ?? l.target);
        linkByKey.set(`${s}->${t}`, l);
      }

      dd.nodes_added?.forEach((n) => {
        const k = String(n.id);
        if (!nodeById.has(k)) {
          const nn = { id: n.id };
          g.nodes.push(nn);
          nodeById.set(k, nn);
        }
      });

      if (dd.nodes_removed?.length) {
        const del = new Set(dd.nodes_removed.map((x) => String(x.id)));

        g.nodes = g.nodes.filter((n) => !del.has(String(n.id)));
        g.links = g.links.filter((l) => {
          const s = String((l.source as any)?.id ?? l.source);
          const t = String((l.target as any)?.id ?? l.target);
          return !(del.has(s) || del.has(t));
        });

        nodeById.clear();
        for (const n of g.nodes) nodeById.set(String(n.id), n);

        linkByKey.clear();
        for (const l of g.links) {
          const s = String((l.source as any)?.id ?? l.source);
          const t = String((l.target as any)?.id ?? l.target);
          linkByKey.set(`${s}->${t}`, l);
        }
      }

      dd.links_added?.forEach((l) => {
        const src = String(l.source);
        const tgt = String(l.target);

        if (!nodeById.has(src)) {
          const nn = { id: src };
          g.nodes.push(nn);
          nodeById.set(src, nn);
        }
        if (!nodeById.has(tgt)) {
          const nn = { id: tgt };
          g.nodes.push(nn);
          nodeById.set(tgt, nn);
        }

        const key = `${src}->${tgt}`;
        if (!linkByKey.has(key)) {
          const ll = { source: src, target: tgt };
          g.links.push(ll);
          linkByKey.set(key, ll);
        }
      });

      if (dd.links_removed?.length) {
        const del = new Set(
          dd.links_removed.map(
            (x) => `${String(x.source)}->${String(x.target)}`,
          ),
        );

        g.links = g.links.filter((l) => {
          const key = `${String((l.source as any)?.id ?? l.source)}->${String(
            (l.target as any)?.id ?? l.target,
          )}`;
          return !del.has(key);
        });
      }

      dataRef.current = g;
      normalizeGraphData(dataRef.current);
      ensureTetherLinks(dataRef.current);

      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      rafRef.current = requestAnimationFrame(() => bump((x) => x + 1));
    },
  });

  const graphData = dataRef.current;

  // Load initial graph snapshot so FIG isn't empty before deltas arrive.
  useEffect(() => {
    let alive = true;

    const load = async () => {
      const u = graphId?.startsWith("U:") ? graphId : getUniverseGraphId();
      if (!u || !u.startsWith("U:")) return;

      try {
        const res = await fetchSubgraph(u);
        if (!alive) return;
        const nodes = Array.isArray(res.nodes) ? res.nodes : [];
        const links = Array.isArray(res.links) ? res.links : [];
        if (nodes.length > 0) {
          dataRef.current = { nodes, links };
          normalizeGraphData(dataRef.current);
          ensureTetherLinks(dataRef.current);
          if (rafRef.current) cancelAnimationFrame(rafRef.current);
          rafRef.current = requestAnimationFrame(() => bump((x) => x + 1));
          return;
        }
      } catch {
        // fall through to alternate loaders
      }

      try {
        const list = await fetchNodeScan(u, 250);
        if (!alive) return;
        const nodes = Array.isArray(list) ? list : [];
        const baseNodes = nodes.map((n) => ({
          id: n.id,
          degree: n.degree ?? undefined,
        }));

        if (baseNodes.length > 0) {
          dataRef.current = { nodes: baseNodes, links: [] };
          normalizeGraphData(dataRef.current);
          ensureTetherLinks(dataRef.current);
          if (rafRef.current) cancelAnimationFrame(rafRef.current);
          rafRef.current = requestAnimationFrame(() => bump((x) => x + 1));
        }

        const seed = nodes[0]?.id;
        if (seed) {
          try {
            const res = await fetchNodeSubgraph(u, seed, 2);
            if (!alive) return;

            const subNodes = Array.isArray(res.nodes) ? res.nodes : [];
            const subLinks = Array.isArray(res.links) ? res.links : [];

            if (subLinks.length > 0 || subNodes.length > 1) {
              const nodeMap = new Map<string, any>(
                baseNodes.map((n) => [String(n.id), n]),
              );
              for (const n of subNodes) {
                const id = String((n as any).id);
                if (!nodeMap.has(id)) nodeMap.set(id, n);
                else nodeMap.set(id, { ...nodeMap.get(id), ...n });
              }

              dataRef.current = {
                nodes: Array.from(nodeMap.values()),
                links: subLinks,
              };
              normalizeGraphData(dataRef.current);
              ensureTetherLinks(dataRef.current);
              if (rafRef.current) cancelAnimationFrame(rafRef.current);
              rafRef.current = requestAnimationFrame(() => bump((x) => x + 1));
            }
          } catch {
            // keep nodes-only fallback
          }
        }
      } catch {
        // ignore: SSE deltas may populate later
      }
    };

    load();

    return () => {
      alive = false;
    };
  }, [graphId]);

  return (
    <div
      ref={glow.ref}
      onMouseMove={glow.onMouseMove}
      onMouseLeave={glow.onMouseLeave}
      style={
        {
          "--mx": "55%",
          "--my": "28%",
          "--gvis": "0",
        } as CSSProperties
      }
      className={[
        "group relative h-full w-full overflow-hidden rounded-2xl",
        "bg-slate-950/45",
        "shadow-[0_18px_70px_-36px_rgba(0,0,0,0.85)]",
        "before:pointer-events-none before:absolute before:inset-0 before:opacity-0 before:transition-opacity before:duration-200",
        "before:[background:radial-gradient(720px_circle_at_var(--mx)_var(--my),rgba(34,211,238,0.12),transparent_64%)]",
        "before:opacity-[var(--gvis)]",
        "after:pointer-events-none after:absolute after:inset-0 after:opacity-0 after:transition-opacity after:duration-200",
        "after:[background:radial-gradient(520px_circle_at_var(--mx)_var(--my),rgba(168,85,247,0.10),transparent_66%)]",
        "after:opacity-[var(--gvis)]",
      ].join(" ")}
    >
      <div className="pointer-events-none absolute inset-0 overflow-hidden rounded-2xl [mask-image:linear-gradient(to_bottom,black,transparent_18%,black)]">
        <div className="absolute inset-0 bg-gradient-to-r from-cyan-400/6 via-transparent to-purple-400/6" />
      </div>

      <div
        ref={containerRef}
        className="relative z-[1] h-full w-full overflow-hidden rounded-2xl"
      >
        {/* @ts-ignore */}
        <ForceGraph3D
          width={size.w}
          height={size.h}
          graphData={graphData}
          nodeLabel={buildNodeTooltip}
          nodeAutoColorBy="group"
          enableNodeDrag={enableNodeDrag ?? true}
          linkOpacity={0.35}
          linkWidth={(l: any) =>
            l.rel === "tether" ? 0.2 : (l.weight ?? 1) * 0.5
          }
          onNodeClick={(node: any) => onNodeSelect(node?.id ?? null)}
        />
      </div>
    </div>
  );
}
