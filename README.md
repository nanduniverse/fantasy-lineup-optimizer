# Fantasy Football — Lineup Optimizer

A 2026/27 fantasy football matchup builder. Add your full roster on the left and your opponent's starters on the right; the optimizer finds the legal lineup with the highest estimated win probability.

## Run locally

Requires Python 3.11+ and Node 20.19+ (or Node 22.12+).

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

This workspace already has a working Python 3.13 environment: use `source .venv313/bin/activate` instead. The system Python is too old.

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. API docs: http://localhost:8000/docs. Optional `.env.example` files document CORS and the frontend API URL.

## The matchup flow

- The product is fixed to the **2026 NFL season**, including its 2027 postseason branding; the modeled weeks are regular-season weeks 1–18.
- Current rostered **QB, RB, WR, TE, and K players plus team D/ST** load automatically, including rookies; reserve and exempt players remain visible with availability labels.
- Each side has its own search, position filters, and add/remove buttons. There are no player-assignment or season dropdowns.
- Add bench options to your roster; add only starters to the opponent's side.
- Choose **No PPR**, **Half PPR**, or **Full PPR**. Both teams recalculate automatically, retaining player selections where eligible.
- Configure starter slots under Lineup settings. The defaults are 1 QB, 2 RB, 2 WR, 1 TE, 1 FLEX, 1 K, and 1 D/ST.
- Run **Optimize lineup** for a recommendation, estimated win probability, and alternatives.

## Data and projections

