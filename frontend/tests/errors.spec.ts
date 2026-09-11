import { test, expect } from '@playwright/test';

test('unknown pages show a plain 404 with a working home link', async ({ page }) => {
  await page.goto('/page-that-does-not-exist');
  await expect(page.getByRole('heading', { name: '404 — Page not found' })).toBeVisible();
  await page.getByRole('link', { name: 'Go to homepage' }).click();
  await expect(page.getByRole('heading', { name: 'Lineup optimizer', exact: true })).toBeVisible();
});

test('render failures show a plain recovery screen and reload works', async ({ page }) => {
  await page.route('**/src/App.tsx', route => route.fulfill({
    contentType: 'application/javascript',
    body: 'export default function App() { throw new Error("test-only-render-failure"); }',
  }));
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Something went wrong' })).toBeVisible();
  await expect(page.getByText('test-only-render-failure', { exact: true })).toHaveCount(0);
  await page.unroute('**/src/App.tsx');
  await page.getByRole('button', { name: 'Reload page' }).click();
  await expect(page.getByRole('heading', { name: 'Lineup optimizer', exact: true })).toBeVisible();
});
