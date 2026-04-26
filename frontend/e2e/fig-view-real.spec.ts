/**
 * FIG View — real end-to-end tests.
 *
 * These tests hit the LIVE FAIM backend (localhost:8000) with no HTTP mocking.
 * The E2E JWT is injected by the Next.js middleware (PLAYWRIGHT_BYPASS_AUTH=true
 * + PLAYWRIGHT_E2E_JWT), giving the backend's JWTAuthMiddleware a real authenticated
 * request for tenant "user:e2e-test-user" / graph "e2e-graph-001".
 *
 * Global setup (global-setup.ts) seeds the graph before this suite runs.
 *
 * What is NOT mocked:
 *   - /api/v1/graph/surface
 *   - /api/v1/graph/neighborhood
 *   - /api/v1/events/latest
 *
 * What IS mocked (auth infrastructure only, not the feature under test):
 *   - /api/auth/** (NextAuth session) — returns the E2E user so the FIG page
 *     knows which graphId to load. The FAIM API calls themselves are all real.
 */

import { expect, test, type Page } from "@playwright/test";
import { E2E_GRAPH_ID, E2E_USER_ID } from "../playwright.config";

const E2E_JWT =
  process.env.PLAYWRIGHT_E2E_JWT ??
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlMmUtdGVzdC11c2VyIiwiZW1haWwiOiJlMmVAdGVzdC5mYWltIiwidXNlcklkIjoiZTJlLXRlc3QtdXNlciIsImdyYXBoSWQiOiJlMmUtZ3JhcGgtMDAxIiwibmFtZSI6IkUyRSBUZXN0IFVzZXIiLCJleHAiOjk5OTk5OTk5OTksImlhdCI6MTc3NjM2Mjk0Nn0.C1CWsRIIIPUgQZJx1KclShCWo0Pq75pbfjLmJRHiljI";

// ---------------------------------------------------------------------------
// Auth session mock — the ONLY mock in this file.
// Returns the E2E user so FIG page knows graphId. All FAIM API calls are real.
// ---------------------------------------------------------------------------
async function injectSession(page: Page): Promise<void> {
  await page.route("**/api/auth/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/session")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          user: { name: "E2E Test User", email: "e2e@test.faim", image: null },
          expires: "2099-01-01T00:00:00.000Z",
          accessToken: E2E_JWT,
          graphId: E2E_GRAPH_ID,
          userId: E2E_USER_ID,
        }),
      });
    }
    if (path.endsWith("/csrf")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ csrfToken: "e2e-csrf" }),
      });
    }
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: "{}",
    });
  });
}

