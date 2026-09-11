# Engineering walkthrough

The product answers one question: which legal set of starters most often beats this opponent under our scoring model? The API is the source of truth; React collects inputs and presents results.

## Follow one request

1. `frontend/src/components/NflBuilder.tsx` lets you select real NFL players and scoring rules. `providers/nflverse.py` fetches weekly box scores; `services/scoring.py` calculates each game’s points; `services/current_season.py` joins the 2026 veteran roster to prior/current history and builds model inputs. Historical/manual APIs remain available outside the main UI. Editing inputs clears old results so recommendations cannot silently refer to a previous roster.
2. `schemas/player.py` and `schemas/lineup.py` validate the API boundary. Player IDs must be unique, teams cannot share players, numeric inputs must be bounded, and at least one slot must exist. Invalid fields return 422; impossible rosters return 400.
3. `projection.py` transforms inputs into immutable distributions. It blends the last four games (65%) with the season average (35%), then adjusts for matchup and injury. Recent standard deviation estimates volatility, with fallback and minimum values for small samples. Boom rate increases volatility. These constants are assumptions, not learned parameters.
4. `lineup_generator.py` allocates FLEX slots among RB/WR/TE, then chooses combinations within each position. This creates each player set once. Swapping two RBs between RB and FLEX cannot create a different recommendation. Combinatorial counts reject searches above 5,000 candidates before constructing them.
5. `optimizer.py` samples each player once for all simulated weeks. Every candidate reuses those samples and the same opponent totals. This is called common random numbers: shared players have the same outcome when comparing competing decisions. Sorted player IDs and a seed make results independent of input ordering. Candidate × simulation × starter work is capped at 100 million additions.
6. Each candidate receives `(wins + half the ties) / simulations`. Results sort by this score, then projected points. The API returns the best lineup and up to three alternatives, including explicit FLEX assignments.

## Why this objective matters

Imagine a safe player scoring around 20 and a volatile player averaging 19. Against an opponent scoring around 30, volatility offers a chance of clearing the target. Against an opponent around 10, the safe player is more likely to protect the advantage. The optimizer test suite checks both cases. A test should protect a meaningful behavior, rather than simply repeat implementation formulas.

## Modeling honesty

The simulator uses jointly normal distributions with shared NFL-team passing factors. Negative draws are possible. We deliberately avoid clipping them: clipping increases the simulated mean, especially for volatile players, while the displayed expected points would remain unchanged. A proper nonnegative model needs calibrated distributions whose moments match the reported projections.

The displayed low/high values are heuristic reference scores (`max(0, mean − 1.25σ)` and `mean + 1.75σ`), not hard bounds or calibrated confidence intervals. Injury risk is a mean adjustment, not a separate probability of missing the game. Recent inputs are oldest to newest. Imported box scores are converted to the chosen format on the server for both teams. Manual inputs must already use the same scoring system. Input points from −100 to 100 are supported, including negative games from turnovers.

The seed makes the result repeatable, not correct. At 5,000 simulations a probability near 50% has roughly 0.7 percentage points of Monte Carlo standard error for one fixed candidate. Selecting the maximum across many candidates adds selection bias. Tiny differences between alternatives should not be interpreted as dependable advantages. Historical backtesting and calibration are necessary before trusting these estimates in real decisions.

## Boundaries and tradeoffs

No database is needed because each request contains everything required for an answer. Pure services keep HTTP, math, and UI separate, making a future model replacement easier. The endpoint is synchronous so FastAPI can execute it in its worker thread pool. Per-request limits bound computation, but public deployment still needs concurrency controls and rate limits.

The NFL player picker now uses the 2026 active-veteran roster and explicit scoring presets. Historical statistics are projection inputs, while current roster assignments determine stacks. Rookies are excluded. The weekly ESPN adapter supplies current absences, byes, and depth charts; active status alone is not a game-day guarantee. Manual projection APIs remain available. League imports, authentication, persistence, correlations, and machine learning remain future work.

## Running and changing it

