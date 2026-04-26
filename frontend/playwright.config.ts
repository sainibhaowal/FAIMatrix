import { defineConfig, devices } from "@playwright/test";

const includeWebkit = process.env.PLAYWRIGHT_INCLUDE_WEBKIT === "true";

// Long-lived E2E JWT signed with NEXTAUTH_SECRET for user e2e-test-user / graph e2e-graph-001.
// Expires year 2286 — safe for test use only, never use in production.
const E2E_JWT =
  process.env.PLAYWRIGHT_E2E_JWT ??
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlMmUtdGVzdC11c2VyIiwiZW1haWwiOiJlMmVAdGVzdC5mYWltIiwidXNlcklkIjoiZTJlLXRlc3QtdXNlciIsImdyYXBoSWQiOiJlMmUtZ3JhcGgtMDAxIiwibmFtZSI6IkUyRSBUZXN0IFVzZXIiLCJleHAiOjk5OTk5OTk5OTksImlhdCI6MTc3NjM2Mjk0Nn0.C1CWsRIIIPUgQZJx1KclShCWo0Pq75pbfjLmJRHiljI";

export const E2E_GRAPH_ID = "e2e-graph-001";
export const E2E_USER_ID = "e2e-test-user";
export const E2E_BACKEND_URL =
  process.env.PLAYWRIGHT_BACKEND_URL ?? "http://localhost:8000";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false, // real backend — serialise to avoid data races
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : 1, // single worker for real backend tests
  reporter: "html",
  globalSetup: "./e2e/global-setup.ts",
  globalTeardown: "./e2e/global-teardown.ts",
  use: {
    baseURL: "http://localhost:8011",
    trace: "on-first-retry",
  },
  projects: includeWebkit
    ? [
        {
          name: "chromium",
          use: { ...devices["Desktop Chrome"] },
        },
        {
          name: "Mobile Safari",
          use: { ...devices["iPhone 12"] },
        },
      ]
    : [
        {
          name: "chromium",
          use: { ...devices["Desktop Chrome"] },
        },
      ],
  webServer: {
    command: "npx next dev -p 8011",
    url: "http://localhost:8011",
    env: {
      ...process.env,
      PLAYWRIGHT_BYPASS_AUTH: "true",
      PLAYWRIGHT_E2E_JWT: E2E_JWT,
    },
    reuseExistingServer: !process.env.CI,
  },
});
