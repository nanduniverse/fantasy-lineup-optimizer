import { useEffect, useRef, useState } from 'react';
import { importEspnLeague } from '../lib/api';
import type { LeagueImport, LeagueRequest } from '../types';

function leagueId(value: string): string {
  if (/^\d{1,20}$/.test(value.trim())) return value.trim();
  try {
    const url = new URL(value.trim());
    if (url.hostname !== 'fantasy.espn.com') throw new Error();
    const id = url.searchParams.get('leagueId') ?? '';
    if (/^\d{1,20}$/.test(id)) return id;
  } catch { /* Show the same actionable message for malformed links. */ }
  throw new Error('Enter an ESPN league ID or a fantasy.espn.com league link.');
}

export function LeagueImporter({ week, disabled, onApply, onPending }: {
  week: number; disabled: boolean; onApply: (data: LeagueImport) => void; onPending: (pending: boolean) => void;
}) {
  const [input, setInput] = useState('');
  const [s2, setS2] = useState('');
  const [swid, setSwid] = useState('');
  const [connection, setConnection] = useState<Omit<LeagueRequest, 'week' | 'team_id'> | null>(null);
  const [league, setLeague] = useState<LeagueImport | null>(null);
  const [teamId, setTeamId] = useState<number | null>(null);
  const [search, setSearch] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const discovery = useRef<AbortController | null>(null);
  useEffect(() => () => discovery.current?.abort(), []);

  async function connect() {
    setError('');
    let id: string;
    try { id = leagueId(input); } catch (e) { setError((e as Error).message); return; }
    discovery.current?.abort();
    const controller = new AbortController(); discovery.current = controller;
    setLoading(true);
    const credentials = { league_id: id, ...(s2 ? { espn_s2: s2 } : {}), ...(swid ? { swid } : {}) };
    try {
      const data = await importEspnLeague({ ...credentials, week }, controller.signal);
      if (controller.signal.aborted) return;
      setTeamId(null); setConnection(credentials); setLeague(data); setSearch('');
      setS2(''); setSwid('');
    } catch (e) { if (!controller.signal.aborted) setError((e as Error).message); }
    finally { if (!controller.signal.aborted) setLoading(false); }
  }

  useEffect(() => {
    if (!connection || teamId === null) return;
    const controller = new AbortController();
    setLoading(true); setError(''); onPending(true);
    importEspnLeague({ ...connection, week, team_id: teamId }, controller.signal).then(data => {
      if (!controller.signal.aborted) { setLeague(data); onApply(data); }
    }).catch(e => { if (!controller.signal.aborted) setError((e as Error).message); })
      .finally(() => { if (!controller.signal.aborted) { setLoading(false); onPending(false); } });
    return () => { controller.abort(); onPending(false); };
  }, [connection, teamId, week, refresh, onApply, onPending]);

  function disconnect() {
    discovery.current?.abort(); setConnection(null); setTeamId(null); setLeague(null);
    setS2(''); setSwid(''); setError(''); setLoading(false);
  }

  return <details className="league-import"><summary>Import an ESPN league <span>Load your roster and weekly opponent</span></summary>
    {!connection ? <form onSubmit={e => { e.preventDefault(); void connect(); }}>
      <label>League link or ID<input aria-label="ESPN league link or ID" value={input} onChange={e => setInput(e.target.value)} placeholder="Paste your ESPN league link" disabled={loading || disabled} /></label>
      <details className="private-league"><summary>Private league?</summary><p>ESPN private leagues need your ESPN session cookies. In your browser’s developer tools, open Application/Storage → Cookies → ESPN and copy espn_s2 and SWID. These grant account access: only enter them in a deployment you trust. They stay in memory for this connection and are cleared when you disconnect or reload.</p>
        <label>espn_s2<input aria-label="ESPN session cookie" type="password" autoComplete="off" value={s2} onChange={e => setS2(e.target.value)} /></label>
        <label>SWID<input aria-label="ESPN SWID" type="password" autoComplete="off" value={swid} onChange={e => setSwid(e.target.value)} /></label>
      </details>
      <button className="primary" disabled={loading || disabled || !input.trim()}>{loading ? 'Finding league…' : 'Find my league'}</button>
    </form> : <div>
      <div className="league-title"><strong>{league?.name}</strong><button onClick={disconnect} disabled={disabled}>Disconnect</button></div>
      <label>Which team is yours?<input aria-label="Find your league team" value={search} onChange={e => setSearch(e.target.value)} placeholder="Search team names" /></label>
      <div className="league-teams">{league?.teams.filter(t => t.name.toLowerCase().includes(search.toLowerCase())).map(t => <button key={t.id} aria-pressed={teamId === t.id} disabled={loading || disabled} onClick={() => setTeamId(t.id)}>{t.name} <small>#{t.id}</small></button>)}</div>
      {teamId !== null && <button disabled={loading || disabled} onClick={() => setRefresh(n => n + 1)}>Refresh imported matchup</button>}
      {loading && <p role="status">Loading week {week} roster and opponent…</p>}
      {!loading && !error && league?.selected_team && league.week === week && <div className="import-result"><strong>{league.selected_team.name} vs {league.opponent?.name ?? 'No scheduled opponent'} · Week {week}</strong><p>Imported {league.your_player_ids.length} roster players and {league.opponent_player_ids.length} opponent starters. You can still edit both sides below.</p>{league.warnings.map(w => <p key={w}>{w}</p>)}</div>}
    </div>}
    {error && <p className="error" role="alert">{error}</p>}
  </details>;
}
