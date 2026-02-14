import { expect, test } from "@playwright/test";

type KeyItem = {
  tenant_id: string;
  key_id: string;
  key_prefix: string;
  scopes: string[];
  created_at: string;
  created_by: string | null;
  expires_at: string | null;
  revoked_at: string | null;
  revoked_reason: string | null;
  rotated_from_key_id: string | null;
  last_used_at: string | null;
  is_active: boolean;
};

type MockOptions = {
  failCreate?: boolean;
};

function isoNow(): string {
  return new Date().toISOString();
}

function makeKey(
  keyId: string,
  keyPrefix: string,
  scopes: string[],
  overrides?: Partial<KeyItem>,
): KeyItem {
  const revokedAt = overrides?.revoked_at ?? null;
  return {
    tenant_id: "tenant_e2e",
    key_id: keyId,
    key_prefix: keyPrefix,
    scopes,
    created_at: overrides?.created_at ?? isoNow(),
    created_by: overrides?.created_by ?? "user:e2e",
    expires_at: overrides?.expires_at ?? null,
    revoked_at: revokedAt,
    revoked_reason: overrides?.revoked_reason ?? null,
    rotated_from_key_id: overrides?.rotated_from_key_id ?? null,
    last_used_at: overrides?.last_used_at ?? null,
    is_active: revokedAt == null,
  };
}

async function installApiKeyMocks(page: import("@playwright/test").Page, options?: MockOptions) {
  await page.route("**/api/auth/session**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        user: { name: "E2E User", email: "e2e@example.com" },
        expires: "2099-01-01T00:00:00.000Z",
        accessToken: "e2e-token",
      }),
    });
  });

  let counter = 2;
  const keys: KeyItem[] = [
    makeKey("faim_k0001", "faim_0001", ["keys.read", "keys.write", "memory.read", "memory.write"]),
  ];
  const audit: Array<{
    id: string;
    tenant_id: string;
    key_id: string;
    action: string;
    actor: string;
    request_id: string;
    meta: Record<string, unknown>;
    created_at: string;
  }> = [
    {
      id: "evt-seed-created",
      tenant_id: "tenant_e2e",
      key_id: "faim_k0001",
      action: "created",
      actor: "user:e2e",
      request_id: "req-seed",
      meta: {},
      created_at: isoNow(),
    },
  ];

  await page.route("**/api/v1/api-keys**", async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const path = url.pathname;
    const method = req.method().toUpperCase();

    if (method === "GET" && path.endsWith("/api/v1/api-keys")) {
      const includeRevoked = url.searchParams.get("include_revoked") === "true";
      const items = includeRevoked ? keys : keys.filter((item) => item.revoked_at == null);
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items,
          total: items.length,
          include_revoked: includeRevoked,
        }),
      });
      return;
    }

    if (method === "GET" && path.endsWith("/api/v1/api-keys/audit")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: audit.slice().reverse(),
          total: audit.length,
          limit: 80,
        }),
      });
      return;
    }

    if (method === "POST" && path.endsWith("/api/v1/api-keys")) {
      if (options?.failCreate) {
        await route.fulfill({
          status: 500,
          contentType: "application/json",
          body: JSON.stringify({ detail: "Create key blocked by mock policy" }),
        });
        return;
      }

      const next = String(counter).padStart(4, "0");
      counter += 1;
      const keyId = `faim_k${next}`;
      const keyPrefix = `faim_${next}`;
      const created = makeKey(
        keyId,
        keyPrefix,
        ["keys.read", "keys.write", "memory.read", "memory.write"],
      );
      keys.unshift(created);
      audit.push({
        id: `evt-created-${next}`,
        tenant_id: "tenant_e2e",
        key_id: keyId,
        action: "created",
        actor: "user:e2e",
        request_id: `req-created-${next}`,
        meta: {},
        created_at: isoNow(),
      });
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          key: created,
          plaintext_key: `${keyId}_plaintext`,
        }),
      });
      return;
    }

    if (method === "POST" && path.includes("/api/v1/api-keys/") && path.endsWith("/rotate")) {
      const parts = path.split("/");
      const keyId = decodeURIComponent(parts[parts.length - 2] || "");
      const source = keys.find((item) => item.key_id === keyId);
      if (!source || source.revoked_at) {
        await route.fulfill({
          status: 404,
          contentType: "application/json",
          body: JSON.stringify({ detail: "API key not found" }),
        });
        return;
      }

      const next = String(counter).padStart(4, "0");
      counter += 1;
      const newId = `faim_k${next}`;
      const newPrefix = `faim_${next}`;
      source.revoked_at = isoNow();
      source.revoked_reason = "rotated";
      source.is_active = false;

      const replacement = makeKey(newId, newPrefix, [...source.scopes], {
        rotated_from_key_id: source.key_id,
      });
      keys.unshift(replacement);
      audit.push({
        id: `evt-rotated-${next}`,
        tenant_id: "tenant_e2e",
        key_id: source.key_id,
        action: "rotated",
        actor: "user:e2e",
        request_id: `req-rotated-${next}`,
        meta: { new_key_id: replacement.key_id },
        created_at: isoNow(),
      });
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          old_key: source,
          new_key: replacement,
          plaintext_key: `${newId}_plaintext`,
        }),
      });
      return;
    }

    if (method === "POST" && path.includes("/api/v1/api-keys/") && path.endsWith("/revoke")) {
      const parts = path.split("/");
      const keyId = decodeURIComponent(parts[parts.length - 2] || "");
      const key = keys.find((item) => item.key_id === keyId);
      if (!key || key.revoked_at) {
        await route.fulfill({
          status: 404,
          contentType: "application/json",
          body: JSON.stringify({ detail: "API key not found" }),
        });
        return;
      }

      key.revoked_at = isoNow();
      key.revoked_reason = "revoked from dashboard";
      key.is_active = false;
      audit.push({
        id: `evt-revoked-${keyId}`,
        tenant_id: "tenant_e2e",
        key_id: keyId,
        action: "revoked",
        actor: "user:e2e",
        request_id: `req-revoked-${keyId}`,
        meta: {},
        created_at: isoNow(),
      });
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ key }),
      });
      return;
    }

    await route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ detail: `Unhandled mock route: ${method} ${path}` }),
    });
  });
}

