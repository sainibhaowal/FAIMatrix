import { expect, test, type Page } from "@playwright/test";

function sessionPayload(graphId = "phase-r6-graph") {
  return {
    user: {
      name: "Phase R6 Tester",
      email: "phase-r6@example.com",
      image: null,
    },
    expires: "2099-01-01T00:00:00.000Z",
    accessToken: "phase-r6-token",
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
        body: JSON.stringify({ csrfToken: "phase-r6-csrf" }),
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

test.describe("Evolution Phase R6 Validation", () => {
  test("shows requested vs effective mode from backend responses and timeline events", async ({
    page,
  }) => {
    await mockAuthenticatedSession(page, "phase-r6-graph");

    await page.route("**/api/v1/**", async (route) => {
      const req = route.request();
      const url = new URL(req.url());
      const path = url.pathname;

      if (path.endsWith("/metrics/scorecard") && req.method() === "GET") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            graph_id: "phase-r6-graph",
            graph_version: 42,
            graph_hash: "hash-r6-001",
            dimension_D: 1.42,
            entropy_H: 0.37,
            pressure_lambda: 0.11,
            node_count: 123,
            edge_count: 321,
            redundancy: 0.21,
            novelty: 0.79,
            energy: 0.44,
            computed_at: "2026-02-20T10:00:00Z",
          }),
        });
      }

      if (path.endsWith("/events/latest") && req.method() === "GET") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            graph_id: "phase-r6-graph",
            last_seq: 7,
            last_kind: "EVOLUTION_COMPLETE",
            last_ts: "2026-02-20T10:00:00Z",
            snapshot_hash: "snapshot-r6",
            event_count: 7,
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
              graph_id: "phase-r6-graph",
              tenant_id: "tenant-r6",
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
            graph_id: "phase-r6-graph",
            tenant_id: "tenant-r6",
            has_more: false,
            next_seq: 7,
            count: 2,
            events: [
              {
                seq: 6,
                id: "evt-r6-6",
                kind: "DIAGNOSTICS_SNAPSHOT",
                ts: "2026-02-20T10:00:00Z",
                payload: {
                  metrics: {
                    D: 1.42,
                    H: 0.37,
                    lambda: 0.11,
                  },
                },
              },
              {
                seq: 7,
                id: "evt-r6-7",
                kind: "EVOLUTION_COMPLETE",
                ts: "2026-02-20T10:00:01Z",
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
          }),
        });
      }

      if (path.endsWith("/evolve/status") && req.method() === "GET") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            graph_id: "phase-r6-graph",
            tenant_id: "tenant-r6",
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
              graph_id: "phase-r6-graph",
              graph_version: 42,
              last_seen_version: 42,
              last_evolved_version: 41,
              last_evolved_at: "2026-02-20T09:58:00Z",
              last_enqueued_job_id: "job-r6-enqueued",
            },
            due: {
              source: "memory_write",
              is_due: true,
              reason: "version_delta_met",
              graph_version: 42,
              last_seen_version: 42,
              last_evolved_version: 41,
              version_delta: 1,
              min_version_delta: 1,
              min_interval_seconds: 300,
              elapsed_since_last_evolved_seconds: 420,
            },
            active_job: null,
            last_enqueued_job: {
              job_id: "job-r6-enqueued",
              status: "pending",
              created_at: "2026-02-20T09:59:00Z",
              updated_at: "2026-02-20T09:59:05Z",
              started_at: null,
              completed_at: null,
              error_message: null,
              source: "memory_write",
              trigger_graph_version: 42,
              trigger_version_delta: 1,
              self_invent_requested: true,
            },
            last_event: {
              last_event_seq: 7,
              last_event_kind: "EVOLUTION_COMPLETE",
              last_event_ts: "2026-02-20T10:00:01Z",
              last_snapshot_hash: "snapshot-r6",
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
            graph_version: 43,
            merges: 3,
            prunes: 1,
            inventions: 2,
            diagnostics: { profile: "fast" },
            events_emitted: ["EVOLUTION_COMPLETE"],
            latency_ms: 211,
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
    await expect(
      page.getByRole("heading", { name: "Evolution Control Plane" }),
    ).toBeVisible();
    await expect(
      page.locator("text=Requested mode: strict/relaxed"),
    ).toBeVisible();
    await expect(
      page.locator(
        "text=Backend will return effective mode and durability for each run.",
      ),
    ).toBeVisible();

    await page.getByRole("button", { name: "Run evolve now" }).click();

    await expect(
      page.locator(
        "text=Requested strict/relaxed -> Effective fast/strict | durability: sync_strict",
      ),
    ).toBeVisible();
    await expect(
      page.locator(
        "text=completion: sync_strict | aggressiveness: performance",
      ),
    ).toBeVisible();
    await expect(
      page.locator(
        "text=Completed: merges=2, prunes=1, inventions=1 | mode strict/relaxed -> fast/strict (sync_strict)",
      ),
    ).toBeVisible();
  });
});
