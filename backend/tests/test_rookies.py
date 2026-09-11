from dataclasses import replace
from datetime import datetime, timezone
import httpx
import pytest
from app.providers.espn_projections import EspnProjectionProvider, ProjectionSnapshot, WeeklyProjection, parse_projections
from app.providers.nflverse import PlayerGame, ProviderError, SeasonData
from app.providers.rosters import CurrentRoster, RosterPlayer
from app.schemas.nfl import NflContext
from app.schemas.scoring import OffensiveStats, ScoringFormat
from app.services.current_season import current_catalog
from app.services.rookies import rookie_entry

NOW = datetime(2026, 9, 10, tzinfo=timezone.utc)
ROOKIE = RosterPlayer('rookie', 'Test Rookie', 'RB', 'CIN', '123', is_rookie=True, draft_pick=3)
def snapshot(stats=None):
    return ProjectionSnapshot({'123': WeeklyProjection('123', 'RB', stats if stats is not None else {'24': 60, '53': 3.5, '42': 20, '25': .5})}, NOW, 'espn')
def record():
    return dict(seasonId=2026, statSourceId=1, statSplitTypeId=1, scoringPeriodId=1, stats={'24': 60})
def payload(records):
    return {'players': [{'player': {'id': 123, 'defaultPositionId': 2, 'stats': records}}]}
@pytest.mark.parametrize('format,expected', [('standard', 11), ('half_ppr', 12.75), ('ppr', 14.5)])
def test_fractional_scoring(format, expected):
    assert snapshot().projections['123'].points(ScoringFormat(format)) == expected
@pytest.mark.parametrize('field,value', [('seasonId', 2025), ('statSourceId', 0), ('statSplitTypeId', 0), ('scoringPeriodId', 2)])
def test_only_requested_weekly_forecasts(field, value):
    wrong = record(); wrong[field] = value
    assert parse_projections(payload([wrong]), 2026, 1) == {}
    assert '123' in parse_projections(payload([wrong, record()]), 2026, 1)
@pytest.mark.parametrize('bad', [[], {}, {'players': None}])
def test_invalid_payload(bad):
    with pytest.raises(ProviderError): parse_projections(bad, 2026, 1)
def test_missing_is_not_zero():
    data = record(); data['stats'] = {}
    assert parse_projections(payload([data]), 2026, 1) == {}
    zero = rookie_entry(ROOKIE, NflContext(season=2026, target_week=1), snapshot({'24': 0}))
    missing = rookie_entry(ROOKIE, NflContext(season=2026, target_week=1), None)
    assert zero.has_projection and zero.projected_points == 0
    assert not missing.has_projection and not missing.eligible and missing.projected_points is None
@pytest.mark.parametrize('yards', [1, 60, 300])
def test_adjustment_bounded_without_fake_games(yards):
    result = rookie_entry(ROOKIE, NflContext(season=2026, target_week=1), snapshot({'24': yards}))
    assert abs(result.player.season_average - yards / 10) <= yards / 100 + .0001
    assert result.games_played == 0 and result.last_played_week is None
    assert not result.player.recent_points
    result = rookie_entry(replace(ROOKIE, draft_pick=None), NflContext(season=2026, target_week=1), snapshot({'24': yards}))
    assert result.projected_points == yards / 10

def test_real_games_replace_forecast_without_future_leakage():
    roster = CurrentRoster((ROOKIE,), NOW, 'roster')
    history = SeasonData((PlayerGame('rookie', 'Test Rookie', 'RB', 'CIN', 2026, 1, OffensiveStats(rushing_yards=90)),), NOW, 'stats')
    opening = current_catalog(roster, [history], NflContext(season=2026, target_week=1), snapshot())
    following = current_catalog(roster, [history], NflContext(season=2026, target_week=2), snapshot())
    assert opening.players[0].projection_method == 'espn_draft'
    assert following.players[0].projection_method == 'history'
    assert following.players[0].projected_points == 9

def test_provider_errors_degrade_and_cache():
    calls = []
    def handle(request):
        calls.append(request)
        return httpx.Response(200, json=[])
    provider = EspnProjectionProvider(httpx.MockTransport(handle))
    assert provider.snapshot(2026, 1, ['123']).warnings
    assert provider.snapshot(2026, 1, ['123']).projections == {}
    assert len(calls) == 1

def test_rookie_availability_and_no_duplicate_workload_boost():
    from app.providers.weekly import DepthPlayer, Report, WeeklySnapshot
    from app.services.workload import apply_weekly
    roster = CurrentRoster((ROOKIE, RosterPlayer('v', 'Veteran', 'RB', 'CIN', '456')), NOW, 'roster')
    history = SeasonData((PlayerGame('v', 'Veteran', 'RB', 'CIN', 2025, 18, OffensiveStats(carries=20, rushing_yards=80)),), NOW, 'stats')
    baseline = current_catalog(roster, [history], NflContext(season=2026, target_week=1), snapshot())
    weekly = WeeklySnapshot(2026, 1, NOW, 1, True, {'456': Report('out', NOW)}, {'CIN': (DepthPlayer('456', 'RB', 1), DepthPlayer('123', 'RB', 2))}, frozenset({'CIN'}))
    adjusted = apply_weekly(baseline, roster, [history], weekly)
    rookie = next(p for p in adjusted.players if p.is_rookie)
    assert rookie.projected_points == next(p for p in baseline.players if p.is_rookie).projected_points
    assert rookie.added_carries == 0
    blocked = apply_weekly(baseline, roster, [history], replace(weekly, reports={'123': Report('out', NOW)}))
    rookie = next(p for p in blocked.players if p.is_rookie)
    assert not rookie.eligible and rookie.projected_points == 0
