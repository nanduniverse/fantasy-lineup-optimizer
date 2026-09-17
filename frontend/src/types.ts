export type PlayerProjection = {
  player_id: string;
  name: string;
  position: string;
  slot: string;
  team?: string | null;
  mean: number;
  floor: number;
  ceiling: number;
  volatility: number;
};

export type LineupResult = {
  starters: PlayerProjection[];
  expected_points: number;
  win_probability: number;
};

export type RecommendationResponse = {
  recommended: LineupResult;
  alternatives: LineupResult[];
  opponent_expected_points: number;
  simulations: number;
  seed: number;
};

export type ScoringFormat = "standard" | "half_ppr" | "ppr";
export type Position = "QB" | "RB" | "WR" | "TE" | "K" | "DST";
export type RosterRules = { qb: number; rb: number; wr: number; te: number; flex: number; k: number; dst: number };
export type NflContext = { season: number; target_week: number; scoring_format: ScoringFormat };
export type WeeklyCoverage = {
  verified: boolean;
  current_week: number | null;
  fetched_at: string;
  source_urls: string[];
  warnings: string[];
};
export type NflPlayer = {
  image_url?: string | null;
  is_rookie: boolean;
  draft_pick: number | null;
  has_projection: boolean;
  projection_method: string;
  espn_projected_points: number | null;
  draft_prior_points: number | null;
  draft_adjustment: number;
  projection_source_url: string | null;
  projection_fetched_at: string | null;
  projection_notes: string[];
  availability: string;
  eligible: boolean;
  availability_updated_at: string | null;
  depth_rank: number | null;
  baseline_projected_points: number | null;
  projected_carries: number;
  projected_targets: number;
  projected_passing_attempts: number;
  added_carries: number;
  added_targets: number;
  added_passing_attempts: number;
  workload_notes: string[];
  player: { player_id: string; name: string; position: Position; season_average: number; recent_points: number[] };
  team: string;
  projected_points: number | null;
  history_season: number | null;
  games_played: number;
  last_played_week: number | null;
};
export type NflCatalog = NflContext & {
  weekly: WeeklyCoverage | null;
  source: string;
  source_url: string;
  fetched_at: string;
  available_through_week: number | null;
  players: NflPlayer[];
  warnings: string[];
};
export type NflRecommendationRequest = NflContext & {
  your_player_ids: string[];
  opponent_player_ids: string[];
  rules: RosterRules;
  simulations: number;
  seed: number;
};
export type NflRecommendationResponse = RecommendationResponse & NflContext & {
  weekly: WeeklyCoverage | null;
  player_adjustments: NflPlayer[];
  source: string;
  source_url: string;
  fetched_at: string;
  warnings: string[];
};

export type LeagueTeam = { id: number; name: string };
export type LeagueImport = {
  league_id: string; name: string; week: number; teams: LeagueTeam[];
  selected_team: LeagueTeam | null; opponent: LeagueTeam | null;
  your_player_ids: string[]; opponent_player_ids: string[];
  rules: RosterRules; scoring_format: ScoringFormat; warnings: string[];
};
export type LeagueRequest = { league_id: string; week: number; team_id?: number; espn_s2?: string; swid?: string };

export type NewsFeed = {
  articles: { title: string; url: string; source: string; published_at: string }[];
  fetched_at: string | null;
  stale: boolean;
  warnings: string[];
};
