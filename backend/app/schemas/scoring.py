from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ScoringFormat(str, Enum):
    STANDARD = "standard"
    HALF_PPR = "half_ppr"
    PPR = "ppr"

    @property
    def reception_points(self) -> float:
        return {self.STANDARD: 0.0, self.HALF_PPR: 0.5, self.PPR: 1.0}[self]


class OffensiveStats(BaseModel):
    """Provider-independent, single-game offensive box score."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, frozen=True)
    passing_attempts: int = Field(default=0, ge=0)
    carries: int = Field(default=0, ge=0)
    targets: int = Field(default=0, ge=0)
    passing_yards: float = 0
    passing_tds: int = Field(default=0, ge=0)
    interceptions: int = Field(default=0, ge=0)
    rushing_yards: float = 0
    rushing_tds: int = Field(default=0, ge=0)
    receptions: int = Field(default=0, ge=0)
    receiving_yards: float = 0
    receiving_tds: int = Field(default=0, ge=0)
    fumbles_lost: int = Field(default=0, ge=0)
    two_point_conversions: int = Field(default=0, ge=0)