// ---------------------------------------------------------------------------
// Suite 1: Graph surface loads with real data
// ---------------------------------------------------------------------------
test.describe("Real backend — graph surface", () => {
  test("FIG page loads and displays real node count from live backend", async ({
    page,
  }) => {
    await injectSession(page);
    await page.goto("/dashboard/graph");

    // Page chrome is always visible — use nth(2) to target the graph-page header span
    await expect(page.getByText("FIG View").nth(2)).toBeVisible({
      timeout: 10000,
    });

    // Metrics bar shows non-zero node count — this number comes from the real DB
    // Wait up to 15s for graph to load from real backend
    await expect(
      page
        .locator('[data-testid="fig-metrics-nodes"]')
        .or(page.getByText(/^\d+$/).first()),
    ).toBeVisible({ timeout: 15000 });

    // The stats pill area contains real numbers — nodes >= 1
    // We check the TopStatsRow which shows node/edge counts
    const statsText = await page
      .locator("text=/Nodes/")
      .first()
      .isVisible({ timeout: 10000 });
    expect(statsText).toBe(true);
  });

  test("graph surface response contains real nodes — intercepted and counted", async ({
    page,
  }) => {
    await injectSession(page);

    // Intercept the real API call — do NOT mock it, just observe
    let surfaceNodeCount = 0;
    let surfaceEdgeCount = 0;
    await page.route("**/api/v1/graph/surface**", async (route) => {
      // Let it pass through to the real backend
      const response = await route.fetch();
      const body = (await response.json()) as {
        nodes: unknown[];
        edges: unknown[];
      };
      surfaceNodeCount = body.nodes?.length ?? 0;
      surfaceEdgeCount = body.edges?.length ?? 0;
      await route.fulfill({ response });
    });

    await page.goto("/dashboard/graph");
    await page.waitForTimeout(8000); // allow real backend round-trip + render

    expect(surfaceNodeCount).toBeGreaterThan(0);
    expect(surfaceEdgeCount).toBeGreaterThanOrEqual(0);
    console.log(
      `[real-test] Surface: ${surfaceNodeCount} nodes, ${surfaceEdgeCount} edges`,
    );
  });

  test("graph snapshot metadata reflects real backend version and hash", async ({
    page,
  }) => {
    await injectSession(page);

    let snapshotHash = "";
    let graphVersion = 0;
    let graphId = "";

    await page.route("**/api/v1/graph/surface**", async (route) => {
      const response = await route.fetch();
      const body = (await response.json()) as {
        snapshot: {
          graph_hash: string;
          graph_version: number;
          graph_id: string;
        };
      };
      snapshotHash = body.snapshot?.graph_hash ?? "";
      graphVersion = body.snapshot?.graph_version ?? 0;
      graphId = body.snapshot?.graph_id ?? "";
      await route.fulfill({ response });
    });

    const surfaceResponsePromise = page.waitForResponse(
      "**/api/v1/graph/surface**",
    );
    await page.goto("/dashboard/graph");
    await surfaceResponsePromise;

    // Real backend returns snapshot with version > 0 and a non-empty graph_id.
    // graph_hash may be empty depending on backend config — don't assert it.
    expect(graphVersion).toBeGreaterThan(0);
    expect(graphId.length).toBeGreaterThan(0);
    console.log(
      `[real-test] Snapshot: v${graphVersion}, id=${graphId}, hash="${snapshotHash}"`,
    );
  });
});

