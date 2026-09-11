from itertools import combinations, product
from math import comb

from app.core.roster_rules import RosterRules
from app.models.domain import PlayerDistribution

MAX_CANDIDATES = 5000


def generate_legal_lineups(
    players: list[PlayerDistribution], rules: RosterRules
) -> list[tuple[PlayerDistribution, ...]]:
    """Choose position counts first, so FLEX assignments never duplicate a team."""
    positions = ("QB", "RB", "WR", "TE", "K", "DST")
    pools = {pos: sorted((p for p in players if p.position == pos), key=lambda p: p.player_id)
             for pos in positions}
    required = (rules.qb, rules.rb, rules.wr, rules.te, rules.k, rules.dst)
    for pos, count in zip(positions, required):
        if len(pools[pos]) < count:
            raise ValueError(f"Not enough {pos} players to create a legal lineup")
    allocations = []
    total = 0
    for rb_extra in range(rules.flex + 1):
        for wr_extra in range(rules.flex - rb_extra + 1):
            counts = (rules.qb, rules.rb + rb_extra, rules.wr + wr_extra,
                      rules.te + rules.flex - rb_extra - wr_extra, rules.k, rules.dst)
            if any(count > len(pools[pos]) for pos, count in zip(positions, counts)):
                continue
            size = 1
            for pos, count in zip(positions, counts):
                size *= comb(len(pools[pos]), count)
            total += size
            if total > MAX_CANDIDATES:
                raise ValueError(f"Roster exceeds {MAX_CANDIDATES} legal lineups; reduce roster or slots")
            allocations.append(counts)
    if not total:
        raise ValueError("Roster cannot form a legal lineup under the supplied rules")
    return [tuple(player for group in groups for player in group)
            for counts in allocations
            for groups in product(*(combinations(pools[pos], count)
                                    for pos, count in zip(positions, counts)))]
