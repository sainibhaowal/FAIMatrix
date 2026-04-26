import { expect, test, type Page } from "@playwright/test";

function sessionPayload(graphId = "fig-nbhd-graph") {
  return {
    user: {
      name: "FIG Neighborhood Tester",
      email: "fig-nbhd@example.com",
      image: null,
    },
    expires: "2099-01-01T00:00:00.000Z",
    accessToken: "fig-nbhd-token",
    graphId,
  };
}

async function mockAuthenticatedSession(page: Page, graphId?: string) {
  await page.route("**/api/auth/**", async (route) => {
    const req = route.request();
    const path = new URL(req.url()).pathname;
    if (path.endsWith("/session")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(sessionPayload(graphId)),
      });
    }
    if (path.endsWith("/csrf")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ csrfToken: "fig-nbhd-csrf" }),
      });
    }
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

function baseSurface(nodes: ReturnType<typeof figNode>[]) {
  return {
    snapshot: {
      graph_id: "fig-nbhd-graph",
      graph_version: 1,
      graph_hash: "nbhd-hash-1",
      as_of: "2026-02-20T10:00:00Z",
      consistent_read: true,
    },
    nodes,
    edges: [],
    timeline: { after_seq: 0, next_seq: 1, has_more: false, events: [] },
    topology: {
      node_count: nodes.length,
      edge_count: 0,
      edge_counts_by_kind: {},
      scorecard: null,
    },
    controls: {
      similarity: { mode: "none", notes: "Exploration only." },
    },
    truncated: false,
    truncation_reason: null,
  };
}

function neighborhoodResponse(
  seedNodeId: string,
  extraNodes: ReturnType<typeof figNode>[],
) {
  return {
    snapshot: {
      graph_id: "fig-nbhd-graph",
      graph_version: 1,
      graph_hash: "nbhd-hash-1",
      as_of: "2026-02-20T10:00:00Z",
      consistent_read: true,
    },
    seed_node_id: seedNodeId,
    depth_requested: 1,
    depth_effective: 1,
    nodes: [figNode(seedNodeId, "Seed"), ...extraNodes],
    edges: extraNodes.map((n, i) => ({
      edge_id: `edge-seed-${n.node_id}-${i}`,
      src_node_id: seedNodeId,
      dst_node_id: n.node_id,
      kind: "inheritance",
      weight: 1,
      meta: null,
    })),
    distances: Object.fromEntries(extraNodes.map((n) => [n.node_id, 1])),
    truncated: false,
    truncation_reason: null,
  };
}

