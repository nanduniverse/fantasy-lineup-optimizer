import { useCallback, useEffect, useRef, useState } from "react";
import { loadNflPlayers, recommendNflLineup } from "../lib/api";
import type { NflCatalog, NflPlayer, NflRecommendationResponse, Position, RosterRules, ScoringFormat, LeagueImport } from "../types";
import { LeagueImporter } from "./LeagueImporter";
import { LineupCard } from "./LineupCard";

const FORMATS: Record<ScoringFormat, string> = { standard: "No PPR", half_ppr: "Half PPR", ppr: "Full PPR" };
const DEFAULT_RULES: RosterRules = { qb: 1, rb: 2, wr: 2, te: 1, flex: 1, k: 1, dst: 1 };
const MAX_RULES: RosterRules = { qb: 2, rb: 4, wr: 4, te: 2, flex: 3, k: 2, dst: 2 };
const normalize = (value: string) => value.toLowerCase().replace(/[^a-z0-9]/g, "");

function Avatar({ entry }: { entry: NflPlayer }) {
  const [failedUrl, setFailedUrl] = useState<string | null>(null);
  const url = entry.image_url;
  const initials = entry.player.name.split(/\s+/).map(part => part[0]).slice(0, 2).join("");
  return <span className={`avatar player-photo ${entry.player.position === "DST" ? "team-logo" : ""}`} aria-hidden="true">
    {url && failedUrl !== url ? <img src={url} alt="" loading="lazy" decoding="async" onError={() => setFailedUrl(url)} />
      : <span className="avatar-fallback">{entry.player.position === "DST" ? entry.team : initials}</span>}
  </span>;
}

function RookieInfo({ entry }: { entry: NflPlayer }) {
  if (["K", "DST"].includes(entry.player.position)) return !entry.is_rookie && entry.has_projection ? null : <div className="rookie-info">
    {entry.is_rookie && <span className="rookie-badge">ROOKIE{entry.draft_pick ? ` · PICK ${entry.draft_pick}` : " · UNDRAFTED / PICK UNKNOWN"}</span>}
    {!entry.has_projection && <span className="no-forecast">ESPN forecast unavailable</span>}
  </div>;
  if (!entry.is_rookie) return null;
  return <div className="rookie-info"><span className="rookie-badge">ROOKIE{entry.draft_pick ? ` · PICK ${entry.draft_pick}` : " · UNDRAFTED / PICK UNKNOWN"}</span>
    {entry.projection_method === "espn_draft" ? <details className="rookie-details"><summary>ESPN + draft projection</summary><p>ESPN: {entry.espn_projected_points?.toFixed(1)} pts · Draft adjustment: {entry.draft_adjustment >= 0 ? "+" : ""}{entry.draft_adjustment.toFixed(1)} pts.</p>{entry.projection_notes.map(note => <p key={note}>{note}</p>)}</details>
      : entry.has_projection ? <small>Using recorded NFL games</small> : <span className="no-forecast">ESPN forecast unavailable</span>}
  </div>;
}

const STATUS_LABELS: Record<string, string> = {
  free_agent: "Unsigned free agent", practice_squad: "Practice squad", out: "Out", suspended: "Suspended", ir: "Injured reserve", exempt: "Exempt list",
  inactive: "Inactive", bye: "Bye week", questionable: "Questionable", doubtful: "Doubtful", unknown: "Status unverified",
};
function AvailabilityInfo({ entry }: { entry: NflPlayer }) {
  const gain = entry.eligible && entry.projected_points !== null ? entry.projected_points - (entry.baseline_projected_points ?? entry.projected_points) : 0;
  return <>
    {entry.availability !== "available" && <em className={`availability ${entry.eligible ? "uncertain" : "unavailable"}`}>{STATUS_LABELS[entry.availability] ?? entry.availability}</em>}
    {entry.workload_notes.length > 0 && <details className="workload-details"><summary>{gain > 0.05 ? `↑ +${gain.toFixed(1)} projected points` : "Weekly availability notes"}</summary>
      {gain > 0.05 && <p>Baseline {(entry.baseline_projected_points ?? 0).toFixed(1)} → {entry.projected_points?.toFixed(1) ?? "—"} points. Estimated opportunities: {entry.projected_carries.toFixed(1)} carries, {entry.projected_targets.toFixed(1)} targets{entry.player.position === "QB" ? `, ${entry.projected_passing_attempts.toFixed(1)} pass attempts` : ""}.</p>}
      {entry.workload_notes.map(note => <p key={note}>{note}</p>)}
    </details>}
  </>;
}

