from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.player import PlayerInput


class RosterRulesInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def nonempty(self):
        if sum(self.model_dump().values()) == 0:
            raise ValueError("At least one starter slot is required")
        return self

    qb: int = Field(default=1, ge=0, le=2)
    rb: int = Field(default=2, ge=0, le=4)
    wr: int = Field(default=2, ge=0, le=4)
    te: int = Field(default=1, ge=0, le=2)
    k: int = Field(default=0, ge=0, le=2)
    dst: int = Field(default=0, ge=0, le=2)
    flex: int = Field(default=1, ge=0, le=3)


class RecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    your_roster: list[PlayerInput] = Field(min_length=1, max_length=30)
    opponent_lineup: list[PlayerInput] = Field(min_length=1, max_length=30)
    rules: RosterRulesInput = Field(default_factory=RosterRulesInput)
    simulations: int = Field(default=5000, ge=500, le=50000)
    seed: int = Field(default=42, ge=0, le=2**32 - 1)

    @model_validator(mode="after")
    def unique_player_ids(self):
        ids = [p.player_id for p in self.your_roster]
        if len(ids) != len(set(ids)):
            raise ValueError("your_roster contains duplicate player_id values")
        opponent_ids = [p.player_id for p in self.opponent_lineup]
        if len(opponent_ids) != len(set(opponent_ids)):
            raise ValueError("opponent_lineup contains duplicate player_id values")
        if set(ids) & set(opponent_ids):
            raise ValueError("A player cannot appear on both teams")
        return self


class PlayerProjection(BaseModel):
    player_id: str
    name: str
    position: str
    team: str | None = None
    slot: str
    mean: float
    floor: float
    ceiling: float
    volatility: float


class LineupResult(BaseModel):
    starters: list[PlayerProjection]
    expected_points: float
    win_probability: float


class RecommendationResponse(BaseModel):
    recommended: LineupResult
    alternatives: list[LineupResult]
    opponent_expected_points: float
    simulations: int
    seed: int
