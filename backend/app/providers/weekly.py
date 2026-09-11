"""ESPN live-week reports and ordered depth charts, joined by ESPN athlete ID.

These endpoints are undocumented. Validate shape, season, week and feed age;
never reuse a live report as if it described another requested week.
"""
import json
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from threading import Lock
from time import monotonic
from urllib.parse import urlparse

import httpx

from app.providers.nflverse import ProviderError

BASE = 'https://site.api.espn.com/apis/site/v2/sports/football/nfl'
STATUSES = {
    'active': 'available', 'questionable': 'questionable', 'doubtful': 'doubtful',
    'out': 'out', 'suspension': 'suspended', 'suspended': 'suspended',
    'injured reserve': 'ir', 'physically unable to perform': 'out',
    'non-football injury': 'out', 'inactive': 'inactive',
}
BLOCKED = {'out', 'suspended', 'ir', 'exempt', 'inactive', 'bye'}
TEAM_ALIASES = {'LAR': 'LA', 'WSH': 'WAS'}


def team_code(value: str) -> str:
    return TEAM_ALIASES.get(value, value)


@dataclass(frozen=True)
class Report:
    status: str
    updated_at: datetime | None = None


@dataclass(frozen=True)
class DepthPlayer:
    espn_id: str
    position: str
    rank: int
    status: str = 'available'


@dataclass(frozen=True)
class WeeklySnapshot:
    season: int
    week: int
    fetched_at: datetime
    current_week: int | None = None
    verified: bool = False
    reports: dict[str, Report] = field(default_factory=dict)
    depths: dict[str, tuple[DepthPlayer, ...]] = field(default_factory=dict)
    playing_teams: frozenset[str] = frozenset()
    warnings: tuple[str, ...] = ()
    source_urls: tuple[str, ...] = ()


def athlete_id(athlete: dict) -> str | None:
    if str(athlete.get('id', '')).isdigit():
        return str(athlete['id'])
    for link in athlete.get('links', []):
        parsed = urlparse(link.get('href', ''))
        if parsed.hostname not in {'www.espn.com', 'espn.com'}:
            continue
        match = re.search(r'/id/(\d+)(?:/|$)', parsed.path)
        if match:
            return match[1]
    return None


def feed_time(payload: dict, now: datetime) -> datetime:
    try:
        stamp = datetime.fromisoformat(payload['timestamp'].replace('Z', '+00:00'))
        if stamp.tzinfo is None or now - stamp > timedelta(hours=24) or stamp - now > timedelta(minutes=10):
            raise ValueError('stale timestamp')
        return stamp
    except (KeyError, ValueError, TypeError, AttributeError) as exc:
        raise ProviderError('Weekly ESPN feed is stale or has no valid timestamp') from exc


def parse_reports(payload: dict, season: int, now: datetime) -> dict[str, Report]:
    feed_time(payload, now)
    if payload.get('season', {}).get('year') != season or payload.get('season', {}).get('type') != 2:
        raise ProviderError('Injury report season does not match the matchup')
    if payload.get('status') != 'success' or not isinstance(payload.get('injuries'), list):
        raise ProviderError('ESPN injury report schema changed')
    reports = {}
    try:
        for team in payload['injuries']:
            for row in team['injuries']:
                athlete = row['athlete']
                if athlete.get('position', {}).get('abbreviation') not in {'QB', 'RB', 'WR', 'TE', 'K'}:
                    continue
                pid = athlete_id(athlete)
                if not pid:
                    raise ValueError('Missing offensive athlete ID')
                date = datetime.fromisoformat(row['date'].replace('Z', '+00:00'))
                if date.tzinfo is None or date > now + timedelta(minutes=10):
                    raise ValueError('Invalid report time')
                status = STATUSES.get(str(row['status']).lower(), 'unknown')
                fantasy = row.get('details', {}).get('fantasyStatus', {}).get('abbreviation', '')
                if fantasy == 'RESERVE-CEL':
                    status = 'exempt'
                report = Report(status, date)
                if pid not in reports or date > reports[pid].updated_at:
                    reports[pid] = report
    except (KeyError, ValueError, TypeError, AttributeError) as exc:
        raise ProviderError('ESPN injury report contains invalid player records') from exc
    return reports


