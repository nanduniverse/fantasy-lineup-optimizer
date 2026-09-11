import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';

test('league import selects a team, follows the week, and clears stale opponents on errors', async ({ page }) => {
  const catalog = JSON.parse(await readFile(new URL('./fixtures/weekly-catalog.json', import.meta.url), 'utf8'));
  await page.route('**/api/nfl/current/players?*', route => {
    const week = Number(new URL(route.request().url()).searchParams.get('target_week'));
    return route.fulfill({ json: { ...catalog, target_week: week, weekly: { ...catalog.weekly, verified: true, current_week: week } } });
  });
  let fail = false;
  await page.route('**/api/leagues/espn/import', route => {
    const request = route.request().postDataJSON();
    if (fail) return route.fulfill({ status: 502, json: { detail: 'ESPN temporarily unavailable' } });
    const selected = request.team_id === 1;
    return route.fulfill({ json: {
      league_id: '123', name: 'Our League', week: request.week,
      teams: [{ id: 1, name: 'My Real Team' }, { id: 2, name: 'Week One Rival' }],
      selected_team: selected ? { id: 1, name: 'My Real Team' } : null,
      opponent: selected ? { id: 2, name: request.week === 1 ? 'Week One Rival' : 'Week Two Rival' } : null,
      your_player_ids: selected ? ['00-0039811'] : [],
      opponent_player_ids: selected ? [request.week === 1 ? '00-0038685' : '00-0035700'] : [],
      rules: { qb: 0, rb: 1, wr: 0, te: 0, flex: 0, k: 0, dst: 0 }, scoring_format: 'half_ppr', warnings: ['Review league-specific scoring.'],
    } });
  });
  await page.goto('/');
  await page.locator('.league-import > summary').click();
  await page.getByLabel('ESPN league link or ID').fill('https://fantasy.espn.com/football/league?leagueId=123');
  await page.getByRole('button', { name: 'Find my league' }).click();
  await page.getByLabel('Find your league team').fill('My Real');
  await page.getByRole('button', { name: 'My Real Team' }).click();
  const mine = page.getByRole('region', { name: 'Your team', exact: true });
  const theirs = page.getByRole('region', { name: 'The opponent', exact: true });
  await expect(mine.getByRole('button', { name: 'Remove MarShawn Lloyd from Your team' })).toBeVisible();
  await expect(theirs.getByRole('button', { name: 'Remove Chris Brooks from The opponent' })).toBeVisible();
  await page.getByRole('button', { name: 'Next week' }).click();
  await expect(page.getByText('My Real Team vs Week Two Rival · Week 2', { exact: true })).toBeVisible();
  await expect(theirs.getByRole('button', { name: 'Remove Josh Jacobs from The opponent' })).toBeVisible();
  await expect(theirs.getByRole('button', { name: 'Remove Chris Brooks from The opponent' })).toHaveCount(0);
  await page.screenshot({ path: '/tmp/league-import.png', fullPage: true });
  fail = true;
  await page.getByRole('button', { name: 'Refresh imported matchup' }).click();
  await expect(page.getByText('ESPN temporarily unavailable')).toBeVisible();
  await expect(theirs.getByRole('button', { name: 'Remove Josh Jacobs from The opponent' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Optimize lineup' })).toBeDisabled();
});

test('invalid league URLs show a useful error', async ({ page }) => {
  await page.goto('/');
  await page.locator('.league-import > summary').click();
  await page.getByLabel('ESPN league link or ID').fill('https://example.com/?leagueId=123');
  await page.getByRole('button', { name: 'Find my league' }).click();
  await expect(page.getByText('Enter an ESPN league ID or a fantasy.espn.com league link.')).toBeVisible();
});
