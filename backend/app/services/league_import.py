"""Normalize an ESPN league without guessing player identities or weekly opponents."""
from app.schemas.league import LeagueImport, LeagueRequest, LeagueTeam
from app.schemas.lineup import RosterRulesInput
from app.schemas.nfl import NflCatalog

SLOTS = {'0': 'qb', '2': 'rb', '4': 'wr', '6': 'te', '23': 'flex', '17': 'k', '16': 'dst'}
BENCH = {20, 21}


def parse_league(data: dict, request: LeagueRequest, catalog: NflCatalog | None = None) -> LeagueImport:
    try:
        if data.get('seasonId') != 2026 or str(data.get('id')) != request.league_id:
            raise ValueError('ESPN returned a different league or season.')
        if data.get('scoringPeriodId', request.week) != request.week:
            raise ValueError('ESPN returned data for a different scoring week.')
        settings = data['settings']
        counts = settings['rosterSettings']['lineupSlotCounts']
        unsupported = [slot for slot, count in counts.items() if count and slot not in SLOTS and int(slot) not in BENCH]
        if unsupported:
            raise ValueError('This league uses unsupported starter slots (such as superflex or individual defenders). Import cannot preserve its lineup rules yet.')
        rules = RosterRulesInput(**{name: counts.get(slot, 0) for slot, name in SLOTS.items()})
        scoring = {str(item['statId']): item.get('points', 0) for item in settings['scoringSettings']['scoringItems']}
        ppr = scoring.get('53', scoring.get('41', 0))
        if ppr not in (0, .5, 1):
            raise ValueError('Only no-PPR, half-PPR, and full-PPR reception scoring are supported.')
        format = {0: 'standard', .5: 'half_ppr', 1: 'ppr'}[ppr]
        teams = {int(t['id']): t for t in data['teams']}
        if len(teams) != len(data['teams']) or not teams:
            raise ValueError('ESPN returned an empty or ambiguous team list.')
        def team_label(t):
            return LeagueTeam(id=t['id'], name=t.get('name') or ' '.join(filter(None, [t.get('location'), t.get('nickname')])) or f"Team {t['id']}")
        result = LeagueImport(league_id=request.league_id, name=settings.get('name', 'ESPN league'), week=request.week,
                              teams=[team_label(t) for t in teams.values()], rules=rules, scoring_format=format)
        # Import slots and reception weighting. Do not imply that custom scoring was imported.
        result.warnings.append('Starter slots and PPR format imported. Projections use this app’s scoring rules; league-specific bonuses, yardage, touchdown, kicking, and D/ST settings are not imported. Review scoring before using the estimate.')
        if request.team_id is None:
            return result
        if request.team_id not in teams:
            raise ValueError('Selected team was not found in this league.')
        result.selected_team = team_label(teams[request.team_id])
        periods = settings['scheduleSettings']['matchupPeriods']
        matching_periods = [int(period) for period, weeks in periods.items() if request.week in weeks]
        if len(matching_periods) != 1:
            raise ValueError('No unique league matchup period covers this NFL week.')
        period = matching_periods[0]
        if len(periods[str(period)]) != 1:
            raise ValueError('Multi-week fantasy matchups are not supported by this weekly optimizer.')
        matches = [m for m in data.get('schedule', []) if m.get('matchupPeriodId') == period and request.team_id in
                   (m.get('home', {}).get('teamId'), m.get('away', {}).get('teamId'))]
        if len(matches) > 1:
            raise ValueError('Multiple opponents are scheduled; this app supports one opponent per week.')
        opponent_id = None
        if matches:
            match = matches[0]
            opponent_id = match.get('away' if match.get('home', {}).get('teamId') == request.team_id else 'home', {}).get('teamId')
        if opponent_id is not None:
            if opponent_id not in teams or opponent_id == request.team_id:
                raise ValueError('ESPN returned an invalid opponent.')
            result.opponent = team_label(teams[opponent_id])
        else:
            result.warnings.append('No opponent is scheduled for this week (a bye or unpublished schedule). Opponent starters have been cleared.')
        if catalog is None:
            raise ValueError('Player catalog is required to import rosters.')
        lookup = {p.espn_id: p for p in catalog.players if p.espn_id}
        def roster_ids(team_id, starters_only):
            roster = teams[team_id].get('roster', {}).get('entries')
            if not isinstance(roster, list):
                raise ValueError('ESPN did not provide this team’s roster for the requested week.')
            ids = []
            for row in roster:
                slot = row['lineupSlotId']
                if starters_only and slot in BENCH:
                    continue
                pid = str(row['playerId'])
                player = lookup.get(pid)
                label = row.get('playerPoolEntry', {}).get('player', {}).get('fullName', f'ESPN player {pid}')
                if player is None:
                    result.warnings.append(f'{label}: not found in the app catalog; add a replacement manually.')
                    continue
                if player.player.player_id in ids:
                    raise ValueError('ESPN returned a duplicate roster entry.')
                ids.append(player.player.player_id)
                if not player.eligible:
                    result.warnings.append(f'{label}: currently unavailable or missing a projection. Review before optimizing.')
            return ids
        result.your_player_ids = roster_ids(request.team_id, False)
        result.opponent_player_ids = roster_ids(opponent_id, True) if opponent_id is not None else []
        if len(result.your_player_ids) > 30 or len(result.opponent_player_ids) > 16:
            raise ValueError('This league roster exceeds the app’s supported size.')
        if set(result.your_player_ids) & set(result.opponent_player_ids):
            raise ValueError('A player appears on both teams; this league format is unsupported.')
        result.warnings.append('Opponent starters reflect ESPN’s submitted lineup for this week. Empty slots and later lineup changes require a refresh.')
        return result
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError('ESPN league data is incomplete or has an unsupported structure.') from exc
