from dataclasses import replace
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.api.routes import nfl
from app.main import app
from app.providers.nflverse import PlayerGame, SeasonData
from app.providers.rosters import CurrentRoster, RosterPlayer
from app.providers.weekly import DepthPlayer, Report, WeeklySnapshot
from app.schemas.nfl import NflContext
from app.schemas.scoring import OffensiveStats
from app.services.current_season import current_catalog
from app.services.projection import build_distribution
from app.services.workload import apply_weekly

NOW = datetime(2026, 9, 10, 18, tzinfo=timezone.utc)


def scenario(status='out', scoring='half_ppr', rookie=False):
    roster = CurrentRoster((RosterPlayer('starter', 'Starter', 'RB', 'CIN', '1'),
                            RosterPlayer('backup', 'Backup', 'RB', 'CIN', '2'),
                            RosterPlayer('opponent', 'Opponent', 'RB', 'BUF', '3')), NOW, 'roster')
    def game(pid, team, carries, targets):
        return PlayerGame(pid, pid, 'RB', team, 2025, 18,
                          OffensiveStats(carries=carries, targets=targets, rushing_yards=carries * 4,
                                         receptions=targets, receiving_yards=targets * 6))
    history = SeasonData((game('starter', 'CIN', 20, 5), game('backup', 'CIN', 3, 1),
                          game('opponent', 'BUF', 10, 2)), NOW, 'stats')
    depth = [DepthPlayer('1', 'RB', 1), DepthPlayer('2', 'RB', 2)]
    if rookie:
        depth.append(DepthPlayer('rookie', 'RB', 3))
    snapshot = WeeklySnapshot(2026, 1, NOW, 1, True, {'1': Report(status, NOW)},
                              {'CIN': tuple(depth), 'BUF': (DepthPlayer('3', 'RB', 1),)},
                              frozenset({'CIN', 'BUF'}))
    catalog = current_catalog(roster, [history], NflContext(season=2026, target_week=1, scoring_format=scoring))
    return roster, history, snapshot, catalog


def entry(catalog, pid):
    return next(e for e in catalog.players if e.player.player_id == pid)


@pytest.mark.parametrize('status', ['out', 'suspended', 'ir', 'exempt', 'inactive'])
def test_confirmed_absence_transfers_work_without_mutating_source(status):
    roster, history, snapshot, baseline = scenario(status)
    adjusted = apply_weekly(baseline, roster, [history], snapshot)
    donor, backup = entry(adjusted, 'starter'), entry(adjusted, 'backup')
    assert not donor.eligible and donor.projected_points == 0
    assert backup.added_carries == 20 and backup.added_targets == 5
    assert backup.projected_carries == 23 and backup.projected_targets == 6
    assert backup.projected_points > backup.baseline_projected_points
    assert build_distribution(backup.player).mean == pytest.approx(backup.projected_points, abs=.01)
    assert build_distribution(backup.player).std_dev > build_distribution(entry(baseline, 'backup').player).std_dev
    assert entry(baseline, 'backup').player.workload_points_adjustment == 0
    assert entry(baseline, 'backup').workload_notes == []


@pytest.mark.parametrize('status', ['available', 'questionable', 'doubtful', 'unknown'])
def test_uncertain_players_do_not_trigger_an_assumed_absence(status):
    roster, history, snapshot, baseline = scenario(status)
    adjusted = apply_weekly(baseline, roster, [history], snapshot)
    assert entry(adjusted, 'starter').eligible
    assert entry(adjusted, 'backup').added_carries == 0
    assert entry(adjusted, 'backup').projected_points == entry(baseline, 'backup').projected_points


def test_unmodeled_rookie_keeps_share_of_vacated_work():
    roster, history, snapshot, baseline = scenario(rookie=True)
    adjusted = apply_weekly(baseline, roster, [history], snapshot)
    assert entry(adjusted, 'backup').added_carries == pytest.approx(20 * (1/4) / (1/4 + 1/9), abs=.01)
    assert entry(adjusted, 'backup').added_carries < 20


def test_bye_and_missing_depth_do_not_boost_teammates():
    roster, history, snapshot, baseline = scenario()
    bye = apply_weekly(baseline, roster, [history], replace(snapshot, playing_teams=frozenset({'BUF'})))
    assert entry(bye, 'backup').availability == 'bye'
    assert entry(bye, 'backup').projected_points == 0
    absent_depth = apply_weekly(baseline, roster, [history], replace(snapshot, depths={}))
    assert not entry(absent_depth, 'starter').eligible
    assert entry(absent_depth, 'backup').added_carries == 0


def test_unverified_week_leaves_baselines_but_prevents_recommendations(monkeypatch):
    roster, history, snapshot, baseline = scenario()
    adjusted = apply_weekly(baseline, roster, [history], replace(snapshot, verified=False))
    assert entry(adjusted, 'starter').availability == 'unknown'
    assert entry(adjusted, 'backup').added_carries == 0
    monkeypatch.setattr(nfl, 'current_catalog_for', lambda _: adjusted)
    response = TestClient(app).post('/api/nfl/current/recommend-lineup', json=payload())
    assert response.status_code == 503


def test_scoring_format_changes_value_of_transferred_targets():
    values = []
    for scoring in ('standard', 'half_ppr', 'ppr'):
        roster, history, snapshot, baseline = scenario(scoring=scoring)
        adjusted = apply_weekly(baseline, roster, [history], snapshot)
        values.append(entry(adjusted, 'backup').player.workload_points_adjustment)
    assert values[0] < values[1] < values[2]


