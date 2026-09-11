"""Download and normalize NFL stats; HTTP and CSV details stay outside the model."""
import csv
import io
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from time import monotonic

import httpx
from pydantic import ValidationError

from app.schemas.player import Position
from app.schemas.scoring import OffensiveStats

SOURCE = "nflverse"
BASE_URL = "https://github.com/nflverse/nflverse-data/releases/download/stats_player"
MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024
REQUIRED = {
    "attempts", "carries", "targets",
    "player_id", "player_display_name", "position", "season", "week", "season_type", "team",
    "passing_yards", "passing_tds", "passing_interceptions", "rushing_yards", "rushing_tds",
    "receptions", "receiving_yards", "receiving_tds", "sack_fumbles_lost",
    "rushing_fumbles_lost", "receiving_fumbles_lost", "passing_2pt_conversions",
    "rushing_2pt_conversions", "receiving_2pt_conversions",
}


class ProviderError(Exception):
    pass


class SeasonUnavailable(ProviderError):
    pass


@dataclass(frozen=True)
class PlayerGame:
    player_id: str
    name: str
    position: Position
    team: str
    season: int
    week: int
    stats: OffensiveStats


@dataclass(frozen=True)
class SeasonData:
    games: tuple[PlayerGame, ...]
    fetched_at: datetime
    source_url: str


def parse_stats(content: str, season: int) -> tuple[PlayerGame, ...]:
    reader = csv.DictReader(io.StringIO(content))
    if not REQUIRED.issubset(reader.fieldnames or []):
        raise ProviderError("NFL data schema changed: required scoring columns are missing")
    games = []
    seen = set()
    try:
        for row in reader:
            if row["position"] not in {"QB", "RB", "WR", "TE"} or row["season_type"] != "REG":
                continue
            if int(row["season"]) != season:
                raise ValueError("Unexpected season")
            week = int(row["week"])
            if not 1 <= week <= 18 or not row["player_id"] or not row["player_display_name"]:
                raise ValueError("Missing player identity or invalid week")
            key = (row["player_id"], week)
            if key in seen:
                raise ValueError("Duplicate player game")
            seen.add(key)
            # Missing required numbers are errors, never silently zero-scored.
            stats = OffensiveStats(
                passing_attempts=int(row["attempts"]), carries=int(row["carries"]), targets=int(row["targets"]),
                passing_yards=float(row["passing_yards"]),
                passing_tds=int(row["passing_tds"]),
                interceptions=int(row["passing_interceptions"]),
                rushing_yards=float(row["rushing_yards"]),
                rushing_tds=int(row["rushing_tds"]),
                receptions=int(row["receptions"]),
                receiving_yards=float(row["receiving_yards"]),
                receiving_tds=int(row["receiving_tds"]),
                fumbles_lost=sum(int(row[k]) for k in
                    ("sack_fumbles_lost", "rushing_fumbles_lost", "receiving_fumbles_lost")),
                two_point_conversions=sum(int(row[k]) for k in
                    ("passing_2pt_conversions", "rushing_2pt_conversions", "receiving_2pt_conversions")),
            )
            games.append(PlayerGame(row["player_id"], row["player_display_name"], row["position"],
                                    row["team"], season, week, stats))
    except (ValueError, TypeError, KeyError, csv.Error, ValidationError) as exc:
        raise ProviderError("NFL data contains incomplete or invalid offensive statistics") from exc
    return tuple(sorted(games, key=lambda game: (game.week, game.player_id)))


class NflverseProvider:
    """Bounded, one-hour process cache. A lock prevents duplicate simultaneous downloads."""

    def __init__(self, transport: httpx.BaseTransport | None = None):
        self.transport = transport
        self._cache: OrderedDict[int, tuple[float, SeasonData]] = OrderedDict()
        self._lock = Lock()

    def season(self, season: int) -> SeasonData:
        with self._lock:
            cached = self._cache.get(season)
            if cached and monotonic() - cached[0] < 3600:
                self._cache.move_to_end(season)
                return cached[1]
            url = f"{BASE_URL}/stats_player_week_{season}.csv"
            try:
                with httpx.Client(timeout=30, follow_redirects=True, transport=self.transport) as client:
                    with client.stream("GET", url) as response:
                        if response.status_code == 404:
                            raise SeasonUnavailable(f"NFL statistics for {season} have not been published")
                        response.raise_for_status()
                        content = bytearray()
                        for chunk in response.iter_bytes():
                            content.extend(chunk)
                            if len(content) > MAX_DOWNLOAD_BYTES:
                                raise ProviderError("NFL statistics download exceeded the size limit")
                games = parse_stats(content.decode("utf-8-sig"), season)
            except (httpx.HTTPError, UnicodeError) as exc:
                raise ProviderError("NFL statistics are temporarily unavailable; please retry") from exc
            data = SeasonData(games, datetime.now(timezone.utc), url)
            self._cache[season] = (monotonic(), data)
            self._cache.move_to_end(season)
            while len(self._cache) > 3:
                self._cache.popitem(last=False)
            return data


provider = NflverseProvider()
