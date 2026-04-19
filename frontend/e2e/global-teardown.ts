/**
 * Playwright global teardown.
 *
 * E2E graph data (e2e-graph-001) is intentionally left in place so that
 * successive test runs can reuse it (idempotent seeding in global-setup).
 * Add explicit cleanup here if isolation between runs is required.
 */

export default async function globalTeardown(): Promise<void> {
  console.log('[e2e-teardown] Done — E2E graph data retained for next run.');
}
