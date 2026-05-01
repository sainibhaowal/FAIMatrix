import { expect, test, type Page } from "@playwright/test";

function figViewTitle(page: Page) {
  return page.locator("main").getByText("FIG View", { exact: true }).last();
}

/**
 * FIG View — graph view-state persistence tests.
 *
 * Covers:
 *   1. View state is written to localStorage after surface load.
 *   2. Persisted state is restored on page reload for the same graph version.
 *   3. State is NOT restored when graph version changes (stale guard).
 *   4. State is NOT restored when graphId changes (cross-graph guard).
 */

function sessionPayload(graphId = "fig-persist-graph") {
  return {
    user: { name: "Persist Tester", email: "persist@example.com", image: null },
    expires: "2099-01-01T00:00:00.000Z",
    accessToken: "fig-persist-token",
    graphId,
  };
}

async function mockAuthenticatedSession(page: Page, graphId?: string) {
  await page.route("**/api/auth/**", async (route) => {
    const req = route.request();
    const path = new URL(req.url()).pathname;
    if (path.endsWith("/session"))
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(sessionPayload(graphId)),
      });
    if (path.endsWith("/csrf"))
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ csrfToken: "fig-persist-csrf" }),
      });
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({}),
    });
  });
}

function figNode(nodeId: string, title: string) {
  return {
    node_id: nodeId,
    kind: "atom",
    level: 0,
    vector_hash: `${nodeId}-vh`,
    display: { title, title_source: "anchor", state: "active" },
    metrics: {
      touch_count: 1,
      residual: 0.5,
      last_access: "2026-02-20T10:00:00Z",
    },
    provenance: { raw_id: `${nodeId}-raw`, block_id: `${nodeId}-block` },
  };
}

function surfaceResponse(
  version: number,
  hash: string,
  graphId = "fig-persist-graph",
) {
  return {
    snapshot: {
      graph_id: graphId,
      graph_version: version,
      graph_hash: hash,
      as_of: "2026-02-20T10:00:00Z",
      consistent_read: true,
    },
    nodes: [figNode("node-a", "Alpha"), figNode("node-b", "Beta")],
    edges: [],
    timeline: { after_seq: 0, next_seq: 1, has_more: false, events: [] },
    topology: {
      node_count: 2,
      edge_count: 0,
      edge_counts_by_kind: {},
      scorecard: null,
    },
    controls: { similarity: { mode: "none", notes: "" } },
    truncated: false,
    truncation_reason: null,
  };
}

async function mockApiRoutes(
  page: Page,
  version: number,
  hash: string,
  graphId = "fig-persist-graph",
) {
  await page.route("**/api/v1/**", async (route) => {
    const req = route.request();
    const path = new URL(req.url()).pathname;
    if (path.endsWith("/graph/surface") && req.method() === "GET")
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(surfaceResponse(version, hash, graphId)),
      });
    if (path.endsWith("/events/latest") && req.method() === "GET")
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          graph_id: graphId,
          last_seq: 1,
          last_kind: null,
          last_ts: null,
          snapshot_hash: hash,
          event_count: 1,
        }),
      });
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({}),
    });
  });
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const STORAGE_KEY_PREFIX = "faim.fig.view_state.";

async function readPersistedState(page: Page, graphId = "fig-persist-graph") {
  return page.evaluate((key: string) => {
    const raw = window.localStorage.getItem(key);
    if (!raw) return null;
    try {
      return JSON.parse(raw) as {
        graphId: string;
        graphVersion: number;
        savedAt: string;
        payload: Record<string, unknown>;
      };
    } catch {
      return null;
    }
  }, `${STORAGE_KEY_PREFIX}${graphId}`);
}

