import { defineConfig, devices } from '@playwright/test';

const includeWebkit = process.env.PLAYWRIGHT_INCLUDE_WEBKIT === 'true';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:8011',
    trace: 'on-first-retry',
  },
  projects: includeWebkit
    ? [
        {
          name: 'chromium',
          use: { ...devices['Desktop Chrome'] },
        },
        {
          name: 'Mobile Safari',
          use: { ...devices['iPhone 12'] },
        },
      ]
    : [
        {
          name: 'chromium',
          use: { ...devices['Desktop Chrome'] },
        },
      ],
  webServer: {
    command: 'npx next dev -p 8011',
    url: 'http://localhost:8011',
    env: {
      ...process.env,
      PLAYWRIGHT_BYPASS_AUTH: 'true',
    },
    reuseExistingServer: !process.env.CI,
  },
});
