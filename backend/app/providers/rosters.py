"""Current-season roster identity is separate from historical scoring statistics."""
import csv
import io
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from time import monotonic

import httpx

from app.providers.nflverse import ProviderError, MAX_DOWNLOAD_BYTES


@dataclass(frozen=True)
class RosterPlayer:
    player_id: str
    name: str
    position: str
    team: str
    espn_id: str | None = None
    roster_status: str = "ACT"
    is_rookie: bool = False
    draft_pick: int | None = None


@dataclass(frozen=True)
class CurrentRoster:
    players: tuple[RosterPlayer, ...]
    fetched_at: datetime
    source_url: str


def parse_roster(content: str, season: int) -> tuple[RosterPlayer, ...]:
    reader = csv.DictReader(io.StringIO(content))
    required = {'season', 'gsis_id', 'full_name', 'position', 'team', 'years_exp', 'status'}
    if not required.issubset(reader.fieldnames or []):
        raise ProviderError('Current NFL roster schema has changed')
    players = {}
    try:
        for row in reader:
            if int(row['season']) != season:
                raise ValueError('Wrong roster season')
            allowed = {'ACT', 'RES', 'EXE', 'INA', 'DEV', 'CUT', 'FA'} if row['position'] == 'K' else {'ACT', 'RES', 'EXE', 'INA'}
            if row['position'] not in {'QB', 'RB', 'WR', 'TE', 'K'} or row['status'] not in allowed:
                continue
            if not row['gsis_id'] or not row['years_exp']:
                continue
            player = RosterPlayer(row['gsis_id'], row['full_name'], row['position'], 'FA' if row['status'] in {'CUT', 'FA'} else row['team'], row.get('espn_id') or None, row['status'],
                                  float(row['years_exp']) == 0,
                                  int(row['draft_number']) if row.get('draft_number', '').isdigit() and 1 <= int(row['draft_number']) <= 300 else None)
            if not player.team or not player.name or player.player_id in players:
                raise ValueError('Invalid or ambiguous current team')
            players[player.player_id] = player
    except (ValueError, KeyError, csv.Error) as exc:
        raise ProviderError('Current NFL roster contains invalid records') from exc
    return tuple(players.values())


class RosterProvider:
    def __init__(self):
        self._lock = Lock()
        self._cached = None

    def roster(self, season: int) -> CurrentRoster:
        with self._lock:
            if self._cached and self._cached[0] == season and monotonic() - self._cached[1] < 3600:
                return self._cached[2]
            url = f'https://github.com/nflverse/nflverse-data/releases/download/rosters/roster_{season}.csv'
            try:
                with httpx.Client(timeout=30, follow_redirects=True) as client:
                    with client.stream('GET', url) as response:
                        response.raise_for_status()
                        content = bytearray()
                        for chunk in response.iter_bytes():
                            content.extend(chunk)
                            if len(content) > MAX_DOWNLOAD_BYTES:
                                raise ProviderError('Roster download exceeds size limit')
                players = parse_roster(content.decode('utf-8-sig'), season)
            except (httpx.HTTPError, UnicodeError) as exc:
                raise ProviderError('Current NFL roster is temporarily unavailable; please retry') from exc
            data = CurrentRoster(players, datetime.now(timezone.utc), url)
            self._cached = (season, monotonic(), data)
            return data


roster_provider = RosterProvider()


# Stable ESPN team-defense identities, separate from individual athlete IDs.
DEFENSE_TEAMS = (('-16034', 'Texans D/ST', 'HOU'), ('-16007', 'Broncos D/ST', 'DEN'), ('-16026', 'Seahawks D/ST', 'SEA'), ('-16014', 'Rams D/ST', 'LA'), ('-16023', 'Steelers D/ST', 'PIT'), ('-16033', 'Ravens D/ST', 'BAL'), ('-16021', 'Eagles D/ST', 'PHI'), ('-16008', 'Lions D/ST', 'DET'), ('-16017', 'Patriots D/ST', 'NE'), ('-16030', 'Jaguars D/ST', 'JAX'), ('-16024', 'Chargers D/ST', 'LAC'), ('-16005', 'Browns D/ST', 'CLE'), ('-16012', 'Chiefs D/ST', 'KC'), ('-16009', 'Packers D/ST', 'GB'), ('-16027', 'Buccaneers D/ST', 'TB'), ('-16016', 'Vikings D/ST', 'MIN'), ('-16006', 'Cowboys D/ST', 'DAL'), ('-16010', 'Titans D/ST', 'TEN'), ('-16003', 'Bears D/ST', 'CHI'), ('-16025', '49ers D/ST', 'SF'), ('-16002', 'Bills D/ST', 'BUF'), ('-16020', 'Jets D/ST', 'NYJ'), ('-16018', 'Saints D/ST', 'NO'), ('-16019', 'Giants D/ST', 'NYG'), ('-16011', 'Colts D/ST', 'IND'), ('-16004', 'Bengals D/ST', 'CIN'), ('-16013', 'Raiders D/ST', 'LV'), ('-16001', 'Falcons D/ST', 'ATL'), ('-16029', 'Panthers D/ST', 'CAR'), ('-16028', 'Commanders D/ST', 'WAS'), ('-16015', 'Dolphins D/ST', 'MIA'), ('-16022', 'Cardinals D/ST', 'ARI'))

def with_defenses(roster: CurrentRoster) -> CurrentRoster:
    defenses = tuple(RosterPlayer("dst:" + team, name, "DST", team, espn_id) for espn_id, name, team in DEFENSE_TEAMS)
    return CurrentRoster(roster.players + defenses, roster.fetched_at, roster.source_url)