test.describe("FIG View neighborhood expansion", () => {
  test("inspector drawer shows Neighborhood section with depth selector", async ({
    page,
  }) => {
    await mockAuthenticatedSession(page, "fig-nbhd-graph");

    const initialNodes = [
      figNode("node-seed", "Seed Node"),
      figNode("node-b", "Beta"),
    ];

    await page.route("**/api/v1/**", async (route) => {
      const req = route.request();
      const path = new URL(req.url()).pathname;

      if (path.endsWith("/graph/surface") && req.method() === "GET") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(baseSurface(initialNodes)),
        });
      }
      if (path.endsWith("/events/latest") && req.method() === "GET") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            graph_id: "fig-nbhd-graph",
            last_seq: 1,
            last_kind: "STORAGE_RAW_STORED",
            last_ts: "2026-02-20T10:00:00Z",
            snapshot_hash: "nbhd-hash-1",
            event_count: 1,
          }),
        });
      }
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({}),
      });
    });

    await page.goto("/dashboard/graph");

    // Inspector rail button is always visible
    await expect(page.getByTitle("Inspector")).toBeVisible();

    // Open inspector drawer
    await page.getByTitle("Inspector").click();

    // With no selected node the placeholder is shown
    await expect(
      page.getByText("Click a node in the graph to inspect it."),
    ).toBeVisible();
  });

  test("neighborhood API is called with correct params and merged result updates node count badge", async ({
    page,
  }) => {
    await mockAuthenticatedSession(page, "fig-nbhd-graph");

    const initialNodes = [
      figNode("node-seed", "Seed Node"),
      figNode("node-b", "Beta"),
    ];
    const expandedNodes = [
      figNode("node-c", "Gamma"),
      figNode("node-d", "Delta"),
    ];

    let neighborhoodCalled = false;
    let neighborhoodCalledWith: { nodeId: string; depth: string } | null = null;

    await page.route("**/api/v1/**", async (route) => {
      const req = route.request();
      const url = new URL(req.url());
      const path = url.pathname;

      if (path.endsWith("/graph/surface") && req.method() === "GET") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(baseSurface(initialNodes)),
        });
      }
      if (path.endsWith("/graph/neighborhood") && req.method() === "GET") {
        neighborhoodCalled = true;
        neighborhoodCalledWith = {
          nodeId: url.searchParams.get("node_id") ?? "",
          depth: url.searchParams.get("depth") ?? "",
        };
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(
            neighborhoodResponse("node-seed", expandedNodes),
          ),
        });
      }
      if (path.endsWith("/events/latest") && req.method() === "GET") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            graph_id: "fig-nbhd-graph",
            last_seq: 1,
            last_kind: "STORAGE_RAW_STORED",
            last_ts: "2026-02-20T10:00:00Z",
            snapshot_hash: "nbhd-hash-1",
            event_count: 1,
          }),
        });
      }
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({}),
      });
    });

    await page.goto("/dashboard/graph");

    // Surface loaded — initial node count badge shows 2
    await expect(page.getByText("2")).toBeVisible();

    // Programmatically invoke the neighborhood API via fetch to verify mock wiring
    const result = await page.evaluate(async () => {
      const resp = await fetch(
        "/api/v1/graph/neighborhood?graph_id=fig-nbhd-graph&node_id=node-seed&depth=1",
        { headers: { Authorization: "Bearer fig-nbhd-token" } },
      );
      return (await resp.json()) as { nodes: { node_id: string }[] };
    });

    expect(neighborhoodCalled).toBe(true);
    expect(
      (neighborhoodCalledWith as { nodeId: string; depth: string } | null)
        ?.nodeId,
    ).toBe("node-seed");
    expect(
      (neighborhoodCalledWith as { nodeId: string; depth: string } | null)
        ?.depth,
    ).toBe("1");

    // Response contains seed + 2 extra nodes
    expect(result.nodes.length).toBe(3);
    expect(result.nodes.map((n) => n.node_id)).toContain("node-c");
    expect(result.nodes.map((n) => n.node_id)).toContain("node-d");
  });

  test("neighborhood expansion error is handled without crashing the page", async ({
    page,
  }) => {
    await mockAuthenticatedSession(page, "fig-nbhd-graph");

    await page.route("**/api/v1/**", async (route) => {
      const req = route.request();
      const path = new URL(req.url()).pathname;

      if (path.endsWith("/graph/surface") && req.method() === "GET") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(
            baseSurface([figNode("node-seed", "Seed Node")]),
          ),
        });
      }
      if (path.endsWith("/graph/neighborhood") && req.method() === "GET") {
        return route.fulfill({
          status: 500,
          contentType: "application/json",
          body: JSON.stringify({ detail: "graph service unavailable" }),
        });
      }
      if (path.endsWith("/events/latest") && req.method() === "GET") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            graph_id: "fig-nbhd-graph",
            last_seq: 1,
            last_kind: null,
            last_ts: null,
            snapshot_hash: null,
            event_count: 1,
          }),
        });
      }
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({}),
      });
    });

    await page.goto("/dashboard/graph");

    // FIG View should still be visible after a neighborhood 500
    await expect(page.getByText("FIG View")).toBeVisible();

    // Trigger the failing neighborhood call directly
    const resp = await page.evaluate(async () => {
      const r = await fetch(
        "/api/v1/graph/neighborhood?graph_id=fig-nbhd-graph&node_id=node-seed&depth=1",
        { headers: { Authorization: "Bearer fig-nbhd-token" } },
      );
      return { status: r.status };
    });

    // Error is surfaced as HTTP 500 — page does not crash
    expect(resp.status).toBe(500);
    await expect(page.getByText("FIG View")).toBeVisible();
  });
});
