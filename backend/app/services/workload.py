"""Conservative, auditable opportunity transfer for confirmed weekly absences.

No change to the existing season-selection policy or 65/35 baseline formula.
Injury probability is not inferred from 'questionable'. Unmodeled depth players
retain a share of the pool rather than gifting it to the modeled veterans.
"""
from collections import defaultdict
from dataclasses import replace
from statistics import mean

from app.providers.nflverse import SeasonData
from app.providers.rosters import CurrentRoster
from app.providers.weekly import BLOCKED, WeeklySnapshot, team_code
from app.schemas.nfl import NflCatalog, WeeklyCoverage
from app.services.projection import build_distribution

OPPORTUNITIES = ('carries', 'targets', 'passing_attempts')
CAPS = {'carries': 35, 'targets': 20, 'passing_attempts': 50}


def weighted(values: list[float]) -> float:
    return .65 * mean(values[-4:]) + .35 * mean(values) if values else 0.0


def apply_weekly(catalog: NflCatalog, roster: CurrentRoster, histories: list[SeasonData],
                 snapshot: WeeklySnapshot) -> NflCatalog:
    if (snapshot.season, snapshot.week) != (catalog.season, catalog.target_week):
        snapshot = replace(snapshot, verified=False, saved=False, reports={}, depths={}, playing_teams=frozenset(), warnings=snapshot.warnings + ('Weekly report does not match this matchup.',))
    # Work on a response copy; cached sources and the baseline catalog stay immutable.
    result = catalog.model_copy(deep=True)
    result.weekly = WeeklyCoverage(verified=snapshot.verified, current_week=snapshot.current_week,
                                  fetched_at=snapshot.fetched_at, source_urls=list(snapshot.source_urls),
                                  warnings=list(snapshot.warnings))
    result.warnings.extend(snapshot.warnings)
    identities = {v.player_id: v for v in roster.players}
    entries = {e.player.player_id: e for e in result.players}
    espn_entries = {identities[pid].espn_id: entry for pid, entry in entries.items() if identities[pid].espn_id}
    games = defaultdict(list)
    team_latest = defaultdict(int)
    for history in histories:
        for game in history.games:
            if game.season > result.season or (game.season == result.season and game.week >= result.target_week):
                continue
            if game.season == result.season:
                team_latest[team_code(game.team)] = max(team_latest[team_code(game.team)], game.week)
            if game.player_id in entries and game.season == entries[game.player_id].history_season:
                games[game.player_id].append(game)
    for records in games.values():
        records.sort(key=lambda g: g.week)
    baseline = {}
    for pid, entry in entries.items():
        veteran = identities[pid]
        entry.baseline_projected_points = entry.projected_points
        baseline[pid] = {key: getattr(entry, 'projected_' + key) if entry.projection_method == 'espn_draft'
                         else weighted([float(getattr(g.stats, key)) for g in games[pid]]) for key in OPPORTUNITIES}
        for key in OPPORTUNITIES:
            setattr(entry, 'projected_' + key, round(baseline[pid][key], 2))
        depth = next((d for d in snapshot.depths.get(team_code(entry.team), ()) if d.espn_id == veteran.espn_id), None)
        report = snapshot.reports.get(veteran.espn_id)
        if snapshot.verified or snapshot.saved:
            if entry.team == 'FA' or veteran.roster_status in {'CUT', 'FA'}:
                entry.availability = 'free_agent'
            elif veteran.roster_status == 'DEV':
                entry.availability = 'practice_squad'
            elif team_code(entry.team) not in snapshot.playing_teams:
                entry.availability = 'bye'
            elif veteran.roster_status == 'EXE':
                entry.availability = 'exempt'
            elif report and report.status in BLOCKED:
                entry.availability = report.status
            elif veteran.roster_status in {'RES', 'INA'}:
                entry.availability = 'inactive'
            elif report:
                entry.availability = report.status
            elif depth:
                entry.availability = depth.status
            else:
                entry.availability = 'available' if veteran.espn_id else 'unknown'
            entry.depth_rank = depth.rank if depth else None
            entry.availability_updated_at = report.updated_at if report else snapshot.fetched_at
        else:
            entry.availability = 'unknown'
        entry.eligible = entry.has_projection and entry.availability not in BLOCKED and veteran.roster_status not in {'CUT', 'FA', 'DEV'} and entry.team != 'FA'
        if not entry.eligible:
            entry.projected_points = 0 if entry.has_projection else None
            for key in OPPORTUNITIES:
                setattr(entry, 'projected_' + key, 0)
            entry.workload_notes.append(f'{entry.availability.title()}: excluded from this week’s recommended starters.' if entry.has_projection else 'No weekly projection available: cannot be recommended yet.')
        if entry.availability in {'questionable', 'doubtful'}:
            entry.workload_notes.append('Uncertain availability: no assumed absence or automatic workload transfer. Check the final game status.')
    if not snapshot.verified:
        result.warnings.append('Weekly availability is not verified. Recommendations are paused; no workload adjustment is applied.')
        return result

    groups = defaultdict(list)
    for entry in result.players:
        groups[(team_code(entry.team), entry.player.position)].append(entry)
    for (team, position), group in groups.items():
        if team not in snapshot.depths or team not in snapshot.playing_teams:
            continue
        donors = [e for e in group if e.has_projection and e.projection_method == 'history' and e.availability in BLOCKED and e.availability != 'bye']
        if not donors:
            continue
        depth_pool = [d for d in snapshot.depths[team] if d.position == position]
        recipients = []
        for depth in depth_pool:
            modeled = espn_entries.get(depth.espn_id)
            # A changed-team or changed-position identity is not a valid recipient.
            if modeled and (team_code(modeled.team), modeled.player.position) != (team, position):
                continue
            report = snapshot.reports.get(depth.espn_id)
            status = modeled.availability if modeled else (report.status if report else depth.status)
            if status not in BLOCKED:
                recipients.append(depth)  # Uncertain players retain a share; it is not gifted to healthy teammates.
        if not recipients:
            continue
        total_weight = sum(1 / d.rank**2 for d in recipients)
        for donor in donors:
            # Once the latest game already reflects this absence, do not add its
            # volume again on top of replacement production in current-season stats.
            latest = team_latest[team]
            donor_played_latest = any(g.season == result.season and team_code(g.team) == team and g.week == latest
                                     for g in games[donor.player.player_id])
            recipients_use_latest = any(any(g.season == result.season and team_code(g.team) == team and g.week == latest
                                           for g in games[e.player.player_id])
                                       for d in recipients if (e := espn_entries.get(d.espn_id)))
            if latest and not donor_played_latest and recipients_use_latest:
                donor.workload_notes.append('No extra transfer: current-season replacement history already includes the most recent team game without this player.')
                continue
            transferable = ('passing_attempts', 'carries') if position == 'QB' else ('carries', 'targets') if position == 'RB' else ('targets',)
            for depth in recipients:
                entry = espn_entries.get(depth.espn_id)
                if not entry or not entry.has_projection or entry.projection_method != 'history' or entry.availability != 'available':
                    continue  # Unmodeled or uncertain players keep their share unassigned.
                share = (1 / depth.rank**2) / total_weight
                additions = {}
                for key in transferable:
                    existing = baseline[entry.player.player_id][key] + getattr(entry, 'added_' + key)
                    addition = min(baseline[donor.player.player_id][key] * share, max(0, CAPS[key] - existing))
                    setattr(entry, 'added_' + key, getattr(entry, 'added_' + key) + addition)
                    additions[key] = addition
                if sum(additions.values()) > 0:
                    detail = ', '.join(f'+{value:.1f} {key.replace("_", " ")}' for key, value in additions.items() if value > 0)
                    entry.workload_notes.append(f'{donor.player.name} {donor.availability}: {detail}, allocated by available {position} depth order.')

    for entry in result.players:
        if not entry.eligible or entry.projection_method != 'history':
            continue
        stats = [g.stats for g in games[entry.player.player_id]]
        # Small-sample efficiency is shrunk with explicit opportunity priors. These
        # are heuristic rates, not imported projections or a blend of prior seasons.
        carries = sum(s.carries for s in stats)
        targets = sum(s.targets for s in stats)
        attempts = sum(s.passing_attempts for s in stats)
        catch_points = result.scoring_format.reception_points
        rush_rate = (sum(s.rushing_yards / 10 + 6 * s.rushing_tds for s in stats) + 40 * .57) / (carries + 40)
        target_rate = (sum(s.receiving_yards / 10 + 6 * s.receiving_tds + catch_points * s.receptions for s in stats)
                       + 30 * (1.02 + .65 * catch_points)) / (targets + 30)
        pass_rate = (sum(s.passing_yards / 25 + 4 * s.passing_tds - 2 * s.interceptions for s in stats)
                     + 100 * .4) / (attempts + 100)
        delta = max(0, entry.added_carries * rush_rate + entry.added_targets * target_rate + entry.added_passing_attempts * pass_rate)
        entry.player = entry.player.model_copy(update={'workload_points_adjustment': round(min(60, delta), 4), 'workload_std_dev': round(min(60, delta) * .35, 4)})
        entry.projected_points = round(build_distribution(entry.player).mean, 2)
        for key in OPPORTUNITIES:
            added = getattr(entry, 'added_' + key)
            setattr(entry, 'projected_' + key, round(baseline[entry.player.player_id][key] + added, 2))
            setattr(entry, 'added_' + key, round(added, 2))
    result.players.sort(key=lambda e: (not e.eligible, -(e.projected_points or 0), e.player.name))
    result.warnings.append('Workload transfers use confirmed absences and inverse-square depth weights within a position. Questionable/doubtful players do not trigger transfers. ESPN-forecast, unmodeled and uncertain-player shares receive no extra transfer, and are not reassigned. Efficiency and opportunity caps are heuristic.')
    return result
