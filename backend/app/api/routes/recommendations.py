from fastapi import APIRouter, HTTPException

from app.data.sample_data import SAMPLE_REQUEST
from app.schemas.lineup import RecommendationRequest, RecommendationResponse
from app.services.recommendation import build_recommendation

router = APIRouter(tags=["recommendations"])


@router.get("/sample-roster")
def sample_roster() -> dict:
    return SAMPLE_REQUEST


@router.post("/recommend-lineup", response_model=RecommendationResponse)
def recommend_lineup(payload: RecommendationRequest) -> RecommendationResponse:
    try:
        return build_recommendation(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
