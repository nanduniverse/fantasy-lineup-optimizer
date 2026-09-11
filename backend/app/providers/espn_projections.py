"""Public ESPN fantasy weekly projections. Filter explicitly: defaults include old seasons."""
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from threading import Lock
from time import monotonic

import httpx

from app.providers.nflverse import ProviderError
from app.schemas.scoring import ScoringFormat

BASE = 'https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons'
POSITIONS = {1: 'QB', 2: 'RB', 3: 'WR', 4: 'TE', 5: 'K', 16: 'DST'}
SCORING_KEYS = {'3', '4', '20', '24', '25', '41', '53', '42', '43', '72', '62', '19', '26', '44'}


@dataclass(frozen=True)
class WeeklyProjection:
    espn_id: str
    position: str
    stats: dict[str, float]

    def points(self, scoring: ScoringFormat) -> float:
        s = self.stats
        if self.position == 'K':
            return 3*s.get('80', 0) + 4*s.get('77', 0) + 5*s.get('74', 0) + s.get('86', 0) - s.get('85', 0) - s.get('88', 0)
        if self.position == 'DST':
            # Score probability-weighted points-allowed bands, not the band of the mean.
            bands = {'89': 10, '90': 7, '91': 4, '92': 1, '121': 1, '122': 0, '123': -1, '124': -4, '125': -4}
            return s.get('99', 0) + 2*sum(s.get(k, 0) for k in ('95', '96', '97', '98')) + 6*s.get('105', 0) + sum(s.get(k, 0)*v for k, v in bands.items())
        receptions = s.get('53', s.get('41', 0))
        conversions = s.get('62', sum(s.get(k, 0) for k in ('19', '26', '44')))
        return (s.get('3', 0) / 25 + 4 * s.get('4', 0) - 2 * s.get('20', 0)
                + (s.get('24', 0) + s.get('42', 0)) / 10
                + 6 * (s.get('25', 0) + s.get('43', 0))
                + scoring.reception_points * receptions - 2 * s.get('72', 0) + 2 * conversions)


@dataclass(frozen=True)
class ProjectionSnapshot:
    projections: dict[str, WeeklyProjection]
    fetched_at: datetime
    source_url: str
    warnings: tuple[str, ...] = ()


def parse_projections(payload: dict, season: int, week: int) -> dict[str, WeeklyProjection]:
    if not isinstance(payload, dict) or not isinstance(payload.get('players'), list):
        raise ProviderError('ESPN projection response has no player list')
    parsed = {}
    try:
        for wrapper in payload['players']:
            player = wrapper['player']
            if player.get('defaultPositionId') not in POSITIONS:
                continue
            records = [r for r in player.get('stats', []) if r.get('seasonId') == season
                       and r.get('statSourceId') == 1 and r.get('statSplitTypeId') == 1
                       and r.get('scoringPeriodId') == week]
            if not records:
                continue
            if len(records) != 1:
                raise ValueError('Ambiguous weekly forecast')
            values = records[0].get('stats', {})
            scoring_keys = {'74', '77', '80', '86'} if player['defaultPositionId'] == 5 else {'89', '99', '105'} if player['defaultPositionId'] == 16 else SCORING_KEYS
            if not scoring_keys.intersection(values):
                continue  # Empty projection is unavailable, not a published zero-point forecast.
            stats = {str(k): float(v) for k, v in values.items()}
            if any(not isfinite(v) for v in stats.values()):
                raise ValueError('Nonfinite projection')
            if any(stats.get(k, 0) < 0 for k in ('0', '23', '58', '4', '20', '25', '41', '53', '43', '72')):
                raise ValueError('Negative projected event count')
            pid = str(player['id'])
            if not pid.lstrip('-').isdigit() or pid in parsed:
                raise ValueError('Invalid or duplicate athlete identity')
            parsed[pid] = WeeklyProjection(pid, POSITIONS[player['defaultPositionId']], stats)
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise ProviderError('ESPN weekly projection records are invalid') from exc
    return parsed


class EspnProjectionProvider:
    def __init__(self, transport: httpx.BaseTransport | None = None):
        self.transport = transport
        self._lock = Lock()
        self._cached = None

    def snapshot(self, season: int, week: int, athlete_ids: list[str]) -> ProjectionSnapshot:
        ids = tuple(sorted({int(pid) for pid in athlete_ids if pid.lstrip('-').isdigit()}))
        key = (season, week, ids)
        url = f'{BASE}/{season}/segments/0/leaguedefaults/3?view=kona_player_info&scoringPeriodId={week}'
        with self._lock:
            if self._cached and self._cached[0] == key and monotonic() - self._cached[1] < 300:
                return self._cached[2]
            now = datetime.now(timezone.utc)
            try:
                projections = {}
                if len(ids) > 300:
                    raise ProviderError('ESPN projection request exceeds player limit')
                with httpx.Client(timeout=20, transport=self.transport) as client:
                    for start in range(0, len(ids), 100):
                        batch = ids[start:start + 100]
                        filters = {'players': {
                            'filterIds': {'value': batch}, 'limit': 100,
                            'sortPercOwned': {'sortPriority': 1, 'sortAsc': False},
                            'filterStatsForTopScoringPeriodIds': {'value': 2, 'additionalValue': [f'11{season}{week}']},
                        }}
                        with client.stream('GET', url, headers={'X-Fantasy-Filter': json.dumps(filters)}) as response:
                            response.raise_for_status()
                            body = bytearray()
                            for chunk in response.iter_bytes():
                                body.extend(chunk)
                                if len(body) > 10 * 1024 * 1024:
                                    raise ProviderError('ESPN projection download exceeded its size limit')
                        parsed = parse_projections(json.loads(body), season, week)
                        projections.update({pid: p for pid, p in parsed.items() if int(pid) in batch})
                result = ProjectionSnapshot(projections, now, url)
            except (httpx.HTTPError, ProviderError, ValueError) as exc:
                result = ProjectionSnapshot({}, now, url, ('ESPN forecasts are unavailable. Kickers, D/ST, and rookies without game history cannot be recommended until forecasts return.',))
            self._cached = (key, monotonic(), result)
            return result


projection_provider = EspnProjectionProvider()
