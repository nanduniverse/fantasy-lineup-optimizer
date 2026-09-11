from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Position = Literal["QB", "RB", "WR", "TE", "K", "DST"]


class PlayerInput(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, str_strip_whitespace=True, extra="forbid")

    player_id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=120)
    team: str | None = Field(default=None, min_length=2, max_length=4)
    position: Position
    recent_points: list[float] = Field(default_factory=list, max_length=8)
    season_average: float = Field(ge=-100, le=100)
    matchup_multiplier: float = Field(default=1.0, ge=0.5, le=1.5)
    injury_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    projection_std_dev: float | None = Field(default=None, ge=0, le=100)
    workload_std_dev: float = Field(default=0, ge=0, le=30)
    workload_points_adjustment: float = Field(default=0, ge=0, le=60)
    boom_rate: float | None = Field(default=None, ge=0.0, le=1.0)

    @field_validator("recent_points")
    @classmethod
    def recent_points_valid(cls, values: list[float]) -> list[float]:
        if any(not -100 <= value <= 100 for value in values):
            raise ValueError("recent_points must be finite values between -100 and 100")
        return values
