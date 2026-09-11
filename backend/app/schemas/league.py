from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
from app.schemas.lineup import RosterRulesInput
from app.schemas.scoring import ScoringFormat


class LeagueRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', hide_input_in_errors=True)
    league_id: str = Field(pattern=r'^\d{1,20}$')
    week: int = Field(ge=1, le=18)
    team_id: int | None = Field(default=None, ge=0)
    espn_s2: SecretStr | None = None
    swid: SecretStr | None = None

    @field_validator('espn_s2', 'swid')
    @classmethod
    def valid_cookie(cls, value):
        if value and (len(value.get_secret_value()) > 8192 or any(ord(c) < 32 or ord(c) > 126 or c == ';' for c in value.get_secret_value())):
            raise ValueError('Invalid authentication value')
        return value


class LeagueTeam(BaseModel):
    id: int
    name: str


class LeagueImport(BaseModel):
    league_id: str
    name: str
    week: int
    teams: list[LeagueTeam]
    selected_team: LeagueTeam | None = None
    opponent: LeagueTeam | None = None
    your_player_ids: list[str] = Field(default_factory=list)
    opponent_player_ids: list[str] = Field(default_factory=list)
    rules: RosterRulesInput
    scoring_format: ScoringFormat
    warnings: list[str] = Field(default_factory=list)
