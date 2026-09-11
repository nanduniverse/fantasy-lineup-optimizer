"""Weekly K and D/ST forecasts; no fabricated offensive history or workload transfer."""
from app.providers.espn_projections import ProjectionSnapshot
from app.providers.rosters import RosterPlayer
from app.schemas.nfl import NflContext, NflPlayer
from app.schemas.player import PlayerInput


def special_entry(identity: RosterPlayer, context: NflContext, snapshot: ProjectionSnapshot | None) -> NflPlayer:
    forecast = snapshot.projections.get(identity.espn_id) if snapshot else None
    points = forecast.points(context.scoring_format) if forecast and forecast.position == identity.position else None
    if points is not None and not -100 <= points <= 100:
        points = None
    available = points is not None
    return NflPlayer(
        player=PlayerInput(player_id=identity.player_id, name=identity.name, team=identity.team,
                           position=identity.position, season_average=round(points or 0, 4),
                           projection_std_dev=4 if identity.position == 'K' else 6),
        is_rookie=identity.is_rookie, draft_pick=identity.draft_pick,
        team=identity.team, projected_points=round(points, 2) if available else None,
        games_played=0, last_played_week=None, has_projection=available, eligible=available,
        projection_method='espn_weekly' if available else 'unavailable',
        espn_projected_points=round(points, 2) if available else None,
        projection_source_url=snapshot.source_url if snapshot else None,
        projection_fetched_at=snapshot.fetched_at if snapshot else None,
        projection_notes=['ESPN weekly projected statistics scored using this app’s K/D/ST rules. PPR does not change these points. No draft or offensive workload adjustment.',
                          'Simulation standard deviation is an uncalibrated assumption: K 4 points; D/ST 6 points. Opposing offense/defense correlations are not modeled.'] if available else ['No matching ESPN weekly forecast available; excluded from recommendations.'],
    )
