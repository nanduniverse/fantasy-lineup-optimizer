from app.schemas.scoring import OffensiveStats, ScoringFormat


def fantasy_points(stats: OffensiveStats, scoring: ScoringFormat) -> float:
    """Fractional offensive scoring, with no bonuses or special-teams points."""
    return round(
        stats.passing_yards / 25
        + 4 * stats.passing_tds
        - 2 * stats.interceptions
        + (stats.rushing_yards + stats.receiving_yards) / 10
        + 6 * (stats.rushing_tds + stats.receiving_tds)
        + scoring.reception_points * stats.receptions
        - 2 * stats.fumbles_lost
        + 2 * stats.two_point_conversions,
        2,
    )
