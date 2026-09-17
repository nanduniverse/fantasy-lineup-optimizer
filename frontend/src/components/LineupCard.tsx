import type { LineupResult } from "../types";

type Props = {
  lineup: LineupResult;
  title: string;
};

export function LineupCard({ lineup, title }: Props) {
  return (
    <section className="card">
      <div className="cardHeader">
        <div>
          <p className="eyebrow">{title}</p>
          <h2>{(lineup.win_probability * 100).toFixed(1)}% modeled win chance</h2>
        </div>
        <div className="expected">{lineup.expected_points.toFixed(1)} exp. pts</div>
      </div>

      <div className="players">
        {lineup.starters.map((player) => (
          <article className="player" key={player.player_id}>
            <div>
              <span className="position">{player.slot}</span>
              <strong>{player.name}</strong>
            </div>
            <div className="metrics">
              <span>μ {player.mean.toFixed(1)}</span>
              <span>Low {player.floor.toFixed(1)}</span>
              <span>High {player.ceiling.toFixed(1)}</span>
              <span>σ {player.volatility.toFixed(1)}</span>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
