/**
 * FIG View graph transform utilities — pure functions, no React, no side-effects.
 *
 * Provides client-side graph helpers for:
 *   - Adjacency maps from edges
 *   - Parent/child/neighbor lookups
 *   - Opposition edge filtering
 *   - BFS hop-distance computation
 *   - Search index construction + filtering
 *   - Next/previous relevant memory ordering
 *
 * All operations work on data already fetched from the backend.
 * No API calls made here.
 */

import type { FigEdge, FigNode } from "@/types/figView";
import { safeNodeTitle } from "@/lib/figViewSafety";

// ---------------------------------------------------------------------------
// Index helpers
// ---------------------------------------------------------------------------

/**
 * Build an O(1) lookup map from node_id to FigNode.
 */
export function buildNodeIndex(nodes: FigNode[]): Map<string, FigNode> {
  const map = new Map<string, FigNode>();
  for (const n of nodes) map.set(n.node_id, n);
  return map;
}

// ---------------------------------------------------------------------------
// Adjacency map
// ---------------------------------------------------------------------------

export type AdjacencyMap = {
  outgoing: Map<string, FigEdge[]>;
  incoming: Map<string, FigEdge[]>;
};

/**
 * Build adjacency maps from edges.
 * Preserves full edge objects so callers have weight/kind without a second lookup.
 */
export function buildAdjacency(edges: FigEdge[]): AdjacencyMap {
  const outgoing = new Map<string, FigEdge[]>();
  const incoming = new Map<string, FigEdge[]>();

  for (const e of edges) {
    if (!outgoing.has(e.src_node_id)) outgoing.set(e.src_node_id, []);
    outgoing.get(e.src_node_id)!.push(e);

    if (!incoming.has(e.dst_node_id)) incoming.set(e.dst_node_id, []);
    incoming.get(e.dst_node_id)!.push(e);
  }

  return { outgoing, incoming };
}

// ---------------------------------------------------------------------------
// Neighbor / parent / child lookups
// ---------------------------------------------------------------------------

/**
 * Return all distinct neighbor node IDs (both outgoing and incoming).
 */
export function getNeighborIds(nodeId: string, adj: AdjacencyMap): string[] {
  const seen = new Set<string>();
  for (const e of adj.outgoing.get(nodeId) ?? []) {
    if (e.dst_node_id !== nodeId) seen.add(e.dst_node_id);
  }
  for (const e of adj.incoming.get(nodeId) ?? []) {
    if (e.src_node_id !== nodeId) seen.add(e.src_node_id);
  }
  return Array.from(seen);
}

/**
 * Incoming node IDs (parents in a directed sense).
 */
export function getParentIds(nodeId: string, adj: AdjacencyMap): string[] {
  return (adj.incoming.get(nodeId) ?? [])
    .map((e) => e.src_node_id)
    .filter((id) => id !== nodeId);
}

/**
 * Outgoing node IDs (children in a directed sense).
 */
export function getChildIds(nodeId: string, adj: AdjacencyMap): string[] {
  return (adj.outgoing.get(nodeId) ?? [])
    .map((e) => e.dst_node_id)
    .filter((id) => id !== nodeId);
}

/**
 * All edges incident to a node (both directions).
 */
export function getEdgesBetween(nodeId: string, adj: AdjacencyMap): FigEdge[] {
  const seen = new Set<string>();
  const result: FigEdge[] = [];
  for (const e of [
    ...(adj.outgoing.get(nodeId) ?? []),
    ...(adj.incoming.get(nodeId) ?? []),
  ]) {
    if (!seen.has(e.edge_id)) {
      seen.add(e.edge_id);
      result.push(e);
    }
  }
  return result;
}

/**
 * All opposition edges incident to a node.
 */
export function getOppositionEdges(
  nodeId: string,
  adj: AdjacencyMap,
): FigEdge[] {
  return getEdgesBetween(nodeId, adj).filter((e) => e.kind === "opposition");
}

/**
 * All inheritance edges incident to a node.
 */
export function getInheritanceEdges(
  nodeId: string,
  adj: AdjacencyMap,
): FigEdge[] {
  return getEdgesBetween(nodeId, adj).filter((e) => e.kind === "inheritance");
}

// ---------------------------------------------------------------------------
// BFS hop distance (client-side fallback, undirected)
// ---------------------------------------------------------------------------

/**
 * Compute minimum hop distance between two nodes using BFS on the client-side
 * adjacency. This is a local fallback when explain endpoint hasn't been called.
 *
 * Returns null if no path exists within maxHops.
 */
