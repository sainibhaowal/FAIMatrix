import { expect, test, type Page } from "@playwright/test";

/**
 * FIG View — dedicated end-to-end coverage.
 *
 * Covers the full FIG interaction surface that is reachable without canvas
 * interaction (canvas node-click requires a running D3 simulation):
 *
 *   1. Page load — success, empty, error, degraded
 *   2. Top mode tabs (Explore / Analyze / Lineage) and auto-drawer open
 *   3. Right rail — all 8 drawers open, render correct content, close correctly
 *   4. Drawer toggle behaviour (active button closes, Close button closes)
 *   5. Search overlay — open via "/", Escape to close, type-to-filter, no-match
 *   6. Refresh button re-issues the surface fetch
 *   7. Graph header — FIG View label, truncated graphId, sync status badge
 *   8. API non-regression — 500 handled, retry works, unexpected shape handled
 */

// ---------------------------------------------------------------------------
// Shared fixtures
// ---------------------------------------------------------------------------

const GRAPH_ID = "fig-e2e-test-graph-0001";

function figViewTitle(page: Page) {
  return page.locator("main").getByText("FIG View", { exact: true }).last();
}

function railButton(page: Page, label: string) {
  return page.getByRole("button", { name: label, exact: true });
}

async function openSearchOverlay(page: Page) {
  await page.getByRole("button", { name: "Search /" }).click();
  await expect(
    page.getByPlaceholder("Search nodes by title, kind, or ID…"),
  ).toBeVisible();
}

function sessionPayload(graphId = GRAPH_ID) {
  return {
    user: { name: "FIG E2E Tester", email: "fig-e2e@example.com", image: null },
    expires: "2099-01-01T00:00:00.000Z",
    accessToken: "fig-e2e-token",
    graphId,
  };
}

async function mockAuth(page: Page, graphId = GRAPH_ID) {
  await page.route("**/api/auth/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
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
        body: JSON.stringify({ csrfToken: "fig-e2e-csrf" }),
      });
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({}),
    });
  });
}

function figNode(nodeId: string, title: string, kind = "atom") {
  return {
    node_id: nodeId,
    kind,
    level: 0,
    vector_hash: `${nodeId}-vh`,
    display: { title, title_source: "anchor", state: "active" },
    metrics: {
      touch_count: 2,
      residual: 0.75,
      last_access: "2026-03-01T10:00:00Z",
    },
    provenance: { raw_id: `${nodeId}-raw`, block_id: `${nodeId}-block` },
  };
}

function figEdge(
  edgeId: string,
  src: string,
  dst: string,
  kind = "inheritance",
) {
  return {
    edge_id: edgeId,
    src_node_id: src,
    dst_node_id: dst,
    kind,
    weight: 1.0,
    meta: null,
  };
}

function standardSurface(graphId = GRAPH_ID) {
  return {
    snapshot: {
      graph_id: graphId,
      graph_version: 1,
      graph_hash: "e2e-hash-abc123",
      as_of: "2026-03-01T10:00:00Z",
      consistent_read: true,
    },
    nodes: [
      figNode("node-alpha", "Alpha Node", "atom"),
      figNode("node-beta", "Beta Node", "concept"),
    ],
    edges: [figEdge("edge-ab", "node-alpha", "node-beta", "inheritance")],
    timeline: {
      after_seq: 0,
      next_seq: 3,
      has_more: false,
      events: [
        {
          seq: 1,
          kind: "STORAGE_RAW_STORED",
          ts: "2026-03-01T09:00:00Z",
          payload_keys: ["graph_id"],
          graph_id: graphId,
        },
        {
          seq: 2,
          kind: "STORAGE_EXTRACTED",
          ts: "2026-03-01T09:01:00Z",
          payload_keys: ["graph_id"],
          graph_id: graphId,
        },
        {
          seq: 3,
          kind: "QUERY_COMPLETE",
          ts: "2026-03-01T10:00:00Z",
          payload_keys: ["graph_id"],
          graph_id: graphId,
        },
      ],
    },
    topology: {
      node_count: 2,
      edge_count: 1,
      edge_counts_by_kind: { inheritance: 1 },
      scorecard: null,
    },
    controls: { similarity: { mode: "cosine", notes: "Exploration only." } },
    truncated: false,
    truncation_reason: null,
  };
}

