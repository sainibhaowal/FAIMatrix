import { expect, test, type Page } from "@playwright/test";

function sessionPayload(graphId = "phase-f-graph") {
  return {
    user: {
      name: "Phase F Tester",
      email: "phase-f@example.com",
      image: null,
    },
    expires: "2099-01-01T00:00:00.000Z",
    accessToken: "phase-f-token",
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
        body: JSON.stringify({ csrfToken: "phase-f-csrf" }),
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

test.describe("Storage Phase F Validation", () => {
  test("queue supports per-file cancel/retry lifecycle transitions", async ({ page }) => {
    await mockAuthenticatedSession(page, "phase-f-queue");

    let uploadCount = 0;
    let cancelRequestedForJob = false;

    await page.route("**/api/v1/storage/**", async (route) => {
      const req = route.request();
      const url = new URL(req.url());
      const path = url.pathname;

      if (path.endsWith("/summary") && req.method() === "GET") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            graph_id: "phase-f-queue",
            total_files: 2,
            total_bytes: 64,
            by_status: { ingested: 1, failed: 1, dedup_hit: 0 },
            by_type: { "text/plain": 2 },
          }),
        });
      }
      if (path.endsWith("/supported-types") && req.method() === "GET") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            max_upload_size_bytes: 10485760,
            max_upload_size_mb: 10,
            total_extensions: 45,
            total_content_types: 29,
            extensions: [".txt", ".pdf", ".png"],
            content_types: ["text/plain", "application/pdf", "image/png"],
            categories: {
              documents: [".pdf"],
              images: [".png"],
              code: [".py"],
              text_data: [".txt"],
              other: [],
            },
            extractor_doc_types: { pdf: 1, image: 1, text: 1 },
            ocr_enabled: false,
            ocr_engine: "tesseract",
            ocr_fail_closed: false,
            ocr_capable_extensions: [".pdf", ".png"],
          }),
        });
      }

      if (path.endsWith("/backends/health") && req.method() === "GET") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            postgres: true,
            redis: true,
            qdrant: false,
            raw_store: true,
          }),
        });
      }

      if (path.endsWith("/files") && req.method() === "GET") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            items: [],
            total: 0,
            limit: 20,
            offset: 0,
          }),
        });
      }

      if (path.endsWith("/uploads") && req.method() === "POST") {
        uploadCount += 1;
        if (uploadCount === 1) {
          return route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              job_id: "job-retry",
              graph_id: "phase-f-queue",
              status: "failed",
              requested_files: 1,
              processed_files: 1,
              success_files: 0,
              failed_files: 1,
              dedup_hits: 0,
              cancelled_files: 0,
              files: [
                {
                  filename: "retry.txt",
                  status: "failed",
                  raw_id: "11111111-1111-1111-1111-111111111111",
                  packet_hash: null,
                  node_count: 0,
                  vector_count: 0,
                  error: "extract parser failed",
                },
              ],
            }),
          });
        }

        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            job_id: "job-cancel",
            graph_id: "phase-f-queue",
            status: "running",
            requested_files: 1,
            processed_files: 0,
            success_files: 0,
            failed_files: 0,
            dedup_hits: 0,
            cancelled_files: 0,
            files: [
              {
                filename: "cancel.txt",
                status: "ingesting",
                raw_id: "22222222-2222-2222-2222-222222222222",
                packet_hash: null,
                node_count: 0,
                vector_count: 0,
                error: null,
              },
            ],
          }),
        });
      }

      if (path.endsWith("/uploads/job-retry") && req.method() === "GET") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            job_id: "job-retry",
            graph_id: "phase-f-queue",
            status: "failed",
            requested_files: 1,
            processed_files: 1,
            success_files: 0,
            failed_files: 1,
            dedup_hits: 0,
            cancelled_files: 0,
            cancel_requested: false,
            files: [
              {
                raw_id: "11111111-1111-1111-1111-111111111111",
                graph_id: "phase-f-queue",
                filename: "retry.txt",
                mime_type: "text/plain",
                size_bytes: 24,
                sha256: "sha-retry",
                ingest_status: "failed",
                packet_hash: null,
                node_count: 0,
                vector_count: 0,
                error: "extract parser failed",
                uploaded_at: "2026-02-11T00:00:00Z",
                ingested_at: null,
                updated_at: "2026-02-11T00:00:01Z",
                delete_requested: false,
              },
            ],
          }),
        });
      }

      if (path.endsWith("/uploads/job-cancel") && req.method() === "GET") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            job_id: "job-cancel",
            graph_id: "phase-f-queue",
            status: cancelRequestedForJob ? "cancelled" : "running",
            requested_files: 1,
            processed_files: cancelRequestedForJob ? 1 : 0,
            success_files: 0,
            failed_files: 0,
            dedup_hits: 0,
            cancelled_files: cancelRequestedForJob ? 1 : 0,
            cancel_requested: cancelRequestedForJob,
            cancel_reason: cancelRequestedForJob ? "Requested from storage UI" : null,
            files: [
              {
                raw_id: "22222222-2222-2222-2222-222222222222",
                graph_id: "phase-f-queue",
                filename: "cancel.txt",
                mime_type: "text/plain",
                size_bytes: 24,
                sha256: "sha-cancel",
                ingest_status: cancelRequestedForJob ? "cancelled" : "ingesting",
                packet_hash: null,
                node_count: 0,
                vector_count: 0,
                error: cancelRequestedForJob ? "Cancelled from UI" : null,
                uploaded_at: "2026-02-11T00:00:00Z",
                ingested_at: null,
                updated_at: "2026-02-11T00:00:02Z",
                delete_requested: false,
              },
            ],
          }),
        });
      }

      if (path.endsWith("/uploads/job-retry/events") && req.method() === "GET") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            job_id: "job-retry",
            events: [
              { seq: 1, kind: "step_start", ts: "2026-02-11T00:00:00Z", payload: { message: "started" } },
              {
                seq: 2,
                kind: "step_progress",
                ts: "2026-02-11T00:00:01Z",
                payload: { status: "failed", message: "extract parser failed" },
              },
            ],
          }),
        });
      }

      if (path.endsWith("/uploads/job-cancel/events") && req.method() === "GET") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            job_id: "job-cancel",
            events: [
              { seq: 1, kind: "step_start", ts: "2026-02-11T00:00:00Z", payload: { message: "started" } },
              {
                seq: 2,
                kind: "step_progress",
                ts: "2026-02-11T00:00:01Z",
                payload: { status: cancelRequestedForJob ? "cancelled" : "ingesting", message: "running" },
              },
            ],
          }),
        });
      }

      if (path.endsWith("/uploads/job-cancel/cancel") && req.method() === "POST") {
        cancelRequestedForJob = true;
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            job_id: "job-cancel",
            status: "cancel_requested",
            cancel_requested: true,
            cancel_reason: "Requested from storage UI",
          }),
        });
      }

      if (
        path.endsWith("/files/11111111-1111-1111-1111-111111111111/retry") &&
        req.method() === "POST"
      ) {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            status: "ok",
            file: {
              raw_id: "11111111-1111-1111-1111-111111111111",
              graph_id: "phase-f-queue",
              filename: "retry.txt",
              mime_type: "text/plain",
              size_bytes: 24,
              sha256: "sha-retry",
              ingest_status: "ingested",
              packet_hash: "packet-retry",
              node_count: 2,
              vector_count: 2,
              error: null,
              uploaded_at: "2026-02-11T00:00:00Z",
              ingested_at: "2026-02-11T00:00:03Z",
              updated_at: "2026-02-11T00:00:03Z",
              delete_requested: false,
            },
            ingest: {
              status: "completed",
              packet_hash: "packet-retry",
              nodes_written: 2,
              vector_count: 2,
              error: null,
            },
          }),
        });
      }

      return route.fulfill({
        status: 404,
        contentType: "application/json",
        body: JSON.stringify({ detail: `unmocked ${req.method()} ${path}` }),
      });
    });

    await page.goto("/dashboard/storage");
    await expect(page.getByTestId("storage-page-title")).toBeVisible();
    await expect(page.getByTestId("storage-supported-types-open")).toContainText(
      "Supported Files (45)"
    );
    await page.getByTestId("storage-supported-types-open").click();
    await expect(page.getByTestId("storage-supported-types-panel")).toBeVisible();
    await page.keyboard.press("Escape");

    await page.setInputFiles('input[type="file"]', [
      { name: "retry.txt", mimeType: "text/plain", buffer: Buffer.from("retry payload") },
      { name: "cancel.txt", mimeType: "text/plain", buffer: Buffer.from("cancel payload") },
    ]);

    const retryRow = page
      .locator('[data-testid="storage-queue-item"][data-filename="retry.txt"]')
      .first();
    await expect(retryRow).toBeVisible();
    await expect(retryRow).toContainText("failed");

    await retryRow.getByTestId("storage-queue-retry").click();
    await expect(retryRow).toContainText("ingested");

    const cancelRow = page
      .locator('[data-testid="storage-queue-item"][data-filename="cancel.txt"]')
      .first();
    await expect(cancelRow).toBeVisible();
    await cancelRow.getByTestId("storage-queue-cancel").click();
    await expect(cancelRow).toContainText("cancelled");
  });

  test("provenance panel loads inspect details from backend contract", async ({ page }) => {
    await mockAuthenticatedSession(page, "phase-f-provenance");

    await page.route("**/api/v1/storage/**", async (route) => {
      const req = route.request();
      const url = new URL(req.url());
      const path = url.pathname;

      if (path.endsWith("/summary") && req.method() === "GET") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            graph_id: "phase-f-provenance",
            total_files: 1,
            total_bytes: 128,
            by_status: { ingested: 1 },
            by_type: { "text/plain": 1 },
          }),
        });
      }
      if (path.endsWith("/supported-types") && req.method() === "GET") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            max_upload_size_bytes: 10485760,
            max_upload_size_mb: 10,
            total_extensions: 45,
            total_content_types: 29,
            extensions: [".txt", ".pdf", ".png"],
            content_types: ["text/plain", "application/pdf", "image/png"],
            categories: {
              documents: [".pdf"],
              images: [".png"],
              code: [".py"],
              text_data: [".txt"],
              other: [],
            },
            extractor_doc_types: { pdf: 1, image: 1, text: 1 },
            ocr_enabled: false,
            ocr_engine: "tesseract",
            ocr_fail_closed: false,
            ocr_capable_extensions: [".pdf", ".png"],
          }),
        });
      }
      if (path.endsWith("/backends/health") && req.method() === "GET") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            postgres: true,
            redis: true,
            qdrant: true,
            raw_store: true,
          }),
        });
      }
      if (path.endsWith("/files") && req.method() === "GET") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            items: [
              {
                raw_id: "33333333-3333-3333-3333-333333333333",
                graph_id: "phase-f-provenance",
                filename: "prov.txt",
                mime_type: "text/plain",
                size_bytes: 128,
                sha256: "sha-prov",
                ingest_status: "ingested",
                packet_hash: "packet-prov",
                node_count: 3,
                vector_count: 3,
                error: null,
                uploaded_at: "2026-02-11T00:00:00Z",
                ingested_at: "2026-02-11T00:00:01Z",
                updated_at: "2026-02-11T00:00:01Z",
                delete_requested: false,
              },
            ],
            total: 1,
            limit: 20,
            offset: 0,
          }),
        });
      }
      if (path.endsWith("/files/33333333-3333-3333-3333-333333333333/provenance") && req.method() === "GET") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            file: {
              raw_id: "33333333-3333-3333-3333-333333333333",
              graph_id: "phase-f-provenance",
              filename: "prov.txt",
              mime_type: "text/plain",
              size_bytes: 128,
              sha256: "sha-prov",
              ingest_status: "ingested",
              packet_hash: "packet-prov",
              node_count: 3,
              vector_count: 3,
              error: null,
              uploaded_at: "2026-02-11T00:00:00Z",
              ingested_at: "2026-02-11T00:00:01Z",
              updated_at: "2026-02-11T00:00:01Z",
              delete_requested: false,
            },
            raw_ref: {
              raw_id: "33333333-3333-3333-3333-333333333333",
              sha256: "sha-prov",
              uri: "raw://tenant/33/3333333333333333333333333333333333333333333333333333333333333333",
              mime_type: "text/plain",
              size_bytes: 128,
              created_at: "2026-02-11T00:00:00Z",
            },
            dedup: {
              packet_hash: "packet-prov",
              dedup_record_found: true,
              dedup_raw_id: "33333333-3333-3333-3333-333333333333",
              dedup_node_count: 3,
              dedup_created_at: "2026-02-11T00:00:01Z",
            },
            node_count: 1,
            event_count: 1,
            nodes: [
              {
                node_id: "node-1",
                kind: "atom",
                vector_hash: "vh-1",
                block_id: "block-1",
                created_at: "2026-02-11T00:00:01Z",
              },
            ],
            events: [{ seq: 1, kind: "INGEST_COMPLETED", ts: "2026-02-11T00:00:01Z", payload_keys: ["raw_id"] }],
          }),
        });
      }

      return route.fulfill({
        status: 404,
        contentType: "application/json",
        body: JSON.stringify({ detail: `unmocked ${req.method()} ${path}` }),
      });
    });

    await page.goto("/dashboard/storage");
    await expect(page.getByTestId("storage-page-title")).toBeVisible();

    await page.getByTestId("storage-file-inspect").first().click();

    await expect(page.getByTestId("storage-provenance-panel")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Provenance Inspect" })).toBeVisible();
    await expect(page.locator("text=filename:").first()).toBeVisible();
    await expect(page.locator("text=prov.txt").first()).toBeVisible();
    await expect(page.locator("text=dedup_record_found:").first()).toBeVisible();
  });
});
