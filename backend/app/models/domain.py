from dataclasses import dataclass


@dataclass(frozen=True)
class PlayerDistribution:
    player_id: str
    name: str
    position: str
    mean: float
    std_dev: float
    floor: float
    ceiling: float
    team: str | None = None