function latestEventResponse(graphId = GRAPH_ID) {
  return {
    graph_id: graphId,
    last_seq: 3,
    last_kind: "QUERY_COMPLETE",
    last_ts: "2026-03-01T10:00:00Z",
    snapshot_hash: "e2e-hash-abc123",
    event_count: 3,
  };
}

async function mockStandardApi(page: Page, graphId = GRAPH_ID) {
  await page.route("**/api/v1/**", async (route) => {
    const req = route.request();
    const path = new URL(req.url()).pathname;
    if (path.endsWith("/graph/surface") && req.method() === "GET")
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(standardSurface(graphId)),
      });
    if (path.endsWith("/events/latest") && req.method() === "GET")
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(latestEventResponse(graphId)),
      });
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({}),
    });
  });
}

async function loadFigPage(page: Page, graphId = GRAPH_ID) {
  await mockAuth(page, graphId);
  await mockStandardApi(page, graphId);
  await page.goto("/dashboard/graph");
  await expect(figViewTitle(page)).toBeVisible();
}

// ---------------------------------------------------------------------------
// 1. Page load states
// ---------------------------------------------------------------------------

test.describe("FIG View — page load states", () => {
  test("successful load renders FIG View title, mode tabs, and rail buttons", async ({
    page,
  }) => {
    await loadFigPage(page);

    // Title always present
    await expect(figViewTitle(page)).toBeVisible();

    // Three top-mode tabs
    await expect(page.getByText("Explore")).toBeVisible();
    await expect(page.getByText("Analyze")).toBeVisible();
    await expect(page.getByText("Lineage")).toBeVisible();

    // Eight right-rail buttons by title
    for (const label of [
      "Inspector",
      "Nodes",
      "Edges",
      "Relation",
      "Legend",
      "Snapshot",
      "Timeline",
      "Controls",
    ]) {
      await expect(railButton(page, label)).toBeVisible();
    }
  });

  test("empty graph shows empty state message", async ({ page }) => {
    await mockAuth(page);
    await page.route("**/api/v1/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (path.endsWith("/graph/surface"))
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            ...standardSurface(),
            nodes: [],
            edges: [],
            topology: {
              node_count: 0,
              edge_count: 0,
              edge_counts_by_kind: {},
              scorecard: null,
            },
          }),
        });
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({}),
      });
    });

    await page.goto("/dashboard/graph");
    await expect(page.getByText("No nodes in this graph")).toBeVisible();
  });

  test("API 500 on surface load shows error state", async ({ page }) => {
    await mockAuth(page);
    await page.route("**/api/v1/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (path.endsWith("/graph/surface"))
        return route.fulfill({
          status: 500,
          contentType: "application/json",
          body: JSON.stringify({ detail: "internal server error" }),
        });
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({}),
      });
    });

    await page.goto("/dashboard/graph");
    await expect(page.getByText("Failed to load graph")).toBeVisible();
  });

  test("truncated response renders degraded badge", async ({ page }) => {
    await mockAuth(page);
    await page.route("**/api/v1/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (path.endsWith("/graph/surface"))
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            ...standardSurface(),
            truncated: true,
            truncation_reason: "node cap reached",
          }),
        });
      if (path.endsWith("/events/latest"))
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(latestEventResponse()),
        });
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({}),
      });
    });

    await page.goto("/dashboard/graph");
    await expect(page.getByText("degraded")).toBeVisible();
  });

  test("transient surface error re-issues the surface fetch and recovers", async ({
    page,
  }) => {
    await mockAuth(page);
    let callCount = 0;
    await page.route("**/api/v1/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (path.endsWith("/graph/surface")) {
        callCount += 1;
        if (callCount === 1)
          return route.fulfill({
            status: 500,
            contentType: "application/json",
            body: JSON.stringify({ detail: "temporary error" }),
          });
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(standardSurface()),
        });
      }
      if (path.endsWith("/events/latest"))
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(latestEventResponse()),
        });
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({}),
      });
    });

    await page.goto("/dashboard/graph");
    await expect(figViewTitle(page)).toBeVisible();
    expect(callCount).toBeGreaterThanOrEqual(2);
  });
});

// ---------------------------------------------------------------------------
// 2. Top mode tabs
// ---------------------------------------------------------------------------