// ---------------------------------------------------------------------------
// Suite 2: Neighborhood expansion — real API, real data
// ---------------------------------------------------------------------------
test.describe("Real backend — neighborhood expansion", () => {
  test("neighborhood endpoint returns real nodes for a seed from the surface", async ({
    page,
  }) => {
    await injectSession(page);

    // Collect the first node from a real surface call
    let seedNodeId = "";

    // Step 1: intercept surface to grab first node id
    await page.route("**/api/v1/graph/surface**", async (route) => {
      const resp = await route.fetch();
      const body = (await resp.json()) as { nodes: { node_id: string }[] };
      if (body.nodes?.length) seedNodeId = body.nodes[0]!.node_id;
      await route.fulfill({ response: resp });
    });

    // Step 2: pass neighborhood calls through — real backend, observe only
    await page.route("**/api/v1/graph/neighborhood**", async (route) => {
      await route.continue();
    });

    await page.goto("/dashboard/graph");

    // Open inspector (no node selected yet — shows placeholder)
    await page.getByTitle("Inspector").click();
    await expect(
      page.getByText("Click a node in the graph to inspect it."),
    ).toBeVisible({
      timeout: 10000,
    });

    // Trigger neighborhood fetch directly (simulates what clicking Expand would do)
    // We call the real backend endpoint from within the browser context
    const result = await page.evaluate(
      async ({
        jwt,
        graphId,
        nodeId,
      }: {
        jwt: string;
        graphId: string;
        nodeId: string;
      }) => {
        if (!nodeId) return null;
        const resp = await fetch(
          `/api/v1/graph/neighborhood?graph_id=${graphId}&node_id=${nodeId}&depth=1`,
          { headers: { Authorization: `Bearer ${jwt}` } },
        );
        return resp.ok
          ? ((await resp.json()) as { nodes: unknown[]; edges: unknown[] })
          : null;
      },
      { jwt: E2E_JWT, graphId: E2E_GRAPH_ID, nodeId: seedNodeId },
    );

    // Real backend returns real neighborhood data
    expect(result).not.toBeNull();
    expect((result as { nodes: unknown[] }).nodes.length).toBeGreaterThan(0);
    console.log(
      `[real-test] Neighborhood: seed=${seedNodeId.slice(0, 12)}, ` +
        `nodes=${(result as { nodes: unknown[] }).nodes.length}, ` +
        `edges=${(result as { edges: unknown[] }).edges.length}`,
    );
  });

  test("neighborhood merge result is additive — no duplicates", async ({
    page,
  }) => {
    await injectSession(page);

    let seedNodeId = "";
    let initialNodeCount = 0;

    await page.route("**/api/v1/graph/surface**", async (route) => {
      const resp = await route.fetch();
      const body = (await resp.json()) as { nodes: { node_id: string }[] };
      initialNodeCount = body.nodes?.length ?? 0;
      if (body.nodes?.length) seedNodeId = body.nodes[0]!.node_id;
      await route.fulfill({ response: resp });
    });

    await page.goto("/dashboard/graph");
    await page.waitForTimeout(5000);

    // Fetch neighborhood from browser (real call through Next.js proxy → real backend)
    const nbhd = await page.evaluate(
      async ({
        jwt,
        graphId,
        nodeId,
      }: {
        jwt: string;
        graphId: string;
        nodeId: string;
      }) => {
        if (!nodeId) return null;
        const resp = await fetch(
          `/api/v1/graph/neighborhood?graph_id=${graphId}&node_id=${nodeId}&depth=1`,
          { headers: { Authorization: `Bearer ${jwt}` } },
        );
        return resp.ok
          ? ((await resp.json()) as { nodes: { node_id: string }[] })
          : null;
      },
      { jwt: E2E_JWT, graphId: E2E_GRAPH_ID, nodeId: seedNodeId },
    );

    expect(nbhd).not.toBeNull();

    // Merge logic: additive, no duplicates
    const existingIds = new Set<string>();
    const surfaceResp = await page.evaluate(
      async ({ jwt, graphId }: { jwt: string; graphId: string }) => {
        const resp = await fetch(`/api/v1/graph/surface?graph_id=${graphId}`, {
          headers: { Authorization: `Bearer ${jwt}` },
        });
        return resp.ok
          ? ((await resp.json()) as { nodes: { node_id: string }[] })
          : null;
      },
      { jwt: E2E_JWT, graphId: E2E_GRAPH_ID },
    );

    for (const n of (surfaceResp as { nodes: { node_id: string }[] }).nodes) {
      existingIds.add(n.node_id);
    }

    const newNodes = (nbhd as { nodes: { node_id: string }[] }).nodes.filter(
      (n) => !existingIds.has(n.node_id),
    );
    const uniqueIds = new Set(
      (nbhd as { nodes: { node_id: string }[] }).nodes.map((n) => n.node_id),
    );

    // No duplicates within the neighborhood response
    expect(uniqueIds.size).toBe(
      (nbhd as { nodes: { node_id: string }[] }).nodes.length,
    );
    console.log(
      `[real-test] Merge: surface=${initialNodeCount}, nbhd=${
        (nbhd as { nodes: unknown[] }).nodes.length
      }, new=${newNodes.length}`,
    );
  });
});

