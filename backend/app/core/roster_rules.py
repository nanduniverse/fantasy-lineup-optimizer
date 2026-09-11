from dataclasses import dataclass


@dataclass(frozen=True)
class RosterRules:
    qb: int = 1
    rb: int = 2
    wr: int = 2
    te: int = 1
    k: int = 0
    dst: int = 0
    flex: int = 1

    @property
    def starter_count(self) -> int:
        return self.qb + self.rb + self.wr + self.te + self.flex + self.k + self.dst


DEFAULT_RULES = RosterRules()
FLEX_ELIGIBLE = {"RB", "WR", "TE"}