test.describe("FIG View — top mode tabs", () => {
  test("Analyze tab click opens the Snapshot drawer", async ({ page }) => {
    await loadFigPage(page);
    await page.getByText("Analyze").click();
    // Snapshot drawer shows graph version
    await expect(page.getByText("Version 1")).toBeVisible();
  });

  test("Lineage tab click opens the Edges drawer", async ({ page }) => {
    await loadFigPage(page);
    await page.getByText("Lineage").click();
    // Edges drawer shows edge kind counts
    await expect(page.getByText("inheritance", { exact: true })).toBeVisible();
  });

  test("Explore tab click opens the Nodes drawer", async ({ page }) => {
    await loadFigPage(page);
    // Switch away first so Explore triggers the auto-open
    await page.getByText("Analyze").click();
    await page.getByText("Explore").click();
    // Nodes drawer lists our two nodes
    await expect(page.getByText("Alpha Node")).toBeVisible();
    await expect(page.getByText("Beta Node")).toBeVisible();
  });

  test("active top tab has cyan highlight style", async ({ page }) => {
    await loadFigPage(page);
    await page.getByText("Lineage").click();
    await expect(page.getByText("Lineage")).toHaveClass(/bg-cyan/);
    await expect(page.getByText("Explore")).not.toHaveClass(/bg-cyan/);
  });
});

// ---------------------------------------------------------------------------
// 3. Right rail drawers — open and content
// ---------------------------------------------------------------------------

