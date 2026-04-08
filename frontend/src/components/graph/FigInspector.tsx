"use client";

/**
 * FIG View — Node Inspector Panel
 *
 * Full-detail panel for a selected graph node. Answers:
 *   "What is this node and why is it here?"
 *
 * Sections:
 *   1. Header (title, kind, state, pin, nav)
 *   2. Identity (node_id, level, vector_hash, deep link)
 *   3. Provenance (raw_id, block_id, storage link)
 *   4. Metrics (touch_count, residual, last_access)
 *   5. Parents
 *   6. Children
 *   7. Opposition/Conflict
 *   8. Explain Relation (when pinned node differs from selected)
 *
 * Safety:
 *   - No v_native vectors, no auth tokens, no cross-tenant identifiers
 *   - Deep links use /dashboard/storage and /api/v1/node — safe per contract §7
 *   - All display values from backend only
 */

import { useState } from "react";

import { Badge, Spinner } from "@/components/ui";
import {
  getChildIds,
  getOppositionEdges,
  getParentIds,
  getRelevantNeighborOrder,
  type AdjacencyMap,
} from "@/lib/figViewGraphTransform";
import { nodeColorByState } from "@/lib/figViewLayout";
import { nodeStateClass, safeNodeTitle } from "@/lib/figViewSafety";
import type { FigEdge, FigExplainResponse, FigNode, FigNodeDisplayState } from "@/types/figView";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type FigInspectorProps = {
  node: FigNode;
  graphId: string;
  allEdges: FigEdge[];
  nodeIndex: Map<string, FigNode>;
  adj: AdjacencyMap;
  pinnedNodeId: string | null;
  onPinToggle: (nodeId: string) => void;
  onNavigateToNode: (nodeId: string) => void;
  onRequestExplain: (fromNodeId: string, toNodeId: string) => void;
  explainResult: FigExplainResponse | null;
  explainLoading: boolean;
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SectionHeader({
  title,
  open,
  onToggle,
}: {
  title: string;
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      onClick={onToggle}
      className="flex w-full items-center justify-between py-1.5 text-[10px] font-semibold uppercase tracking-widest text-slate-400 hover:text-slate-200 transition-colors"
    >
      <span>{title}</span>
      <span className="text-slate-600">{open ? "▲" : "▼"}</span>
    </button>
  );
}

function CopyableValue({ value, label }: { value: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(value).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };
  return (
    <button
      onClick={handleCopy}
      title={`Copy ${label ?? "value"}`}
      className="flex items-center gap-1 font-mono text-[10px] text-slate-400 hover:text-cyan-300 transition-colors truncate max-w-full"
    >
      <span className="truncate">{value}</span>
      {copied && <span className="text-emerald-400 shrink-0">✓</span>}
    </button>
  );
}

function NodeRef({
  nodeId,
  nodeIndex,
  onNavigate,
}: {
  nodeId: string;
  nodeIndex: Map<string, FigNode>;
  onNavigate: (id: string) => void;
}) {
  const n = nodeIndex.get(nodeId);
  if (!n) return (
    <div className="flex items-center gap-2 rounded-md bg-slate-900/40 px-2 py-1.5 text-xs text-slate-500">
      <span className="font-mono">{nodeId.slice(0, 12)}…</span>
    </div>
  );
  const title = safeNodeTitle(n);
  const state = nodeStateClass(n) as FigNodeDisplayState;
  const color = nodeColorByState(state, false);
  return (
    <button
      onClick={() => onNavigate(nodeId)}
      className="flex w-full items-center justify-between gap-2 rounded-md bg-slate-900/40 border border-slate-800/60 px-2 py-1.5 text-xs hover:border-cyan-500/30 hover:bg-slate-900/70 transition-all"
    >
      <div className="flex items-center gap-2 min-w-0">
        <span className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: color }} />
        <span className="truncate text-slate-200 font-medium">{title}</span>
        <Badge size="sm" variant="outline">{n.kind}</Badge>
      </div>
      <span className="text-[9px] text-slate-500 shrink-0">→</span>
    </button>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function FigInspector({
  node,
  graphId,
  nodeIndex,
  adj,
  pinnedNodeId,
  onPinToggle,
  onNavigateToNode,
  onRequestExplain,
  explainResult,
  explainLoading,
}: FigInspectorProps) {
  const [sections, setSections] = useState<Record<string, boolean>>({
    identity: true,
    provenance: true,
    metrics: true,
    parents: true,
    children: false,
    opposition: true,
    explain: true,
  });
  const [showAllParents, setShowAllParents] = useState(false);
  const [showAllChildren, setShowAllChildren] = useState(false);

  const toggleSection = (key: string) =>
    setSections((prev) => ({ ...prev, [key]: !prev[key] }));

  const title = safeNodeTitle(node);
  const stateKey = nodeStateClass(node) as FigNodeDisplayState;
  const stateColor = nodeColorByState(stateKey, false);
  const isPinned = pinnedNodeId === node.node_id;

  const parentIds = getParentIds(node.node_id, adj);
  const childIds = getChildIds(node.node_id, adj);
  const oppositionEdges = getOppositionEdges(node.node_id, adj);
  const relevantOrder = getRelevantNeighborOrder(node.node_id, adj, nodeIndex);

  const shownParents = showAllParents ? parentIds : parentIds.slice(0, 5);
  const shownChildren = showAllChildren ? childIds : childIds.slice(0, 5);

  const pinnedNode = pinnedNodeId ? nodeIndex.get(pinnedNodeId) : null;
  const canExplain = pinnedNodeId && pinnedNodeId !== node.node_id;

  return (
    <div className="flex flex-col gap-0 text-xs">

      {/* ================================================================
          HEADER — title, state, pin, navigation
      ================================================================ */}
      <div className="mb-3 rounded-lg border border-slate-800/60 bg-slate-900/40 px-3 py-2.5">
        {/* Color strip */}
        <div className="mb-2 h-0.5 rounded-full" style={{ backgroundColor: stateColor }} />

        {/* Title + kind */}
        <div className="flex items-start justify-between gap-2">
          <p className="font-semibold text-slate-100 text-[13px] leading-tight truncate max-w-[200px]" title={title}>
            {title}
          </p>
          <button
            onClick={() => onPinToggle(node.node_id)}
            title={isPinned ? "Unpin node" : "Pin node for comparison"}
            className={`shrink-0 rounded-md px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-widest border transition-all ${
              isPinned
                ? "border-violet-400/50 bg-violet-500/20 text-violet-300"
                : "border-slate-700/60 text-slate-500 hover:border-cyan-400/30 hover:text-cyan-300"
            }`}
          >
            {isPinned ? "Pinned" : "Pin"}
          </button>
        </div>

        {/* Badges */}
        <div className="mt-1.5 flex flex-wrap gap-1">
          <Badge size="sm" variant="outline">{node.kind}</Badge>
          <span
            className="inline-flex items-center rounded-full px-2 py-0.5 text-[9px] font-semibold border"
            style={{ color: stateColor, borderColor: stateColor + "44" }}
          >
            {stateKey}
          </span>
          <Badge size="sm" variant="secondary">L{node.level}</Badge>
        </div>

        {/* Navigation row */}
        {relevantOrder.length > 0 && (
          <div className="mt-2 flex items-center gap-1 border-t border-slate-800/60 pt-2">
            <span className="text-[9px] text-slate-500 mr-1">Navigate:</span>
            {relevantOrder.slice(0, 3).map((nid) => {
              const n = nodeIndex.get(nid);
              if (!n) return null;
              return (
                <button
                  key={nid}
                  onClick={() => onNavigateToNode(nid)}
                  title={`Navigate to ${safeNodeTitle(n)}`}
                  className="rounded-md border border-slate-700/60 bg-slate-900/60 px-1.5 py-0.5 text-[9px] text-slate-400 hover:text-cyan-300 hover:border-cyan-400/30 transition-all truncate max-w-[70px]"
                >
                  {safeNodeTitle(n).slice(0, 12)}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* ================================================================
          IDENTITY
      ================================================================ */}
      <div className="border-t border-slate-800/40">
        <SectionHeader title="Identity" open={sections.identity} onToggle={() => toggleSection("identity")} />
        {sections.identity && (
          <div className="mb-3 space-y-1.5 pl-1">
            <div className="flex items-center justify-between">
              <span className="text-slate-500">node_id</span>
              <CopyableValue value={node.node_id} label="node_id" />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">kind</span>
              <span className="font-mono text-slate-300">{node.kind}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">level</span>
              <span className="font-mono text-slate-300">{node.level}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">vector_hash</span>
              <span className="font-mono text-[9px] text-slate-500">{(node.vector_hash ?? "").slice(0, 12)}…</span>
            </div>
            {/* Safe deep link — node detail API per contract §7 */}
            <a
              href={`/api/v1/node/${node.node_id}?graph_id=${encodeURIComponent(graphId)}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-[10px] text-cyan-600 hover:text-cyan-400 transition-colors"
            >
              <span>View node API</span>
              <span>↗</span>
            </a>
          </div>
        )}
      </div>

      {/* ================================================================
          PROVENANCE
      ================================================================ */}
      {(node.provenance?.raw_id || node.provenance?.block_id) && (
        <div className="border-t border-slate-800/40">
          <SectionHeader title="Provenance" open={sections.provenance} onToggle={() => toggleSection("provenance")} />
          {sections.provenance && (
            <div className="mb-3 space-y-1.5 pl-1">
              {node.provenance?.raw_id && (
                <div className="flex items-center justify-between gap-2">
                  <span className="text-slate-500 shrink-0">raw_id</span>
                  <CopyableValue value={node.provenance.raw_id} label="raw_id" />
                </div>
              )}
              {node.provenance?.block_id && (
                <div className="flex items-center justify-between gap-2">
                  <span className="text-slate-500 shrink-0">block_id</span>
                  <CopyableValue value={node.provenance.block_id} label="block_id" />
                </div>
              )}
              {/* Safe deep link to storage — per contract §7 */}
              {node.provenance?.raw_id && (
                <a
                  href={`/dashboard/storage`}
                  className="flex items-center gap-1 text-[10px] text-cyan-600 hover:text-cyan-400 transition-colors"
                  title="Open Storage page (filter manually by raw_id)"
                >
                  <span>Open Storage page</span>
                  <span>↗</span>
                </a>
              )}
            </div>
          )}
        </div>
      )}

      {/* ================================================================
          METRICS
      ================================================================ */}
      {node.metrics && (
        <div className="border-t border-slate-800/40">
          <SectionHeader title="Metrics" open={sections.metrics} onToggle={() => toggleSection("metrics")} />
          {sections.metrics && (
            <div className="mb-3 grid grid-cols-3 gap-2 pl-1">
              <div className="rounded-lg bg-slate-900/40 border border-slate-800/60 px-2 py-1.5 text-center">
                <p className="text-[9px] text-slate-500">touches</p>
                <p className="font-mono text-slate-200 font-semibold">{node.metrics.touch_count}</p>
              </div>
              <div className="rounded-lg bg-slate-900/40 border border-slate-800/60 px-2 py-1.5 text-center">
                <p className="text-[9px] text-slate-500">residual</p>
                <p className="font-mono text-slate-200 font-semibold">
                  {typeof node.metrics.residual === "number"
                    ? node.metrics.residual.toFixed(2)
                    : "—"}
                </p>
              </div>
              <div className="rounded-lg bg-slate-900/40 border border-slate-800/60 px-2 py-1.5 text-center">
                <p className="text-[9px] text-slate-500">last access</p>
                <p className="font-mono text-[9px] text-slate-300">
                  {node.metrics.last_access
                    ? new Date(node.metrics.last_access).toLocaleDateString()
                    : "—"}
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ================================================================
          PARENTS
      ================================================================ */}
      {parentIds.length > 0 && (
        <div className="border-t border-slate-800/40">
          <SectionHeader
            title={`Parents (${parentIds.length})`}
            open={sections.parents}
            onToggle={() => toggleSection("parents")}
          />
          {sections.parents && (
            <div className="mb-3 flex flex-col gap-1 pl-1">
              {shownParents.map((id) => (
                <NodeRef key={id} nodeId={id} nodeIndex={nodeIndex} onNavigate={onNavigateToNode} />
              ))}
              {parentIds.length > 5 && (
                <button
                  onClick={() => setShowAllParents((v) => !v)}
                  className="text-[10px] text-slate-500 hover:text-cyan-400 transition-colors"
                >
                  {showAllParents ? "Show less" : `+${parentIds.length - 5} more`}
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {/* ================================================================
          CHILDREN
      ================================================================ */}
      {childIds.length > 0 && (
        <div className="border-t border-slate-800/40">
          <SectionHeader
            title={`Children (${childIds.length})`}
            open={sections.children}
            onToggle={() => toggleSection("children")}
          />
          {sections.children && (
            <div className="mb-3 flex flex-col gap-1 pl-1">
              {shownChildren.map((id) => (
                <NodeRef key={id} nodeId={id} nodeIndex={nodeIndex} onNavigate={onNavigateToNode} />
              ))}
              {childIds.length > 5 && (
                <button
                  onClick={() => setShowAllChildren((v) => !v)}
                  className="text-[10px] text-slate-500 hover:text-cyan-400 transition-colors"
                >
                  {showAllChildren ? "Show less" : `+${childIds.length - 5} more`}
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {/* ================================================================
          OPPOSITION / CONFLICT
      ================================================================ */}
      {oppositionEdges.length > 0 && (
        <div className="border-t border-slate-800/40">
          <SectionHeader
            title={`Conflicts/Opposition (${oppositionEdges.length})`}
            open={sections.opposition}
            onToggle={() => toggleSection("opposition")}
          />
          {sections.opposition && (
            <div className="mb-3 flex flex-col gap-1 pl-1">
              {oppositionEdges.map((edge) => {
                const otherId = edge.src_node_id === node.node_id ? edge.dst_node_id : edge.src_node_id;
                return (
                  <div key={edge.edge_id} className="flex items-center justify-between gap-2 rounded-md bg-red-950/30 border border-red-900/30 px-2 py-1.5">
                    <button
                      onClick={() => onNavigateToNode(otherId)}
                      className="truncate text-red-300 hover:text-red-200 transition-colors text-left min-w-0"
                    >
                      {safeNodeTitle(nodeIndex.get(otherId) ?? { node_id: otherId, kind: "?", level: 0, vector_hash: "", display: { title: otherId.slice(0, 8), title_source: "node_id", state: "unknown" } })}
                    </button>
                    <span className="shrink-0 text-[9px] font-mono text-red-500">w:{edge.weight.toFixed(2)}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ================================================================
          EXPLAIN RELATION
      ================================================================ */}
      <div className="border-t border-slate-800/40">
        <SectionHeader title="Explain Relation" open={sections.explain} onToggle={() => toggleSection("explain")} />
        {sections.explain && (
          <div className="mb-3 pl-1">
            {!pinnedNodeId && (
              <p className="text-[10px] text-slate-500 italic">
                Pin a node first to explain the relation between it and this node.
              </p>
            )}
            {pinnedNodeId && pinnedNodeId === node.node_id && (
              <p className="text-[10px] text-slate-500 italic">
                Select a different node to explain the path from the pinned node.
              </p>
            )}
            {canExplain && (
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-[10px] text-slate-400">
                  <span className="text-violet-300 font-medium truncate max-w-[100px]">
                    {pinnedNode ? safeNodeTitle(pinnedNode) : pinnedNodeId!.slice(0, 8)}
                  </span>
                  <span>→</span>
                  <span className="text-cyan-300 font-medium truncate max-w-[100px]">{title}</span>
                </div>

                <button
                  onClick={() => onRequestExplain(pinnedNodeId!, node.node_id)}
                  disabled={explainLoading}
                  className="flex w-full items-center justify-center gap-2 rounded-md border border-cyan-500/30 bg-cyan-950/30 px-3 py-1.5 text-[11px] text-cyan-300 hover:bg-cyan-950/50 disabled:opacity-50 transition-all"
                >
                  {explainLoading ? (
                    <>
                      <Spinner size="sm" />
                      <span>Explaining…</span>
                    </>
                  ) : (
                    "Find Path"
                  )}
                </button>

                {explainResult && (
                  <div className="rounded-lg border border-slate-800/60 bg-slate-900/40 p-2.5 space-y-1.5">
                    <div className="flex items-center gap-1.5">
                      <span
                        className={`h-2 w-2 rounded-full ${explainResult.path_found ? "bg-emerald-400" : "bg-red-400"}`}
                      />
                      <span className="text-[10px] font-semibold text-slate-200">
                        {explainResult.path_found ? "Path found" : "No path found"}
                      </span>
                    </div>

                    {explainResult.path_found && (
                      <>
                        <p className="text-[10px] text-slate-400">{explainResult.explanation.summary}</p>
                        <div className="flex flex-wrap gap-1">
                          <Badge size="sm" variant="outline">
                            {explainResult.explanation.hops} hop{explainResult.explanation.hops !== 1 ? "s" : ""}
                          </Badge>
                          {explainResult.explanation.edge_kinds_used.map((k) => (
                            <Badge key={k} size="sm" variant="secondary">{k}</Badge>
                          ))}
                          {explainResult.explanation.relation_distance != null && (
                            <Badge size="sm" variant="outline">
                              dist: {explainResult.explanation.relation_distance}
                            </Badge>
                          )}
                        </div>
                        {explainResult.paths.map((path, i) => (
                          <div key={i} className="text-[9px] text-slate-500 font-mono">
                            {path.node_ids.map((id) => {
                              const n = nodeIndex.get(id);
                              return n ? safeNodeTitle(n).slice(0, 10) : id.slice(0, 8);
                            }).join(" → ")}
                          </div>
                        ))}
                      </>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

    </div>
  );
}
