import { expect, test, type Page } from "@playwright/test";

function sessionPayload(graphId = "r6-evolution-graph") {
  return {
    user: {
      name: "R6 Evolution Tester",
      email: "r6-evolution@example.com",
      image: null,
    },
    expires: "2099-01-01T00:00:00.000Z",
    accessToken: "r6-evolution-token",
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
        body: JSON.stringify({ csrfToken: "r6-evolution-csrf" }),
      });
    }
    if (path.endsWith("/providers")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({}),
      });
    }
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({}),
    });
  });
}

test.describe("Evolution R6", () => {
  test("shows effective mode from evolve response and event timeline", async ({
    page,
  }) => {
    await mockAuthenticatedSession(page, "r6-evolution-graph");

    await page.route("**/api/v1/**", async (route) => {
      const req = route.request();
      const url = new URL(req.url());
      const path = url.pathname;

      if (path.endsWith("/metrics/scorecard") && req.method() === "GET") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            graph_id: "r6-evolution-graph",
            graph_version: 9,
            graph_hash: "hash-r6-evo",
            dimension_D: 1.1,
            entropy_H: 0.2,
            pressure_lambda: 0.3,
            node_count: 50,
            edge_count: 75,
            redundancy: 0.4,
            novelty: 0.6,
            energy: 0.8,
            computed_at: "2026-02-20T10:00:00Z",
          }),
        });
      }
      if (path.endsWith("/events/latest") && req.method() === "GET") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            graph_id: "r6-evolution-graph",
            last_seq: 12,
            last_kind: "EVOLUTION_COMPLETE",
            last_ts: "2026-02-20T10:00:00Z",
            snapshot_hash: "snapshot-r6-evo",
            event_count: 12,
          }),
        });
      }
      if (path.endsWith("/storage/summary") && req.method() === "GET") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            graph_id: "r6-evolution-graph",
            total_files: 4,
            total_bytes: 123456,
            by_status: {
              ingested: 4,
            },
            by_type: {
              "application/pdf": 4,
            },
          }),
        });
      }
      if (path.endsWith("/storage/files") && req.method() === "GET") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            items: [
              {
                raw_id: "raw-r6-1",
                graph_id: "r6-evolution-graph",
                filename: "doc1.pdf",
                mime_type: "application/pdf",
                size_bytes: 12345,
                sha256: "sha-r6-1",
                ingest_status: "ingested",
                packet_hash: "packet-r6-1",
                node_count: 10,
                vector_count: 10,
                error: null,
                uploaded_at: "2026-02-20T09:00:00Z",
                ingested_at: "2026-02-20T09:00:05Z",
                updated_at: "2026-02-20T09:00:05Z",
                delete_requested: false,
              },
            ],
            total: 1,
            limit: 5,
            offset: 0,
          }),
        });
      }
      if (path.endsWith("/events") && req.method() === "GET") {
        const afterSeq = Number(url.searchParams.get("after_seq") || "0");
        if (afterSeq > 0) {
          return route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              graph_id: "r6-evolution-graph",
              tenant_id: "tenant-r6-evo",
              events: [],
              has_more: false,
              next_seq: afterSeq,
              count: 0,
            }),
          });
        }
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            graph_id: "r6-evolution-graph",
            tenant_id: "tenant-r6-evo",
            events: [
              {
                seq: 12,
                id: "event-r6-12",
                kind: "EVOLUTION_COMPLETE",
                ts: "2026-02-20T10:00:00Z",
                payload: {
                  merges: 2,
                  prunes: 1,
                  inventions: 1,
                  requested_profile: "strict",
                  requested_persist_mode: "relaxed",
                  effective_profile: "fast",
                  effective_persist_mode: "strict",
                  durability_path: "sync_strict",
                },
              },
            ],
            has_more: false,
            next_seq: 12,
            count: 1,
          }),
        });
      }
      if (path.endsWith("/evolve/status") && req.method() === "GET") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            graph_id: "r6-evolution-graph",
            tenant_id: "tenant-r6-evo",
            runtime: {
              self_evolve_enabled: true,
              self_evolve_trigger_mode: "hybrid",
              self_evolve_min_interval_seconds: 300,
              self_evolve_min_version_delta: 1,
              self_evolve_max_actions: 100,
              self_evolve_scan_interval_seconds: 30,
              self_invent_enabled: true,
              self_invent_on_evolve: true,
              jobs_enabled: true,
            },
            state: {
              graph_id: "r6-evolution-graph",
              graph_version: 9,
              last_seen_version: 9,
              last_evolved_version: 8,
              last_evolved_at: "2026-02-20T09:58:00Z",
              last_enqueued_job_id: "job-r6-evo",
            },
            due: {
              source: "memory_write",
              is_due: true,
              reason: "version_delta_met",
              graph_version: 9,
              last_seen_version: 9,
              last_evolved_version: 8,
              version_delta: 1,
              min_version_delta: 1,
              min_interval_seconds: 300,
              elapsed_since_last_evolved_seconds: 420,
            },
            active_job: null,
            last_enqueued_job: null,
            last_event: {
              last_event_seq: 12,
              last_event_kind: "EVOLUTION_COMPLETE",
              last_event_ts: "2026-02-20T10:00:00Z",
              last_snapshot_hash: "snapshot-r6-evo",
              last_skip_reason: null,
            },
          }),
        });
      }
      if (path.endsWith("/evolve") && req.method() === "POST") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            status: "completed",
            graph_version: 10,
            merges: 3,
            prunes: 1,
            inventions: 2,
            diagnostics: {},
            events_emitted: ["EVOLUTION_COMPLETE"],
            latency_ms: 120,
            requested_profile: "strict",
            requested_persist_mode: "relaxed",
            effective_profile: "fast",
            effective_persist_mode: "strict",
            durability_path: "sync_strict",
            evolve_aggressiveness: "performance",
            completion_mode: "sync_strict",
            state_update_status: "updated",
            state_update_error: null,
            error: null,
          }),
        });
      }

      return route.fulfill({
        status: 404,
        contentType: "application/json",
        body: JSON.stringify({ detail: `unmocked ${req.method()} ${path}` }),
      });
    });

    await page.goto("/dashboard/evolution");
    await expect(page.getByTestId("evolution-page-title")).toBeVisible();
    await expect(
      page.locator("text=Requested mode: strict/relaxed"),
    ).toBeVisible();

    await page.getByRole("button", { name: "Run evolve now" }).click();

    await expect(
      page
        .locator(
          "text=Requested strict/relaxed -> Effective fast/strict | durability: sync_strict",
        )
        .first(),
    ).toBeVisible();
    await expect(
      page
        .locator(
          "text=Completed: merges=2, prunes=1, inventions=1 | mode strict/relaxed -> fast/strict (sync_strict)",
        )
        .first(),
    ).toBeVisible();
  });
});
