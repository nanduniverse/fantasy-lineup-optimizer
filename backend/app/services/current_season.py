from collections import defaultdict
from statistics import mean

from app.providers.nflverse import SeasonData
from app.providers.rosters import CurrentRoster
from app.schemas.nfl import NflCatalog, NflContext, NflPlayer
from app.schemas.player import PlayerInput
from app.services.projection import build_distribution
from app.services.scoring import fantasy_points
from app.providers.espn_projections import ProjectionSnapshot
from app.services.rookies import rookie_entry

SEASON = 2026


def current_catalog(roster: CurrentRoster, histories: list[SeasonData], context: NflContext, rookie_projections: ProjectionSnapshot | None = None) -> NflCatalog:
    by_player = defaultdict(list)
    for history in histories:
        for game in history.games:
            if game.season < context.season or (game.season == context.season and game.week < context.target_week):
                by_player[game.player_id].append(game)
    players = []
    missing = 0
    for veteran in roster.players:
        games = sorted(by_player[veteran.player_id], key=lambda game: (game.season, game.week))
        if veteran.position in {"K", "DST"}:
            from app.services.special_teams import special_entry
            players.append(special_entry(veteran, context, rookie_projections))
            continue
        if not games and veteran.is_rookie:
            players.append(rookie_entry(veteran, context, rookie_projections))
            continue
        if not games:
            missing += 1
            continue
        # Current season supersedes prior-season prior once games exist. Before that,
        # use the most recent season with recorded games (up to two years back).
        history_season = games[-1].season
        games = [g for g in games if g.season == history_season]
        points = [fantasy_points(g.stats, context.scoring_format) for g in games]
        player = PlayerInput(player_id=veteran.player_id, name=veteran.name, position=veteran.position,
                             team=veteran.team, season_average=round(mean(points), 4), recent_points=points[-8:])
        players.append(NflPlayer(player=player, team=veteran.team, is_rookie=veteran.is_rookie, draft_pick=veteran.draft_pick, games_played=len(games),
                                 last_played_week=games[-1].week, history_season=history_season,
                                 projected_points=round(build_distribution(player).mean, 2)))
    identities = {p.player_id: p for p in roster.players}
    for entry in players:
        identity = identities[entry.player.player_id]
        entry.espn_id = identity.espn_id
        if identity.position == 'DST':
            code = {'LA': 'lar', 'WAS': 'wsh'}.get(identity.team, identity.team.lower())
            entry.image_url = f'https://a.espncdn.com/i/teamlogos/nfl/500/{code}.png'
        elif identity.espn_id and identity.espn_id.isdigit():
            entry.image_url = f'https://a.espncdn.com/i/headshots/nfl/players/full/{identity.espn_id}.png'
    warnings = [
        '2026 rostered players, including rookies, kickers and team D/ST. Reserve/exempt players remain visible so their absence can inform replacement workloads.',
        'Preseason projections use the latest available season of game history. Current-season games replace that baseline when available.',
        'Stacks share a simulated passing environment (assumed QB–WR/TE correlation 0.30). This changes risk, not projected points; it does not guarantee better odds.',
        'Weekly availability and depth information is applied separately. Opponent defenses are not modeled. Win probabilities are uncalibrated estimates.',
    ]
    if rookie_projections:
        warnings.extend(rookie_projections.warnings)
    if missing:
        warnings.append(f'{missing} rostered veterans have no scoring history in the last two seasons and are omitted.')
    return NflCatalog(**context.model_dump(), source='nflverse', source_url=roster.source_url,
                      fetched_at=min([roster.fetched_at] + [h.fetched_at for h in histories]),
                      available_through_week=max((g.week for h in histories for g in h.games
                          if g.season == context.season and g.week < context.target_week), default=None),
                      players=sorted(players, key=lambda p: (-(p.projected_points or 0), p.player.name)), warnings=warnings)
