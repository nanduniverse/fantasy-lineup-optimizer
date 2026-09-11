from copy import deepcopy
from datetime import datetime, timezone
import httpx
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.providers.leagues import fetch_league
from app.providers.nflverse import ProviderError
from app.schemas.league import LeagueRequest
from app.schemas.nfl import NflCatalog, NflPlayer
from app.schemas.player import PlayerInput
from app.services.league_import import parse_league


def fixture():
    def team(id, name, players):
        return {'id':id,'name':name,'roster':{'entries':[{'playerId':pid,'lineupSlotId':slot,'playerPoolEntry':{'player':{'fullName':f'Player {pid}'}}} for pid,slot in players]}}
    return {'id':123,'seasonId':2026,'settings':{'name':'Test league','rosterSettings':{'lineupSlotCounts':{'0':1,'17':1,'16':1,'20':3,'21':1}},'scoringSettings':{'scoringItems':[{'statId':53,'points':.5}]},'scheduleSettings':{'matchupPeriods':{'1':[1],'2':[2]}}},
            'teams':[team(1,'My Team',[(1,0),(2,17),(-16001,16),(3,20)]),team(2,'Week One',[(4,0),(5,17),(-16002,16),(6,20)]),team(3,'Week Two',[(7,0),(8,17),(-16003,16)])],
            'schedule':[{'matchupPeriodId':1,'home':{'teamId':1},'away':{'teamId':2}},{'matchupPeriodId':2,'home':{'teamId':3},'away':{'teamId':1}}]}

def catalog():
    return NflCatalog(season=2026,target_week=1,scoring_format='half_ppr',source='test',source_url='test',fetched_at=datetime.now(timezone.utc),available_through_week=None,warnings=[],players=[NflPlayer(player=PlayerInput(player_id=f'p{pid}',name=f'Player {pid}',position='QB',season_average=10),espn_id=str(pid),team='BUF',games_played=1,last_played_week=1) for pid in [1,2,3,4,5,6,7,8,-16001,-16002,-16003]])

def test_list_teams_without_catalog_or_names_as_ids():
    result=parse_league(fixture(),LeagueRequest(league_id='123',week=1))
    assert [t.name for t in result.teams]==['My Team','Week One','Week Two']
    assert result.rules.k==result.rules.dst==result.rules.qb==1
    assert result.rules.rb==0 and result.scoring_format=='half_ppr'

@pytest.mark.parametrize('week,opponent,ids',[(1,2,['p4','p5','p-16002']),(2,3,['p7','p8','p-16003'])])
def test_full_roster_opponent_starters_and_week(week,opponent,ids):
    result=parse_league(fixture(),LeagueRequest(league_id='123',week=week,team_id=1),catalog())
    assert result.opponent.id==opponent
    assert result.your_player_ids==['p1','p2','p-16001','p3']
    assert result.opponent_player_ids==ids

def test_missing_player_reported_without_name_guessing():
    data=catalog();data.players=[p for p in data.players if p.espn_id!='4']
    result=parse_league(fixture(),LeagueRequest(league_id='123',week=1,team_id=1),data)
    assert any('Player 4: not found' in w for w in result.warnings)
    assert len(result.opponent_player_ids)==2

def test_bye_clears_opponent():
    data=fixture();data['schedule'][0].pop('away')
    result=parse_league(data,LeagueRequest(league_id='123',week=1,team_id=1),catalog())
    assert result.opponent is None and result.opponent_player_ids==[]

@pytest.mark.parametrize('change',[lambda d:d.update(seasonId=2025),lambda d:d['settings']['rosterSettings']['lineupSlotCounts'].update({'7':1}),lambda d:d['settings']['scheduleSettings']['matchupPeriods'].update({'1':[1,2]}),lambda d:d['teams'][1].pop('roster')])
def test_unsupported_or_incomplete_data_rejected(change):
    data=fixture();change(data)
    with pytest.raises(ValueError):parse_league(data,LeagueRequest(league_id='123',week=1,team_id=1),catalog())

def test_provider_fixed_host_week_and_request_scoped_auth():
    requests=[]
    def handle(request):
        requests.append(request)
        return httpx.Response(200,json=fixture())
    transport=httpx.MockTransport(handle)
    fetch_league(LeagueRequest(league_id='123',week=2,espn_s2='secret',swid='{id}'),transport)
    fetch_league(LeagueRequest(league_id='123',week=1),transport)
    assert requests[0].url.host=='lm-api-reads.fantasy.espn.com'
    assert requests[0].url.params['scoringPeriodId']=='2'
    assert 'espn_s2=secret' in requests[0].headers['cookie']
    assert 'cookie' not in requests[1].headers

@pytest.mark.parametrize('code',[401,403,404,500])
def test_provider_access_failures(code):
    with pytest.raises(ProviderError):fetch_league(LeagueRequest(league_id='123',week=1),httpx.MockTransport(lambda _:httpx.Response(code)))

def test_validation_never_echoes_authentication():
    response=TestClient(app).post('/api/leagues/espn/import',json={'league_id':'123','week':1,'espn_s2':'secret;bad'})
    assert response.status_code==422
    assert 'secret' not in response.text and 'input' not in response.text

def test_import_endpoint_applies_league_context(monkeypatch):
    from app.api.routes import leagues
    monkeypatch.setattr(leagues,'fetch_league',lambda _:fixture())
    contexts=[]
    def current(context):
        contexts.append(context)
        return catalog()
    monkeypatch.setattr(leagues,'current_catalog_for',current)
    response=TestClient(app).post('/api/leagues/espn/import',json={'league_id':'123','week':2,'team_id':1})
    assert response.status_code==200
    assert response.json()['opponent']['id']==3
    assert contexts[0].target_week==2 and contexts[0].scoring_format=='half_ppr'
    assert 'espn_s2' not in response.text

def test_wrong_scoring_week_rejected():
    data=fixture();data['scoringPeriodId']=2
    with pytest.raises(ValueError):parse_league(data,LeagueRequest(league_id='123',week=1))
