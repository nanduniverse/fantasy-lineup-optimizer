from datetime import datetime, timezone, timedelta

import httpx
import pytest

from app.providers.nflverse import ProviderError
from app.providers.weekly import WeeklyProvider, athlete_id, parse_depth, parse_reports

NOW = datetime(2026, 9, 10, 18, tzinfo=timezone.utc)


def report_payload():
    return {'timestamp': NOW.isoformat(), 'status': 'success', 'season': {'year': 2026, 'type': 2},
            'injuries': [{'id': '9', 'injuries': [
                {'date': NOW.isoformat(), 'status': 'Suspension', 'athlete': {
                    'position': {'abbreviation': 'RB'},
                    'links': [{'href': 'https://www.espn.com/nfl/player/_/id/123/test-player'}]}}
            ]}]}


def depth_payload():
    return {'timestamp': NOW.isoformat(), 'status': 'success', 'season': {'year': 2026, 'type': 2},
            'depthchart': [{'positions': {
                'rb': {'position': {'abbreviation': 'RB'}, 'athletes': [{'id': '1'}, {'id': '2'}]},
                'lb': {'position': {'abbreviation': 'LB'}, 'athletes': [{'id': '3'}]},
                'wr1': {'position': {'abbreviation': 'WR'}, 'athletes': [{'id': '4'}, {'id': '5'}]},
                'wr2': {'position': {'abbreviation': 'WR'}, 'athletes': [{'id': '5'}]},
            }}]}


def test_stable_espn_id_link_mapping_and_suspensions():
    parsed = parse_reports(report_payload(), 2026, NOW)
    assert parsed['123'].status == 'suspended'
    assert athlete_id({'links': [{'href': 'https://untrusted.test/nfl/player/_/id/123/a'}]}) is None
    assert athlete_id({'displayName': 'Someone'}) is None


def test_depth_order_and_duplicate_flanker_slots():
    parsed = {p.espn_id: p for p in parse_depth(depth_payload(), 2026, NOW)}
    assert '3' not in parsed
    assert parsed['1'].rank == 1 and parsed['2'].rank == 2
    assert parsed['5'].rank == 1


@pytest.mark.parametrize('parser, payload', [(parse_reports, report_payload), (parse_depth, depth_payload)])
def test_stale_and_wrong_season_reports_are_rejected(parser, payload):
    with pytest.raises(ProviderError):
        parser(payload(), 2026, NOW + timedelta(days=2))
    with pytest.raises(ProviderError):
        parser(payload(), 2025, NOW)


def test_oldest_report_cannot_override_newer_clearance():
    payload = report_payload()
    row = payload['injuries'][0]['injuries'][0]
    older = {**row, 'date': (NOW - timedelta(days=3)).isoformat()}
    cleared = {**row, 'status': 'Active'}
    payload['injuries'][0]['injuries'] = [cleared, older]
    assert parse_reports(payload, 2026, NOW)['123'].status == 'available'


def test_future_week_does_not_fetch_or_apply_current_injuries():
    calls = []
    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(200, json={'season': {'type': 2, 'year': 2026}, 'week': {'number': 1}})
    provider = WeeklyProvider(httpx.MockTransport(handler))
    snapshot = provider.snapshot(2026, 3)
    assert not snapshot.verified and snapshot.current_week == 1
    assert len(calls) == 1
    assert snapshot.reports == {}
    assert provider.snapshot(2026, 3) is snapshot
    assert len(calls) == 1


def test_network_failure_is_explicit_unknown_not_available():
    provider = WeeklyProvider(httpx.MockTransport(lambda _: httpx.Response(503)))
    snapshot = provider.snapshot(2026, 1)
    assert not snapshot.verified
    assert snapshot.warnings