test.describe("API Keys Page", () => {
  test("supports create, rotate, revoke actions", async ({ page }) => {
    await installApiKeyMocks(page);
    page.on("dialog", async (dialog) => {
      await dialog.accept();
    });

    await page.goto("/dashboard/api-keys");
    await expect(page.getByRole("heading", { name: "API Keys" })).toBeVisible();
    await expect(page.getByText("faim_0001")).toBeVisible();

    await page.getByRole("button", { name: "Create key" }).click();
    await expect(page.getByText("One-time key reveal")).toBeVisible();
    await expect(page.getByText("faim_k0002_plaintext")).toBeVisible();

    await page.locator("button", { hasText: "Dismiss" }).first().click();
    await page.getByRole("button", { name: "Rotate" }).first().click();
    await expect(page.getByText("faim_k0003_plaintext")).toBeVisible();

    await page.getByRole("button", { name: "Revoke" }).first().click();
    await expect(page.getByText("revoked").first()).toBeVisible();
    await expect(page.getByText("rotated").first()).toBeVisible();
  });

  test("renders error state on create failure", async ({ page }) => {
    await installApiKeyMocks(page, { failCreate: true });
    await page.goto("/dashboard/api-keys");

    await page.getByRole("button", { name: "Create key" }).click();
    await expect(page.getByText("Create key blocked by mock policy")).toBeVisible();
    await expect(page.getByText("One-time key reveal")).toHaveCount(0);
  });
});
