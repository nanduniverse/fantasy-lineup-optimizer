from math import exp

from app.providers.espn_projections import ProjectionSnapshot
from app.providers.rosters import RosterPlayer
from app.schemas.nfl import NflContext, NflPlayer
from app.schemas.player import PlayerInput

# Draft capital is a deliberately small, uncalibrated opportunity prior.
# These are weekly no-PPR anchors at pick 1, not ESPN values or learned coefficients.
DRAFT_ANCHORS = {'QB': 17.0, 'RB': 10.0, 'WR': 8.0, 'TE': 5.0}
RECEPTION_ANCHORS = {'QB': 0.0, 'RB': 2.0, 'WR': 4.0, 'TE': 3.0}


def rookie_entry(rookie: RosterPlayer, context: NflContext, snapshot: ProjectionSnapshot | None) -> NflPlayer:
    projection = snapshot.projections.get(rookie.espn_id) if snapshot and rookie.espn_id else None
    player = PlayerInput(player_id=rookie.player_id, name=rookie.name, team=rookie.team,
                         position=rookie.position, season_average=0)
    common = dict(player=player, team=rookie.team, is_rookie=True, draft_pick=rookie.draft_pick,
                  games_played=0, last_played_week=None, history_season=None,
                  projection_source_url=snapshot.source_url if snapshot else None,
                  projection_fetched_at=snapshot.fetched_at if snapshot else None)
    if not projection or projection.position != rookie.position:
        return NflPlayer(**common, has_projection=False, eligible=False, projected_points=None,
                         projection_method='unavailable', projection_notes=['No matching ESPN weekly forecast is published or mapped for this rookie. No game history is fabricated.'])
    espn = projection.points(context.scoring_format)
    if not -100 <= espn <= 100:
        return NflPlayer(**common, has_projection=False, eligible=False, projection_method='unavailable',
                         projection_notes=['ESPN forecast is outside the supported weekly range.'])
    prior = None
    mean = espn
    if rookie.draft_pick:
        prior = (DRAFT_ANCHORS[rookie.position] + context.scoring_format.reception_points * RECEPTION_ANCHORS[rookie.position]) * exp(-(rookie.draft_pick - 1) / 120)
        blended = .90 * espn + .10 * prior
        limit = abs(espn) * .10
        mean = max(espn - limit, min(espn + limit, blended))
    player.season_average = round(mean, 4)
    player.projection_std_dev = round(max(2.5, abs(mean) * .50), 4) if mean != 0 else 0
    notes = [f'ESPN week {context.target_week} forecast recalculated for {context.scoring_format.value}.',
             '90% ESPN / 10% draft-position prior; the draft adjustment is capped at ±10% of ESPN. Draft weights are heuristic, not calibrated.' if prior is not None else 'No verified draft pick: ESPN forecast is used without a draft adjustment.',
             'No additional absence boost is added to this forecast; ESPN may already account for depth-chart changes.']
    return NflPlayer(**common, projection_method='espn_draft', espn_projected_points=round(espn, 2),
                     draft_prior_points=round(prior, 2) if prior is not None else None,
                     draft_adjustment=round(mean - espn, 2), projected_points=round(mean, 2),
                     projected_carries=round(projection.stats.get('23', 0), 2),
                     projected_targets=round(projection.stats.get('58', 0), 2),
                     projected_passing_attempts=round(projection.stats.get('0', 0), 2),
                     projection_notes=notes)
