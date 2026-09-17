import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { readFileSync } from 'node:fs';
const catalog = JSON.parse(readFileSync(new URL('./fixtures/weekly-catalog.json', import.meta.url), 'utf8'));

test.beforeEach(async ({ page }) => {
  const fullCatalog = { ...catalog, players: Array.from({ length: 8 }, (_, index) => {
    const entry = catalog.players[index % catalog.players.length];
    return { ...entry, player: { ...entry.player, player_id: `accessibility-${index}` } };
  }) };
  await page.route('**/api/nfl/current/players?*', route => route.fulfill({ json: fullCatalog }));
  await page.route('**/api/news', route => route.fulfill({ json: { articles: [{ title: 'Football update', url: 'https://example.com/story', source: 'Test', published_at: '2026-09-17T10:00:00Z' }], fetched_at: '2026-09-17T12:00:00Z', stale: false, warnings: [] } }));
});

test('no optional storage, cookies, or third-party browser requests by default', async ({ page, context }) => {
  const external: string[] = [];
  page.on('request', request => { if (new URL(request.url()).origin !== new URL(test.info().project.use.baseURL as string).origin) external.push(request.url()); });
  await page.goto('/');
  await expect(page.getByText('Football update', { exact: true })).toBeVisible();
  expect(await page.evaluate(() => Object.keys(localStorage).filter(k => k.startsWith('fantasy:v1:')))).toEqual([]);
  expect(await page.evaluate(async () => (await navigator.serviceWorker.getRegistrations()).length)).toBe(0);
  expect(await context.cookies()).toEqual([]);
  expect(external).toEqual([]);
});

test('keyboard navigation, import notice and error focus', async ({ page }) => {
  await page.goto('/');
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'Skip to content' })).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.locator('#main-content')).toBeFocused();
  const summary = page.locator('.league-import > summary');
  await summary.focus(); await page.keyboard.press('Enter');
  await expect(page.locator('#league-import-notice')).toBeVisible();
  const input = page.getByLabel('ESPN league link or ID');
  await input.fill('not-a-league'); await input.press('Enter');
  await expect(input).toBeFocused();
  await expect(input).toHaveAttribute('aria-invalid', 'true');
  await expect(page.getByRole('alert')).toContainText('Enter an ESPN league ID');
});

for (const width of [1280, 375, 320]) {
  test(`main page accessibility and reflow at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/');
    await expect(page.getByText('Football update', { exact: true })).toBeVisible();
    await page.locator('.league-import > summary').click();
    await page.locator('.private-league > summary').click();
    await page.locator('.lineup-settings > summary').click();
    const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze();
    expect(results.violations.map(v => ({ id: v.id, nodes: v.nodes.map(n => ({ target: n.target, summary: n.failureSummary })) })) ).toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  });
}

for (const [path, title] of [['/privacy', 'Privacy policy'], ['/terms', 'Terms and conditions'], ['/cookies', 'Cookie & storage policy']]) {
  test(`${path} supports direct navigation and accessibility`, async ({ page }) => {
    await page.goto(path);
    await expect(page.getByRole('heading', { level: 1, name: title })).toBeVisible();
    const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze();
    expect(results.violations).toEqual([]);
  });
}

test('withdrawing storage permission clears saved records and service worker', async ({ page }) => {
  await page.goto('/');
  const choice = page.getByRole('checkbox', { name: 'Save on this device for offline use' });
  await Promise.all([page.waitForEvent('load'), choice.check()]);
  await expect(choice).toBeChecked();
  await expect(page.getByText('Football update', { exact: true })).toBeVisible();
  await page.waitForFunction(() => Object.keys(localStorage).some(k => k.startsWith('fantasy:v1:')));
  await page.evaluate(async () => { await navigator.serviceWorker.ready; });
  await Promise.all([page.waitForEvent('load'), page.getByRole('button', { name: 'Clear saved data and turn off offline saving' }).click()]);
  await expect(choice).not.toBeChecked();
  await expect(page.getByText('Football update', { exact: true })).toBeVisible();
  expect(await page.evaluate(() => Object.keys(localStorage).filter(k => k.startsWith('fantasy:v1:')))).toEqual([]);
  expect(await page.evaluate(async () => (await navigator.serviceWorker.getRegistrations()).length)).toBe(0);
  expect(await page.evaluate(async () => (await caches.keys()).filter(k => k.startsWith('fantasy-shell-')))).toEqual([]);
});
