/**
 * FIG View safety utilities.
 *
 * - Safe node-title fallback (client-side, mirrors backend, never fabricates)
 * - Graph-state local persistence with tenant/version guards
 */

import type { FigNode } from "@/types/figView";

// ---------------------------------------------------------------------------
// Safe Node Title
// ---------------------------------------------------------------------------

/**
 * Return the safest display title for a node.
 *
 * Uses backend-computed `display.title` as primary source.
 * Only falls back to a synthetic label when the backend field is empty,
 * and never invents semantic meaning.
 */
export function safeNodeTitle(node: FigNode): string {
  const backendTitle = node.display?.title;
  if (backendTitle && backendTitle.trim()) return backendTitle.trim();
  return `${node.kind}\u00b7${node.node_id.slice(0, 8)}`;
}

/**
 * Return a CSS-friendly class suffix for the node display state.
 * Unknown/unexpected values map to "unknown".
 */
const KNOWN_STATES = new Set([
  "active",
  "historical",
  "compressed",
  "deduplicated",
  "pruned",
  "cold",
  "deactivated",
  "unknown",
]);

export function nodeStateClass(node: FigNode): string {
  const state = node.display?.state;
  return KNOWN_STATES.has(state) ? state : "unknown";
}

// ---------------------------------------------------------------------------
// Graph-State Local Persistence
// ---------------------------------------------------------------------------

const VIEW_STATE_PREFIX = "faim.fig.view_state.";

type PersistedViewState = {
  graphId: string;
  graphVersion: number;
  savedAt: string;
  payload: Record<string, unknown>;
};

function _storageKey(graphId: string): string {
  return `${VIEW_STATE_PREFIX}${graphId}`;
}

/**
 * Save view state for a specific graph + version.
 * Overwrites any prior entry for this graphId.
 */
export function persistGraphViewState(
  graphId: string,
  graphVersion: number,
  payload: Record<string, unknown>,
): void {
  if (typeof window === "undefined") return;
  const entry: PersistedViewState = {
    graphId,
    graphVersion,
    savedAt: new Date().toISOString(),
    payload,
  };
  try {
    window.localStorage.setItem(_storageKey(graphId), JSON.stringify(entry));
  } catch {
    // Storage full or unavailable — silently degrade.
  }
}

/**
 * Load view state only if graphId and graphVersion match exactly.
 * Returns null if no match (stale version, wrong graph, parse error).
 */
export function loadGraphViewState(
  graphId: string,
  graphVersion: number,
): Record<string, unknown> | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(_storageKey(graphId));
    if (!raw) return null;
    const entry: PersistedViewState = JSON.parse(raw);
    if (entry.graphId !== graphId) return null;
    if (entry.graphVersion !== graphVersion) return null;
    return entry.payload;
  } catch {
    return null;
  }
}

/**
 * Remove persisted view state for graphs other than the current one.
 * Call on graph switch to prevent cross-tenant state leakage.
 */
export function clearStaleGraphState(currentGraphId: string): void {
  if (typeof window === "undefined") return;
  const toRemove: string[] = [];
  for (let i = 0; i < window.localStorage.length; i++) {
    const key = window.localStorage.key(i);
    if (
      key &&
      key.startsWith(VIEW_STATE_PREFIX) &&
      key !== _storageKey(currentGraphId)
    ) {
      toRemove.push(key);
    }
  }
  for (const key of toRemove) {
    window.localStorage.removeItem(key);
  }
}