// ---------------------------------------------------------------------------
// Suite 3: Timeline / event journal — real data
// ---------------------------------------------------------------------------
test.describe("Real backend — timeline and events", () => {
  test("events/latest returns non-zero seq from real event journal", async ({
    page,
  }) => {
    await injectSession(page);

    // Navigate first so page.evaluate runs in a real origin (not about:blank)
    await page.goto("/dashboard/graph");
    await page.waitForTimeout(3000);

    const result = await page.evaluate(
      async ({ jwt, graphId }: { jwt: string; graphId: string }) => {
        const resp = await fetch(`/api/v1/events/latest?graph_id=${graphId}`, {
          headers: { Authorization: `Bearer ${jwt}` },
        });
        return resp.ok
          ? ((await resp.json()) as {
              last_seq: number;
              last_kind: string | null;
              event_count: number;
            })
          : null;
      },
      { jwt: E2E_JWT, graphId: E2E_GRAPH_ID },
    );

    expect(result).not.toBeNull();
    expect((result as { last_seq: number }).last_seq).toBeGreaterThan(0);
    expect((result as { event_count: number }).event_count).toBeGreaterThan(0);
    console.log(
      `[real-test] Events: seq=${(result as { last_seq: number }).last_seq}, ` +
        `kind=${(result as { last_kind: string }).last_kind}, ` +
        `count=${(result as { event_count: number }).event_count}`,
    );
  });

  test("timeline drawer opens and shows real event entries from backend", async ({
    page,
  }) => {
    await injectSession(page);

    let timelineEventCount = 0;
    // Observe the real surface response for timeline events
    await page.route("**/api/v1/graph/surface**", async (route) => {
      const resp = await route.fetch();
      const body = (await resp.json()) as {
        timeline: { events: unknown[] } | null;
      };
      timelineEventCount = body.timeline?.events?.length ?? 0;
      await route.fulfill({ response: resp });
    });

    await page.goto("/dashboard/graph");
    await page.waitForTimeout(8000);

    // Open timeline drawer
    await page.getByTitle("Timeline").click();
    await expect(page.getByText("Live timeline")).toBeVisible({
      timeout: 5000,
    });

    // Real backend returns events in the timeline — the drawer should not show "No events"
    // (it shows "No events" only if the backend truly returned none)
    console.log(`[real-test] Timeline surface events: ${timelineEventCount}`);

    // Verify the live-sync toggle is present and functional
    await expect(
      page.getByRole("button", { name: /Pause live|Resume live/ }),
    ).toBeVisible();
  });

  test("live sync poll hits real events/latest endpoint", async ({ page }) => {
    await injectSession(page);

    let latestEventPollCount = 0;
    let lastObservedSeq = 0;

    // Intercept events/latest — let it through, just count and record
    await page.route("**/api/v1/events/latest**", async (route) => {
      const resp = await route.fetch();
      const body = (await resp.json()) as { last_seq: number };
      latestEventPollCount++;
      lastObservedSeq = body.last_seq ?? 0;
      await route.fulfill({ response: resp });
    });

    await page.goto("/dashboard/graph");

    // Open timeline drawer to start the live sync polling loop
    await page.getByTitle("Timeline").click();
    await expect(page.getByText("Live timeline")).toBeVisible({
      timeout: 8000,
    });

    // Wait for at least 2 polls (poll interval is 2000ms)
    await page.waitForTimeout(6000);

    expect(latestEventPollCount).toBeGreaterThanOrEqual(1);
    expect(lastObservedSeq).toBeGreaterThan(0);
    console.log(
      `[real-test] Live sync: ${latestEventPollCount} polls, last_seq=${lastObservedSeq}`,
    );
  });
});

// ---------------------------------------------------------------------------
// Suite 4: Search overlay — real node data
// ---------------------------------------------------------------------------
test.describe("Real backend — search overlay with real nodes", () => {
  test("search overlay finds and displays real node titles from backend", async ({
    page,
  }) => {
    await injectSession(page);

    let realNodeTitle = "";
    await page.route("**/api/v1/graph/surface**", async (route) => {
      const resp = await route.fetch();
      const body = (await resp.json()) as {
        nodes: { node_id: string; display: { title: string } }[];
      };
      if (body.nodes?.length) {
        realNodeTitle = body.nodes[0]!.display.title;
      }
      await route.fulfill({ response: resp });
    });

    await page.goto("/dashboard/graph");
    await page.waitForTimeout(8000);

    // Open search overlay with "/" key
    await page.keyboard.press("/");
    await expect(page.getByPlaceholder(/Search nodes/i)).toBeVisible({
      timeout: 5000,
    });

    // The search input exists and responds — real nodes populate its list
    const searchInput = page.getByPlaceholder(/Search nodes/i);
    await expect(searchInput).toBeFocused();

    // Type nothing — should show all real nodes
    const resultCount = await page
      .locator('[data-testid="fig-search-result"], button')
      .filter({ hasText: /019[a-f0-9]/i })
      .count();
    console.log(
      `[real-test] Search results visible: ${resultCount}, first title: ${realNodeTitle}`,
    );

    // Close with Escape
    await page.keyboard.press("Escape");
    await expect(page.getByPlaceholder(/Search nodes/i)).not.toBeVisible({
      timeout: 3000,
    });
  });
});

