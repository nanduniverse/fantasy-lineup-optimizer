import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';

test('2026 matchup, stack selection, scoring changes, and recommendation', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await expect(page.getByText('NFL 2026 / 27', { exact: true })).toBeVisible();
  await expect(page.getByRole('combobox')).toHaveCount(0);
  const mine = page.getByRole('region', { name: 'Your team', exact: true });
  const theirs = page.getByRole('region', { name: 'The opponent', exact: true });
  async function add(panel: typeof mine, search: string, fullName: string, side: string) {
    await panel.getByRole('textbox').fill(search);
    await panel.getByRole('button', { name: `Add ${fullName} to ${side}`, exact: true }).click();
  }
  for (const [search, name] of [['Burrow', 'Joe Burrow'], ['Chase', "Ja'Marr Chase"], ['Henry', 'Derrick Henry'], ['Jonathan Taylor', 'Jonathan Taylor'], ['Jefferson', 'Justin Jefferson'], ['Kelce', 'Travis Kelce'], ['Barkley', 'Saquon Barkley'], ['Goff', 'Jared Goff'], ['Brandon Aubrey', 'Brandon Aubrey'], ['Texans D/ST', 'Texans D/ST']]) {
    await add(mine, search, name, 'Your team');
  }
  await expect(mine.getByText('CIN stack available', { exact: false })).toBeVisible();
  for (const [search, name] of [['Josh Allen', 'Josh Allen'], ['McCaffrey', 'Christian McCaffrey'], ['Bijan Robinson', 'Bijan Robinson'], ['CeeDee Lamb', 'CeeDee Lamb'], ['Amon-Ra', 'Amon-Ra St. Brown'], ['Kittle', 'George Kittle'], ['Nico Collins', 'Nico Collins'], ['Cameron Dicker', 'Cameron Dicker'], ['Broncos D/ST', 'Broncos D/ST']]) {
    await add(theirs, search, name, 'The opponent');
  }
  await mine.getByRole('textbox').fill('');
  await theirs.getByRole('textbox').fill('');
  await page.getByRole('button', { name: 'Full PPR', exact: true }).click();
  await expect(mine.getByRole('button', { name: 'Remove Joe Burrow from Your team' })).toBeVisible();
  const optimize = page.getByRole('button', { name: 'Optimize lineup' });
  await expect(optimize).toBeEnabled();
  await optimize.click();
  await expect(page.getByRole('heading', { name: 'Recommended starters' })).toBeVisible();
  await expect(page.getByText('Your best starting lineup', { exact: true })).toBeVisible();
  await page.screenshot({ path: '/tmp/football-desktop.png', fullPage: true });
  await mine.getByRole('button', { name: 'Remove Joe Burrow from Your team' }).click();
  await expect(page.getByRole('heading', { name: 'Recommended starters' })).toHaveCount(0);
  expect(errors).toEqual([]);
});

test('mobile layout stays within the viewport', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await page.getByRole('region', { name: 'Your team', exact: true }).getByRole('textbox').fill('Josh Allen');
  await expect(page.getByRole('button', { name: 'Add Josh Allen to Your team' })).toBeVisible({ timeout: 45000 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: '/tmp/football-mobile.png', fullPage: true });
});

test('weekly availability, workload explanation, and wrong-week guard', async ({ page }) => {
  const fixture = JSON.parse(await readFile(new URL('./fixtures/weekly-catalog.json', import.meta.url), 'utf8'));
  await page.route('**/api/nfl/current/players?*', async route => {
    const week = Number(new URL(route.request().url()).searchParams.get('target_week'));
    await route.fulfill({ json: { ...fixture, target_week: week,
      weekly: { ...fixture.weekly, verified: week === 1, current_week: 1,
        warnings: week === 1 ? [] : ['Weekly availability is only verified for the current regular-season week (1).'] } } });
  });
  await page.goto('/');
  const mine = page.getByRole('region', { name: 'Your team', exact: true });
  const theirs = page.getByRole('region', { name: 'The opponent', exact: true });
  await mine.getByRole('textbox').fill('Jacobs');
  await theirs.getByRole('textbox').fill('Jacobs');
  await expect(theirs.getByRole('button', { name: 'Add Josh Jacobs to The opponent' })).toBeDisabled();
  await expect(mine.getByText('Exempt list', { exact: true })).toBeVisible();
  await mine.getByRole('button', { name: 'Add Josh Jacobs to Your team' }).click();
  await mine.getByRole('textbox').fill('Lloyd');
  await mine.locator('summary').filter({ hasText: /projected points/ }).click();
  await expect(mine.getByText(/Josh Jacobs exempt:.*carries/)).toBeVisible();
  await expect(mine.getByText('RB · GB · Depth 1', { exact: true })).toBeVisible();
  await page.screenshot({ path: '/tmp/football-weekly.png', fullPage: true });
  await page.getByRole('button', { name: 'Next week' }).click();
  await expect(page.getByText(/Weekly availability is only verified for the current/)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Optimize lineup' })).toBeDisabled();
  await page.getByRole('button', { name: 'Go to week 1' }).click();
  await expect(page.getByText(/Weekly reports checked/)).toBeVisible();
});

test('rookies expose ESPN and draft estimates and can join a roster', async ({ page }) => {
  await page.goto('/');
  const mine = page.getByRole('region', { name: 'Your team', exact: true });
  await mine.getByLabel('Rookies only').check();
  await mine.getByRole('textbox').fill('Jeremiyah Love');
  await mine.locator('summary').filter({ hasText: 'ESPN + draft projection' }).click();
  await expect(mine.getByText(/90% ESPN/)).toBeVisible();
  await mine.getByRole('button', { name: 'Add Jeremiyah Love to Your team', exact: true }).click();
  await expect(mine.getByRole('button', { name: 'Remove Jeremiyah Love from Your team' })).toBeVisible();
  await page.screenshot({ path: '/tmp/football-rookies.png', fullPage: true });
});

test('rookie kickers and unsigned kickers remain searchable', async ({ page }) => {
  await page.goto('/');
  const mine = page.getByRole('region', { name: 'Your team', exact: true });
  const theirs = page.getByRole('region', { name: 'The opponent', exact: true });
  await mine.getByRole('button', { name: 'K', exact: true }).click();
  await mine.getByLabel('Rookies only').check();
  await mine.getByRole('textbox').fill('Trey Smack');
  await expect(mine.getByText(/ROOKIE/)).toBeVisible();
  await mine.getByRole('button', { name: 'Add Trey Smack to Your team', exact: true }).click();
  await theirs.getByRole('textbox').fill('Younghoe Koo');
  await expect(theirs.getByText('Unsigned free agent', { exact: true })).toBeVisible();
  await expect(theirs.getByRole('button', { name: 'Add Younghoe Koo to The opponent', exact: true })).toBeDisabled();
});
