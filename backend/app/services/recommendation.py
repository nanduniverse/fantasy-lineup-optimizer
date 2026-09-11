from app.core.roster_rules import RosterRules
from app.schemas.lineup import RecommendationRequest, RecommendationResponse
from app.services.lineup_generator import generate_legal_lineups
from app.services.optimizer import optimize_lineup
from app.services.projection import build_distribution


def build_recommendation(payload: RecommendationRequest) -> RecommendationResponse:
    """Shared application service for manual inputs and provider-derived histories."""
    rules = RosterRules(**payload.rules.model_dump())
    roster = [build_distribution(player) for player in payload.your_roster]
    opponent = [build_distribution(player) for player in payload.opponent_lineup]
    if len(opponent) != rules.starter_count:
        raise ValueError(f"opponent_lineup must contain exactly {rules.starter_count} starters")
    generate_legal_lineups(opponent, rules)
    ranked, opponent_expected = optimize_lineup(
        roster=roster, opponent=opponent, rules=rules,
        simulations=payload.simulations, seed=payload.seed,
    )
    return RecommendationResponse(
        recommended=ranked[0], alternatives=ranked[1:4],
        opponent_expected_points=opponent_expected, simulations=payload.simulations, seed=payload.seed,
    )
