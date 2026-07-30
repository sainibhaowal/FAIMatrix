import { expect, test, type Page } from "@playwright/test";

function sessionPayload(graphId = "r6-storage-graph") {
  return {
    user: {
      name: "R6 Storage Tester",
      email: "r6-storage@example.com",
      image: null,
    },
    expires: "2099-01-01T00:00:00.000Z",
    accessToken: "r6-storage-token",
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
        body: JSON.stringify({ csrfToken: "r6-storage-csrf" }),
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

test.describe("Storage R6", () => {
  test("shows requested vs effective mode on queue items", async ({ page }) => {
    await mockAuthenticatedSession(page, "r6-storage-graph");

    await page.route("**/api/v1/storage/**", async (route) => {
      const req = route.request();
      const url = new URL(req.url());
      const path = url.pathname;

      if (path.endsWith("/summary") && req.method() === "GET") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            graph_id: "r6-storage-graph",
            total_files: 1,
            total_bytes: 100,
            by_status: { ingested: 1, failed: 0, dedup_hit: 0 },
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
            total_extensions: 3,
            total_content_types: 1,
            extensions: [".txt", ".md", ".pdf"],
            content_types: ["text/plain"],
            categories: {
              documents: [".pdf"],
              images: [],
              code: [],
              text_data: [".txt"],
              other: [],
            },
            extractor_doc_types: { text: 1 },
            ocr_enabled: false,
            ocr_engine: "tesseract",
            ocr_fail_closed: false,
            ocr_capable_extensions: [".pdf"],
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
            items: [],
            total: 0,
            limit: 20,
            offset: 0,
          }),
        });
      }
      if (path.endsWith("/uploads") && req.method() === "POST") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            job_id: "r6-upload-job",
            graph_id: "r6-storage-graph",
            status: "ingested",
            requested_files: 1,
            processed_files: 1,
            success_files: 1,
            failed_files: 0,
            dedup_hits: 0,
            cancelled_files: 0,
            requested_profile: "strict",
            requested_persist_mode: "relaxed",
            effective_profile: "strict",
            effective_persist_mode: "relaxed",
            durability_path: "core_sync_secondary_async",
            files: [
              {
                filename: "mode.txt",
                status: "ingested",
                raw_id: "44444444-4444-4444-4444-444444444444",
                packet_hash: "packet-r6",
                node_count: 1,
                vector_count: 1,
                error: null,
                requested_profile: "strict",
                requested_persist_mode: "relaxed",
                effective_profile: "strict",
                effective_persist_mode: "relaxed",
                durability_path: "core_sync_secondary_async",
              },
            ],
          }),
        });
      }
      if (path.endsWith("/uploads/r6-upload-job") && req.method() === "GET") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            job_id: "r6-upload-job",
            graph_id: "r6-storage-graph",
            status: "done",
            requested_files: 1,
            processed_files: 1,
            success_files: 1,
            failed_files: 0,
            dedup_hits: 0,
            cancelled_files: 0,
            cancel_requested: false,
            requested_profile: "strict",
            requested_persist_mode: "relaxed",
            effective_profile: "strict",
            effective_persist_mode: "relaxed",
            durability_path: "core_sync_secondary_async",
            files: [
              {
                raw_id: "44444444-4444-4444-4444-444444444444",
                graph_id: "r6-storage-graph",
                filename: "mode.txt",
                mime_type: "text/plain",
                size_bytes: 11,
                sha256: "sha-mode",
                ingest_status: "ingested",
                packet_hash: "packet-r6",
                node_count: 1,
                vector_count: 1,
                error: null,
                uploaded_at: "2026-02-20T00:00:00Z",
                ingested_at: "2026-02-20T00:00:01Z",
                updated_at: "2026-02-20T00:00:01Z",
                delete_requested: false,
              },
            ],
          }),
        });
      }
      if (
        path.endsWith("/uploads/r6-upload-job/events") &&
        req.method() === "GET"
      ) {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            job_id: "r6-upload-job",
            events: [],
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
    await expect(
      page.locator("text=Requested mode: strict/relaxed"),
    ).toBeVisible();

    await page.setInputFiles('input[type="file"]', [
      {
        name: "mode.txt",
        mimeType: "text/plain",
        buffer: Buffer.from("mode payload"),
      },
    ]);

    const row = page
      .locator('[data-testid="storage-queue-item"][data-filename="mode.txt"]')
      .first();
    await expect(row).toBeVisible();
    await expect(row.getByTestId("storage-queue-mode")).toContainText(
      "Requested strict/relaxed -> Effective strict/relaxed | durability: core_sync_secondary_async",
    );
  });
});
