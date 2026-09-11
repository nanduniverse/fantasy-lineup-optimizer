from dataclasses import dataclass

import numpy as np

from app.core.roster_rules import RosterRules
from app.models.domain import PlayerDistribution
from app.schemas.lineup import LineupResult, PlayerProjection
from app.services.lineup_generator import generate_legal_lineups
from app.services.simulator import sample_player_scores


@dataclass
class RankedLineup:
    result: LineupResult
    raw_win_probability: float


def _serialize_lineup(
    lineup: tuple[PlayerDistribution, ...],
    win_probability: float,
    rules: RosterRules,
) -> LineupResult:
    remaining = {pos: getattr(rules, pos.lower()) for pos in ("QB", "RB", "WR", "TE", "K", "DST")}
    slots = {}
    for player in lineup:
        slots[player.player_id] = player.position if remaining[player.position] else "FLEX"
        remaining[player.position] = max(0, remaining[player.position] - 1)
    starters = [
        PlayerProjection(
            player_id=p.player_id,
            name=p.name,
            position=p.position,
            team=p.team,
            slot=slots[p.player_id],
            mean=round(p.mean, 2),
            floor=round(p.floor, 2),
            ceiling=round(p.ceiling, 2),
            volatility=round(p.std_dev, 2),
        )
        for p in lineup
    ]
    starters.sort(key=lambda p: ("QB", "RB", "WR", "TE", "FLEX", "K", "DST").index(p.slot))

    return LineupResult(
        starters=starters,
        expected_points=round(sum(p.mean for p in lineup), 2),
        win_probability=round(win_probability, 4),
    )


def optimize_lineup(
    roster: list[PlayerDistribution],
    opponent: list[PlayerDistribution],
    rules: RosterRules,
    simulations: int,
    seed: int | None,
) -> tuple[list[LineupResult], float]:
    candidates = generate_legal_lineups(roster, rules)
    if len(candidates) * simulations * rules.starter_count > 100_000_000:
        raise ValueError("Simulation budget exceeded; reduce simulations, roster size, or slots")
    rng = np.random.default_rng(seed)
    # One joint draw across BOTH teams preserves stacks and opposing-team player relationships.
    samples = sample_player_scores(roster + opponent, simulations, rng)
    opponent_scores = sum((samples[p.player_id] for p in opponent), np.zeros(simulations))
    opponent_expected = float(sum(player.mean for player in opponent))

    ranked: list[RankedLineup] = []

    for lineup in candidates:
        scores = sum((samples[p.player_id] for p in lineup), np.zeros(simulations))
        wins = np.mean(scores > opponent_scores)
        ties = np.mean(scores == opponent_scores)
        win_probability = float(wins + 0.5 * ties)

        ranked.append(
            RankedLineup(
                result=_serialize_lineup(lineup, win_probability, rules),
                raw_win_probability=win_probability,
            )
        )

    ranked.sort(
        key=lambda item: (
            item.raw_win_probability,
            item.result.expected_points,
        ),
        reverse=True,
    )

    return [item.result for item in ranked], round(opponent_expected, 2)
