import { expect, test, type Page } from "@playwright/test";

function sessionPayload(graphId = "control-center-graph") {
  return {
    user: {
      name: "Control Center Tester",
      email: "control-center@example.com",
      image: null,
    },
    expires: "2099-01-01T00:00:00.000Z",
    accessToken: "control-center-token",
    graphId,
    isAdmin: true,
  };
}

async function mockAuthenticatedAdminSession(page: Page, graphId?: string) {
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
        body: JSON.stringify({ csrfToken: "control-center-csrf" }),
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

test.describe("Control Center", () => {
  test("renders the enterprise console and legacy routes redirect", async ({
    page,
  }) => {
    await mockAuthenticatedAdminSession(page, "control-center-graph");

    await page.route("**/api/admin/status", async (route) => {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "ok",
          health: {
            status: "ok",
            timestamp: "2026-05-04T08:00:00Z",
          },
          readiness: {
            status: "ready",
            db_connected: true,
            tables_ok: true,
            migrations_ok: true,
            latest_migration: 23,
            applied_migration: 23,
            missing_tables: [],
          },
          version: {
            version: "1.0.0",
            stage: "localprod",
            build_time: "2026-05-04T07:30:00Z",
            features: {},
          },
          runtime: {
            env: "production",
            mode: "production",
            public_origin: "https://faimatrix.localhost:8443",
            cors_origins: ["https://faimatrix.localhost:8443"],
            backup_dir: "/var/lib/faim/backups",
            raw_store_path: "/var/lib/faim/raw/blobs",
            auth_db_primary: true,
            auth_scope_enforcement_enabled: true,
            enable_cache: true,
            enable_index: true,
            enable_jobs: true,
            encryption_at_rest: true,
            encryption_fail_closed: true,
            admin_key_configured: true,
          },
          backups: [
            {
              name: "backup_faim_20260504.sql.gz",
              kind: "database",
              compressed: true,
              path: "/var/lib/faim/backups/backup_faim_20260504.sql.gz",
              size_bytes: 2048,
              modified_at: "2026-05-04T07:45:00Z",
            },
          ],
          alerts: [
            {
              id: "health:ok",
              severity: "warning",
              title: "Service health degraded",
              message:
                "Health endpoint returned degraded. Investigate the API and proxy layer.",
              source: "health",
              created_at: "2026-05-04T07:50:00Z",
              acknowledged: false,
            },
          ],
          alert_delivery: {
            provider: "resend",
            enabled: true,
            from_email: "FAIMATRIX <noreply@faimatrix.com>",
            recipients: ["ops@faimatrix.com"],
            recipients_count: 1,
          },
        }),
      });
    });

    await page.goto("/dashboard/control-plane");
    await expect(
      page.getByRole("heading", { name: "Control Center" }),
    ).toBeVisible();
    await expect(page.getByRole("tab", { name: "Overview" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    await expect(page.getByRole("tabpanel")).toContainText("Service health");
    await expect(page.getByText("Send alerts email")).toHaveCount(0);
    await expect(page.getByText("Send test email")).toHaveCount(0);

    await page.getByRole("tab", { name: "Incidents" }).click();
    await expect(page.getByRole("tab", { name: "Incidents" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    await expect(page.getByRole("tabpanel")).toContainText("Incident workflow");

    await page.getByRole("tab", { name: "Security" }).click();
    await expect(page.getByRole("tab", { name: "Security" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    await expect(page.getByRole("tabpanel")).toContainText("Role assignments");

    await page.goto("/dashboard/admin");
    await expect(page).toHaveURL(/\/dashboard\/control-plane/);

    await page.goto("/dashboard/admin/alerts");
    await expect(page).toHaveURL(/section=incidents/);
    await expect(
      page.getByRole("heading", { name: "Incidents" }),
    ).toBeVisible();
  });
});
