# Architecture Decisions

## Product goal

Build a current-season matchup and find the legal starting lineup with the greatest estimated probability of beating the specified opponent. The UI is deliberately centered on 2026 NFL players, with no historical season picker.

```text
React: your roster | opponent starters
                  |
FastAPI: current-season API
                  |
2026 roster + prior/current game statistics
                  |
Offensive scoring -> player distributions
                  |
Legal lineups + joint team-correlated simulations
                  |
Highest estimated win probability + alternatives
```

## Data boundaries

`providers/rosters.py` retrieves the 2026 roster, filters to rostered QB/RB/WR/TE players, and supplies current team identities. Retired, cut, and defensive players are excluded. Rookies are included. Reserve, exempt, and inactive veterans remain in the catalog so confirmed absences can inform replacement workloads. An active designation does not prove game-day eligibility.

`providers/nflverse.py` normalizes weekly raw statistics into `OffensiveStats`. Both providers have one-hour process caches, bounded downloads, and explicit schema/error handling. The provider is nflverse, a community NFL dataset, not an official NFL/ESPN API.

`services/scoring.py` owns point rules. Standard, half-PPR, and PPR differ only in reception weighting. Calculate each historical game before averaging or estimating volatility. Avoid double-counting lost fumbles across aggregate and component fields.

`services/current_season.py` joins roster identities to game histories by stable player ID. It uses the latest available 2025/2024 season as the opening-week prior, then switches to the player's 2026 games as they become available. The target week and later weeks are filtered before feature aggregation. Veterans without usable history are omitted explicitly. Rookies without history use verified weekly ESPN forecasts through `services/rookies.py`.

Current team identity always comes from the 2026 roster, even if the historical statistics came from a different NFL team. This is essential for correct stack grouping after trades. The current-season endpoint is not intended as a historical backtesting API because roster snapshots can change.

## Model boundaries

`projection.py` blends recent points and a season average, then produces a mean and standard deviation. The transparent heuristic can later be replaced without changing the UI or lineup rules.

`lineup_generator.py` enumerates legal combinations by position counts, avoiding duplicate FLEX assignments. It counts and bounds the search before enumeration.

`simulator.py` uses a shared standard-normal passing factor per NFL team plus independent player residuals:

```text
player score = mean + std_dev × (loading × team factor + sqrt(1 − loading²) × player residual)
QB loading = 0.60
WR/TE loading = 0.50
RB or unknown team loading = 0
```

Each player's marginal mean and variance are preserved. QB–WR/TE correlation is 0.30; WR/TE pairs share 0.25. This factor construction guarantees a valid joint covariance structure. The coefficients are heuristic and need calibration.

`optimizer.py` draws all players on both fantasy teams jointly, once per simulated week. Every candidate reuses those player outcomes. This both reduces comparison noise and preserves same-NFL-team dependencies across the fantasy matchup. Results rank by wins plus half ties, then expected points.

A stack does not always help. It increases variance when its members are on the same fantasy team, which can benefit an underdog while hurting a favorite. No points or probability multiplier is awarded merely for selecting a stack.

`services/recommendation.py` coordinates roster checks, projections, and optimization. Routes handle HTTP concerns. Historical/manual endpoints are retained for API compatibility but are not the default product flow.

## UI decisions

The light cream/green interface presents two independent searchable player panels. Scoring uses segmented buttons; week uses previous/next buttons; slot configuration is secondary. Scoring changes trigger a new fetch, cancel stale requests, retain valid selections, and clear previous results. Roster edits clear results. The opponent must contain exactly the required legal starters; your team may include bench options.

Desktop shows both sides together; mobile stacks the panels vertically. Network errors offer retry, and empty/loading states are explicit. Browser tests exercise the real local services and a mobile viewport.

## Limits and next work

No database is necessary for the stateless matchup flow. Persistence becomes useful for saved rosters, users, and league imports.

Before trusting win probabilities, add archived point-in-time data, calibrated correlations/distributions, and historical evaluation. Opponent defense, weather, game-level pace, coaching-driven role changes, and season-to-season shrinkage are not yet modeled. Current-week availability and conservative depth-based workload transfers are implemented below. Moving from one current-season game directly to a current-only estimate is an intentionally simple starting rule; a calibrated blend with the prior is a future improvement.

## Weekly report boundary

`providers/weekly.py` reads ESPN’s scoreboard, injuries, team directory, and 32 team depth charts. The regular-season year/week must match the requested matchup. Injury/depth feed timestamps must be within 24 hours; fetched snapshots cache for five minutes (failures for 30 seconds). Bounded HTTP downloads, timeouts, and eight concurrent depth requests limit resource use. A feed failure produces explicit unverified coverage instead of a healthy-player assumption. Recommendations require verified weekly coverage.

ESPN injury records may omit a direct athlete ID. The adapter extracts the ID only from canonical ESPN player links; it never matches by display name. nflverse’s `espn_id` bridges the providers. Duplicate WR depth slots resolve to the best published rank for the athlete. This is a position depth order, not a universal team receiver ranking. Team aliases such as LAR/LA and WSH/WAS are normalized.

The full current-week scoreboard identifies playing teams and byes after structural checks. Suspended, exempt, IR, out and inactive players remain visible but cannot be recommended. A reserve/exempt roster designation cannot be cleared solely by a generic active injury report. Questionable and doubtful statuses remain uncertain, without inventing an inactivity probability.

If a team’s depth chart fails, availability still applies and that team receives no replacement adjustments. Coverage warnings expose the gap. Live reports are not an archived historical or future-week availability database.

## Workload transfer boundary

`services/workload.py` operates on a copy of the baseline catalog and never mutates cached provider records. The season-selection and original 65/35 baseline formulas are unchanged. Carries, targets and attempts now accompany raw box scores.

Each unavailable player’s baseline opportunities form a separate transfer pool. Available same-position depth entries receive weights `1 / rank²`. The denominator includes rookie/unmodeled and uncertain-status replacements, so their opportunity shares are withheld rather than reassigned to healthy teammates. RB pools transfer carries and targets; WR/TE pools transfer targets; QB pools transfer attempts and carries. There is no cross-position redistribution or automatic receiver penalty when a QB is out.

Recipient projected opportunities are capped at 35 carries, 20 targets, and 50 passing attempts; caps constrain additions, not existing baselines. Existing historical efficiency is shrunk with pseudo-opportunities: 40 carries at 0.57 points each, 30 targets at `1.02 + 0.65 × reception_points`, and 100 attempts at 0.40 points each. These are uncalibrated default rates. Additional fumble and two-point-conversion events are not separately predicted by the transfer model.

Added points are capped at 60. Added role uncertainty is `0.35 × added_points`, combined with the original standard deviation in quadrature. This avoids representing a newly promoted backup as both high-volume and artificially certain.

A donor who missed the most recent current-season team game does not trigger another transfer when recipient histories already include that game. This prevents obvious double-counting; it is not a complete historical snap/availability model and does not identify partial-game exits. Multi-season injury blending has not been introduced.

The current recommendation route filters unavailable players from your candidate roster and rejects unavailable opponent starters. It resolves adjustments server-side and returns the exact selected-player adjustment metadata used by the simulation. The UI does not manufacture projection boosts.

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