async function writePersistedState(
  page: Page,
  graphId: string,
  graphVersion: number,
  payload: Record<string, unknown>,
) {
  await page.evaluate(
    ([key, value]) =>
      window.localStorage.setItem(key as string, value as string),
    [
      `${STORAGE_KEY_PREFIX}${graphId}`,
      JSON.stringify({
        graphId,
        graphVersion,
        savedAt: new Date().toISOString(),
        payload,
      }),
    ],
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe("FIG View — view-state persistence", () => {
  test("saves view state to localStorage after surface loads", async ({
    page,
  }) => {
    await mockAuthenticatedSession(page, "fig-persist-graph");
    await mockApiRoutes(page, 1, "hash-v1");

    await page.goto("/dashboard/graph");

    // Wait for the graph to render
    await expect(figViewTitle(page)).toBeVisible();

    // Click the Lineage tab to change layoutMode from default "explore"
    await page.getByText("Lineage").click();

    // Wait for debounce (500 ms) + buffer
    await page.waitForTimeout(800);

    const stored = await readPersistedState(page);
    expect(stored).not.toBeNull();
    expect(stored!.graphId).toBe("fig-persist-graph");
    expect(stored!.graphVersion).toBe(1);
    expect(stored!.payload.layoutMode).toBe("lineage");
  });

  test("restores persisted layout mode and filters on reload for same graph version", async ({
    page,
  }) => {
    await mockAuthenticatedSession(page, "fig-persist-graph");
    await mockApiRoutes(page, 1, "hash-v1");

    await page.goto("/dashboard/graph");
    await expect(figViewTitle(page)).toBeVisible();

    // Pre-seed localStorage with a saved state that has "lineage" layout and hidden node kinds
    await writePersistedState(page, "fig-persist-graph", 1, {
      layoutMode: "lineage",
      topMode: "lineage",
      locked: false,
      hiddenNodeKinds: ["atom"],
      hiddenEdgeKinds: [],
      selectedNodeId: null,
      activeDrawer: null,
      timelineLiveEnabled: true,
    });

    // Reload — loadSurface will run and restore the saved state
    await page.reload();
    await expect(figViewTitle(page)).toBeVisible();

    // The Lineage tab should be active (bg-cyan class applied)
    const lineageBtn = page.getByText("Lineage");
    await expect(lineageBtn).toBeVisible();
    // Active tab has the cyan highlight style
    await expect(lineageBtn).toHaveClass(/bg-cyan/);
  });

  test("does NOT restore state when graph version changes (stale guard)", async ({
    page,
  }) => {
    await mockAuthenticatedSession(page, "fig-persist-graph");
    // Surface reports version 2, but saved state was for version 1
    await mockApiRoutes(page, 2, "hash-v2");

    await page.goto("/dashboard/graph");
    await expect(figViewTitle(page)).toBeVisible();

    // Pre-seed state for version 1
    await writePersistedState(page, "fig-persist-graph", 1, {
      layoutMode: "lineage",
      topMode: "lineage",
      locked: true,
      hiddenNodeKinds: [],
      hiddenEdgeKinds: [],
      selectedNodeId: null,
      activeDrawer: null,
      timelineLiveEnabled: false,
    });

    await page.reload();
    await expect(figViewTitle(page)).toBeVisible();

    // "lineage" should NOT be active — default "explore" should be
    const exploreBtn = page.getByText("Explore");
    await expect(exploreBtn).toBeVisible();
    await expect(exploreBtn).toHaveClass(/bg-cyan/);
  });

  test("clearStaleGraphState removes other graph keys on new graph load", async ({
    page,
  }) => {
    await mockAuthenticatedSession(page, "fig-persist-graph");
    await mockApiRoutes(page, 1, "hash-v1");

    await page.goto("/dashboard/graph");
    await expect(figViewTitle(page)).toBeVisible();

    // Inject a stale entry for a different graph
    await page.evaluate(
      ([key]) => {
        window.localStorage.setItem(
          key as string,
          JSON.stringify({
            graphId: "other-graph",
            graphVersion: 5,
            savedAt: new Date().toISOString(),
            payload: { layoutMode: "explore" },
          }),
        );
      },
      [`${STORAGE_KEY_PREFIX}other-graph`],
    );

    // Reload — clearStaleGraphState runs in loadSurface
    await page.reload();
    await expect(figViewTitle(page)).toBeVisible();

    // The stale key should be gone after the surface reload cleanup runs.
    await page.waitForFunction(
      ([key]) => window.localStorage.getItem(key as string) === null,
      [`${STORAGE_KEY_PREFIX}other-graph`],
    );
  });
});