export function computeGraphDistance(
  fromId: string,
  toId: string,
  adj: AdjacencyMap,
  maxHops: number = 8,
): number | null {
  if (fromId === toId) return 0;
  const visited = new Set<string>([fromId]);
  const queue: [string, number][] = [[fromId, 0]];
  while (queue.length > 0) {
    const [current, dist] = queue.shift()!;
    if (dist >= maxHops) continue;
    for (const neighbor of getNeighborIds(current, adj)) {
      if (neighbor === toId) return dist + 1;
      if (!visited.has(neighbor)) {
        visited.add(neighbor);
        queue.push([neighbor, dist + 1]);
      }
    }
  }
  return null;
}

// ---------------------------------------------------------------------------
// Search index
// ---------------------------------------------------------------------------

export type SearchIndexEntry = {
  node_id: string;
  title: string;
  kind: string;
  state: string;
};

/**
 * Build a flat searchable list from nodes.
 * Uses safeNodeTitle for display.
 */
export function buildSearchIndex(nodes: FigNode[]): SearchIndexEntry[] {
  return nodes.map((n) => ({
    node_id: n.node_id,
    title: safeNodeTitle(n),
    kind: n.kind,
    state: n.display?.state ?? "unknown",
  }));
}

/**
 * Filter search index by query string.
 * Case-insensitive substring match against title + kind.
 * Returns matching node_ids.
 */
export function filterNodesBySearch(
  index: SearchIndexEntry[],
  query: string,
): SearchIndexEntry[] {
  if (!query.trim()) return [];
  const q = query.trim().toLowerCase();
  return index.filter(
    (e) =>
      e.title.toLowerCase().includes(q) ||
      e.kind.toLowerCase().includes(q) ||
      e.node_id.toLowerCase().startsWith(q),
  );
}

// ---------------------------------------------------------------------------
// Next / previous relevant memory ordering
// ---------------------------------------------------------------------------

/**
 * Sort neighbor IDs by relevance for next/previous navigation.
 *
 * Ordering rules (per plan §6):
 *   1. Edge weight descending (stronger edges first)
 *   2. Tie-break: inheritance before opposition
 *   3. Tie-break: lexicographic node_id ascending
 *
 * Returns an ordered list of neighbor node_ids.
 */
export function getRelevantNeighborOrder(
  nodeId: string,
  adj: AdjacencyMap,
  nodeIndex: Map<string, FigNode>,
): string[] {
  const edges = getEdgesBetween(nodeId, adj);
  // Dedupe edges per neighbor — keep highest-weight edge for ranking
  const bestByNeighbor = new Map<string, FigEdge>();
  for (const e of edges) {
    const neighborId = e.src_node_id === nodeId ? e.dst_node_id : e.src_node_id;
    if (neighborId === nodeId) continue;
    const existing = bestByNeighbor.get(neighborId);
    if (!existing || e.weight > existing.weight) {
      bestByNeighbor.set(neighborId, e);
    }
  }

  const EDGE_KIND_PRIORITY: Record<string, number> = {
    inheritance: 0,
    opposition: 1,
  };

  return Array.from(bestByNeighbor.entries())
    .sort(([aId, aEdge], [bId, bEdge]) => {
      // 1. Weight descending
      if (bEdge.weight !== aEdge.weight) return bEdge.weight - aEdge.weight;
      // 2. Edge kind priority
      const ap = EDGE_KIND_PRIORITY[aEdge.kind] ?? 99;
      const bp = EDGE_KIND_PRIORITY[bEdge.kind] ?? 99;
      if (ap !== bp) return ap - bp;
      // 3. Lexicographic
      return aId.localeCompare(bId);
    })
    .map(([id]) => id)
    .filter((id) => nodeIndex.has(id));
}

/**
 * Get next neighbor node_id in the relevant order.
 * Returns null if none.
 */
export function getNextRelevantNode(
  currentNodeId: string,
  adj: AdjacencyMap,
  nodeIndex: Map<string, FigNode>,
): string | null {
  const order = getRelevantNeighborOrder(currentNodeId, adj, nodeIndex);
  return order.length > 0 ? order[0]! : null;
}

/**
 * Get previous neighbor node_id relative to a focused node in the sorted order.
 * "Previous" = navigate backward through the sorted neighbor list.
 * If no current focus, returns last in the order.
 */
export function getPrevRelevantNode(
  currentNodeId: string,
  fromNodeId: string,
  adj: AdjacencyMap,
  nodeIndex: Map<string, FigNode>,
): string | null {
  const order = getRelevantNeighborOrder(fromNodeId, adj, nodeIndex);
  const idx = order.indexOf(currentNodeId);
  if (idx <= 0) return order.length > 0 ? order[order.length - 1]! : null;
  return order[idx - 1]!;
}

/**
 * Get the highest-weight edge between a node and a specific neighbor.
 * Returns null if no edge exists between them.
 */
export function getBestEdgeToNeighbor(
  nodeId: string,
  neighborId: string,
  adj: AdjacencyMap,
): FigEdge | null {
  const edges = getEdgesBetween(nodeId, adj).filter(
    (e) => e.src_node_id === neighborId || e.dst_node_id === neighborId,
  );
  if (edges.length === 0) return null;
  return edges.reduce((best, e) => (e.weight > best.weight ? e : best));
}

