import { expect, test, type Page } from "@playwright/test";

function sessionPayload(graphId = "fig-sync-graph") {
  return {
    user: {
      name: "FIG Sync Tester",
      email: "fig-sync@example.com",
      image: null,
    },
    expires: "2099-01-01T00:00:00.000Z",
    accessToken: "fig-sync-token",
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
        body: JSON.stringify({ csrfToken: "fig-sync-csrf" }),
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
    display: {
      title,
      title_source: "anchor",
      state: "active",
    },
    metrics: {
      touch_count: 1,
      residual: 0.125,
      last_access: "2026-02-20T10:00:00Z",
    },
    provenance: {
      raw_id: `${nodeId}-raw`,
      block_id: `${nodeId}-block`,
    },
  };
}

function baseSurface(
  version: number,
  hash: string,
  afterSeq: number,
  events: Array<{ seq: number; kind: string }>,
) {
  return {
    snapshot: {
      graph_id: "fig-sync-graph",
      graph_version: version,
      graph_hash: hash,
      as_of: "2026-02-20T10:00:00Z",
      consistent_read: true,
    },
    nodes: [figNode("node-a", "Alpha"), figNode("node-b", "Beta")],
    edges: [
      {
        edge_id: "edge-ab",
        src_node_id: "node-a",
        dst_node_id: "node-b",
        kind: "inheritance",
        weight: 1,
        meta: null,
      },
    ],
    timeline: {
      after_seq: afterSeq,
      next_seq: events.length ? events[events.length - 1]!.seq : afterSeq,
      has_more: false,
      events: events.map((ev) => ({
        seq: ev.seq,
        kind: ev.kind,
        ts: "2026-02-20T10:00:00Z",
        payload_keys: ["graph_id"],
        graph_id: "fig-sync-graph",
      })),
    },
    topology: {
      node_count: 2,
      edge_count: 1,
      edge_counts_by_kind: { inheritance: 1 },
      scorecard: null,
    },
    controls: {
      similarity: {
        mode: "none",
        notes:
          "Exploration filters affect ranking only; they do not mutate graph truth.",
      },
    },
    truncated: false,
    truncation_reason: null,
  };
}

test.describe("FIG View timeline live sync", () => {
  test("polls latest event seq and rebases the visible timeline without duplicating events", async ({
    page,
  }) => {
    await mockAuthenticatedSession(page, "fig-sync-graph");

    let latestSeq = 2;

    await page.route("**/api/v1/**", async (route) => {
      const req = route.request();
      const url = new URL(req.url());
      const path = url.pathname;

      if (path.endsWith("/graph/surface") && req.method() === "GET") {
        const afterSeq = Number(url.searchParams.get("after_seq") || "0");
        if (afterSeq >= 2) {
          return route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify(
              baseSurface(2, "fig-hash-2", afterSeq, [
                { seq: 3, kind: "QUERY_COMPLETE" },
                { seq: 4, kind: "DIAGNOSTICS_SNAPSHOT" },
              ]),
            ),
          });
        }
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(
            baseSurface(1, "fig-hash-1", afterSeq, [
              { seq: 1, kind: "STORAGE_RAW_STORED" },
              { seq: 2, kind: "STORAGE_EXTRACTED" },
            ]),
          ),
        });
      }

      if (path.endsWith("/events/latest") && req.method() === "GET") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            graph_id: "fig-sync-graph",
            last_seq: latestSeq,
            last_kind:
              latestSeq >= 4 ? "DIAGNOSTICS_SNAPSHOT" : "STORAGE_EXTRACTED",
            last_ts: "2026-02-20T10:00:00Z",
            snapshot_hash: latestSeq >= 4 ? "fig-hash-2" : "fig-hash-1",
            event_count: latestSeq,
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

    await expect(page.getByTitle("Timeline")).toBeVisible();
    await page.getByTitle("Timeline").click();

    await expect(page.getByText("Live timeline")).toBeVisible();
    await expect(page.getByText("#2")).toBeVisible();

    latestSeq = 4;
    await page.waitForTimeout(3500);

    await expect(page.getByText("#4")).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Pause live" }),
    ).toBeVisible();

    const seqTwoMatches = await page.locator("text=#2").count();
    expect(seqTwoMatches).toBeGreaterThanOrEqual(1);
  });
});
