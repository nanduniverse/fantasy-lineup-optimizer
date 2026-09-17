import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
const catalog = JSON.parse(readFileSync(new URL('./fixtures/weekly-catalog.json', import.meta.url), 'utf8'));

// Run against the built preview: OFFLINE_TEST_URL=http://127.0.0.1:4173 npm run test:e2e -- offline.spec.ts
const url = process.env.OFFLINE_TEST_URL;
test('production shell, player catalog, matchup and news survive an offline reload', async ({ page, context }) => {
  test.skip(!url, 'Requires the production preview for service workers');
  await page.route('**/api/nfl/current/players?*', route => route.fulfill({ json: catalog }));
  await page.route('**/api/news', route => route.fulfill({ json: {
    articles: [{ title: 'Saved fantasy update', url: 'https://example.com/story', source: 'Test', published_at: '2026-09-17T10:00:00Z' }],
    fetched_at: '2026-09-17T12:00:00Z', stale: false, warnings: [],
  } }));
  await page.goto(url!);
  await expect(page.getByText('Saved fantasy update')).toBeVisible();
  await page.evaluate(async () => { await navigator.serviceWorker.ready; });
  await page.waitForFunction(() => !!navigator.serviceWorker.controller);
  const add = page.getByRole('button', { name: /Add .* to Your team/ }).first();
  await expect(add).toBeEnabled();
  await add.click();
  await expect(page.getByRole('button', { name: /Remove .* from Your team/ })).toHaveCount(1);
  await page.unrouteAll();
  await context.setOffline(true);
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Lineup optimizer' })).toBeVisible();
  await expect(page.getByText('Saved fantasy update')).toBeVisible();
  await expect(page.getByText(/Offline \/ saved data from/)).toBeVisible();
  await expect(page.getByRole('button', { name: /Remove .* from Your team/ })).toHaveCount(1);
  await expect(page.getByRole('button', { name: /Optimize lineup/ })).toBeDisabled();
});
