from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.routes import nfl
from app.main import app
from app.providers.nflverse import NflverseProvider, ProviderError, SeasonData, SeasonUnavailable, parse_stats
from app.schemas.nfl import NflContext
from app.schemas.scoring import ScoringFormat
from app.services.nfl import build_catalog

FIXTURE = Path(__file__).parent / "fixtures" / "nflverse_2025.csv"


@pytest.fixture
def data():
    return SeasonData(parse_stats(FIXTURE.read_text(), 2025), datetime.now(timezone.utc), "https://example.com/stats.csv")


def test_provider_filters_nonoffense_and_normalizes_all_fumbles(data):
    assert {g.position for g in data.games} == {"QB", "RB", "WR", "TE"}
    henry = next(g for g in data.games if g.name == "Derrick Henry" and g.week == 1)
    assert henry.stats.fumbles_lost == 1
    assert henry.stats.receptions == 1


def test_scoring_is_applied_before_history_aggregation_and_cutoff(data):
    catalogs = [build_catalog(data, NflContext(season=2025, target_week=3, scoring_format=f)) for f in ScoringFormat]
    standard, half, ppr = [{p.player.player_id: p for p in c.players} for c in catalogs]
    for pid, entry in standard.items():
        games = [g for g in data.games if g.player_id == pid and g.week < 3]
        receptions = sum(g.stats.receptions for g in games) / len(games)
        assert ppr[pid].player.season_average - entry.player.season_average == pytest.approx(receptions, abs=0.0001)
        assert half[pid].player.season_average - entry.player.season_average == pytest.approx(receptions / 2, abs=0.0001)
        assert entry.games_played == len(games)
        assert entry.last_played_week < 3
    assert catalogs[0].available_through_week == 2
    # Later games cannot change any features, even if already present in the downloaded season.
    before = SeasonData(tuple(g for g in data.games if g.week < 3), data.fetched_at, data.source_url)
    assert build_catalog(before, NflContext(season=2025, target_week=3)) == catalogs[1]


def test_week_one_does_not_invent_history(data):
    catalog = build_catalog(data, NflContext(season=2025, target_week=1))
    assert catalog.players == []
    assert catalog.available_through_week is None
    assert "Week 1" in catalog.warnings[-1]


def test_provider_cache_avoids_repeated_downloads():
    calls = []
    def handler(request):
        calls.append(request.url)
        return httpx.Response(200, text=FIXTURE.read_text())
    provider = NflverseProvider(httpx.MockTransport(handler))
    first = provider.season(2025)
    assert provider.season(2025) is first
    assert len(calls) == 1
    assert str(calls[0]).endswith("/stats_player_week_2025.csv")


@pytest.mark.parametrize("status, error", [(404, SeasonUnavailable), (429, ProviderError), (500, ProviderError)])
def test_provider_failure_is_not_fake_data(status, error):
    provider = NflverseProvider(httpx.MockTransport(lambda _: httpx.Response(status)))
    with pytest.raises(error):
        provider.season(2025)


def test_provider_timeout():
    def handler(request):
        raise httpx.ReadTimeout("timeout", request=request)
    with pytest.raises(ProviderError, match="temporarily unavailable"):
        NflverseProvider(httpx.MockTransport(handler)).season(2025)


def test_provider_rejects_schema_drift_and_missing_values():
    with pytest.raises(ProviderError, match="schema changed"):
        parse_stats("player_id,position\na,QB", 2025)
    text = FIXTURE.read_text()
    with pytest.raises(ProviderError, match="invalid offensive"):
        parse_stats(text.replace(",2025,", ",oops,", 1), 2025)


@pytest.fixture
def client(monkeypatch, data):
    monkeypatch.setattr(nfl.provider, "season", lambda season: data)
    return TestClient(app)


def test_catalog_endpoint(client):
    response = client.get("/api/nfl/players", params={"season": 2025, "target_week": 3, "scoring_format": "ppr"})
    assert response.status_code == 200
    body = response.json()
    assert body["scoring_format"] == "ppr"
    assert body["source"] == "nflverse"
    assert {p["player"]["position"] for p in body["players"]} == {"QB", "RB", "WR", "TE"}


def test_nfl_recommendation_recalculates_both_teams(client, data):
    roster_id = next(g.player_id for g in data.games if g.position == "WR")
    opponent_id = next(g.player_id for g in data.games if g.position == "TE")
    payload = dict(season=2025, target_week=3, your_player_ids=[roster_id], opponent_player_ids=[opponent_id],
                   rules=dict(qb=0, rb=0, wr=0, te=0, flex=1), simulations=500)
    responses = []
    for scoring in ["standard", "half_ppr", "ppr"]:
        response = client.post("/api/nfl/recommend-lineup", json={**payload, "scoring_format": scoring})
        assert response.status_code == 200, response.text
        responses.append(response.json())
    assert responses[0]["recommended"]["expected_points"] < responses[1]["recommended"]["expected_points"] < responses[2]["recommended"]["expected_points"]
    assert responses[0]["opponent_expected_points"] < responses[1]["opponent_expected_points"] < responses[2]["opponent_expected_points"]
    assert responses[2]["recommended"]["starters"][0]["slot"] == "FLEX"
    assert responses[2]["scoring_format"] == "ppr"
    invalid = client.post("/api/nfl/recommend-lineup", json={**payload, "your_player_ids": ["unknown"]})
    assert invalid.status_code == 400
    duplicate = client.post("/api/nfl/recommend-lineup", json={**payload, "opponent_player_ids": [roster_id]})
    assert duplicate.status_code == 422


@pytest.mark.parametrize("params", [dict(season=2025, target_week=0), dict(season=2025, target_week=3, scoring_format="wrong"), dict(season=1900, target_week=3)])
def test_catalog_validation(client, params):
    assert client.get("/api/nfl/players", params=params).status_code == 422


def test_unavailable_season_returns_actionable_error(monkeypatch):
    def unavailable(season):
        raise SeasonUnavailable("NFL statistics have not been published")
    monkeypatch.setattr(nfl.provider, "season", unavailable)
    response = TestClient(app).get("/api/nfl/players?season=2025&target_week=2")
    assert response.status_code == 404
    assert "published" in response.json()["detail"]


def test_turnovers_and_conversions_are_counted_once():
    import csv
    import io
    rows = list(csv.DictReader(io.StringIO(FIXTURE.read_text())))
    row = next(row for row in rows if row['position'] == 'QB').copy()
    for key in ('sack_fumbles_lost', 'rushing_fumbles_lost', 'receiving_fumbles_lost',
                'passing_2pt_conversions', 'rushing_2pt_conversions', 'receiving_2pt_conversions'):
        row[key] = '1'
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(row))
    writer.writeheader()
    writer.writerow(row)
    game = parse_stats(output.getvalue(), 2025)[0]
    assert game.stats.fumbles_lost == 3
    assert game.stats.two_point_conversions == 3
    row['season_type'] = 'POST'
    writer.writerow(row)
    assert len(parse_stats(output.getvalue(), 2025)) == 1


def test_corrupt_required_number_is_not_zero_scored():
    import csv
    import io
    row = next(row for row in csv.DictReader(io.StringIO(FIXTURE.read_text())) if row['position'] == 'RB')
    for value in ('', 'NaN', 'Infinity'):
        row['rushing_yards'] = value
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
        with pytest.raises(ProviderError):
            parse_stats(output.getvalue(), 2025)