The backend uses [nflverse current rosters](https://nflreadr.nflverse.com/reference/load_rosters.html) and [weekly player statistics](https://nflreadr.nflverse.com/reference/load_player_stats.html), plus ESPN’s public injury, scoreboard, and depth-chart JSON feeds. nflverse is a community dataset; ESPN’s public endpoints are undocumented and may change. No API key is needed.

The 2026 roster supplies player identity and team assignments, so historical teams do not create false stacks after trades. Veterans with `ACT`, `RES`, `EXE`, or `INA` roster status are included; reserve/exempt players are retained as potential sources of vacated workload. Weekly reports determine whether a player may be recommended. Active roster status alone does not guarantee game-day availability.

Opening-week projections use each veteran's most recent recorded season in 2025–2024. Once that player has 2026 games before the target week, those games replace the prior-season baseline. Veterans with no records in that window are omitted and counted in a coverage warning. Rookies without history use the forecast model below. Past seasons are model inputs, not user-facing modes.

Scoring is calculated from raw offensive statistics:

| Event | Points |
| --- | ---: |
| Passing yards | 1 / 25 yards |
| Passing touchdown | 4 |
| Interception thrown | −2 |
| Rushing / receiving yards | 1 / 10 yards |
| Rushing / receiving touchdown | 6 |
| Offensive fumble lost | −2 |
| Passing / rushing / receiving two-point conversion | 2 |
| Reception | 0 / 0.5 / 1 by format |

Negative scores are preserved. No bonuses, return scores, defense, or special-teams points are included.

## Stacks and uncertainty

QB/WR/TE players on the same current NFL team share a simulated passing environment. The initial model assumes QB–WR/TE correlation of 0.30 and receiver–receiver correlation of 0.25. These are explicit heuristic assumptions, not calibrated estimates.

Stacking changes lineup variance without adding free projected points. It can improve an underdog's upside or increase a favorite's downside. Both fantasy teams participate in the same joint simulation, including when your opponent starts your quarterback's receiver.

Current-week absences, byes, and depth-based replacement workloads are modeled as described below. Opponent defenses, and schedule-specific game environments are not modeled. The normal scoring model is unbounded, with possible negative draws. Estimated odds are not calibrated predictions or guaranteed advantages.

## Weekly availability, depth charts, and replacement work

The app checks ESPN’s live regular-season week before applying its injury and depth reports. It never applies the current report to another selected week. Future/historical weeks without matching live reports can show baseline projections, but recommendations are paused until availability can be verified.

- Confirmed **out, suspended, injured reserve, exempt, inactive, and bye** players are excluded from recommended starters. You may keep them on your own roster; they cannot be selected as opponent starters.
- **Questionable and doubtful** players remain eligible with explicit warnings. They do not trigger assumed absences or automatic transfers. No fabricated play probabilities are assigned.
- Depth charts show published order within each offensive position. Reports and depth entries join through ESPN athlete IDs mapped from nflverse, not names.
- Vacated RB carries/targets, WR/TE targets, and QB attempts/carries are shared among available players at the same position using inverse-square depth weights. Both fantasy teams receive the same adjusted player projections.
- Rookie/unmodeled depth entries and questionable/doubtful/unknown-status replacements retain a share of the pool without receiving an automatic boost. That share is not gifted to the modeled backups.
- Added opportunities are valued using the recipient’s historical efficiency with conservative opportunity-based priors. Estimated role changes add uncertainty as well as points.
- Once the most recent current-season game already records replacement production without the starter, the extra transfer is suppressed to avoid counting the absence twice.

Player cards show availability and depth rank. Expand the green projection adjustment to see baseline points, adjusted points, carries/targets, and the absent teammate responsible. Weekly reports refresh every five minutes while the page is open; **Refresh reports** checks again using the same five-minute server cache. Historical stats and roster identity still use one-hour caches.

Unavailable or stale weekly feeds pause recommendations. Partial team depth-chart failures disable redistribution for those teams and show warnings; confirmed absences still apply. The API returns a separate `weekly` object with verification state, fetch time, current week, source URLs, and coverage warnings. Recommendations include `player_adjustments` for the selected players.

These workload allocations are heuristic estimates. They do not anticipate coaching decisions, redistribute across positions, infer injury severity from news, or predict return dates. Scores are not live in-game totals. Suspensions and exempt-list absences use structured reported status rather than guessed end dates.

## API

- `GET /api/health`
- `GET /api/nfl/current/players?season=2026&target_week=1&scoring_format=half_ppr`
- `POST /api/nfl/current/recommend-lineup`

Recommendation request:

```json
{
  "season": 2026,
  "target_week": 1,
  "scoring_format": "half_ppr",
  "your_player_ids": ["PLAYER_ID_FROM_CATALOG"],
  "opponent_player_ids": ["ANOTHER_PLAYER_ID_FROM_CATALOG"],
  "rules": {"qb": 1, "rb": 0, "wr": 0, "te": 0, "flex": 0},
  "simulations": 10000,
  "seed": 42
}
```

The existing `/api/nfl/players`, `/api/nfl/recommend-lineup`, `/api/sample-roster`, and `/api/recommend-lineup` endpoints remain available for historical/manual API consumers, outside the main UI.

Downloads have size limits and one-hour caches. Searches are bounded to 5,000 candidates and 100 million candidate × simulation × starter additions. Invalid lineups are rejected, and provider failures never produce fictional replacement data.

## Validation

```bash
cd backend
.venv313/bin/python -m pytest
```

```bash
cd frontend
npm run build
npm run test:e2e
```

Browser smoke tests require the local frontend/backend running, network access to nflverse and ESPN, and installed Google Chrome. The weekly UI test uses a captured fixture for deterministic status checks. They cover the full two-team selection flow, Burrow–Chase stack display, scoring changes, recommendations, and mobile overflow.

See [ARCHITECTURE.md](ARCHITECTURE.md) and [ENGINEERING_GUIDE.md](ENGINEERING_GUIDE.md) for the design and model explanation.

## Rookie forecasts

`providers/espn_projections.py` retrieves public ESPN fantasy forecasts by stable ESPN athlete ID. It accepts only projected statistics for the requested 2026 regular-season week; season totals, actual results, and other weeks are excluded. Forecasts cache for five minutes. Fractional projected receptions and touchdowns remain fractional and are scored using the selected no-PPR, half-PPR, or PPR rules.

`services/rookies.py` blends 90% ESPN points with 10% of a position-specific NFL overall draft-pick prior. The final adjustment cannot exceed ±10% of ESPN's forecast. This is NFL draft position, not fantasy ADP. The draft prior is a transparent heuristic, not a trained model: `(position anchor + reception weight × reception anchor) × exp(-(pick - 1) / 120)`. Weekly no-PPR anchors are QB 17, RB 10, WR 8, TE 5; reception anchors are 0, 2, 4, and 3 respectively. Missing draft picks use ESPN unchanged; a published zero stays zero.

Rookies have no fabricated historical games. Missing or unmapped forecasts display as unavailable and cannot enter recommendations. Once a rookie records current-season games before the requested week, the historical model replaces the rookie prior. Confirmed absences still block selection. ESPN forecasts receive no additional workload boost because ESPN may already include depth-chart changes; their share of redistributed veteran workload is withheld rather than reassigned.

Simulation uncertainty is assumed to be 50% of the rookie mean with a 2.5-point floor (zero for a published zero forecast). Both the draft prior and this uncertainty need future backtesting. The UI exposes rookie badges, draft picks, and ESPN/draft breakdowns so users can inspect the estimate.

## Kickers and defense/special teams

The website defaults to 1 K and 1 D/ST in addition to its seven offensive slots. Both counts are adjustable, and neither position can fill FLEX. Existing manual API clients retain zero K/DST slots unless explicitly requested.

Kickers include rookie and undrafted players, rostered veterans, practice-squad players, and additional kickers listed in ESPN's fantasy player pool. Identity matching uses ESPN IDs, never names. The current NFL roster takes precedence when ESPN's team assignment differs. Unsigned players show FA; unsigned, cut, and practice-squad kickers are visible but excluded from recommendations. Discovery is limited to the available provider lists and is not a complete registry of every unsigned prospect.

All 32 team defenses are selectable as combined D/ST units. K and D/ST use ESPN projected statistics for the exact selected week, with no draft adjustment or offensive workload redistribution. Missing forecasts remain unavailable. Weekly injury reports apply to kickers; byes apply to both positions. Forecasts and kicker discovery refresh through five-minute caches.

K scoring: field goals under 40 yards +3, 40–49 +4, 50+ +5; made extra points +1; missed field goals and extra points −1. D/ST: sacks +1; interceptions, fumble recoveries, blocked kicks and safeties +2; combined defensive/special-teams touchdowns +6, counted once. Points allowed: 0 +10, 1–6 +7, 7–13 +4, 14–21 +1, 22–27 0, 28–34 −1, 35+ −4. Projected points-allowed band probabilities are weighted directly; scoring the band of average points allowed would be mathematically incorrect. No yards-allowed scoring. These rules stay identical across PPR settings.

The simulation currently assumes K standard deviation 4 points and D/ST 6 points. Those assumptions are uncalibrated; opposing offensive player/DST correlations are not modeled. Stat identifiers were checked against live ESPN responses and the [ESPN API client stat mapping](https://raw.githubusercontent.com/cwendt94/espn-api/master/espn_api/football/constant.py).

## ESPN league import

Open **Import an ESPN league**, paste the 2026 league link or numeric ID, then select your team by name. The app imports your complete roster and the scheduled opponent's submitted starters for the selected NFL week. Starter slot counts and no/half/full-PPR weighting are applied automatically. Changing weeks refreshes the matchup; **Refresh imported matchup** retrieves later roster and lineup changes. Manual edits remain available.

Public leagues need only the league ID. Private leagues can provide ESPN `espn_s2` and `SWID` session cookies through password fields. These are account-access credentials: use only a trusted deployment over HTTPS (or your local development server). They are held in browser memory only, sent in POST bodies, used by a request-scoped backend client, and never cached or persisted by the app. Disconnecting or reloading clears them. Validation responses omit input values so failed validation cannot echo credentials. Do not enable request-body logging for this endpoint.

`POST /api/leagues/espn/import` reads the fixed ESPN league endpoint with `mTeam`, `mRoster`, `mSettings`, and `mMatchup` views plus the requested `scoringPeriodId`. With no `team_id` it lists league teams; with a team ID it maps roster ESPN IDs to the current app catalog and resolves the opponent through the league's matchup-period mapping. Team names are labels, not identity keys. No arbitrary URLs are fetched. Downloads are bounded and time out; missing mappings and unavailable players are reported rather than guessed. Provider/parser behavior follows the [ESPN client league implementation](https://raw.githubusercontent.com/cwendt94/espn-api/master/espn_api/football/league.py).

Current limits: 2026, single-week head-to-head matchups, supported QB/RB/WR/TE/FLEX/K/DST slots. Superflex, individual defenders, multi-week matchups, and multiple simultaneous opponents are rejected explicitly. A bye or unpublished matchup clears opponent starters. Failed refreshes also clear the opponent so the previous week's team cannot be optimized accidentally.

This imports rosters, slots, and reception weighting, **not custom scoring rules**. League-specific bonuses, touchdown/yardage rules, and K/DST scoring may differ from this app; the import panel explicitly calls this out. Opponent starters are whatever ESPN currently has submitted, not a prediction of future lineup changes. No writes are made to the ESPN league.

League import is tested with controlled provider and browser fixtures; an actual user's private league has not been verified in this workspace.