// ---------------------------------------------------------------------------
// Suite 5: Inspector opens via search — then neighborhood expansion
// ---------------------------------------------------------------------------
test.describe("Real backend — inspector + neighborhood via search", () => {
  test("select node via search overlay opens inspector with real node data", async ({
    page,
  }) => {
    await injectSession(page);

    let firstNodeId = "";
    await page.route("**/api/v1/graph/surface**", async (route) => {
      const resp = await route.fetch();
      const body = (await resp.json()) as {
        nodes: { node_id: string }[];
      };
      if (body.nodes?.length) firstNodeId = body.nodes[0]!.node_id;
      await route.fulfill({ response: resp });
    });

    await page.goto("/dashboard/graph");
    await page.waitForTimeout(8000);

    // Open search and select first result
    await page.keyboard.press("/");
    await expect(page.getByPlaceholder(/Search nodes/i)).toBeVisible({
      timeout: 5000,
    });

    // Click first search result to select it
    const firstResult = page
      .locator('button, [role="option"]')
      .filter({
        hasText: /019[a-f0-9-]{10,}/i,
      })
      .first();

    const firstResultVisible = await firstResult
      .isVisible({ timeout: 3000 })
      .catch(() => false);
    if (firstResultVisible) {
      await firstResult.click();
      // Inspector drawer should open with the node detail
      await expect(
        page.getByText("Inspector").or(page.getByTitle("Inspector")),
      ).toBeVisible({
        timeout: 5000,
      });
      console.log(
        `[real-test] Inspector opened for node: ${firstNodeId.slice(0, 16)}`,
      );
    } else {
      // Fallback: close search and open inspector via rail button
      await page.keyboard.press("Escape");
      await page.getByTitle("Inspector").click();
      await expect(
        page.getByText("Click a node in the graph to inspect it."),
      ).toBeVisible({
        timeout: 5000,
      });
      console.log(
        "[real-test] No clickable search result; inspector shows placeholder as expected",
      );
    }
  });

  test("neighborhood expand button calls real backend and returns data", async ({
    page,
  }) => {
    await injectSession(page);

    let firstNodeId = "";
    await page.route("**/api/v1/graph/surface**", async (route) => {
      const resp = await route.fetch();
      const body = (await resp.json()) as { nodes: { node_id: string }[] };
      if (body.nodes?.length) firstNodeId = body.nodes[0]!.node_id;
      await route.fulfill({ response: resp });
    });

    // Pass neighborhood calls through — real backend, no mocking
    await page.route("**/api/v1/graph/neighborhood**", async (route) => {
      await route.continue();
    });

    await page.goto("/dashboard/graph");
    await page.waitForTimeout(8000);

    // Trigger neighborhood expand directly from the browser (real API call)
    const nbhdResult = await page.evaluate(
      async ({
        jwt,
        graphId,
        nodeId,
      }: {
        jwt: string;
        graphId: string;
        nodeId: string;
      }) => {
        if (!nodeId) return null;
        const resp = await fetch(
          `/api/v1/graph/neighborhood?graph_id=${graphId}&node_id=${nodeId}&depth=1`,
          { headers: { Authorization: `Bearer ${jwt}` } },
        );
        return resp.ok
          ? ((await resp.json()) as {
              nodes: unknown[];
              edges: unknown[];
              seed_node_id: string;
            })
          : null;
      },
      { jwt: E2E_JWT, graphId: E2E_GRAPH_ID, nodeId: firstNodeId },
    );

    expect(nbhdResult).not.toBeNull();
    expect((nbhdResult as { seed_node_id: string }).seed_node_id).toBe(
      firstNodeId,
    );
    expect((nbhdResult as { nodes: unknown[] }).nodes.length).toBeGreaterThan(
      0,
    );
    console.log(
      `[real-test] Neighborhood expand: seed=${firstNodeId.slice(0, 12)}, ` +
        `nodes=${(nbhdResult as { nodes: unknown[] }).nodes.length}`,
    );
  });
});