Use the two terminal setup commands in README.md. Run `cd backend && .venv/bin/python -m pytest` for domain and API tests. Run `cd frontend && npm run build` for TypeScript checking and a production bundle. `npm run preview` serves that bundle locally; the API must also be running.

Backend configuration: copy `backend/.env.example` to `backend/.env`. Frontend configuration: copy `frontend/.env.example` to `frontend/.env` and restart Vite after edits. Frontend environment values are public browser configuration, never secrets.

When adding features, first identify the boundary they belong to. Scoring normalization belongs before projection; game correlations belong in simulation; league imports should translate provider data into the existing request model. Build a historical evaluation harness before replacing the transparent heuristic with a more complicated model.

## Why scoring happens before projection

Suppose a receiver has 5 catches for 70 yards and one receiving touchdown. That game scores 13 standard points, 15.5 half-PPR points, or 18 PPR points. Those are three different histories for the model, not just three display labels. Recalculate each game first, then estimate the average and volatility. Otherwise you would miss how reception volume affects both expected points and consistency.

The implementation stores normalized raw game statistics in the cache and computes scoring in a pure function. Tests use small captured provider fixtures and synthetic box scores: known scoring totals, negative games, reception differences, offensive filtering, target-week exclusion, cache behavior, upstream failures, and the full API path. No automated test requires an external network call. A separate live-data smoke check verified the catalog and seven-player recommendations in all three formats.

The provider's published fantasy-point columns are intentionally unused: our application owns its scoring rules. Offensive fumbles lost are the sum of sack, rushing, and receiving losses; we do not also subtract the provider's aggregate fumble count. That avoids double deductions. Special-teams contributions and league-specific bonuses are outside these presets.

## The 2026 product and correlated outcomes

The main screen is fixed to the 2026 season. Your roster, including bench options, goes on the left; your opponent's exact starting lineup goes on the right. The user no longer navigates older seasons or assigns teams through dropdown menus.

The roster feed supplies today's veteran identity and NFL team. The latest available 2025/2024 season supplies an opening-week baseline, recalculated in the selected scoring format. Eligible earlier 2026 games take over when present. This separation prevents a traded player's old team from creating the wrong stack. Veterans without records in the supported history window are omitted and counted in the coverage notes.

For Burrow and Chase, imagine simulating the Bengals' passing environment each week. A strong shared environment tends to lift both; a weak one tends to lower both. Each player also has individual randomness. We use loadings 0.60 for QB and 0.50 for WR/TE, giving 0.30 correlation. Residual scaling preserves every player's existing mean and standard deviation.

Both fantasy teams share those environments. If the opponent starts Chase against your Burrow, independently drawing their scores would miss an important dependency. All players are drawn jointly before any lineup is compared.

Correlation changes the spread of outcomes, not the mean. A stack can improve the chance of reaching a difficult target while increasing the risk of missing an easy one. Tests explicitly verify both cases and check the empirical simulated correlations. The coefficients are assumptions, not learned estimates; calibration is still necessary.

## Example: starter unavailable, backup promoted

Before this feature, a backup’s projection only rose after he recorded higher scoring games. Now a confirmed starter absence creates a pool of estimated vacated opportunities before kickoff. If a starter normally gets 20 carries and the remaining depth order has two backs ranked 1 and 2, inverse-square weights divide that pool 80/20: 16 extra carries for the first back and 4 for the second, subject to caps. Additional targets are handled separately.

We value those opportunities using each recipient’s efficiency, stabilized with a small prior so one long touchdown on two career carries does not generate absurd projections. Scoring format affects transferred target value through reception points. Increased role uncertainty also widens the simulated distribution.

This is not a prediction of a coach’s exact plan. The UI exposes both the source status and the modeled adjustment. “Questionable” is not treated as “out,” and unknown future-week availability is not silently filled with today’s injury list. If the backup’s current-season history already includes the latest team game without the starter, a second boost is suppressed.

The workflow remains stateless: all available teammates receive adjustments before either fantasy roster is optimized, regardless of which backups the user selected. Otherwise a user could accidentally inflate a backup simply by leaving a competing teammate off their fantasy roster.

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
