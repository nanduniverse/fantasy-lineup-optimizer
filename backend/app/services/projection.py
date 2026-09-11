from statistics import mean, pstdev
from math import hypot

from app.models.domain import PlayerDistribution
from app.schemas.player import PlayerInput


def build_distribution(player: PlayerInput) -> PlayerDistribution:
    """Create a transparent MVP scoring distribution for a player.

    Recent games receive more influence than the season average. Matchup and
    injury inputs then adjust the expected value. Volatility is primarily
    empirical, with conservative fallbacks for tiny samples.
    """
    recent = player.recent_points[-4:]

    if recent:
        recent_avg = mean(recent)
        weighted_mean = 0.65 * recent_avg + 0.35 * player.season_average
    else:
        weighted_mean = player.season_average

    injury_multiplier = max(0.50, 1.0 - 0.35 * player.injury_risk)
    adjusted_mean = weighted_mean * player.matchup_multiplier * injury_multiplier + player.workload_points_adjustment

    if len(recent) >= 2:
        empirical_std = pstdev(recent)
    else:
        empirical_std = max(3.0, player.season_average * 0.25)

    boom_adjustment = 1.0 + 0.35 * (player.boom_rate or 0.0)
    base_std = player.projection_std_dev if player.projection_std_dev is not None else max(2.0, empirical_std * boom_adjustment)
    std_dev = hypot(base_std, player.workload_std_dev)

    floor = max(0.0, adjusted_mean - 1.25 * std_dev)
    ceiling = adjusted_mean + 1.75 * std_dev

    return PlayerDistribution(
        player_id=player.player_id,
        name=player.name,
        position=player.position,
        team=player.team,
        mean=round(adjusted_mean, 3),
        std_dev=round(std_dev, 3),
        floor=round(floor, 3),
        ceiling=round(ceiling, 3),
    )
