from datetime import datetime, timezone

import numpy as np
import pytest

from app.models.domain import PlayerDistribution
from app.providers.nflverse import PlayerGame, SeasonData
from app.providers.rosters import CurrentRoster, RosterPlayer, parse_roster
from app.schemas.nfl import NflContext
from app.schemas.scoring import OffensiveStats
from app.services.current_season import current_catalog
from app.services.simulator import sample_player_scores
from app.services.optimizer import optimize_lineup
from app.core.roster_rules import RosterRules


def test_current_roster_includes_rookies_filters_retired_cut_and_defense():
    csv = 'season,gsis_id,full_name,position,team,years_exp,status\n' + '\n'.join([
        '2026,v,Veteran,QB,CIN,5,ACT', '2026,r,Rookie,WR,CIN,0,ACT',
        '2026,c,Cut,WR,CIN,4,CUT', '2026,d,Defense,LB,CIN,4,ACT',
        '2026,x,Retired,QB,CIN,10,RET', '2026,i,Reserve,WR,CIN,2,RES',
    ])
    assert [p.player_id for p in parse_roster(csv, 2026)] == ['v', 'r', 'i']
    assert parse_roster(csv, 2026)[2].roster_status == 'RES'


def test_opening_week_uses_prior_stats_but_current_team():
    now = datetime.now(timezone.utc)
    roster = CurrentRoster((RosterPlayer('v', 'Veteran', 'WR', 'CIN'),), now, 'roster')
    old = PlayerGame('v', 'Veteran', 'WR', 'BUF', 2025, 18, OffensiveStats(receptions=5, receiving_yards=70))
    future = PlayerGame('v', 'Veteran', 'WR', 'CIN', 2026, 1, OffensiveStats(receiving_yards=500))
    histories = [SeasonData((old, future), now, 'stats')]
    opening = current_catalog(roster, histories, NflContext(season=2026, target_week=1))
    player = opening.players[0]
    assert player.history_season == 2025
    assert player.player.season_average == 9.5
    assert player.player.team == 'CIN'
    assert player.projected_points == 9.5
    next_week = current_catalog(roster, histories, NflContext(season=2026, target_week=2))
    assert next_week.players[0].history_season == 2026
    assert next_week.players[0].player.season_average == 50


def distribution(pid, pos, team=None, mean=10, std=5):
    return PlayerDistribution(pid, pid, pos, mean, std, 2, 20, team)


def test_stack_correlations_preserve_each_players_mean_and_variance():
    players = [distribution('q', 'QB', 'CIN'), distribution('w', 'WR', 'CIN'),
               distribution('t', 'TE', 'CIN'), distribution('o', 'WR', 'BUF')]
    draws = sample_player_scores(players, 200000, np.random.default_rng(42))
    assert np.corrcoef(draws['q'], draws['w'])[0, 1] == pytest.approx(.30, abs=.01)
    assert np.corrcoef(draws['w'], draws['t'])[0, 1] == pytest.approx(.25, abs=.01)
    assert abs(np.corrcoef(draws['q'], draws['o'])[0, 1]) < .01
    for values in draws.values():
        assert values.mean() == pytest.approx(10, abs=.05)
        assert values.std() == pytest.approx(5, abs=.05)


def test_stack_helps_upside_but_does_not_always_improve_odds():
    stack = [distribution('q', 'QB', 'CIN'), distribution('w', 'WR', 'CIN')]
    independent = [distribution('q', 'QB'), distribution('w', 'WR')]
    rules = RosterRules(qb=1, rb=0, wr=1, te=0, flex=0)
    for opponent_mean, direction in [(30, 1), (10, -1)]:
        opponent = [distribution('op', 'QB', mean=opponent_mean, std=2)]
        linked, _ = optimize_lineup(stack, opponent, rules, 50000, 42)
        unlinked, _ = optimize_lineup(independent, opponent, rules, 50000, 42)
        assert direction * (linked[0].win_probability - unlinked[0].win_probability) > .01
        assert linked[0].expected_points == unlinked[0].expected_points == 20
