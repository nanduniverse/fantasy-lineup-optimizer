import math
import numpy as np

from app.models.domain import PlayerDistribution

# Heuristic shared passing-environment loading, not a calibrated causal bonus.
# QB-WR/TE correlation = .60 * .50 = .30; receiver-receiver = .25.
PASSING_LOADINGS = {'QB': 0.60, 'WR': 0.50, 'TE': 0.50}


def sample_player_scores(players: list[PlayerDistribution], simulations: int,
                         rng: np.random.Generator) -> dict[str, np.ndarray]:
    teams = sorted({p.team for p in players if p.team and p.position in PASSING_LOADINGS})
    environment = {team: rng.standard_normal(simulations) for team in teams}
    samples = {}
    for player in sorted(players, key=lambda p: p.player_id):
        loading = PASSING_LOADINGS.get(player.position, 0.0) if player.team else 0.0
        individual = rng.standard_normal(simulations)
        z = math.sqrt(1 - loading**2) * individual
        if loading:
            z += loading * environment[player.team]
        samples[player.player_id] = player.mean + player.std_dev * z
    return samples


def simulate_lineup_scores(lineup: tuple[PlayerDistribution, ...] | list[PlayerDistribution],
                           simulations: int, rng: np.random.Generator) -> np.ndarray:
    samples = sample_player_scores(list(lineup), simulations, rng)
    return sum(samples.values(), np.zeros(simulations))