test.describe("FIG View — right rail drawers", () => {
  test("Inspector drawer: placeholder shown when no node is selected", async ({
    page,
  }) => {
    await loadFigPage(page);
    await page.getByTitle("Inspector").click();
    await expect(
      page.getByText("Click a node in the graph to inspect it."),
    ).toBeVisible();
  });

  test("Nodes drawer: lists loaded nodes with kind badges", async ({
    page,
  }) => {
    await loadFigPage(page);
    await railButton(page, "Nodes").click();
    await expect(page.getByText("Alpha Node")).toBeVisible();
    await expect(page.getByText("Beta Node")).toBeVisible();
    // Kind badges
    await expect(page.getByText("atom")).toBeVisible();
    await expect(page.getByText("concept")).toBeVisible();
  });

  test("Edges drawer: shows edge kind and count", async ({ page }) => {
    await loadFigPage(page);
    await railButton(page, "Edges").click();
    await expect(page.getByText("inheritance", { exact: true })).toBeVisible();
    await expect(page.getByText("Edges (1)")).toBeVisible();
  });

  test("Relation drawer: shows node pickers and Find Connection button", async ({
    page,
  }) => {
    await loadFigPage(page);
    await page.getByTitle("Relation").click();
    await expect(
      page.getByText(
        "Select two nodes to find and explain the shortest path between them.",
      ),
    ).toBeVisible();
    await expect(page.getByText("Find Connection")).toBeVisible();
  });

  test("Snapshot drawer: shows graph version and hash", async ({ page }) => {
    await loadFigPage(page);
    await page.getByTitle("Snapshot").click();
    await expect(page.getByText("Version 1")).toBeVisible();
    await expect(page.getByText("e2e-hash-abc123")).toBeVisible();
  });

  test("Timeline drawer: shows Live timeline toggle and event list", async ({
    page,
  }) => {
    await loadFigPage(page);
    await page.getByTitle("Timeline").click();
    await expect(page.getByText("Live timeline")).toBeVisible();
    // Pause/Resume live button
    await expect(
      page.getByRole("button", { name: /pause live/i }),
    ).toBeVisible();
    // Event seq entries
    await expect(page.getByText("#1")).toBeVisible();
    await expect(page.getByText("#3")).toBeVisible();
  });

  test("Controls drawer: shows layout mode buttons", async ({ page }) => {
    await loadFigPage(page);
    await page.getByTitle("Controls").click();
    // FigControls renders layout modes
    await expect(page.getByText("Explore").first()).toBeVisible();
    await expect(page.getByText("Lineage").first()).toBeVisible();
  });

  test("Legend drawer opens without error", async ({ page }) => {
    await loadFigPage(page);
    await page.getByTitle("Legend").click();
    // Legend renders node kind filter rows — our kinds are atom and concept
    await expect(page.getByText("atom").first()).toBeVisible();
    await expect(page.getByText("concept").first()).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// 4. Drawer toggle behaviour
// ---------------------------------------------------------------------------

test.describe("FIG View — drawer toggle behaviour", () => {
  test("clicking an active rail button closes its drawer", async ({ page }) => {
    await loadFigPage(page);

    // Open the Nodes drawer
    await railButton(page, "Nodes").click();
    await expect(page.getByText("Alpha Node")).toBeVisible();

    // Click the same button again to close
    await railButton(page, "Nodes").click();
    await expect(page.getByText("Alpha Node")).not.toBeVisible();
  });

  test("Close button inside drawer header closes the drawer", async ({
    page,
  }) => {
    await loadFigPage(page);

    await page.getByTitle("Snapshot").click();
    await expect(page.getByText("Version 1")).toBeVisible();

    // Click the Close button inside the drawer
    await page.getByRole("button", { name: "Close" }).click();
    await expect(page.getByText("Version 1")).not.toBeVisible();
  });

  test("opening one drawer closes any previously open drawer", async ({
    page,
  }) => {
    await loadFigPage(page);

    // Open Nodes
    await railButton(page, "Nodes").click();
    await expect(page.getByText("Alpha Node")).toBeVisible();

    // Open Snapshot — Nodes should close (only one FloatingDrawer renders at a time)
    await page.getByTitle("Snapshot").click();
    await expect(page.getByText("Version 1")).toBeVisible();
    await expect(page.getByText("Alpha Node")).not.toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// 5. Search overlay
// ---------------------------------------------------------------------------

test.describe("FIG View — search overlay", () => {
  test('pressing "/" opens the search overlay', async ({ page }) => {
    await loadFigPage(page);
    await page.keyboard.press("/");
    await expect(
      page.getByPlaceholder("Search nodes by title, kind, or ID…"),
    ).toBeVisible();
  });

  test("Escape closes the search overlay", async ({ page }) => {
    await loadFigPage(page);
    await openSearchOverlay(page);
    await page.keyboard.press("Escape");
    await expect(
      page.getByPlaceholder("Search nodes by title, kind, or ID…"),
    ).not.toBeVisible();
  });

  test("typing in search filters node results", async ({ page }) => {
    await loadFigPage(page);
    await openSearchOverlay(page);

    const input = page.getByPlaceholder("Search nodes by title, kind, or ID…");
    await input.fill("Alpha");

    await expect(page.getByText("Alpha Node")).toBeVisible();
    // Beta should not appear after filtering
    await expect(page.getByText("Beta Node")).not.toBeVisible();
  });

  test("empty query shows all nodes", async ({ page }) => {
    await loadFigPage(page);
    await openSearchOverlay(page);

    // Both nodes visible with no filter
    await expect(page.getByText("Alpha Node")).toBeVisible();
    await expect(page.getByText("Beta Node")).toBeVisible();
  });

  test("no-match query shows no-match message", async ({ page }) => {
    await loadFigPage(page);
    await openSearchOverlay(page);
    await page
      .getByPlaceholder("Search nodes by title, kind, or ID…")
      .fill("zzznomatch");
    await expect(page.getByText(/No nodes match/)).toBeVisible();
  });

  test("result count is shown in search footer", async ({ page }) => {
    await loadFigPage(page);
    await openSearchOverlay(page);
    // With no filter, 2 results
    await expect(page.getByText("2 results")).toBeVisible();
  });

  test("Search button in top bar also opens the search overlay", async ({
    page,
  }) => {
    await loadFigPage(page);
    await page.getByTitle("Search nodes (press /)").click();
    await expect(
      page.getByPlaceholder("Search nodes by title, kind, or ID…"),
    ).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// 6. Refresh button
// ---------------------------------------------------------------------------

test.describe("FIG View — refresh button", () => {
  test("refresh button re-issues the surface fetch", async ({ page }) => {
    await mockAuth(page);
    let surfaceFetchCount = 0;
    await page.route("**/api/v1/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (path.endsWith("/graph/surface")) {
        surfaceFetchCount += 1;
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(standardSurface()),
        });
      }
      if (path.endsWith("/events/latest"))
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(latestEventResponse()),
        });
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({}),
      });
    });

    await page.goto("/dashboard/graph");
    await expect(figViewTitle(page)).toBeVisible();
    const initialCount = surfaceFetchCount;

    // Click the refresh icon button (RefreshCw in top-right bar area)
    await page.getByRole("button", { name: "Refresh graph" }).click();

    // Surface should be called again
    await page.waitForTimeout(300);
    expect(surfaceFetchCount).toBeGreaterThan(initialCount);
  });
});

// ---------------------------------------------------------------------------
// 7. Graph header
// ---------------------------------------------------------------------------

test.describe("FIG View — graph header", () => {
  test("truncated graphId is shown in header", async ({ page }) => {
    const longGraphId = "fig-e2e-test-graph-0001";
    await mockAuth(page, longGraphId);
    await mockStandardApi(page, longGraphId);
    await page.goto("/dashboard/graph");
    await expect(figViewTitle(page)).toBeVisible();
    // graphLabel = graphId.slice(0, 12) + "…" = "fig-e2e-test…"
    await expect(page.getByText("fig-e2e-test…")).toBeVisible();
  });

  test("timeline sync status badge is visible", async ({ page }) => {
    await loadFigPage(page);
    // The badge shows "idle" by default (timeline drawer not open)
    await expect(page.getByText("idle")).toBeVisible();
  });

  test("similarity mode badge is shown in Controls drawer", async ({
    page,
  }) => {
    await loadFigPage(page);
    await page.getByTitle("Controls").click();
    await expect(page.getByText(/similarity: cosine/i)).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// 8. API non-regression
// ---------------------------------------------------------------------------

test.describe("FIG View — API non-regression", () => {
  test("page stays mounted when /events/latest returns 500", async ({
    page,
  }) => {
    await mockAuth(page);
    await page.route("**/api/v1/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (path.endsWith("/graph/surface"))
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(standardSurface()),
        });
      if (path.endsWith("/events/latest"))
        return route.fulfill({
          status: 500,
          contentType: "application/json",
          body: JSON.stringify({ detail: "journal unavailable" }),
        });
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({}),
      });
    });

    await page.goto("/dashboard/graph");
    await expect(figViewTitle(page)).toBeVisible();
    // Page still renders graph — timeline polling degrades gracefully
    await railButton(page, "Nodes").click();
    await expect(page.getByText("Alpha Node")).toBeVisible();
  });

  test("page handles graph with no edges gracefully", async ({ page }) => {
    await mockAuth(page);
    await page.route("**/api/v1/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (path.endsWith("/graph/surface"))
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            ...standardSurface(),
            edges: [],
            topology: {
              node_count: 2,
              edge_count: 0,
              edge_counts_by_kind: {},
              scorecard: null,
            },
          }),
        });
      if (path.endsWith("/events/latest"))
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(latestEventResponse()),
        });
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({}),
      });
    });

    await page.goto("/dashboard/graph");
    await expect(figViewTitle(page)).toBeVisible();

    // Edges drawer shows no-edges message
    await page.getByTitle("Edges").click();
    await expect(page.getByText("No edges found")).toBeVisible();
  });

  test("page handles missing topology field without crashing", async ({
    page,
  }) => {
    await mockAuth(page);
    await page.route("**/api/v1/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (path.endsWith("/graph/surface"))
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ ...standardSurface(), topology: null }),
        });
      if (path.endsWith("/events/latest"))
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(latestEventResponse()),
        });
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({}),
      });
    });

    await page.goto("/dashboard/graph");
    await expect(figViewTitle(page)).toBeVisible();
    // Metrics bar falls back gracefully
    await railButton(page, "Nodes").click();
    await expect(page.getByText("Alpha Node")).toBeVisible();
  });

  test("consistent_read: false results in degraded state", async ({ page }) => {
    await mockAuth(page);
    await page.route("**/api/v1/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (path.endsWith("/graph/surface"))
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            ...standardSurface(),
            snapshot: { ...standardSurface().snapshot, consistent_read: false },
          }),
        });
      if (path.endsWith("/events/latest"))
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(latestEventResponse()),
        });
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({}),
      });
    });

    await page.goto("/dashboard/graph");
    // Snapshot assembled from multiple reads → degraded
    await expect(page.getByText("degraded")).toBeVisible();
  });
});
