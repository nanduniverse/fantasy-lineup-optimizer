from collections import defaultdict
from statistics import mean

from app.providers.nflverse import SOURCE, SeasonData
from app.schemas.nfl import NflCatalog, NflContext, NflPlayer
from app.schemas.player import PlayerInput
from app.services.scoring import fantasy_points


def build_catalog(data: SeasonData, context: NflContext) -> NflCatalog:
    # Filter BEFORE aggregation: the target week and future weeks must not leak into features.
    by_player = defaultdict(list)
    for game in data.games:
        if game.season == context.season and game.week < context.target_week:
            by_player[game.player_id].append(game)
    players = []
    for games in by_player.values():
        games.sort(key=lambda g: g.week)
        latest = games[-1]
        points = [fantasy_points(g.stats, context.scoring_format) for g in games]
        players.append(NflPlayer(
            player=PlayerInput(player_id=latest.player_id, name=latest.name, position=latest.position,
                               season_average=round(mean(points), 4), recent_points=points[-8:]),
            team=latest.team, games_played=len(games), last_played_week=latest.week,
        ))
    through = max((game.week for game in data.games if game.week < context.target_week), default=None)
    warnings = [
        "Historical regular-season statistics, not live projections or an active roster. "
        "No injury, availability, upcoming bye, or matchup data is applied.",
        "Only recorded games count toward averages; missing games are not scored as zero. "
        "Players without prior games in the selected season are unavailable.",
    ]
    if through is None:
        warnings.append("No games before the target week. Week 1 needs a prior-season or rookie projection model.")
    elif through < context.target_week - 1:
        warnings.append(f"Data only reaches week {through}; the selected target week has a history gap.")
    return NflCatalog(**context.model_dump(), source=SOURCE, source_url=data.source_url,
                      fetched_at=data.fetched_at, available_through_week=through,
                      players=sorted(players, key=lambda p: (-p.player.season_average, p.player.player_id)),
                      warnings=warnings)
