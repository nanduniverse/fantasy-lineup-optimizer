from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.lineup import RecommendationResponse, RosterRulesInput
from app.schemas.player import PlayerInput
from app.schemas.scoring import ScoringFormat


PlayerId = Annotated[str, Field(min_length=1, max_length=100)]


class NflContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    season: int = Field(ge=1999, le=datetime.now().year)
    target_week: int = Field(ge=1, le=18)
    scoring_format: ScoringFormat = ScoringFormat.HALF_PPR


class NflRecommendationRequest(NflContext):
    your_player_ids: list[PlayerId] = Field(min_length=1, max_length=30)
    opponent_player_ids: list[PlayerId] = Field(min_length=1, max_length=16)
    rules: RosterRulesInput = Field(default_factory=RosterRulesInput)
    simulations: int = Field(default=5000, ge=500, le=50000)
    seed: int = Field(default=42, ge=0, le=2**32 - 1)

    @model_validator(mode="after")
    def unique_ids(self):
        ids = self.your_player_ids + self.opponent_player_ids
        if len(ids) != len(set(ids)):
            raise ValueError("Each player may be selected only once across both teams")
        return self


class WeeklyCoverage(BaseModel):
    verified: bool
    current_week: int | None = None
    fetched_at: datetime
    source_urls: list[str]
    warnings: list[str]


class NflPlayer(BaseModel):
    image_url: str | None = None
    espn_id: str | None = None
    is_rookie: bool = False
    draft_pick: int | None = None
    has_projection: bool = True
    projection_method: str = "history"
    espn_projected_points: float | None = None
    draft_prior_points: float | None = None
    draft_adjustment: float = 0
    projection_source_url: str | None = None
    projection_fetched_at: datetime | None = None
    projection_notes: list[str] = Field(default_factory=list)

    availability: str = "unknown"
    eligible: bool = True
    availability_updated_at: datetime | None = None
    depth_rank: int | None = None
    baseline_projected_points: float | None = None
    projected_carries: float = 0
    projected_targets: float = 0
    projected_passing_attempts: float = 0
    added_carries: float = 0
    added_targets: float = 0
    added_passing_attempts: float = 0
    workload_notes: list[str] = Field(default_factory=list)

    player: PlayerInput
    team: str
    projected_points: float | None = None
    history_season: int | None = None
    games_played: int
    last_played_week: int | None


class NflCatalog(NflContext):
    weekly: WeeklyCoverage | None = None
    source: str
    source_url: str
    fetched_at: datetime
    available_through_week: int | None
    players: list[NflPlayer]
    warnings: list[str]


class NflRecommendationResponse(RecommendationResponse):
    weekly: WeeklyCoverage | None = None
    player_adjustments: list[NflPlayer] = Field(default_factory=list)
    season: int
    target_week: int
    scoring_format: ScoringFormat
    source: str
    source_url: str
    fetched_at: datetime
    warnings: list[str]
