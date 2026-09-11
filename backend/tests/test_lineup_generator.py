from app.core.roster_rules import RosterRules
from app.models.domain import PlayerDistribution
from app.services.lineup_generator import generate_legal_lineups


def p(pid: str, pos: str) -> PlayerDistribution:
    return PlayerDistribution(pid, pid, pos, 10, 3, 5, 16)


def test_generates_legal_lineups():
    players = [
        p("q1", "QB"),
        p("r1", "RB"), p("r2", "RB"), p("r3", "RB"),
        p("w1", "WR"), p("w2", "WR"), p("w3", "WR"),
        p("t1", "TE"), p("t2", "TE"),
    ]

    lineups = generate_legal_lineups(players, RosterRules())

    assert lineups
    assert all(len(lineup) == 7 for lineup in lineups)
    assert all(sum(player.position == "QB" for player in lineup) == 1 for lineup in lineups)