function TeamPanel({ title, subtitle, side, entries, otherIds, catalog, loading, max, onAdd, onRemove }: {
  title: string; subtitle: string; side: "you" | "opponent"; entries: NflPlayer[];
  otherIds: string[]; catalog: NflCatalog | null; loading: boolean; max: number;
  onAdd: (id: string) => void; onRemove: (id: string) => void;
}) {
  const [search, setSearch] = useState("");
  const [rookiesOnly, setRookiesOnly] = useState(false);
  const [position, setPosition] = useState<Position | "">("");
  const [showPicker, setShowPicker] = useState(true);
  const [limit, setLimit] = useState(6);
  const selected = new Set([...entries.map(e => e.player.player_id), ...otherIds]);
  const candidates = catalog?.players.filter(e => !selected.has(e.player.player_id)
    && (!rookiesOnly || e.is_rookie)
    && (!position || position === e.player.position)
    && normalize(`${e.player.name} ${e.team}`).includes(normalize(search))) ?? [];
  const stackTeams = [...new Set(entries.filter(e => e.eligible && e.player.position === "QB" && entries.some(r =>
    r.eligible &&
    r.team === e.team && ["WR", "TE"].includes(r.player.position))).map(e => e.team))];
  return <section className={`team-panel ${side}`} aria-label={title}>
    <header className="team-heading"><div className="team-icon">{side === "you" ? "01" : "02"}</div><div><h2>{title}</h2><p>{subtitle}</p></div><span className="count">{entries.length}<small> / {max}</small></span></header>
    {stackTeams.length > 0 && <div className="stack-note">⌁ {stackTeams.join(" + ")} stack available <span>Shared passing upside</span></div>}
    <div className="roster-list">
      {entries.map(entry => <article className="roster-player" key={entry.player.player_id}>
        <Avatar entry={entry} /><div className="player-name"><strong>{entry.player.name}</strong><span>{entry.player.position} <b>·</b> {entry.team}{entry.depth_rank ? ` · Depth ${entry.depth_rank}` : ""}</span><RookieInfo entry={entry} /><AvailabilityInfo entry={entry} /></div>
        <div className="projection">{entry.projected_points?.toFixed(1) ?? "—"}<small>proj. pts</small></div>
        <button className="remove" disabled={loading} onClick={() => onRemove(entry.player.player_id)} aria-label={`Remove ${entry.player.name} from ${title}`}>×</button>
      </article>)}
      {!entries.length && <div className="empty-roster"><span>{side === "you" ? "＋" : "⚑"}</span><h3>{side === "you" ? "Add your roster" : "Add opponent starters"}</h3><p>{side === "you" ? "Select starters and bench players from the list below." : "Add the players your opponent plans to start."}</p></div>}
    </div>
    <button className="picker-toggle" onClick={() => setShowPicker(!showPicker)} aria-expanded={showPicker}>{showPicker ? "− Close player search" : "+ Add players"}</button>
    {showPicker && <div className="player-picker">
      <label className="search-box"><span aria-hidden="true">⌕</span><input aria-label={`Search ${title}`} placeholder="Search a player or NFL team…" value={search} onChange={e => { setSearch(e.target.value); setLimit(6); }} /></label>
      <div className="position-tabs" role="group" aria-label={`Filter ${title} by position`}>
        {(["", "QB", "RB", "WR", "TE", "K", "DST"] as const).map(pos => <button key={pos} aria-pressed={position === pos} onClick={() => { setPosition(pos); setLimit(6); }}>{pos === "DST" ? "D/ST" : pos || "All players"}</button>)}
      </div>
      <label className="rookie-filter"><input type="checkbox" checked={rookiesOnly} onChange={event => { setRookiesOnly(event.target.checked); setLimit(6); }} /> Rookies only</label>
      {loading && !catalog && <div className="loading-state" role="status">Loading NFL players…</div>}
      {!loading && catalog && candidates.length === 0 && <p className="muted">No available players match this search.</p>}
      <div className="candidate-list">{candidates.slice(0, limit).map(entry => <article className="candidate" key={entry.player.player_id}>
        <Avatar entry={entry} /><div className="player-name"><strong>{entry.player.name}</strong><span>{entry.player.position} <b>·</b> {entry.team}{entry.depth_rank ? ` · Depth ${entry.depth_rank}` : ""}</span><RookieInfo entry={entry} /><AvailabilityInfo entry={entry} /></div><div className="projection">{entry.projected_points?.toFixed(1) ?? "—"}<small>proj. pts</small></div>
        <button className="add-player" aria-label={`Add ${entry.player.name} to ${title}`} disabled={loading || entries.length >= max || (side === "opponent" && !entry.eligible)} onClick={() => onAdd(entry.player.player_id)}>+</button>
      </article>)}</div>
      {candidates.length > limit && <button className="show-more" onClick={() => setLimit(n => n + 12)}>Show more players ↓</button>}
    </div>}
  </section>;
}

