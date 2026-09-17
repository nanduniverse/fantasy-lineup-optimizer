import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
const fixture = JSON.parse(readFileSync(new URL('./fixtures/weekly-catalog.json', import.meta.url), 'utf8'));
const appUrl = process.env.OFFLINE_TEST_URL ?? 'http://localhost:5173';

test('ESPN availability has distinct labeled colors and unknown is never green', async ({ page }) => {
  const catalog = structuredClone(fixture);
  const statuses = ['available', 'questionable', 'doubtful', 'out', 'unknown'];
  catalog.players = statuses.map((status, index) => ({ ...fixture.players[0], player: { ...fixture.players[0].player, player_id: `status-${index}` }, availability: status }));
  await page.route('**/api/nfl/current/players?*', route => route.fulfill({ json: catalog }));
  await page.route('**/api/news', route => route.fulfill({ json: { articles: [], fetched_at: null, stale: true, warnings: [] } }));
  await page.goto(appUrl);
  const panel = page.getByRole('region', { name: 'Your team', exact: true });
  for (const [status, label, color] of [
    ['available', 'Available', 'rgb(22, 101, 52)'],
    ['questionable', 'Questionable', 'rgb(113, 63, 18)'],
    ['doubtful', 'Doubtful', 'rgb(154, 52, 18)'],
    ['out', 'Out', 'rgb(153, 27, 27)'],
    ['unknown', 'No current report', 'rgb(55, 65, 81)'],
  ]) {
    const badge = panel.locator(`.status-${status}`);
    await expect(badge).toHaveText(`Status: ${label}`);
    await expect(badge).toHaveCSS('color', color);
  }
  await expect(page.getByText('Status unverified', { exact: true })).toHaveCount(0);
});

test('an empty matchup moves to ESPN’s current week', async ({ page }) => {
  await page.route('**/api/nfl/current/players?*', route => {
    const week = Number(new URL(route.request().url()).searchParams.get('target_week'));
    return route.fulfill({ json: { ...fixture, target_week: week, weekly: { ...fixture.weekly, current_week: 2, verified: week === 2 } } });
  });
  await page.route('**/api/news', route => route.fulfill({ json: { articles: [], fetched_at: null, stale: true, warnings: [] } }));
  await page.goto(appUrl);
  await expect(page.getByText('Week 2', { exact: true })).toBeVisible();
});