def test_no_repeat_boost_after_backup_records_the_absence():
    roster, history, snapshot, _ = scenario()
    current = SeasonData((PlayerGame('backup', 'Backup', 'RB', 'CIN', 2026, 1,
                                    OffensiveStats(carries=23, rushing_yards=92)),), NOW, 'current')
    context = NflContext(season=2026, target_week=2)
    baseline = current_catalog(roster, [history, current], context)
    adjusted = apply_weekly(baseline, roster, [history, current], replace(snapshot, week=2, current_week=2))
    assert entry(adjusted, 'backup').added_carries == 0
    assert entry(adjusted, 'backup').projected_carries == 23
    assert 'already includes' in entry(adjusted, 'starter').workload_notes[-1]


def payload():
    return dict(season=2026, target_week=1, your_player_ids=['starter', 'backup'],
                opponent_player_ids=['opponent'], rules=dict(qb=0, rb=1, wr=0, te=0, flex=0), simulations=500)


def test_api_excludes_absent_your_players_and_rejects_absent_opponent(monkeypatch):
    roster, history, snapshot, baseline = scenario('suspended')
    adjusted = apply_weekly(baseline, roster, [history], snapshot)
    monkeypatch.setattr(nfl, 'current_catalog_for', lambda _: adjusted)
    client = TestClient(app)
    response = client.post('/api/nfl/current/recommend-lineup', json=payload())
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['recommended']['starters'][0]['player_id'] == 'backup'
    assert body['recommended']['starters'][0]['mean'] == entry(adjusted, 'backup').projected_points
    assert body['weekly']['verified']
    assert len(body['player_adjustments']) == 3
    response = client.post('/api/nfl/current/recommend-lineup', json={**payload(), 'your_player_ids': ['backup'], 'opponent_player_ids': ['starter']})
    assert response.status_code == 400
    response = client.post('/api/nfl/current/recommend-lineup', json={**payload(), 'your_player_ids': ['starter']})
    assert response.status_code == 400


def test_opportunity_caps_and_wrong_week_guard():
    roster, history, snapshot, _ = scenario()
    massive = replace(history.games[0], stats=OffensiveStats(carries=100, rushing_yards=400, targets=5, receptions=5))
    history = replace(history, games=(massive, *history.games[1:]))
    baseline = current_catalog(roster, [history], NflContext(season=2026, target_week=1))
    adjusted = apply_weekly(baseline, roster, [history], snapshot)
    assert entry(adjusted, 'backup').projected_carries == 35
    assert entry(adjusted, 'backup').added_carries <= 100
    wrong_week = apply_weekly(baseline, roster, [history], replace(snapshot, week=2))
    assert not wrong_week.weekly.verified
    assert entry(wrong_week, 'backup').added_carries == 0


def test_questionable_backup_share_is_not_gifted_to_healthy_teammate():
    roster, history, snapshot, _ = scenario()
    roster = replace(roster, players=(*roster.players[:2], replace(roster.players[2], team='CIN')))
    history = replace(history, games=(*history.games[:2], replace(history.games[2], team='CIN')))
    snapshot = replace(snapshot, reports={'1': Report('out', NOW), '2': Report('questionable', NOW)},
                       depths={'CIN': (DepthPlayer('1', 'RB', 1), DepthPlayer('2', 'RB', 2), DepthPlayer('3', 'RB', 3))})
    baseline = current_catalog(roster, [history], NflContext(season=2026, target_week=1))
    adjusted = apply_weekly(baseline, roster, [history], snapshot)
    assert entry(adjusted, 'backup').eligible
    assert entry(adjusted, 'backup').added_carries == 0
    assert entry(adjusted, 'opponent').added_carries == pytest.approx(20 * (1/9) / (1/4 + 1/9), abs=.01)


def test_quarterback_replacement_receives_attempts_and_extra_uncertainty():
    roster, history, snapshot, _ = scenario()
    roster = replace(roster, players=tuple(replace(v, position='QB') for v in roster.players))
    history = replace(history, games=tuple(replace(g, position='QB', stats=OffensiveStats(
        passing_attempts=30 if g.player_id != 'backup' else 5,
        passing_yards=210 if g.player_id != 'backup' else 35,
    )) for g in history.games))
    snapshot = replace(snapshot, depths={team: tuple(replace(d, position='QB') for d in depths)
                                        for team, depths in snapshot.depths.items()})
    baseline = current_catalog(roster, [history], NflContext(season=2026, target_week=1))
    adjusted = apply_weekly(baseline, roster, [history], snapshot)
    backup = entry(adjusted, 'backup')
    assert backup.projected_passing_attempts == 35
    assert backup.added_passing_attempts == 30
    assert backup.player.workload_std_dev > 0
    assert backup.projected_points > backup.baseline_projected_points


def test_saved_statuses_display_but_cannot_drive_new_recommendations(monkeypatch):
    roster, history, snapshot, baseline = scenario()
    adjusted = apply_weekly(baseline, roster, [history], replace(snapshot, verified=False, saved=True))
    assert entry(adjusted, 'starter').availability == 'out'
    assert entry(adjusted, 'backup').added_carries == 0
    assert not adjusted.weekly.verified
    monkeypatch.setattr(nfl, 'current_catalog_for', lambda _: adjusted)
    assert TestClient(app).post('/api/nfl/current/recommend-lineup', json=payload()).status_code == 503
    mismatched = apply_weekly(baseline, roster, [history], replace(snapshot, week=2, verified=False, saved=True))
    assert entry(mismatched, 'starter').availability == 'unknown'