export function NflBuilder() {
  const [scoring, setScoring] = useState<ScoringFormat>("half_ppr");
  const [week, setWeek] = useState(1);
  const [catalog, setCatalog] = useState<NflCatalog | null>(null);
  const [yourIds, setYourIds] = useState<string[]>([]);
  const [opponentIds, setOpponentIds] = useState<string[]>([]);
  const [rules, setRules] = useState<RosterRules>(DEFAULT_RULES);
  const [loading, setLoading] = useState(true);
  const [optimizing, setOptimizing] = useState(false);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const [result, setResult] = useState<NflRecommendationResponse | null>(null);
  const resultsRef = useRef<HTMLDivElement>(null);
  const starterCount = Object.values(rules).reduce((sum, value) => sum + value, 0);
  const busy = loading || optimizing || importing;
  const applyImport = useCallback((data: LeagueImport) => {
    setYourIds(data.your_player_ids); setOpponentIds(data.opponent_player_ids);
    setRules(data.rules); setScoring(data.scoring_format); setResult(null); setRetry(n => n + 1);
  }, []);
  const importPending = useCallback((pending: boolean) => {
    setImporting(pending);
    if (pending) { setOpponentIds([]); setResult(null); }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(""); setResult(null); setCatalog(null);
    loadNflPlayers({ season: 2026, target_week: week, scoring_format: scoring }, controller.signal).then(data => {
      if (controller.signal.aborted) return;
      setCatalog(data);
      const ids = new Set(data.players.map(p => p.player.player_id));
      setYourIds(old => old.filter(id => ids.has(id)));
      setOpponentIds(old => old.filter(id => ids.has(id)));
    }).catch(err => { if (!controller.signal.aborted) setError(err instanceof Error ? err.message : "Could not load NFL players"); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [scoring, week, retry]);

  useEffect(() => {
    if (optimizing) return;
    const interval = setInterval(() => setRetry(n => n + 1), 300000);
    return () => clearInterval(interval);
  }, [optimizing]);

  const yours = catalog?.players.filter(e => yourIds.includes(e.player.player_id)) ?? [];
  const opponents = catalog?.players.filter(e => opponentIds.includes(e.player.player_id)) ?? [];
  function legality(entries: NflPlayer[], exact: boolean): string | null {
    if (exact && entries.length !== starterCount) return `Add exactly ${starterCount} opponent starters.`;
    if (!exact && entries.length < starterCount) return `Add at least ${starterCount} available players to your roster.`;
    for (const pos of ["QB", "RB", "WR", "TE", "K", "DST"] as const) {
      if (entries.filter(e => e.player.position === pos).length < rules[pos.toLowerCase() as keyof RosterRules])
        return `${exact ? "Opponent needs" : "Your roster needs"} more ${pos} players.`;
    }
    for (const pos of ["QB", "K", "DST"] as const) {
      if (exact && entries.filter(e => e.player.position === pos).length !== rules[pos.toLowerCase() as keyof RosterRules]) return `Check the opponent’s ${pos} slots.`;
    }
    if (entries.filter(e => ["RB", "WR", "TE"].includes(e.player.position)).length < rules.rb + rules.wr + rules.te + rules.flex) return "Add more RB, WR, or TE players to fill FLEX.";
    return null;
  }
  const issue = catalog && !catalog.weekly?.verified ? "Weekly availability isn’t verified for this week. Refresh reports or choose the current NFL week."
    : opponents.some(p => !p.eligible) ? "Replace the unavailable opponent starters before optimizing."
    : starterCount === 0 ? "Choose at least one starter slot." : legality(yours.filter(p => p.eligible), false) ?? legality(opponents, true);

  async function optimize() {
    setOptimizing(true); setError(""); setResult(null);
    try {
      const next = await recommendNflLineup({ season: 2026, target_week: week, scoring_format: scoring,
        your_player_ids: yourIds, opponent_player_ids: opponentIds, rules, simulations: 10000, seed: 42 });
      setResult(next);
      requestAnimationFrame(() => resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
    } catch (err) { setError(err instanceof Error ? err.message : "Could not optimize your lineup"); }
    finally { setOptimizing(false); }
  }

  return <>
    <LeagueImporter week={week} disabled={optimizing} onApply={applyImport} onPending={importPending} />
    <div className="matchup-controls"><div className="week-control"><span className="control-label">YOUR MATCHUP</span><div><button aria-label="Previous week" disabled={busy || week === 1} onClick={() => setWeek(w => w - 1)}>‹</button><strong>Week {week}</strong><button aria-label="Next week" disabled={busy || week === 18} onClick={() => setWeek(w => w + 1)}>›</button></div></div>
      <div className="scoring-control"><span className="control-label">SCORING FORMAT</span><div className="segmented" role="group" aria-label="Scoring format">{Object.entries(FORMATS).map(([value, title]) => <button key={value} disabled={optimizing} aria-pressed={scoring === value} onClick={() => { setResult(null); setScoring(value as ScoringFormat); }}>{title}</button>)}</div></div>
      <div className="model-tag"><span>⌁</span><div><strong>QB + receiver stacks</strong><small>Included in matchup simulations</small></div></div>
    </div>
    <details className="lineup-settings"><summary>Lineup settings <span>{Object.entries(rules).filter(([, count]) => count).map(([slot, count]) => `${count} ${slot.toUpperCase()}`).join(" · ")}</span></summary><div className="slot-settings">{(Object.keys(rules) as (keyof RosterRules)[]).map(slot => <label key={slot}>{slot.toUpperCase()}<input aria-label={`${slot.toUpperCase()} slots`} type="number" min={0} max={MAX_RULES[slot]} value={rules[slot]} disabled={busy} onChange={e => { setRules({ ...rules, [slot]: Math.max(0, Math.min(MAX_RULES[slot], Math.trunc(Number(e.target.value)))) }); setResult(null); }} /></label>)}</div></details>
    {error && <div className="error" role="alert">{error} {!catalog && <button onClick={() => setRetry(n => n + 1)}>Try again</button>}</div>}
    <div className="weekly-toolbar" aria-live="polite">
      <span>{catalog?.weekly?.verified ? `Weekly reports checked ${new Date(catalog.weekly.fetched_at).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })} · refreshes every 5 minutes` : loading ? "Checking availability and depth charts…" : "Weekly availability not verified"}</span>
      <button disabled={busy} onClick={() => setRetry(n => n + 1)}>Refresh reports ↻</button>
    </div>
    {catalog?.weekly && !catalog.weekly.verified && <div className="coverage-warning" role="status">{catalog.weekly.warnings.join(" ")}
      {catalog.weekly.current_week && catalog.weekly.current_week !== week && <button disabled={busy} onClick={() => setWeek(catalog.weekly!.current_week!)}>Go to week {catalog.weekly.current_week}</button>}
    </div>}
    {catalog?.weekly?.verified && catalog.weekly.warnings.length > 0 && <div className="coverage-warning"><strong>Partial depth-chart coverage.</strong> {catalog.weekly.warnings.join(" ")}</div>}
    <div className="matchup-grid">
      <TeamPanel title="Your team" subtitle="Starters + bench" side="you" entries={yours} otherIds={opponentIds} catalog={catalog} loading={busy} max={30}
        onAdd={id => { setYourIds(old => [...old, id]); setResult(null); }} onRemove={id => { setYourIds(old => old.filter(p => p !== id)); setResult(null); }} />
      <TeamPanel title="The opponent" subtitle="Starting lineup only" side="opponent" entries={opponents} otherIds={yourIds} catalog={catalog} loading={busy} max={starterCount}
        onAdd={id => { setOpponentIds(old => [...old, id]); setResult(null); }} onRemove={id => { setOpponentIds(old => old.filter(p => p !== id)); setResult(null); }} />
    </div>
    <div className="optimize-bar"><div><strong>Starting lineup</strong><p>{issue ?? "Both rosters are ready to simulate."}</p></div><button className="primary" disabled={busy || !catalog || !!issue} onClick={optimize}>{optimizing ? "Optimizing…" : "Optimize lineup"}<span>→</span></button></div>
    <p className="baseline-note">Offensive veterans use recorded performance. Rookies without history use ESPN with a limited draft adjustment. Kickers and D/ST use ESPN weekly forecasts.</p>
    {result && <div className="results" ref={resultsRef} aria-live="polite"><div className="result-intro"><p className="eyebrow">MATCHUP RESULTS</p><h2>Recommended starters</h2><p>Week {week} · {FORMATS[scoring]} · Opponent projected {result.opponent_expected_points.toFixed(1)} points</p></div><LineupCard lineup={result.recommended} title="Your best starting lineup" />
      {result.recommended.starters.some(p => p.position === "QB" && p.team && result.recommended.starters.some(r => r.team === p.team && ["WR", "TE"].includes(r.position))) && <p className="stack-explanation">⌁ This lineup includes a QB–receiver stack. Their shared passing outcomes are included in the estimated win probability, with no artificial points bonus.</p>}
      <details className="model-details"><summary>Weekly adjustments used in this result</summary>{result.player_adjustments.filter(p => p.workload_notes.length > 0 || p.is_rookie).map(p => <div key={p.player.player_id}><strong>{p.player.name}</strong><RookieInfo entry={p} /><AvailabilityInfo entry={p} /></div>)}{result.weekly?.warnings.map(w => <p key={w}>{w}</p>)}</details>
      <details className="alternatives"><summary>Compare other lineups</summary>{result.alternatives.map((lineup, i) => <LineupCard key={i} lineup={lineup} title={`Alternative ${i + 1}`} />)}</details>
    </div>}
    <details className="model-details"><summary>How projections and stacks work</summary><p>Receptions score 0 / 0.5 / 1 point. Passing: 1 point per 25 yards and 4 per TD. Rushing/receiving: 1 per 10 yards and 6 per TD. Interceptions and offensive lost fumbles: −2. Two-point conversions: +2.</p><p>Kickers: field goals under 40 yards +3, 40–49 +4, 50+ +5; extra points +1; missed field goals or extra points −1. D/ST: sacks +1; interceptions, fumble recoveries, safeties and blocked kicks +2; defensive/special-teams TDs +6. Points allowed: 0 → +10, 1–6 → +7, 7–13 → +4, 14–21 → +1, 22–27 → 0, 28–34 → −1, 35+ → −4. No yards-allowed scoring. K/D/ST scoring is the same in all PPR formats.</p>{catalog?.warnings.map(w => <p key={w}>{w}</p>)}<p>Same-team QB and WR/TE outcomes share an assumed 0.30 correlation. Stacking can help an underdog’s upside or increase a favorite’s risk. These estimates need historical calibration; a stack is not a guaranteed advantage.</p></details>
  </>;
}
