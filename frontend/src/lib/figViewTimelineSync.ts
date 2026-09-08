/**
 * FIG View timeline sync helpers.
 *
 * Pure utilities for cursor-backed, idempotent timeline reconciliation.
 */

import type { FigSurfaceResponse, FigTimelineEvent } from "@/types/figView";

export type FigTimelineSyncStatus =
  | "idle"
  | "live"
  | "catching_up"
  | "stale"
  | "disconnected"
  | "error";

export type FigTimelineSyncState = {
  enabled: boolean;
  status: FigTimelineSyncStatus;
  lastAppliedSeq: number;
  lastSnapshotHash: string | null;
  lastSnapshotVersion: number;
  lastSyncedAt: string | null;
  lastError: string | null;
  lastEventKind: string | null;
};

const MAX_TIMELINE_EVENTS = 100;

export function createInitialTimelineSyncState(
  enabled = false,
): FigTimelineSyncState {
  return {
    enabled,
    status: enabled ? "idle" : "idle",
    lastAppliedSeq: 0,
    lastSnapshotHash: null,
    lastSnapshotVersion: 0,
    lastSyncedAt: null,
    lastError: null,
    lastEventKind: null,
  };
}

export function normalizeTimelineEvents(
  events: FigTimelineEvent[],
  minSeq = 0,
): FigTimelineEvent[] {
  const seen = new Set<number>();
  const filtered = events
    .filter((event) => event.seq > minSeq)
    .filter((event) => {
      if (seen.has(event.seq)) return false;
      seen.add(event.seq);
      return true;
    })
    .sort((a, b) => a.seq - b.seq);

  return filtered.slice(-MAX_TIMELINE_EVENTS);
}

export function mergeTimelineResponse(
  current: FigSurfaceResponse,
  incoming: FigSurfaceResponse,
  lastAppliedSeq: number,
): FigSurfaceResponse {
  const currentEvents = current.timeline?.events ?? [];
  const incomingEvents = incoming.timeline?.events ?? [];
  const mergedBySeq = new Map<number, FigTimelineEvent>();
  for (const event of currentEvents) {
    mergedBySeq.set(event.seq, event);
  }
  for (const event of incomingEvents) {
    if (event.seq > lastAppliedSeq || !mergedBySeq.has(event.seq)) {
      mergedBySeq.set(event.seq, event);
    }
  }
  const mergedEvents = Array.from(mergedBySeq.values())
    .sort((a, b) => a.seq - b.seq)
    .slice(-MAX_TIMELINE_EVENTS);

  return {
    ...incoming,
    timeline: incoming.timeline
      ? {
          ...incoming.timeline,
          after_seq: current.timeline?.after_seq ?? incoming.timeline.after_seq,
          next_seq:
            mergedEvents.length > 0
              ? mergedEvents[mergedEvents.length - 1]!.seq
              : incoming.timeline.next_seq,
          has_more:
            incoming.timeline.has_more ||
            mergedEvents.length >= MAX_TIMELINE_EVENTS,
          events: mergedEvents,
        }
      : current.timeline,
  };
}

export function deriveTimelineSyncStatus(
  enabled: boolean,
  hasData: boolean,
  isCatchingUp: boolean,
  hasError: boolean,
): FigTimelineSyncStatus {
  if (!enabled) return "idle";
  if (hasError) return "disconnected";
  if (!hasData) return "idle";
  if (isCatchingUp) return "catching_up";
  return "live";
}

export function nextTimelineCursor(
  currentCursor: number,
  latestSeq: number | null | undefined,
  surfaceNextSeq: number | null | undefined,
): number {
  // latestSeq is only a watermark. Advancing to it before fetching pages
  // permanently skips the backlog between the current cursor and that watermark.
  const candidates = [currentCursor, surfaceNextSeq ?? 0];
  return Math.max(...candidates);
}

export function shouldRebaseTimeline(
  prevHash: string | null,
  nextHash: string | null,
  prevVersion: number,
  nextVersion: number,
): boolean {
  if (!prevHash || !nextHash) return false;
  if (prevHash !== nextHash) return true;
  return nextVersion > prevVersion + 1;
}
