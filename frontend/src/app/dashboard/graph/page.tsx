'use client';

import { Suspense, useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { DEFAULT_GRAPH_ID, getUniverseGraphId } from '../../../lib/api';
import { useUserIds } from '../../../contexts/UserContext';

import { Graph3DView } from '../../../components/Graph3DView';
import { NodeInspector } from '../../../components/NodeInspector';
import GraphUploadPanel from '../../../components/graph/GraphUploadPanel';
import NodeRelationsPanel from '../../../components/NodeRelationsPanel';
import GraphAnalyticsPanel from '../../../components/graph/GraphAnalyticsPanel';
import AddMemoryPanel from '../../../components/graph/AddMemoryPanel';
import EvolutionPanel from '../../../components/EvolutionPanel';
import GraphFiltersPanel, { type FilterOptions } from '../../../components/GraphFiltersPanel';

const defaultGraphId =
  process.env.NEXT_PUBLIC_FAIM_DEFAULT_GRAPH_ID ?? DEFAULT_GRAPH_ID;

// Type for filtered graph data
interface FilteredGraphData {
  nodes: any[];
  links: any[];
}

// ✅ THIS inner component is allowed to use useSearchParams()
function GraphPageInner() {
  const searchParams = useSearchParams();
  const initialNodeId = searchParams.get('node');
  
  type RightPanelId =
    | 'add'
    | 'upload'
    | 'inspector'
    | 'relations'
    | 'analytics'
    | 'evolution'
    | 'filters'
    | 'none';

  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(
    initialNodeId,
  );
  const [rightPanel, setRightPanel] = useState<RightPanelId>('none');
  const [nodeDragEnabled, setNodeDragEnabled] = useState(true);
  
  // NEW: Filtered data state for the graph
  const [filteredData, setFilteredData] = useState<FilteredGraphData | null>(null);
  const [isFiltered, setIsFiltered] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    setSelectedNodeId(initialNodeId);
  }, [initialNodeId]);

  const { graphId: contextGraphId } = useUserIds();
  const [graphId, setGraphId] = useState<string>(defaultGraphId);

  // Sync graphId from UserContext (authoritative source)
  useEffect(() => {
    if (contextGraphId && contextGraphId.startsWith('U:')) {
      setGraphId(contextGraphId);
    } else {
      // Fallback: try storage
      const u = getUniverseGraphId();
      if (u.startsWith('U:')) setGraphId(u);
    }
  }, [contextGraphId]);

  // Handle storage events (for multi-tab sync)
  useEffect(() => {
     if (typeof window === 'undefined') return;
     const onStorage = (e: StorageEvent) => {
       if (!e.key) return;
       if (e.key.includes('graph_id')) {
         const u = getUniverseGraphId();
         if (u.startsWith('U:')) setGraphId(u);
       }
     };
     window.addEventListener('storage', onStorage);
     return () => window.removeEventListener('storage', onStorage);
  }, []);

  // Handle ingest complete - refresh the graph
  const handleIngestComplete = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  // Handle filter application - fetch filtered data and update graph
  const handleApplyFilters = useCallback(
    async (filters: FilterOptions) => {
      if (!filters.topic && !filters.dateFrom && !filters.dateTo && filters.minUsage === 0) {
        // No filters - clear filtered data
        setFilteredData(null);
        setIsFiltered(false);
        return;
      }

      try {
        const params = new URLSearchParams();
        if (filters.topic) params.set('topic', filters.topic);
        if (filters.dateFrom) params.set('date_from', filters.dateFrom);
        if (filters.dateTo) params.set('date_to', filters.dateTo);
        if (filters.minUsage > 0) params.set('min_usage', filters.minUsage.toString());
        if (filters.kind) params.set('kind', filters.kind);

        const res = await fetch(`/api/v1/graphs/${graphId}/filtered?${params.toString()}`);
        const data = await res.json();

        if (data.nodes && data.links) {
          setFilteredData({
            nodes: data.nodes,
            links: data.links,
          });
          setIsFiltered(true);
        }
      } catch (e) {
        console.error('Failed to apply filters:', e);
      }
    },
    [graphId],
  );

  // Handle evolution complete - refresh the graph
  const handleEvolutionComplete = useCallback(() => {
    // Clear any filters and refresh
    setFilteredData(null);
    setIsFiltered(false);
    setRefreshKey((k) => k + 1);
  }, []);

  const panelItems: Array<{ id: RightPanelId; label: string; title: string }> =
    [
      { id: 'inspector', label: 'Inspect', title: 'Node inspector' },
      { id: 'relations', label: 'Memory', title: 'Memory / Neighbors / Lineage' },
      { id: 'analytics', label: 'Analytics', title: 'Graph analytics' },
      { id: 'evolution', label: 'Evolve', title: 'Self-Evolution Engine' },
      { id: 'filters', label: 'Filter', title: 'Filter by Topic/Date' },
    ];

  return (
    <div className="relative flex h-full flex-col space-y-4 overflow-hidden rounded-2xl">
      {/* ===== VISUAL EFFECTS ONLY (STATIC, NO CURSOR FOLLOW, NO VIOLET CIRCLE) ===== */}
      <div className="pointer-events-none absolute inset-0 z-[1] overflow-hidden rounded-2xl">
        <div
          className="absolute inset-0 opacity-70"
          style={{
            background:
              'radial-gradient(900px 520px at 18% 12%, rgba(34,211,238,0.18), rgba(0,0,0,0) 60%),' +
              'radial-gradient(900px 520px at 88% 78%, rgba(59,130,246,0.14), rgba(0,0,0,0) 62%),' +
              'radial-gradient(700px 420px at 55% 35%, rgba(14,165,233,0.10), rgba(0,0,0,0) 58%)',
          }}
        />
        <div
          className="absolute inset-0 opacity-80"
          style={{
            background:
              'radial-gradient(1200px 800px at 50% 30%, rgba(0,0,0,0), rgba(0,0,0,0.58) 75%)',
            mixBlendMode: 'multiply',
          }}
        />
        <div
          className="absolute inset-0 opacity-[0.06]"
          style={{
            backgroundImage:
              'url("data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%27120%27 height=%27120%27%3E%3Cfilter id=%27n%27%3E%3CfeTurbulence type=%27fractalNoise%27 baseFrequency=%270.9%27 numOctaves=%272%27 stitchTiles=%27stitch%27/%3E%3C/filter%3E%3Crect width=%27120%27 height=%27120%27 filter=%27url(%23n)%27 opacity=%270.35%27/%3E%3C/svg%3E")',
          }}
        />
      </div>

      <header className="header-container relative z-[2] flex items-center justify-between">
        <div>
          <h1 className="text-sm font-semibold text-slate-100">
            FIG View
            {isFiltered && (
              <span className="ml-2 text-[10px] text-violet-400 font-normal">
                (Filtered)
              </span>
            )}
          </h1>
          <p className="text-xs text-slate-400">
            3D fractal inheritance graph on the left, upload + inspector + memory
            relations on the right.
          </p>
        </div>
        {isFiltered && (
          <button
            onClick={() => {
              setFilteredData(null);
              setIsFiltered(false);
            }}
            className="text-[10px] text-slate-400 hover:text-cyan-300 px-2 py-1 border border-slate-700 rounded"
          >
            Clear Filters
          </button>
        )}
      </header>

      <div className="relative z-[2] flex-1 overflow-hidden">
        <section className="relative flex min-h-[500px] max-h-[calc(100vh-140px)] h-[calc(100vh-190px)] overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60 ring-1 ring-inset ring-cyan-500/10">
          <Graph3DView
            key={refreshKey}
            onNodeSelect={setSelectedNodeId}
            graphId={graphId}
            enableNodeDrag={nodeDragEnabled}
            externalData={filteredData}
          />

          <div className="absolute right-4 top-4 z-20 flex flex-col gap-2">
            {panelItems.map((item) => {
              const active = rightPanel === item.id;
              const isFilterActive = item.id === 'filters' && isFiltered;
              return (
                <button
                  key={item.id}
                  type="button"
                  title={item.title}
                  onClick={() =>
                    setRightPanel((prev) => (prev === item.id ? 'none' : item.id))
                  }
                  className={[
                    'rounded-full border px-3 py-2 text-[10px] font-semibold uppercase tracking-widest',
                    active
                      ? 'border-cyan-400/40 bg-cyan-500/15 text-cyan-200'
                      : isFilterActive
                      ? 'border-violet-400/40 bg-violet-500/15 text-violet-200'
                      : 'border-slate-800/70 bg-slate-950/60 text-slate-300 hover:border-cyan-400/20 hover:bg-cyan-500/5',
                    'transition-all duration-150',
                  ].join(' ')}
                >
                  {item.label}
                  {isFilterActive && !active && (
                    <span className="ml-1 text-violet-400">●</span>
                  )}
                </button>
              );
            })}
            <button
              type="button"
              title="Toggle node drag"
              onClick={() => setNodeDragEnabled((prev) => !prev)}
              className={[
                'rounded-full border px-3 py-2 text-[10px] font-semibold uppercase tracking-widest',
                nodeDragEnabled
                  ? 'border-emerald-400/40 bg-emerald-500/15 text-emerald-200'
                  : 'border-slate-800/70 bg-slate-950/60 text-slate-300 hover:border-emerald-400/20 hover:bg-emerald-500/5',
                'transition-all duration-150',
              ].join(' ')}
            >
              Drag {nodeDragEnabled ? 'On' : 'Off'}
            </button>
          </div>

          {rightPanel !== 'none' && (
            <div className="absolute right-4 top-16 bottom-4 z-20 w-[380px] max-w-[92vw]">
              <div className="relative h-full overflow-hidden rounded-2xl border border-slate-800/70 bg-slate-950/75 shadow-[0_10px_40px_rgba(0,0,0,0.45)] backdrop-blur">
                <button
                  type="button"
                  title="Close panel"
                  onClick={() => setRightPanel('none')}
                  className="absolute right-2 top-2 rounded-md border border-slate-700/70 bg-slate-900/70 px-2 py-1 text-[10px] text-slate-300 hover:border-cyan-400/30 hover:text-cyan-200"
                >
                  Close
                </button>

                <div className="h-full overflow-auto p-2 pt-7">
                  {rightPanel === 'add' && <AddMemoryPanel graphId={graphId} />}
                  {rightPanel === 'upload' && (
                    <GraphUploadPanel
                      graphId={graphId}
                      onIngestComplete={handleIngestComplete}
                    />
                  )}
                  {rightPanel === 'inspector' && <NodeInspector nodeId={selectedNodeId} />}
                  {rightPanel === 'relations' && (
                    <NodeRelationsPanel nodeId={selectedNodeId} graphId={graphId} />
                  )}
                  {rightPanel === 'analytics' && <GraphAnalyticsPanel graphId={graphId} />}
                  {rightPanel === 'evolution' && (
                    <EvolutionPanel 
                      graphId={graphId} 
                      onEvolutionComplete={handleEvolutionComplete}
                    />
                  )}
                  {rightPanel === 'filters' && (
                    <GraphFiltersPanel 
                      graphId={graphId} 
                      onApplyFilters={handleApplyFilters}
                    />
                  )}
                </div>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

// ✅ Default export wraps it in Suspense (fixes build)
export default function GraphPage() {
  return (
    <Suspense
      fallback={<div className="p-4 text-xs text-slate-400">Loading graph…</div>}
    >
      <GraphPageInner />
    </Suspense>
  );
}