def parse_depth(payload: dict, season: int, now: datetime) -> tuple[DepthPlayer, ...]:
    feed_time(payload, now)
    if payload.get('season', {}).get('year') != season or payload.get('season', {}).get('type') != 2:
        raise ProviderError('Depth chart season does not match the matchup')
    if payload.get('status') != 'success' or not isinstance(payload.get('depthchart'), list):
        raise ProviderError('ESPN depth chart schema changed')
    players = {}
    try:
        for formation in payload['depthchart']:
            for slot in formation['positions'].values():
                pos = slot['position']['abbreviation']
                if pos not in {'QB', 'RB', 'WR', 'TE', 'K'}:
                    continue
                for rank, athlete in enumerate(slot['athletes'], 1):
                    pid = athlete_id(athlete)
                    if not pid:
                        raise ValueError('Missing depth athlete ID')
                    injuries = athlete.get('injuries', [])
                    status = STATUSES.get(str(injuries[0].get('status', '')).lower(), 'unknown') if injuries else 'available'
                    entry = DepthPlayer(pid, pos, rank, status)
                    if pid not in players or rank < players[pid].rank:
                        players[pid] = entry
        if not players:
            raise ValueError('Empty offensive depth chart')
    except (KeyError, ValueError, TypeError, AttributeError) as exc:
        raise ProviderError('ESPN offensive depth chart is incomplete') from exc
    return tuple(players.values())


class WeeklyProvider:
    def __init__(self, transport: httpx.BaseTransport | None = None):
        self.transport = transport
        self._lock = Lock()
        self._cached: tuple[float, WeeklySnapshot] | None = None

    def _json(self, client: httpx.Client, path: str) -> dict:
        try:
            with client.stream('GET', BASE + path) as response:
                response.raise_for_status()
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > 15 * 1024 * 1024:
                        raise ProviderError('ESPN weekly download exceeded its size limit')
            result = json.loads(body)
            if not isinstance(result, dict):
                raise ValueError('Expected an object')
            return result
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError('ESPN weekly data is temporarily unavailable') from exc

    def snapshot(self, season: int, week: int) -> WeeklySnapshot:
        with self._lock:
            if self._cached:
                age, cached = monotonic() - self._cached[0], self._cached[1]
                if cached.season == season and cached.week == week and age < (300 if cached.verified else 30):
                    return cached
            now = datetime.now(timezone.utc)
            current_week = None
            paths = ['/scoreboard?limit=1000', '/injuries', '/teams?limit=100']
            try:
                with httpx.Client(timeout=15, transport=self.transport) as client:
                    board = self._json(client, paths[0])
                    reported_week = board.get('week', {}).get('number')
                    current_week = reported_week if isinstance(reported_week, int) and 1 <= reported_week <= 18 else None
                    if board.get('season', {}).get('type') != 2 or board.get('season', {}).get('year') != season or current_week != week:
                        raise ProviderError(f'Weekly availability is only verified for ESPN’s current regular-season week ({current_week}).')
                    teams_payload = self._json(client, paths[2])
                    teams = teams_payload['sports'][0]['leagues'][0]['teams']
                    team_ids = {team_code(row['team']['abbreviation']): str(row['team']['id']) for row in teams}
                    if len(team_ids) != 32:
                        raise ProviderError('Incomplete NFL team directory')
                    playing = set()
                    for event in board['events']:
                        if event.get('season', {}).get('year') != season or event.get('week', {}).get('number') != week:
                            raise ProviderError('Schedule includes a different week')
                        for competition in event['competitions']:
                            for competitor in competition['competitors']:
                                team = team_code(competitor['team']['abbreviation'])
                                if team in playing or team not in team_ids:
                                    raise ProviderError('Ambiguous weekly schedule')
                                playing.add(team)
                    if not 16 <= len(playing) <= 32 or len(playing) % 2:
                        raise ProviderError('Incomplete weekly schedule; cannot identify bye teams')
                    reports = parse_reports(self._json(client, paths[1]), season, now)
                    def fetch_depth(item):
                        team, tid = item
                        path = f'/teams/{tid}/depthcharts'
                        try:
                            payload = self._json(client, path)
                            if team_code(payload.get('team', {}).get('abbreviation', '')) != team:
                                raise ProviderError('Depth chart team mismatch')
                            return team, parse_depth(payload, season, now), None
                        except ProviderError as exc:
                            return team, (), str(exc)
                    with ThreadPoolExecutor(max_workers=8) as pool:
                        results = list(pool.map(fetch_depth, team_ids.items()))
                    warnings = tuple(f'{team}: {error}; workload redistribution disabled for this team.' for team, _, error in results if error)
                    result = WeeklySnapshot(season, week, now, current_week, True, reports,
                                            {team: depth for team, depth, error in results if not error},
                                            frozenset(playing), warnings,
                                            tuple(BASE + path for path in paths) + tuple(BASE + f'/teams/{tid}/depthcharts' for tid in team_ids.values()))
            except (ProviderError, KeyError, IndexError, TypeError, ValueError, AttributeError) as exc:
                result = WeeklySnapshot(season, week, now, current_week, warnings=(str(exc),),
                                        source_urls=tuple(BASE + path for path in paths))
            self._cached = (monotonic(), result)
            return result


weekly_provider = WeeklyProvider()
