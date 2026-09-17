import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests',
  use: { baseURL: process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:5173', channel: 'chrome', screenshot: 'only-on-failure' },
  timeout: 60000,
});
