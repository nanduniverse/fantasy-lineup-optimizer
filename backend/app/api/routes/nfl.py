from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.services.recommendation import build_recommendation
from app.providers.nflverse import ProviderError, SeasonUnavailable, provider
from app.schemas.lineup import RecommendationRequest
from app.schemas.nfl import NflCatalog, NflContext, NflRecommendationRequest, NflRecommendationResponse
from app.services.nfl import build_catalog
from app.providers.weekly import weekly_provider
from app.services.workload import apply_weekly
from app.providers.espn_projections import projection_provider
from app.providers.kickers import kicker_provider

router = APIRouter(prefix="/nfl", tags=["NFL data"])


def catalog_for(context: NflContext) -> NflCatalog:
    try:
        return build_catalog(provider.season(context.season), context)
    except SeasonUnavailable as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/players", response_model=NflCatalog)
def players(context: Annotated[NflContext, Query()]) -> NflCatalog:
    return catalog_for(context)


@router.post("/recommend-lineup", response_model=NflRecommendationResponse)
def recommend_nfl_lineup(payload: NflRecommendationRequest) -> NflRecommendationResponse:
    context = NflContext(**payload.model_dump(include={"season", "target_week", "scoring_format"}))
    catalog = catalog_for(context)
    lookup = {entry.player.player_id: entry.player for entry in catalog.players}
    missing = set(payload.your_player_ids + payload.opponent_player_ids) - lookup.keys()
    if missing:
        raise HTTPException(status_code=400, detail="Selected players have no offensive history before "
                            f"the target week: {', '.join(sorted(missing))}")
    try:
        result = build_recommendation(RecommendationRequest(
            your_roster=[lookup[pid] for pid in payload.your_player_ids],
            opponent_lineup=[lookup[pid] for pid in payload.opponent_player_ids],
            rules=payload.rules, simulations=payload.simulations, seed=payload.seed,
        ))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return NflRecommendationResponse(**result.model_dump(), **context.model_dump(),
                                     source=catalog.source, source_url=catalog.source_url,
                                     fetched_at=catalog.fetched_at, warnings=catalog.warnings)


# The product UI is intentionally fixed to the upcoming 2026 NFL season.
from app.providers.rosters import roster_provider, with_defenses
from app.services.current_season import SEASON, current_catalog


def current_catalog_for(context: NflContext) -> NflCatalog:
    if context.season != SEASON:
        raise HTTPException(status_code=422, detail="The current matchup builder supports the 2026 season")
    try:
        roster, kicker_warnings = kicker_provider.augment(with_defenses(roster_provider.roster(SEASON)), SEASON)
        histories = [provider.season(SEASON - 1), provider.season(SEASON - 2)]
        if context.target_week > 1:
            try:
                histories.append(provider.season(SEASON))
            except SeasonUnavailable:
                pass  # Explicit preseason prior; never fabricated current-season records.
        rookie_ids = [p.espn_id for p in roster.players if (p.is_rookie or p.position in {"K", "DST"}) and p.espn_id]
        forecasts = projection_provider.snapshot(SEASON, context.target_week, rookie_ids)
        baseline = current_catalog(roster, histories, context, forecasts)
        baseline.warnings.extend(kicker_warnings)
        return apply_weekly(baseline, roster, histories, weekly_provider.snapshot(SEASON, context.target_week))
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/current/players", response_model=NflCatalog)
def current_players(context: Annotated[NflContext, Query()]) -> NflCatalog:
    return current_catalog_for(context)


@router.post("/current/recommend-lineup", response_model=NflRecommendationResponse)
def current_recommendation(payload: NflRecommendationRequest) -> NflRecommendationResponse:
    context = NflContext(**payload.model_dump(include={"season", "target_week", "scoring_format"}))
    catalog = current_catalog_for(context)
    if not catalog.weekly or not catalog.weekly.verified:
        raise HTTPException(status_code=503, detail="Weekly availability is not verified for this week. Reload or choose the current NFL week.")
    eligible = {e.player.player_id for e in catalog.players if e.eligible}
    if set(payload.opponent_player_ids) - eligible:
        raise HTTPException(status_code=400, detail="An opponent starter is unavailable or on bye. Update their starting lineup.")
    lookup = {entry.player.player_id: entry.player for entry in catalog.players}
    if set(payload.your_player_ids + payload.opponent_player_ids) - lookup.keys():
        raise HTTPException(status_code=400, detail="A selected player is no longer available in the current player catalog. Reload players.")
    try:
        result = build_recommendation(RecommendationRequest(
            your_roster=[lookup[pid] for pid in payload.your_player_ids if pid in eligible],
            opponent_lineup=[lookup[pid] for pid in payload.opponent_player_ids],
            rules=payload.rules, simulations=payload.simulations, seed=payload.seed,
        ))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return NflRecommendationResponse(**result.model_dump(), **context.model_dump(), source=catalog.source,
                                    source_url=catalog.source_url, fetched_at=catalog.fetched_at, warnings=catalog.warnings,
                                    weekly=catalog.weekly, player_adjustments=[e for e in catalog.players if e.player.player_id in payload.your_player_ids + payload.opponent_player_ids])
