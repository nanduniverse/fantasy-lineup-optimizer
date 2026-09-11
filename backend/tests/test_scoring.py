import pytest

from app.schemas.scoring import OffensiveStats, ScoringFormat
from app.services.scoring import fantasy_points
from app.schemas.player import PlayerInput


@pytest.mark.parametrize("scoring, expected", [(ScoringFormat.STANDARD, 38), (ScoringFormat.HALF_PPR, 40.5), (ScoringFormat.PPR, 43)])
def test_complete_offensive_scoring(scoring, expected):
    stats = OffensiveStats(passing_yards=250, passing_tds=2, interceptions=1,
                           rushing_yards=30, rushing_tds=1, receptions=5,
                           receiving_yards=70, receiving_tds=1, fumbles_lost=2,
                           two_point_conversions=2)
    assert fantasy_points(stats, scoring) == expected


def test_negative_scores_are_preserved():
    score = fantasy_points(OffensiveStats(rushing_yards=-3, fumbles_lost=1), ScoringFormat.PPR)
    assert score == -2.3
    assert PlayerInput(player_id="a", name="A", position="RB", season_average=score,
                       recent_points=[score]).recent_points == [-2.3]


@pytest.mark.parametrize("scoring", list(ScoringFormat))
def test_empty_box_score_is_zero(scoring):
    assert fantasy_points(OffensiveStats(), scoring) == 0
