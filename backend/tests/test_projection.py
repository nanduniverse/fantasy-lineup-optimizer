from app.schemas.player import PlayerInput
from app.services.projection import build_distribution


def test_projection_uses_recent_form_and_matchup():
    player = PlayerInput(
        player_id="1",
        name="Test Player",
        position="WR",
        recent_points=[20, 22, 24, 26],
        season_average=15,
        matchup_multiplier=1.10,
        injury_risk=0,
    )

    distribution = build_distribution(player)

    assert distribution.mean > player.season_average
    assert distribution.ceiling > distribution.mean
    assert distribution.floor < distribution.mean
    assert distribution.std_dev >= 2
