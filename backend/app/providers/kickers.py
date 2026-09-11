"""Discover ESPN-listed kickers, including players outside current NFL rosters."""
from threading import Lock
from time import monotonic
import json
import httpx
from app.providers.espn_projections import BASE
from app.providers.rosters import CurrentRoster, RosterPlayer, DEFENSE_TEAMS
from app.providers.nflverse import ProviderError

TEAM_IDS = {int(espn_id.removeprefix('-160')): team for espn_id, _, team in DEFENSE_TEAMS}


def parse_kickers(payload: dict) -> tuple[RosterPlayer, ...]:
    try:
        rows = payload['players']
        if not isinstance(rows, list) or len(rows) >= 200:
            raise ValueError('Missing or truncated kicker list')
        players = {}
        for row in rows:
            p = row['player']
            if p['defaultPositionId'] != 5:
                continue
            pid, name, team_id = str(p['id']), p['fullName'], p['proTeamId']
            if not pid.isdigit() or not name or pid in players or (team_id != 0 and team_id not in TEAM_IDS):
                raise ValueError('Invalid kicker identity')
            players[pid] = RosterPlayer('espn:' + pid, name, 'K', TEAM_IDS.get(team_id, 'FA'), pid,
                                       'FA' if team_id == 0 else 'ACT')
        return tuple(players.values())
    except (KeyError, TypeError, ValueError) as exc:
        raise ProviderError('ESPN kicker identities are unavailable') from exc


class KickerProvider:
    def __init__(self, transport=None):
        self.transport = transport
        self._lock = Lock()
        self._cached = None

    def augment(self, roster: CurrentRoster, season: int) -> tuple[CurrentRoster, tuple[str, ...]]:
        with self._lock:
            if not self._cached or self._cached[0] != season or monotonic() - self._cached[1] > 300:
                try:
                    url = f'{BASE}/{season}/segments/0/leaguedefaults/3?view=kona_player_info'
                    filters = {'players': {'filterSlotIds': {'value': [17]}, 'limit': 200,
                                          'sortPercOwned': {'sortPriority': 1, 'sortAsc': False}}}
                    with httpx.Client(timeout=20, transport=self.transport) as client:
                        with client.stream('GET', url, headers={'X-Fantasy-Filter': json.dumps(filters)}) as response:
                            response.raise_for_status()
                            body = bytearray()
                            for chunk in response.iter_bytes():
                                body.extend(chunk)
                                if len(body) > 10 * 1024 * 1024:
                                    raise ProviderError('Kicker list exceeds download limit')
                    players = parse_kickers(json.loads(body))
                    warnings = ()
                except (httpx.HTTPError, ProviderError, ValueError):
                    players = ()
                    warnings = ('ESPN kicker discovery is unavailable; only current roster kickers are shown.',)
                self._cached = (season, monotonic(), players, warnings)
            known = {p.espn_id for p in roster.players if p.espn_id}
            extra = tuple(p for p in self._cached[2] if p.espn_id not in known)
            return CurrentRoster(roster.players + extra, roster.fetched_at, roster.source_url), self._cached[3]


kicker_provider = KickerProvider()
