from datetime import datetime, timezone
from dataclasses import replace
import pytest
from app.providers.espn_projections import WeeklyProjection, ProjectionSnapshot, parse_projections
from app.providers.kickers import parse_kickers
from app.providers.rosters import RosterPlayer, CurrentRoster, parse_roster, with_defenses
from app.providers.weekly import WeeklySnapshot
from app.schemas.nfl import NflContext
from app.schemas.scoring import ScoringFormat
from app.services.current_season import current_catalog
from app.services.workload import apply_weekly
from app.services.lineup_generator import generate_legal_lineups
from app.services.projection import build_distribution
from app.services.optimizer import optimize_lineup
from app.core.roster_rules import RosterRules

NOW = datetime.now(timezone.utc)
@pytest.mark.parametrize('scoring', list(ScoringFormat))
def test_kicker_scoring_independent_of_ppr(scoring):
    assert WeeklyProjection('1','K',{'80':1,'77':1,'74':1,'86':2,'85':1,'88':1}).points(scoring) == 12
@pytest.mark.parametrize('scoring', list(ScoringFormat))
def test_defense_scores_bands_and_total_tds_once(scoring):
    stats={'99':2,'95':1,'96':1,'97':1,'98':1,'105':1,'94':1,'103':1,'89':.5,'125':.5,'120':23}
    assert WeeklyProjection('-16001','DST',stats).points(scoring) == 19

def test_rookie_and_unsigned_kickers_are_visible_but_only_available_can_start():
    csv='season,gsis_id,full_name,position,team,years_exp,status,espn_id\n2026,r,Rookie,K,CIN,0,ACT,1\n2026,f,Free Agent,K,BUF,2,CUT,2\n2026,p,Practice,K,BUF,0,DEV,3'
    roster=CurrentRoster(parse_roster(csv,2026),NOW,'roster')
    forecasts=ProjectionSnapshot({str(i):WeeklyProjection(str(i),'K',{'80':2}) for i in range(1,4)},NOW,'espn')
    baseline=current_catalog(roster,[],NflContext(season=2026,target_week=1),forecasts)
    weekly=WeeklySnapshot(2026,1,NOW,1,True,playing_teams=frozenset({'CIN','BUF'}))
    catalog=apply_weekly(baseline,roster,[],weekly)
    entries={p.player.player_id:p for p in catalog.players}
    assert entries['r'].is_rookie and entries['r'].eligible and entries['r'].projected_points==6
    assert entries['f'].availability=='free_agent' and not entries['f'].eligible
    assert entries['p'].availability=='practice_squad' and not entries['p'].eligible
    bye=apply_weekly(baseline,roster,[],replace(weekly,playing_teams=frozenset()))
    assert not next(p for p in bye.players if p.player.player_id=='r').eligible

def test_kicker_discovery_includes_free_agents_and_stable_ids():
    players=parse_kickers({'players':[{'player':{'id':123,'fullName':'Unsigned K','defaultPositionId':5,'proTeamId':0}}]})
    assert players[0].team=='FA' and players[0].player_id=='espn:123'
    assert len(with_defenses(CurrentRoster((),NOW,'r')).players)==32

def test_special_slots_serialize_and_cannot_fill_flex():
    from app.services.special_teams import special_entry
    roster=CurrentRoster((RosterPlayer('k','Kicker','K','CIN','1'),RosterPlayer('d','Defense','DST','BUF','-16002')),NOW,'r')
    forecasts=ProjectionSnapshot({'1':WeeklyProjection('1','K',{'80':2}),'-16002':WeeklyProjection('-16002','DST',{'99':2})},NOW,'e')
    players=[build_distribution(special_entry(p,NflContext(season=2026,target_week=1),forecasts).player) for p in roster.players]
    rules=RosterRules(qb=0,rb=0,wr=0,te=0,flex=0,k=1,dst=1)
    assert len(generate_legal_lineups(players,rules))==1
    result,_=optimize_lineup(players,[],rules,500,42)
    assert [p.slot for p in result[0].starters]==['K','DST']
    with pytest.raises(ValueError):generate_legal_lineups(players,replace(rules,flex=1))

def test_negative_defense_id_and_exact_week():
    record={'seasonId':2026,'scoringPeriodId':1,'statSourceId':1,'statSplitTypeId':1,'stats':{'99':2}}
    payload={'players':[{'player':{'id':-16001,'defaultPositionId':16,'stats':[record]}}]}
    assert '-16001' in parse_projections(payload,2026,1)
    assert not parse_projections(payload,2026,2)
