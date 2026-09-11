import numpy as np
import pytest

from app.core.roster_rules import RosterRules
from app.models.domain import PlayerDistribution
from app.services.optimizer import optimize_lineup
from app.services.lineup_generator import generate_legal_lineups
from app.services.simulator import simulate_lineup_scores


def player(pid, mean, std=2, position="QB"):
    return PlayerDistribution(pid, pid, position, mean, std, mean-std, mean+std)


def test_underdog_prefers_upside_but_favorite_prefers_safety():
    roster = [player("safe", 20, 1), player("upside", 19, 10)]
    rules = RosterRules(qb=1, rb=0, wr=0, te=0, flex=0)
    underdog, _ = optimize_lineup(roster, [player("opponent", 30, 1)], rules, 50000, 42)
    favorite, _ = optimize_lineup(roster, [player("opponent", 10, 1)], rules, 50000, 42)
    assert underdog[0].starters[0].player_id == "upside"
    assert favorite[0].starters[0].player_id == "safe"


def test_seed_and_input_order_are_reproducible():
    roster = [player("a", 20), player("b", 19)]
    rules = RosterRules(qb=1, rb=0, wr=0, te=0, flex=0)
    args = ([player("opponent", 20)], rules, 5000, 7)
    assert optimize_lineup(roster, *args) == optimize_lineup(roster[::-1], *args)


def test_simulated_mean_matches_reported_mean():
    scores = simulate_lineup_scores([player("a", 0, 10)], 100000, np.random.default_rng(42))
    assert abs(scores.mean()) < 0.1


def test_flex_lineups_are_unique_and_slots_are_legal():
    roster = [player(str(i), 10, position="RB") for i in range(4)]
    rules = RosterRules(qb=0, rb=1, wr=0, te=0, flex=1)
    lineups = generate_legal_lineups(roster, rules)
    assert len(lineups) == 6
    assert len({frozenset(p.player_id for p in lineup) for lineup in lineups}) == 6
    ranked, _ = optimize_lineup(roster, [player("o", 10)], rules, 500, 42)
    assert [p.slot for p in ranked[0].starters] == ["RB", "FLEX"]


def test_large_search_is_rejected_before_enumeration():
    roster = [player(str(i), 10, position="WR") for i in range(30)]
    with pytest.raises(ValueError, match="legal lineups"):
        generate_legal_lineups(roster, RosterRules(qb=0, rb=0, wr=4, te=0, flex=3))