// ---------------------------------------------------------------------------
// Scorecard Metrics — client-side computation
// ---------------------------------------------------------------------------

export type FigScorecard = {
  density: number; // 0-1: edges / (nodes × (nodes-1))
  entropy: number; // bits: Shannon entropy of edge kinds
  spectral_radius: number; // largest eigenvalue (via power iteration)
};

/**
 * D — Graph Density
 *
 * edges / (nodes × (nodes - 1))
 *
 * 0 = no connections (empty graph)
 * 1 = fully connected (complete graph)
 * 0.5 = half of all possible edges exist
 */
export function computeDensity(nodeCount: number, edgeCount: number): number {
  if (nodeCount < 2) return 0;
  const maxEdges = nodeCount * (nodeCount - 1);
  return edgeCount / maxEdges;
}

/**
 * H — Shannon Entropy of edge kinds
 *
 * H = -Σ (p_i × log2(p_i))
 *
 * where p_i = count_i / total_edges
 *
 * 0 = all edges are same kind (uniform)
 * High = many different edge kinds (diverse)
 *
 * Max entropy = log2(number_of_kinds)
 */
export function computeEntropy(edges: FigEdge[]): number {
  if (edges.length === 0) return 0;

  // Count edges by kind
  const kindCounts = new Map<string, number>();
  for (const e of edges) {
    kindCounts.set(e.kind, (kindCounts.get(e.kind) ?? 0) + 1);
  }

  // Shannon entropy: H = -Σ (p_i × log2(p_i))
  let entropy = 0;
  for (const count of Array.from(kindCounts.values())) {
    if (count === 0) continue;
    const p = count / edges.length;
    entropy -= p * Math.log2(p);
  }

  return entropy;
}

/**
 * λ — Spectral Radius (largest eigenvalue of adjacency matrix)
 *
 * Uses power iteration method: v_{k+1} = A × v_k / ||A × v_k||
 *
 * Interpretation:
 *   λ ≈ avg degree → sparse random-like graph
 *   λ > avg degree → strong community structure / clustering
 *   λ ↑ → graph is more tightly connected / organized
 *
 * Range: depends on graph, typically [1, max_degree]
 *
 * Convergence: ~20 iterations for good approximation
 */
export function computeSpectralRadius(
  nodes: FigNode[],
  edges: FigEdge[],
  maxIterations = 20,
): number {
  if (nodes.length === 0) return 0;

  // Build sparse adjacency list (undirected — both directions)
  const adj = new Map<string, string[]>();
  for (const node of nodes) {
    adj.set(node.node_id, []);
  }
  for (const edge of edges) {
    const src = adj.get(edge.src_node_id);
    const dst = adj.get(edge.dst_node_id);
    if (src && dst) {
      src.push(edge.dst_node_id);
      dst.push(edge.src_node_id); // Undirected
    }
  }

  // Power iteration: multiply by adjacency matrix repeatedly
  let vector = new Map(nodes.map((n) => [n.node_id, Math.random()]));

  for (let iter = 0; iter < maxIterations; iter++) {
    const nextVector = new Map<string, number>();

    // v_{k+1} = A × v_k
    for (const [nodeId, neighbors] of Array.from(adj)) {
      let sum = 0;
      for (const neighbor of neighbors) {
        sum += vector.get(neighbor) ?? 0;
      }
      nextVector.set(nodeId, sum);
    }

    // Normalize: v_k / ||v_k||
    let norm = 0;
    for (const v of Array.from(nextVector.values())) {
      norm += v * v;
    }
    norm = Math.sqrt(norm);

    if (norm > 1e-10) {
      for (const [k, v] of Array.from(nextVector)) {
        nextVector.set(k, v / norm);
      }
    }

    vector = nextVector;
  }

  // Rayleigh quotient: λ = v^T A v / (v^T v)
  // Approximates the dominant eigenvalue
  let numerator = 0;
  for (const edge of edges) {
    const vSrc = vector.get(edge.src_node_id) ?? 0;
    const vDst = vector.get(edge.dst_node_id) ?? 0;
    numerator += vSrc * vDst;
  }
  numerator *= 2; // Undirected: each edge contributes both directions

  let denominator = 0;
  for (const v of Array.from(vector.values())) {
    denominator += v * v;
  }

  return denominator > 1e-10 ? numerator / denominator : 0;
}

/**
 * Compute all scorecard metrics at once
 */
export function computeScorecard(
  nodes: FigNode[],
  edges: FigEdge[],
): FigScorecard {
  return {
    density: computeDensity(nodes.length, edges.length),
    entropy: computeEntropy(edges),
    spectral_radius: computeSpectralRadius(nodes, edges),
  };
}
